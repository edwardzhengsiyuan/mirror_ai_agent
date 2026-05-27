"""Tests for ``agent.billing.stripe_gateway``.

We mock the Stripe SDK at module level so the tests never make a real
network call. The ``Webhook.construct_event`` helper is exercised through
its own thin wrapper.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
import os
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest

from agent.billing.stripe_gateway import (
    StripeGateway,
    StripeNotConfiguredError,
    StripeSignatureError,
    TopupPack,
    TopupPackConfig,
    load_pack_config,
)


# ---------------------------------------------------------------------------
# Pack config / amount resolution
# ---------------------------------------------------------------------------


def _packs() -> TopupPackConfig:
    return TopupPackConfig(
        currency="cny",
        min_custom_yuan=1,
        max_custom_yuan=9999,
        packs=[
            TopupPack(id="pack_10", label="体验包", amount_yuan=10, amount_fen=1000, credits=1000),
            TopupPack(id="pack_30", label="标准包", amount_yuan=30, amount_fen=3000, credits=3000),
        ],
    )


def _gw(**overrides) -> StripeGateway:
    defaults: Dict[str, Any] = dict(
        secret_key="sk_test_unit",
        webhook_secret="whsec_unit",
        publishable_key="pk_test_unit",
        success_url="https://example.com/billing.html?status=success&session_id={CHECKOUT_SESSION_ID}",
        cancel_url="https://example.com/billing.html?status=cancelled",
        mode="test",
        pack_config=_packs(),
    )
    defaults.update(overrides)
    return StripeGateway(**defaults)


def test_load_pack_config_repo_default_parses() -> None:
    cfg = load_pack_config()
    assert cfg.currency == "cny"
    assert any(p.id == "pack_10" for p in cfg.packs)
    # Every pack should respect the 1元 = 100 credits = 100 fen rule.
    for p in cfg.packs:
        assert p.amount_fen == p.amount_yuan * 100
        assert p.credits == p.amount_fen


def test_resolve_amount_pack_id() -> None:
    gw = _gw()
    out = gw.resolve_amount(pack_id="pack_30")
    assert out["amount_fen"] == 3000
    assert out["credits"] == 3000
    assert out["currency"] == "cny"
    assert out["pack_id"] == "pack_30"


def test_resolve_amount_unknown_pack_raises() -> None:
    gw = _gw()
    with pytest.raises(ValueError, match="unknown pack_id"):
        gw.resolve_amount(pack_id="pack_does_not_exist")


def test_resolve_amount_custom_yuan_ok() -> None:
    gw = _gw()
    out = gw.resolve_amount(custom_yuan=50)
    assert out["amount_fen"] == 5000
    assert out["credits"] == 5000
    assert "50" in out["label"]


def test_resolve_amount_custom_yuan_out_of_range() -> None:
    gw = _gw()
    with pytest.raises(ValueError):
        gw.resolve_amount(custom_yuan=0)
    with pytest.raises(ValueError):
        gw.resolve_amount(custom_yuan=10_000)
    with pytest.raises(ValueError):
        gw.resolve_amount(custom_yuan=-5)


def test_resolve_amount_requires_one_input() -> None:
    gw = _gw()
    with pytest.raises(ValueError):
        gw.resolve_amount()


# ---------------------------------------------------------------------------
# from_env
# ---------------------------------------------------------------------------


def test_from_env_picks_test_keys_by_default() -> None:
    env = {
        "STRIPE_SECRET_KEY_TEST": "sk_test_xx",
        "STRIPE_WEBHOOK_SECRET_TEST": "whsec_test_xx",
        "STRIPE_PUBLISHABLE_KEY_TEST": "pk_test_xx",
        "STRIPE_SECRET_KEY_LIVE": "sk_live_yy",
    }
    gw = StripeGateway.from_env(env)
    assert gw.mode == "test"
    assert gw.secret_key == "sk_test_xx"
    assert gw.publishable_key == "pk_test_xx"


def test_from_env_live_mode() -> None:
    env = {
        "STRIPE_MODE": "live",
        "STRIPE_SECRET_KEY_TEST": "sk_test_xx",
        "STRIPE_SECRET_KEY_LIVE": "sk_live_yy",
        "STRIPE_WEBHOOK_SECRET_LIVE": "whsec_live",
    }
    gw = StripeGateway.from_env(env)
    assert gw.mode == "live"
    assert gw.secret_key == "sk_live_yy"
    assert gw.webhook_secret == "whsec_live"


def test_from_env_missing_secret_key_means_unconfigured() -> None:
    gw = StripeGateway.from_env({})
    assert gw.configured is False
    assert gw.webhook_configured is False


# ---------------------------------------------------------------------------
# build_checkout_session — Stripe SDK is mocked
# ---------------------------------------------------------------------------


def test_build_checkout_session_calls_stripe_correctly() -> None:
    gw = _gw()
    fake_stripe = MagicMock()
    fake_stripe.checkout.Session.create.return_value = {
        "id": "cs_test_abc",
        "url": "https://checkout.stripe.com/c/pay/cs_test_abc",
    }
    with patch.dict("sys.modules", {"stripe": fake_stripe}):
        result = gw.build_checkout_session(
            user_id="u_alice",
            amount_fen=3000,
            credits=3000,
            currency="cny",
            label="¥30 标准包",
        )
    assert result["id"] == "cs_test_abc"
    assert result["url"].startswith("https://checkout.stripe.com")
    # Verify the kwargs we sent.
    kwargs = fake_stripe.checkout.Session.create.call_args.kwargs
    assert kwargs["mode"] == "payment"
    assert "card" in kwargs["payment_method_types"]
    assert "wechat_pay" in kwargs["payment_method_types"]
    # WeChat web requires this option.
    assert kwargs["payment_method_options"]["wechat_pay"]["client"] == "web"
    assert kwargs["client_reference_id"] == "u_alice"
    assert kwargs["metadata"]["user_id"] == "u_alice"
    assert kwargs["metadata"]["credits"] == "3000"
    line = kwargs["line_items"][0]
    assert line["price_data"]["currency"] == "cny"
    assert line["price_data"]["unit_amount"] == 3000
    assert kwargs["success_url"].endswith("{CHECKOUT_SESSION_ID}")


def test_build_checkout_session_sets_api_key() -> None:
    gw = _gw(secret_key="sk_test_special")
    fake_stripe = MagicMock()
    fake_stripe.checkout.Session.create.return_value = {"id": "cs_x", "url": "https://x"}
    with patch.dict("sys.modules", {"stripe": fake_stripe}):
        gw.build_checkout_session(
            user_id="u_bob",
            amount_fen=1000,
            credits=1000,
            currency="cny",
            label="¥10",
        )
    # The SDK reads its own api_key attr from the module.
    assert fake_stripe.api_key == "sk_test_special"


def test_build_checkout_session_card_only() -> None:
    gw = _gw()
    fake_stripe = MagicMock()
    fake_stripe.checkout.Session.create.return_value = {"id": "cs_x", "url": "https://x"}
    with patch.dict("sys.modules", {"stripe": fake_stripe}):
        gw.build_checkout_session(
            user_id="u",
            amount_fen=1000,
            credits=1000,
            currency="cny",
            label="¥10",
            payment_method_types=["card"],
        )
    kwargs = fake_stripe.checkout.Session.create.call_args.kwargs
    assert kwargs["payment_method_types"] == ["card"]
    # No wechat_pay → no special options needed.
    assert "payment_method_options" not in kwargs


def test_build_checkout_without_secret_key_raises() -> None:
    gw = _gw(secret_key=None)
    with pytest.raises(StripeNotConfiguredError):
        gw.build_checkout_session(
            user_id="u",
            amount_fen=1000,
            credits=1000,
            currency="cny",
            label="¥10",
        )


def test_build_checkout_rejects_zero_amount() -> None:
    gw = _gw()
    with pytest.raises(ValueError):
        gw.build_checkout_session(
            user_id="u", amount_fen=0, credits=0, currency="cny", label="x"
        )


# ---------------------------------------------------------------------------
# verify_webhook — uses real construct_event semantics via stripe SDK
# ---------------------------------------------------------------------------


def _build_signed_payload(payload_dict: Dict[str, Any], secret: str, ts: int = None) -> tuple[bytes, str]:
    """Mimic Stripe's signing scheme so we can call construct_event for real."""
    body = json.dumps(payload_dict, separators=(",", ":")).encode("utf-8")
    if ts is None:
        ts = int(time.time())
    signed_payload = f"{ts}.".encode("utf-8") + body
    sig = hmac.new(secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()
    header = f"t={ts},v1={sig}"
    return body, header


def test_verify_webhook_happy_path_returns_dict() -> None:
    secret = "whsec_unit_test"
    gw = _gw(webhook_secret=secret)
    event_payload = {
        "id": "evt_1",
        "object": "event",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "cs_test_42",
                "payment_status": "paid",
                "amount_total": 3000,
                "currency": "cny",
                "client_reference_id": "u_alice",
                "metadata": {"user_id": "u_alice", "credits": "3000"},
                "customer_details": {"email": "alice@example.com"},
            }
        },
    }
    body, header = _build_signed_payload(event_payload, secret)
    out = gw.verify_webhook(body, header)
    assert out["type"] == "checkout.session.completed"
    assert out["data"]["object"]["client_reference_id"] == "u_alice"


