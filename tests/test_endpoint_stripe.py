"""End-to-end tests for the Stripe-related HTTP endpoints.

Covers ``/v1/register``, ``/v1/topup_packs``, ``/v1/checkout/create``, and
``/webhooks/stripe``. The Stripe SDK itself is stubbed where we need to
fake an external response (``Session.create``); webhook signature
verification uses a real HMAC so we exercise the genuine code path.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import sys
import time
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, ROOT)

from web_server import create_app


ADMIN_TOKEN = "admin-test-token"
WEBHOOK_SECRET = "whsec_endpoint_test"
STRIPE_SECRET = "sk_test_endpoint_dummy"


def _stub_turn(*args, **kwargs):
    sink = kwargs.get("event_sink")
    if sink:
        sink({"type": "response", "text": "stub"})
    return {"method": "stub", "response": "stub", "outputs": {}}


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setenv("DEMO_API_TOKEN", ADMIN_TOKEN)
    monkeypatch.setenv("BILLING_DB_PATH", str(tmp_path / "billing.db"))
    monkeypatch.setenv("BILLING_INFLIGHT_LIMIT", "10")
    monkeypatch.setenv("BILLING_RATE_LIMIT_PER_MIN", "10000")
    monkeypatch.setenv("STRIPE_MODE", "test")
    monkeypatch.setenv("STRIPE_SECRET_KEY_TEST", STRIPE_SECRET)
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET_TEST", WEBHOOK_SECRET)
    monkeypatch.setenv("STRIPE_PUBLISHABLE_KEY_TEST", "pk_test_dummy")
    monkeypatch.setenv("STRIPE_SUCCESS_URL", "https://example.com/billing.html?status=success&session_id={CHECKOUT_SESSION_ID}")
    monkeypatch.setenv("STRIPE_CANCEL_URL", "https://example.com/billing.html?status=cancelled")
    return create_app(
        run_turn_func=_stub_turn,
        run_hepan_turn_func=_stub_turn,
        run_cezi_turn_func=_stub_turn,
        run_najia_turn_func=_stub_turn,
        run_zwds_turn_func=_stub_turn,
        storage_root=str(tmp_path / "storage"),
    )


@pytest.fixture
def client(app):
    return app.test_client()


def _admin_headers():
    return {"Authorization": f"Bearer {ADMIN_TOKEN}"}


def _user_headers(api_key: str):
    return {"Authorization": f"Bearer {api_key}"}


def _make_user(client, user_id: str = "u_alice", credits: int = 1000) -> str:
    resp = client.post(
        "/admin/users",
        headers=_admin_headers(),
        json={
            "user_id": user_id,
            "initial_credits": credits,
        },
    )
    assert resp.status_code == 200, resp.get_json()
    return resp.get_json()["api_key"]


# ---------------------------------------------------------------------------
# /v1/register
# ---------------------------------------------------------------------------


def test_register_creates_user_with_random_id_and_zero_balance(client) -> None:
    resp = client.post("/v1/register", json={})
    assert resp.status_code == 200, resp.get_json()
    body = resp.get_json()
    assert body["user"]["user_id"].startswith("u_")
    assert len(body["user"]["user_id"]) == 10  # u_ + 8 hex
    assert body["user"]["balance_credits"] == 0
    assert isinstance(body["api_key"], str) and len(body["api_key"]) >= 30


def test_register_honors_display_name(client) -> None:
    resp = client.post("/v1/register", json={"display_name": "Bob"})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["user"]["display_name"] == "Bob"


def test_register_no_auth_required(client) -> None:
    """Important: this is a *public* endpoint. No bearer token = OK."""
    resp = client.post("/v1/register")
    assert resp.status_code == 200


def test_register_initial_credits_via_env(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DEMO_API_TOKEN", ADMIN_TOKEN)
    monkeypatch.setenv("BILLING_DB_PATH", str(tmp_path / "billing.db"))
    monkeypatch.setenv("REGISTER_INITIAL_CREDITS", "300")
    monkeypatch.setenv("STRIPE_MODE", "test")
    app = create_app(
        run_turn_func=_stub_turn,
        run_hepan_turn_func=_stub_turn,
        run_cezi_turn_func=_stub_turn,
        run_najia_turn_func=_stub_turn,
        run_zwds_turn_func=_stub_turn,
        storage_root=str(tmp_path / "storage"),
    )
    resp = app.test_client().post("/v1/register", json={})
    assert resp.status_code == 200
    assert resp.get_json()["user"]["balance_credits"] == 300


def test_register_returned_api_key_can_authenticate(client) -> None:
    body = client.post("/v1/register", json={}).get_json()
    api_key = body["api_key"]
    bal = client.get("/v1/balance", headers=_user_headers(api_key))
    assert bal.status_code == 200
    assert bal.get_json()["user_id"] == body["user"]["user_id"]


# ---------------------------------------------------------------------------
# /v1/topup_packs
# ---------------------------------------------------------------------------


def test_topup_packs_public_no_auth(client) -> None:
    resp = client.get("/v1/topup_packs")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["currency"] == "cny"
    assert isinstance(body["packs"], list) and len(body["packs"]) >= 1
    assert body["stripe_configured"] is True
    assert body["stripe_mode"] == "test"
    # Sanity: every pack should match the 1元 = 100 credits invariant.
    for p in body["packs"]:
        assert p["amount_fen"] == p["amount_yuan"] * 100
        assert p["credits"] == p["amount_fen"]


def test_topup_packs_signals_unconfigured_stripe(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DEMO_API_TOKEN", ADMIN_TOKEN)
    monkeypatch.setenv("BILLING_DB_PATH", str(tmp_path / "billing.db"))
    monkeypatch.delenv("STRIPE_SECRET_KEY_TEST", raising=False)
    monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)
    monkeypatch.delenv("STRIPE_MODE", raising=False)
    app = create_app(
        run_turn_func=_stub_turn,
        run_hepan_turn_func=_stub_turn,
        run_cezi_turn_func=_stub_turn,
        run_najia_turn_func=_stub_turn,
        run_zwds_turn_func=_stub_turn,
        storage_root=str(tmp_path / "storage"),
    )
    body = app.test_client().get("/v1/topup_packs").get_json()
    assert body["stripe_configured"] is False


# ---------------------------------------------------------------------------
# /v1/checkout/create
# ---------------------------------------------------------------------------


@pytest.fixture
def stripe_module_mock():
    """Patch ``stripe`` so no real network call is made."""
    fake = MagicMock()
    fake.checkout.Session.create.return_value = {
        "id": "cs_test_endpoint",
        "url": "https://checkout.stripe.com/c/pay/cs_test_endpoint",
    }
    with patch.dict(sys.modules, {"stripe": fake}):
        yield fake


def test_checkout_create_with_pack_id(client, stripe_module_mock) -> None:
    api_key = _make_user(client)
    resp = client.post(
        "/v1/checkout/create",
        headers=_user_headers(api_key),
        json={"pack_id": "pack_30"},
    )
    assert resp.status_code == 200, resp.get_json()
    body = resp.get_json()
    assert body["session_id"] == "cs_test_endpoint"
    assert body["checkout_url"].startswith("https://checkout.stripe.com")
    assert body["amount_fen"] == 3000
    assert body["credits"] == 3000
    assert body["currency"] == "cny"
    # Verify the SDK got the right kwargs.
    kwargs = stripe_module_mock.checkout.Session.create.call_args.kwargs
    assert kwargs["client_reference_id"] == "u_alice"
    assert kwargs["metadata"]["user_id"] == "u_alice"
    assert "wechat_pay" in kwargs["payment_method_types"]


def test_checkout_create_with_custom_yuan(client, stripe_module_mock) -> None:
    api_key = _make_user(client)
    resp = client.post(
        "/v1/checkout/create",
        headers=_user_headers(api_key),
        json={"custom_yuan": 50},
    )
    assert resp.status_code == 200, resp.get_json()
    body = resp.get_json()
    assert body["amount_fen"] == 5000
    assert body["credits"] == 5000


def test_checkout_create_rejects_invalid_pack(client, stripe_module_mock) -> None:
    api_key = _make_user(client)
    resp = client.post(
        "/v1/checkout/create",
        headers=_user_headers(api_key),
        json={"pack_id": "pack_does_not_exist"},
    )
    assert resp.status_code == 400
    assert resp.get_json()["error"]["code"] == "invalid_amount"


def test_checkout_create_rejects_admin_token(client, stripe_module_mock) -> None:
    """Admin tokens must be rejected — no real user_id to bind the topup to."""
    resp = client.post(
        "/v1/checkout/create",
        headers=_admin_headers(),
        json={"pack_id": "pack_10"},
    )
    assert resp.status_code in (401, 403), resp.get_json()


def test_checkout_create_no_auth_returns_401(client, stripe_module_mock) -> None:
    resp = client.post(
        "/v1/checkout/create",
        json={"pack_id": "pack_10"},
    )
    assert resp.status_code == 401


def test_checkout_create_503_when_stripe_unconfigured(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DEMO_API_TOKEN", ADMIN_TOKEN)
    monkeypatch.setenv("BILLING_DB_PATH", str(tmp_path / "billing.db"))
    monkeypatch.delenv("STRIPE_SECRET_KEY_TEST", raising=False)
    monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)
    monkeypatch.delenv("STRIPE_MODE", raising=False)
    app = create_app(
        run_turn_func=_stub_turn,
        run_hepan_turn_func=_stub_turn,
        run_cezi_turn_func=_stub_turn,
        run_najia_turn_func=_stub_turn,
        run_zwds_turn_func=_stub_turn,
        storage_root=str(tmp_path / "storage"),
    )
    c = app.test_client()
    body = c.post("/admin/users", headers=_admin_headers(), json={"user_id": "u1", "initial_credits": 0})
    api_key = body.get_json()["api_key"]
    resp = c.post("/v1/checkout/create", headers=_user_headers(api_key), json={"pack_id": "pack_10"})
    assert resp.status_code == 503
    assert resp.get_json()["error"]["code"] == "stripe_not_configured"


# ---------------------------------------------------------------------------
# /webhooks/stripe
# ---------------------------------------------------------------------------


def _sign_event(event_dict: Dict[str, Any], secret: str) -> tuple[bytes, str]:
    body = json.dumps(event_dict, separators=(",", ":")).encode("utf-8")
    ts = int(time.time())
    signed_payload = f"{ts}.".encode("utf-8") + body
    sig = hmac.new(secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()
    return body, f"t={ts},v1={sig}"


def _checkout_completed_event(user_id: str, session_id: str, amount_fen: int = 3000, credits: int = 3000) -> Dict[str, Any]:
    return {
        "id": f"evt_{session_id}",
        "object": "event",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": session_id,
                "object": "checkout.session",
                "payment_status": "paid",
                "amount_total": amount_fen,
                "currency": "cny",
                "client_reference_id": user_id,
                "metadata": {"user_id": user_id, "credits": str(credits)},
                "customer_details": {"email": "alice@example.com"},
                "payment_intent": "pi_test_1",
            }
        },
    }


def test_webhook_credits_user_on_paid_session(client) -> None:
    _make_user(client, user_id="u_alice", credits=0)
    body, sig = _sign_event(_checkout_completed_event("u_alice", "cs_test_111", 3000, 3000), WEBHOOK_SECRET)
    resp = client.post("/webhooks/stripe", data=body, headers={"Stripe-Signature": sig})
    assert resp.status_code == 200, resp.get_data(as_text=True)
    data = resp.get_json()
    assert data["received"] is True
    assert data["user_id"] == "u_alice"
    assert data["credits_added"] == 3000
    assert data["balance_credits"] == 3000
    assert data["duplicate"] is False
    # Sanity: the user's balance via /admin/users now reflects the credit.
    listing = client.get("/admin/users", headers=_admin_headers()).get_json()["users"]
    alice = next(u for u in listing if u["user_id"] == "u_alice")
    assert alice["balance_credits"] == 3000


def test_webhook_replay_is_idempotent(client) -> None:
    _make_user(client, user_id="u_alice", credits=0)
    event = _checkout_completed_event("u_alice", "cs_test_dup", 1000, 1000)
    body, sig = _sign_event(event, WEBHOOK_SECRET)
    r1 = client.post("/webhooks/stripe", data=body, headers={"Stripe-Signature": sig})
    assert r1.status_code == 200
    assert r1.get_json()["balance_credits"] == 1000
    assert r1.get_json()["duplicate"] is False
    # Stripe might retry — repeating the same payload must NOT double-credit.
    body2, sig2 = _sign_event(event, WEBHOOK_SECRET)
    r2 = client.post("/webhooks/stripe", data=body2, headers={"Stripe-Signature": sig2})
    assert r2.status_code == 200
    assert r2.get_json()["duplicate"] is True
    assert r2.get_json()["balance_credits"] == 1000  # unchanged


def test_webhook_bad_signature_returns_400(client) -> None:
    _make_user(client, user_id="u_alice", credits=0)
    body, _ = _sign_event(_checkout_completed_event("u_alice", "cs_test_x", 1000), "wrong_secret")
    resp = client.post(
        "/webhooks/stripe",
        data=body,
        headers={"Stripe-Signature": "t=1,v1=abadabad"},
    )
    assert resp.status_code == 400
    assert resp.get_json()["error"]["code"] == "stripe_signature_invalid"


def test_webhook_unknown_event_type_acked(client) -> None:
    """Stripe sends many event types; we ack non-checkout events without retrying."""
    event = {
        "id": "evt_unrelated",
        "object": "event",
        "type": "payment_intent.succeeded",
        "data": {"object": {"id": "pi_x"}},
    }
    body, sig = _sign_event(event, WEBHOOK_SECRET)
    resp = client.post("/webhooks/stripe", data=body, headers={"Stripe-Signature": sig})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["received"] is True
    assert body["ignored_type"] == "payment_intent.succeeded"


def test_webhook_unpaid_session_acked_without_topup(client) -> None:
    _make_user(client, user_id="u_alice", credits=0)
    event = _checkout_completed_event("u_alice", "cs_test_unpaid", 1000, 1000)
    event["data"]["object"]["payment_status"] = "unpaid"
    body, sig = _sign_event(event, WEBHOOK_SECRET)
    resp = client.post("/webhooks/stripe", data=body, headers={"Stripe-Signature": sig})
    assert resp.status_code == 200
    assert "ignored_reason" in resp.get_json()
    bal = client.get("/admin/users", headers=_admin_headers()).get_json()["users"]
    alice = next(u for u in bal if u["user_id"] == "u_alice")
    assert alice["balance_credits"] == 0  # no topup happened


def test_webhook_unknown_user_returns_404(client) -> None:
    """If the webhook references a user_id we don't have, return 404 so the
    operator can investigate (vs. silently swallowing the payment)."""
    body, sig = _sign_event(_checkout_completed_event("u_does_not_exist", "cs_x", 1000, 1000), WEBHOOK_SECRET)
    resp = client.post("/webhooks/stripe", data=body, headers={"Stripe-Signature": sig})
    assert resp.status_code == 404
    assert resp.get_json()["error"]["code"] == "unknown_user"


def test_webhook_503_when_secret_not_configured(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DEMO_API_TOKEN", ADMIN_TOKEN)
    monkeypatch.setenv("BILLING_DB_PATH", str(tmp_path / "billing.db"))
    monkeypatch.delenv("STRIPE_WEBHOOK_SECRET_TEST", raising=False)
    monkeypatch.delenv("STRIPE_WEBHOOK_SECRET", raising=False)
    monkeypatch.delenv("STRIPE_MODE", raising=False)
    app = create_app(
        run_turn_func=_stub_turn,
        run_hepan_turn_func=_stub_turn,
        run_cezi_turn_func=_stub_turn,
        run_najia_turn_func=_stub_turn,
        run_zwds_turn_func=_stub_turn,
        storage_root=str(tmp_path / "storage"),
    )
    resp = app.test_client().post(
        "/webhooks/stripe",
        data=b"{}",
        headers={"Stripe-Signature": "t=1,v1=x"},
    )
    assert resp.status_code == 503
    assert resp.get_json()["error"]["code"] == "stripe_webhook_not_configured"
