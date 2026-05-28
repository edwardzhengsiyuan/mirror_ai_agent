"""Endpoint tests for the Phase 1 email + password auth surface.

Covers /v1/auth/register, /v1/auth/login, /v1/auth/logout, GET /v1/me,
POST /v1/me/api_key/rotate, POST /v1/me/password, and the underlying
``@login_required`` cookie session machinery.

The fixtures here are deliberately independent from ``test_endpoint_billing``
so the auth tests can run in isolation and so a regression in either suite
doesn't mask the other.
"""

from __future__ import annotations

import os
import sys
import time
from typing import Any, Dict

import pytest

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, ROOT)

from agent.auth.sessions import SessionManager
from web_server import create_app


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setenv("BILLING_DB_PATH", str(tmp_path / "billing.db"))
    monkeypatch.setenv("BILLING_RATE_LIMIT_PER_MIN", "1000")
    # Stable secret for the test so cookies survive across test_client calls
    # within a single test (Flask's test client preserves them automatically,
    # but signing also requires a stable secret).
    monkeypatch.setenv("APP_SECRET_KEY", "test-secret-do-not-use-in-prod")
    # Allow non-HTTPS test cookies — Werkzeug's test client never sets
    # Secure cookies on, but our SessionManager would emit Secure=True by
    # default which is harmless for the test client; we still flip it off
    # to mirror how dev would run locally.
    monkeypatch.setenv("APP_COOKIE_SECURE", "0")
    return create_app(storage_root=str(tmp_path / "storage"))


@pytest.fixture
def client(app):
    return app.test_client()


def _register(client, email="alice@example.com", password="hunter22!", **extra) -> Dict[str, Any]:
    body = {"email": email, "password": password}
    body.update(extra)
    resp = client.post("/v1/auth/register", json=body)
    assert resp.status_code == 201, resp.get_json()
    return resp.get_json()


# ---------------------------------------------------------------------------
# /v1/auth/register
# ---------------------------------------------------------------------------


def test_register_success_sets_session_and_returns_user_with_api_key(client) -> None:
    resp = client.post(
        "/v1/auth/register",
        json={"email": "alice@example.com", "password": "hunter22!", "display_name": "Alice"},
    )
    assert resp.status_code == 201, resp.get_json()
    body = resp.get_json()
    assert body["user"]["email"] == "alice@example.com"
    assert body["user"]["display_name"] == "Alice"
    assert body["user"]["balance_credits"] == 0
    assert body["user"]["user_id"].startswith("u_")
    # Plaintext key is shown once at registration; dashboard relies on it.
    assert body["api_key"]["has_active_key"] is True
    assert body["api_key"]["plaintext"]
    assert isinstance(body["api_key"]["plaintext"], str)
    # Session cookie should be present on the response.
    cookie_header = resp.headers.get("Set-Cookie", "")
    assert "mirror_session=" in cookie_header
    assert "HttpOnly" in cookie_header


def test_register_lowercases_and_trims_email(client) -> None:
    body = _register(client, email="  Alice@Example.COM ")
    assert body["user"]["email"] == "alice@example.com"


@pytest.mark.parametrize(
    "email",
    [
        "",
        "  ",
        "not-an-email",
        "missing-at.com",
        "no-tld@local",
        "spaces in@example.com",
    ],
)
def test_register_rejects_invalid_email(client, email) -> None:
    resp = client.post(
        "/v1/auth/register",
        json={"email": email, "password": "hunter22!"},
    )
    assert resp.status_code == 400
    assert resp.get_json()["error"]["code"] == "invalid_email"


@pytest.mark.parametrize("password", ["", "short", "1234567"])
def test_register_rejects_weak_password(client, password) -> None:
    resp = client.post(
        "/v1/auth/register",
        json={"email": "bob@example.com", "password": password},
    )
    assert resp.status_code == 400
    assert resp.get_json()["error"]["code"] == "weak_password"


def test_register_rejects_duplicate_email(client) -> None:
    _register(client, email="dup@example.com")
    resp = client.post(
        "/v1/auth/register",
        json={"email": "dup@example.com", "password": "hunter22!"},
    )
    assert resp.status_code == 409
    assert resp.get_json()["error"]["code"] == "email_taken"