def test_verify_webhook_bad_signature_raises() -> None:
    secret = "whsec_real"
    gw = _gw(webhook_secret=secret)
    body, header = _build_signed_payload({"x": 1}, "whsec_wrong_secret")
    with pytest.raises(StripeSignatureError):
        gw.verify_webhook(body, header)


def test_verify_webhook_no_secret_raises_not_configured() -> None:
    gw = _gw(webhook_secret=None)
    with pytest.raises(StripeNotConfiguredError):
        gw.verify_webhook(b"{}", "t=1,v1=abc")


def test_verify_webhook_malformed_payload_raises_signature_error() -> None:
    secret = "whsec_test"
    gw = _gw(webhook_secret=secret)
    # Real Stripe construct_event raises ValueError on bad JSON; we map that
    # to StripeSignatureError so callers have a single error class.
    with pytest.raises(StripeSignatureError):
        gw.verify_webhook(b"not-valid-json", "t=1,v1=abc")


# ---------------------------------------------------------------------------
# parse_checkout_completed
# ---------------------------------------------------------------------------


def test_parse_checkout_completed_paid() -> None:
    event = {
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "cs_test_1",
                "payment_status": "paid",
                "amount_total": 3000,
                "currency": "cny",
                "client_reference_id": "u_alice",
                "metadata": {"user_id": "u_alice", "credits": "3000"},
                "customer_details": {"email": "alice@example.com"},
                "payment_intent": "pi_1",
            }
        },
    }
    parsed = StripeGateway.parse_checkout_completed(event)
    assert parsed is not None
    assert parsed["session_id"] == "cs_test_1"
    assert parsed["user_id"] == "u_alice"
    assert parsed["credits"] == 3000
    assert parsed["amount_fen"] == 3000
    assert parsed["currency"] == "cny"
    assert parsed["customer_email"] == "alice@example.com"
    assert parsed["payment_intent"] == "pi_1"


