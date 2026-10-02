"""Exercise the disposable local HTTPS stack. Never targets production hosts."""
import argparse
import hashlib
import hmac
import json
from pathlib import Path
import time
import uuid

import requests


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ca", required=True, type=Path)
    args = parser.parse_args(argv)
    base = "https://localhost:18443"
    client = requests.Session()
    client.trust_env = False
    client.verify = str(args.ca)
    def call(method, path, **kwargs):
        return client.request(method, base + path, timeout=120, **kwargs)
    assert call("GET", "/health").status_code == 200
    credentials = {"email": f"audit-{uuid.uuid4().hex}@example.invalid", "password": uuid.uuid4().hex}
    response = call("POST", "/v1/auth/register", json=credentials)
    assert response.status_code == 201, response.text
    cookie = response.headers["Set-Cookie"]
    assert "Secure" in cookie and "HttpOnly" in cookie and "SameSite=Lax" in cookie
    user = response.json()["user"]["user_id"]
    key = response.json()["api_key"]["plaintext"]
    copied_cookie = client.cookies.get("mirror_session")
    headers = {"Authorization": "Bearer " + key}
    balance = call("GET", "/v1/balance", headers=headers).json()["balance_credits"]
    event = {"id": "evt_audit_" + uuid.uuid4().hex, "object": "event", "type": "checkout.session.completed",
             "data": {"object": {"id": "cs_audit_" + uuid.uuid4().hex, "object": "checkout.session",
                                   "payment_status": "paid", "amount_total": 1000, "currency": "cny", "client_reference_id": user,
                                   "metadata": {"user_id": user, "credits": "1000"}}}}
    body = json.dumps(event).encode()
    timestamp = str(int(time.time()))
    signature = hmac.new(b"whsec_audit_only", timestamp.encode() + b"." + body, hashlib.sha256).hexdigest()
    webhook_headers = {"Stripe-Signature": f"t={timestamp},v1={signature}", "Content-Type": "application/json"}
    for _ in range(2):
        response = call("POST", "/webhooks/stripe", headers=webhook_headers, data=body)
        assert response.status_code == 200, response.text
    assert call("GET", "/v1/balance", headers=headers).json()["balance_credits"] == balance + 1000
    bad = call("POST", "/webhooks/stripe", data=body, headers={"Stripe-Signature": "invalid"})
    assert bad.status_code == 400
    payload = {"question": "今年事业怎么样", "birth": {"year": 1990, "month": 1, "day": 1, "hour": 8}}
    request_id = "audit-" + uuid.uuid4().hex
    response = call("POST", "/v1/ask_stream", json=payload, headers={**headers, "X-Request-Id": request_id})
    assert response.status_code == 200, response.text
    events = [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith("data: ")]
    stages = [e["stage"] for e in events if e["type"] == "billing"]
    assert stages == ["charged", "settled"], stages
    assert any(e["type"] == "answer" for e in events)
    after = call("GET", "/v1/balance", headers=headers).json()["balance_credits"]
    assert after == balance + 500
    repeated = call("POST", "/v1/ask_stream", json=payload, headers={**headers, "X-Request-Id": request_id})
    assert repeated.status_code == 409
    assert call("GET", "/v1/balance", headers=headers).json()["balance_credits"] == after
    assert call("POST", "/v1/auth/logout").status_code == 200
    replay = call("GET", "/v1/me", headers={"Cookie": "mirror_session=" + copied_cookie})
    assert replay.status_code == 401
    print(json.dumps({"tls_verified": True, "secure_cookie": True, "signed_webhook": True,
                      "webhook_replay_credited_once": True, "bad_signature_rejected": True,
                      "sse_settled": True, "duplicate_not_charged": True, "logout_replay_rejected": True,
                      "models": "stub", "payment": "synthetic signed event"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
