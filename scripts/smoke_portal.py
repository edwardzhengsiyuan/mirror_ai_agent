"""End-to-end smoke for the developer-portal auth + dashboard flow.

Walks a freshly-spawned ``web_server`` test client through every step a real
partner developer would take:

    1. POST /v1/auth/register      (email + password, returns api_key)
    2. GET  /v1/me                 (verify cookie session works)
    3. GET  /v1/balance            (verify Bearer api_key works on a billed
                                    endpoint's auth gate)
    4. POST /v1/me/api_key/rotate  (key is replaced; old key returns 401)
    5. GET  /v1/usage              (uses the rotated key)
    6. POST /v1/me/password        (change + re-login with new password)
    7. POST /v1/auth/logout        (cookie cleared, /v1/me → 401)

Run from the repo root:

    .venv/Scripts/python.exe scripts/smoke_portal.py

Or against a live server (uses real HTTP instead of the Flask test client):

    BASE_URL=http://localhost:8000 .venv/Scripts/python.exe scripts/smoke_portal.py

Exits non-zero on the first failed assertion so a CI hook can pick it up.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import uuid

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

# Windows shells default to cp936/gbk and crash on non-ASCII output. Force
# UTF-8 if the stream supports reconfigure() (Python 3.7+).
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except Exception:
        pass


def _green(s: str) -> str:
    return f"\033[32m{s}\033[0m"


def _red(s: str) -> str:
    return f"\033[31m{s}\033[0m"


def _step(n: int, label: str) -> None:
    print(f"\n[{n}] {label}")


def _ok(msg: str) -> None:
    print("    " + _green("[ok] " + msg))


def _fail(msg: str) -> None:
    print("    " + _red("[FAIL] " + msg))
    sys.exit(1)


# ---------------------------------------------------------------------------
# Two transport adapters: in-process test client and real HTTP via requests.
# Both expose a tiny .request(method, path, **kwargs) → (status, json, set_cookie)
# interface so the smoke logic below is shared.
# ---------------------------------------------------------------------------


class FlaskClientAdapter:
    """Use Flask's test client — no network, but exercises full create_app()."""

    def __init__(self) -> None:
        # Isolated tmp dir so we don't pollute the repo's billing.db / storage.
        # ignore_cleanup_errors=True because SQLite's WAL/SHM files can linger
        # in the file table on Windows even after the connection is closed; we
        # don't care because the OS reaps the tempdir eventually.
        try:
            self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        except TypeError:
            # Older Pythons (< 3.10) don't accept ignore_cleanup_errors=.
            self.tmp = tempfile.TemporaryDirectory()
        os.environ["BILLING_DB_PATH"] = os.path.join(self.tmp.name, "billing.db")
        os.environ["APP_SECRET_KEY"] = "smoke-secret"
        os.environ["APP_COOKIE_SECURE"] = "0"
        os.environ.setdefault("BILLING_RATE_LIMIT_PER_MIN", "1000")
        from web_server import create_app

        self.app = create_app(storage_root=os.path.join(self.tmp.name, "storage"))
        self.client = self.app.test_client()

    def request(self, method, path, json_body=None, bearer=None):
        kwargs = {}
        if json_body is not None:
            kwargs["json"] = json_body
        if bearer:
            kwargs["headers"] = {"Authorization": "Bearer " + bearer}
        resp = self.client.open(path, method=method, **kwargs)
        body = None
        try:
            body = resp.get_json()
        except Exception:
            body = None
        return resp.status_code, body

    def close(self):
        self.tmp.cleanup()


class HttpAdapter:
    """Talk to a real running ``web_server`` over HTTP via the ``requests`` lib."""

    def __init__(self, base_url: str) -> None:
        import requests

        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()

    def request(self, method, path, json_body=None, bearer=None):
        url = self.base_url + path
        kwargs = {"timeout": 30}
        if json_body is not None:
            kwargs["json"] = json_body
        if bearer:
            kwargs["headers"] = {"Authorization": "Bearer " + bearer}
        resp = self.session.request(method, url, **kwargs)
        body = None
        try:
            body = resp.json()
        except Exception:
            body = None
        return resp.status_code, body

    def close(self):
        self.session.close()


def make_adapter():
    base = os.environ.get("BASE_URL")
    if base:
        print(f"using HTTP adapter against {base}")
        return HttpAdapter(base)
    print("using in-process Flask test client")
    return FlaskClientAdapter()


def main() -> None:
    adapter = make_adapter()
    try:
        run(adapter)
    finally:
        adapter.close()