def test_parse_checkout_completed_unpaid_returns_none() -> None:
    event = {
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "cs_test_2",
                "payment_status": "unpaid",
                "amount_total": 3000,
                "client_reference_id": "u_alice",
            }
        },
    }
    assert StripeGateway.parse_checkout_completed(event) is None


def test_parse_checkout_completed_other_event_returns_none() -> None:
    assert (
        StripeGateway.parse_checkout_completed({"type": "payment_intent.succeeded"})
        is None
    )
    assert StripeGateway.parse_checkout_completed({}) is None
    assert StripeGateway.parse_checkout_completed("garbage") is None  # type: ignore[arg-type]


def test_parse_checkout_completed_falls_back_to_amount_when_metadata_missing() -> None:
    event = {
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "cs_test_3",
                "payment_status": "paid",
                "amount_total": 5000,
                "currency": "cny",
                "client_reference_id": "u_b",
                # No metadata.credits set
            }
        },
    }
    parsed = StripeGateway.parse_checkout_completed(event)
    assert parsed is not None
    # Defaults to amount_fen (since 1 yuan = 100 credits = 100 fen)
    assert parsed["credits"] == 5000


def test_parse_checkout_completed_missing_user_id_returns_none() -> None:
    event = {
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "cs_test_4",
                "payment_status": "paid",
                "amount_total": 5000,
                # client_reference_id omitted
            }
        },
    }
    assert StripeGateway.parse_checkout_completed(event) is None