def test_register_honors_register_initial_credits_env(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("BILLING_DB_PATH", str(tmp_path / "billing.db"))
    monkeypatch.setenv("APP_SECRET_KEY", "test-secret-do-not-use-in-prod")
    monkeypatch.setenv("APP_COOKIE_SECURE", "0")
    monkeypatch.setenv("REGISTER_INITIAL_CREDITS", "50")
    app = create_app(storage_root=str(tmp_path / "storage"))
    client = app.test_client()
    resp = client.post(
        "/v1/auth/register",
        json={"email": "starter@example.com", "password": "hunter22!"},
    )
    assert resp.status_code == 201, resp.get_json()
    assert resp.get_json()["user"]["balance_credits"] == 50


# ---------------------------------------------------------------------------
# /v1/auth/login
# ---------------------------------------------------------------------------


def test_login_success_sets_session(client) -> None:
    _register(client, email="login@example.com", password="hunter22!")
    # Clear cookies between register and login so we can observe a fresh
    # Set-Cookie on the login response.
    client.delete_cookie("mirror_session", domain="localhost")
    resp = client.post(
        "/v1/auth/login",
        json={"email": "login@example.com", "password": "hunter22!"},
    )
    assert resp.status_code == 200, resp.get_json()
    body = resp.get_json()
    assert body["user"]["email"] == "login@example.com"
    cookie_header = resp.headers.get("Set-Cookie", "")
    assert "mirror_session=" in cookie_header


def test_login_wrong_password_returns_401(client) -> None:
    _register(client, email="wrong@example.com", password="hunter22!")
    client.delete_cookie("mirror_session", domain="localhost")
    resp = client.post(
        "/v1/auth/login",
        json={"email": "wrong@example.com", "password": "wrongpassword"},
    )
    assert resp.status_code == 401
    assert resp.get_json()["error"]["code"] == "invalid_credentials"


def test_login_unknown_email_returns_401(client) -> None:
    resp = client.post(
        "/v1/auth/login",
        json={"email": "ghost@example.com", "password": "hunter22!"},
    )
    assert resp.status_code == 401
    assert resp.get_json()["error"]["code"] == "invalid_credentials"


def test_login_disabled_user_returns_403(client, app) -> None:
    body = _register(client, email="disabled@example.com", password="hunter22!")
    user_id = body["user"]["user_id"]
    # Reach into the billing store to disable the user; this is the same path
    # an admin would take via /admin/users/<id>/status.
    store = app.extensions["auth_session_manager"]  # noqa: F841 (just to confirm install)
    from agent.billing import BillingStore  # local import to avoid top-level cycle
    bs = BillingStore(os.environ["BILLING_DB_PATH"])
    bs.set_user_status(user_id, "disabled")
    client.delete_cookie("mirror_session", domain="localhost")
    resp = client.post(
        "/v1/auth/login",
        json={"email": "disabled@example.com", "password": "hunter22!"},
    )
    assert resp.status_code == 403
    assert resp.get_json()["error"]["code"] == "account_disabled"


def test_login_invalid_email_format_returns_401_not_400(client) -> None:
    # /login deliberately surfaces 401 with invalid_credentials regardless of
    # whether the failure is "bad email shape" or "wrong password", to avoid
    # leaking whether a given email exists.
    resp = client.post(
        "/v1/auth/login",
        json={"email": "not-an-email", "password": "hunter22!"},
    )
    assert resp.status_code == 401
    assert resp.get_json()["error"]["code"] == "invalid_credentials"


# ---------------------------------------------------------------------------
# /v1/auth/logout
# ---------------------------------------------------------------------------


def test_logout_clears_cookie_and_subsequent_me_returns_401(client) -> None:
    _register(client, email="logout@example.com", password="hunter22!")
    # Confirm we're logged in.
    me = client.get("/v1/me")
    assert me.status_code == 200
    # Log out.
    resp = client.post("/v1/auth/logout")
    assert resp.status_code == 200
    set_cookie = resp.headers.get("Set-Cookie", "")
    assert "mirror_session=" in set_cookie
    # max-age=0 OR expires=Thu, 01 Jan 1970 — Werkzeug uses Expires.
    assert "Max-Age=0" in set_cookie or "Expires=Thu, 01 Jan 1970" in set_cookie
    # /me is now unauthorised.
    me2 = client.get("/v1/me")
    assert me2.status_code == 401


# ---------------------------------------------------------------------------
# GET /v1/me + cookie validity
# ---------------------------------------------------------------------------


def test_me_without_cookie_returns_401(client) -> None:
    resp = client.get("/v1/me")
    assert resp.status_code == 401
    assert resp.get_json()["error"]["code"] == "unauthorized"


def test_me_after_register_returns_full_profile(client) -> None:
    reg = _register(client, email="me@example.com", password="hunter22!", display_name="Me")
    resp = client.get("/v1/me")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["user"]["email"] == "me@example.com"
    assert body["user"]["display_name"] == "Me"
    # Plaintext key matches what was returned at registration time.
    assert body["api_key"]["plaintext"] == reg["api_key"]["plaintext"]
    assert body["api_key"]["has_active_key"] is True


def test_me_with_tampered_cookie_returns_401(client) -> None:
    _register(client, email="tamper@example.com", password="hunter22!")
    # Werkzeug test client stores cookies on its client.session_transaction;
    # the simplest tamper is to overwrite the cookie with garbage.
    client.set_cookie("mirror_session", "obviously.not.a.signed.token", domain="localhost")
    resp = client.get("/v1/me")
    assert resp.status_code == 401


def test_me_with_expired_cookie_returns_401() -> None:
    # Unit-level: SessionManager.load returns None for an expired token.
    # itsdangerous truncates the embedded issue time to whole seconds and
    # treats ``age > max_age`` as expired, so with max_age=1 we need at
    # least ~2 wall-clock seconds elapsed to be sure the check fires.
    sm = SessionManager(secret_key="k", max_age_seconds=1, cookie_secure=False)
    token = sm.sign("u_alice")
    assert sm.load(token) == "u_alice"
    time.sleep(2.2)
    assert sm.load(token) is None


def test_session_manager_rejects_signature_swap() -> None:
    """A token signed by manager A must not validate under manager B."""
    a = SessionManager(secret_key="key-a", cookie_secure=False)
    b = SessionManager(secret_key="key-b", cookie_secure=False)
    token = a.sign("u_alice")
    assert b.load(token) is None


def test_session_manager_loads_valid_token() -> None:
    sm = SessionManager(secret_key="k", cookie_secure=False)
    assert sm.load(sm.sign("u_bob")) == "u_bob"
    assert sm.load("") is None
    assert sm.load("not.a.token") is None


# ---------------------------------------------------------------------------
# /v1/me/api_key/rotate
# ---------------------------------------------------------------------------


def test_rotate_api_key_issues_new_and_revokes_old(client) -> None:
    reg = _register(client, email="rotate@example.com", password="hunter22!")
    old_key = reg["api_key"]["plaintext"]
    resp = client.post("/v1/me/api_key/rotate")
    assert resp.status_code == 200, resp.get_json()
    body = resp.get_json()
    new_key = body["new_api_key"]
    assert new_key
    assert new_key != old_key
    # The "current" api_key block now shows the new plaintext.
    assert body["api_key"]["plaintext"] == new_key
    # Subsequent /me returns the new key too.
    me = client.get("/v1/me")
    assert me.get_json()["api_key"]["plaintext"] == new_key

    # The old key must no longer authenticate against billed endpoints.
    resp = client.get("/v1/balance", headers={"Authorization": f"Bearer {old_key}"})
    assert resp.status_code == 401
    # The new key must.
    resp = client.get("/v1/balance", headers={"Authorization": f"Bearer {new_key}"})
    assert resp.status_code == 200


def test_rotate_api_key_requires_login(client) -> None:
    resp = client.post("/v1/me/api_key/rotate")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# /v1/me/password
# ---------------------------------------------------------------------------


def test_change_password_success(client) -> None:
    _register(client, email="pw@example.com", password="oldpassword1")
    resp = client.post(
        "/v1/me/password",
        json={"old_password": "oldpassword1", "new_password": "newpassword2"},
    )
    assert resp.status_code == 200, resp.get_json()
    # Old password no longer works.
    client.delete_cookie("mirror_session", domain="localhost")
    bad = client.post(
        "/v1/auth/login",
        json={"email": "pw@example.com", "password": "oldpassword1"},
    )
    assert bad.status_code == 401
    # New password does work.
    good = client.post(
        "/v1/auth/login",
        json={"email": "pw@example.com", "password": "newpassword2"},
    )
    assert good.status_code == 200


def test_change_password_wrong_old_returns_401(client) -> None:
    _register(client, email="pw2@example.com", password="oldpassword1")
    resp = client.post(
        "/v1/me/password",
        json={"old_password": "totally-wrong", "new_password": "newpassword2"},
    )
    assert resp.status_code == 401
    assert resp.get_json()["error"]["code"] == "invalid_credentials"


def test_change_password_weak_new_returns_400(client) -> None:
    _register(client, email="pw3@example.com", password="oldpassword1")
    resp = client.post(
        "/v1/me/password",
        json={"old_password": "oldpassword1", "new_password": "short"},
    )
    assert resp.status_code == 400
    assert resp.get_json()["error"]["code"] == "weak_password"


def test_change_password_requires_login(client) -> None:
    resp = client.post(
        "/v1/me/password",
        json={"old_password": "x", "new_password": "y"},
    )
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Backward compatibility: /v1/register still works the old way
# ---------------------------------------------------------------------------


def test_legacy_v1_register_still_returns_one_time_key(client) -> None:
    """The pre-auth /v1/register endpoint must remain usable for curl users."""
    resp = client.post("/v1/register", json={"display_name": "Legacy"})
    assert resp.status_code == 200, resp.get_json()
    body = resp.get_json()
    assert body["user"]["user_id"].startswith("u_")
    assert body["user"]["email"] is None  # legacy path doesn't take an email
    assert body["api_key"]
    # The legacy plaintext is NOT stored on the row, so /v1/me would not be
    # reachable without a session anyway. That's fine: legacy is curl-only.


# ---------------------------------------------------------------------------
# clean URLs (the dashboard pages must be reachable without ``.html``)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "path,expected_marker",
    [
        ("/", b"Mirror AI"),  # landing
        ("/login", b"id=\"login-form\""),
        ("/register", b"id=\"register-form\""),
        ("/dashboard", b"id=\"hello\""),
        ("/billing", b"id=\"pack-grid\""),
        ("/docs", b"Quickstart"),
    ],
)
def test_portal_clean_urls_serve_html(client, path, expected_marker) -> None:
    resp = client.get(path)
    assert resp.status_code == 200, path
    # Sanity check the right HTML was served by looking for a unique marker.
    assert expected_marker in resp.data, f"{path} returned unexpected body"