def run(adapter) -> None:
    suffix = uuid.uuid4().hex[:6]
    email = f"smoke-{suffix}@example.com"
    pw_old = "smoke-pass-1"
    pw_new = "smoke-pass-2"

    # ---- 1. register ------------------------------------------------------
    _step(1, "POST /v1/auth/register")
    status, body = adapter.request(
        "POST",
        "/v1/auth/register",
        json_body={"email": email, "password": pw_old, "display_name": "Smoke Test"},
    )
    if status != 201:
        _fail(f"expected 201, got {status} {body}")
    if not body["api_key"]["plaintext"]:
        _fail("api_key.plaintext missing in register response")
    api_key_v1 = body["api_key"]["plaintext"]
    user_id = body["user"]["user_id"]
    _ok(f"user_id={user_id} email={email}")
    _ok(f"api key v1: {api_key_v1[:8]}…")

    # ---- 2. /v1/me --------------------------------------------------------
    _step(2, "GET /v1/me")
    status, body = adapter.request("GET", "/v1/me")
    if status != 200:
        _fail(f"/v1/me returned {status}")
    if body["user"]["email"] != email:
        _fail("/v1/me returned wrong email")
    if body["api_key"]["plaintext"] != api_key_v1:
        _fail("/v1/me returned different api_key plaintext than register")
    _ok("session cookie + plaintext key roundtrip OK")

    # ---- 3. /v1/balance (Bearer auth, exercises the api_key path) --------
    _step(3, "GET /v1/balance (Bearer api_key)")
    status, body = adapter.request("GET", "/v1/balance", bearer=api_key_v1)
    if status != 200:
        _fail(f"/v1/balance returned {status} {body}")
    if body.get("balance_credits") != 0:
        _fail(f"expected balance 0, got {body.get('balance_credits')}")
    _ok("Bearer api_key authenticates and balance==0")

    # ---- 4. rotate api_key ------------------------------------------------
    _step(4, "POST /v1/me/api_key/rotate")
    status, body = adapter.request("POST", "/v1/me/api_key/rotate")
    if status != 200:
        _fail(f"rotate returned {status}")
    api_key_v2 = body["new_api_key"]
    if not api_key_v2 or api_key_v2 == api_key_v1:
        _fail("new_api_key missing or unchanged after rotate")
    _ok(f"new api key v2: {api_key_v2[:8]}…")

    # Old key must now be revoked.
    status, _ = adapter.request("GET", "/v1/balance", bearer=api_key_v1)
    if status != 401:
        _fail(f"old key still works (status={status}); rotate did not revoke")
    _ok("old api_key rejected with 401 after rotate")

    # New key must work.
    status, _ = adapter.request("GET", "/v1/balance", bearer=api_key_v2)
    if status != 200:
        _fail(f"new key returned {status}")
    _ok("new api_key works against /v1/balance")

    # ---- 5. usage (no rows yet, but endpoint should return 200) ----------
    _step(5, "GET /v1/usage (rotated key)")
    status, body = adapter.request("GET", "/v1/usage?limit=10", bearer=api_key_v2)
    if status != 200:
        _fail(f"/v1/usage returned {status}")
    if not isinstance(body.get("rows"), list):
        _fail("/v1/usage missing rows")
    _ok(f"usage returns {len(body['rows'])} rows")

    # ---- 6. password change + re-login -----------------------------------
    _step(6, "POST /v1/me/password + relog with new password")
    status, _ = adapter.request(
        "POST",
        "/v1/me/password",
        json_body={"old_password": pw_old, "new_password": pw_new},
    )
    if status != 200:
        _fail(f"change-password returned {status}")
    _ok("password change accepted")

    # logout, then login with new password
    adapter.request("POST", "/v1/auth/logout")
    status, _ = adapter.request(
        "POST",
        "/v1/auth/login",
        json_body={"email": email, "password": pw_old},
    )
    if status != 401:
        _fail(f"old password still works after change (status={status})")
    status, _ = adapter.request(
        "POST",
        "/v1/auth/login",
        json_body={"email": email, "password": pw_new},
    )
    if status != 200:
        _fail(f"re-login with new password returned {status}")
    _ok("login with new password works; old password rejected")

    # ---- 7. logout & /me 401 ---------------------------------------------
    _step(7, "POST /v1/auth/logout")
    status, _ = adapter.request("POST", "/v1/auth/logout")
    if status != 200:
        _fail(f"logout returned {status}")
    status, _ = adapter.request("GET", "/v1/me")
    if status != 401:
        _fail(f"/v1/me still works after logout (status={status})")
    _ok("session cleared; /v1/me unauthorised")

    print("\n" + _green("All smoke checks passed."))


if __name__ == "__main__":
    main()
