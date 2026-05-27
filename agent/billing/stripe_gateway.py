"""Stripe payment integration.

Wraps the Stripe SDK for two operations:

1. ``build_checkout_session(...)`` — create a Stripe-hosted Checkout Session
   that lets the user pay with card or WeChat Pay. Returns the URL the
   user's browser should be redirected to.
2. ``verify_webhook(payload, signature, secret)`` — validate a Stripe
   webhook payload, then return the parsed ``event`` dict.

The gateway never imports ``stripe`` at module top-level so the rest of
the codebase still loads when the SDK is missing (e.g. in a stripped-down
test environment). The lazy import happens inside the two public methods.

Configuration (env vars, read every call so tests can monkeypatch):
    STRIPE_MODE                       test | live
    STRIPE_SECRET_KEY_TEST/_LIVE      sk_test_... / sk_live_...
    STRIPE_PUBLISHABLE_KEY_TEST/_LIVE pk_test_... / pk_live_...  (frontend only)
    STRIPE_WEBHOOK_SECRET_TEST/_LIVE  whsec_...
    STRIPE_SUCCESS_URL                where to redirect after payment OK
                                       (may include {CHECKOUT_SESSION_ID})
    STRIPE_CANCEL_URL                 where to redirect on cancel
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Custom errors
# ---------------------------------------------------------------------------


class StripeNotConfiguredError(Exception):
    """Raised when STRIPE_SECRET_KEY_* is missing."""


class StripeSignatureError(Exception):
    """Raised when a webhook payload's signature doesn't verify."""


def _stripe_object_default(obj: Any) -> Any:
    """JSON serializer fallback for Stripe SDK objects."""
    for attr in ("to_dict_recursive", "to_dict"):
        fn = getattr(obj, attr, None)
        if callable(fn):
            try:
                return fn()
            except Exception:
                continue
    if hasattr(obj, "__dict__"):
        return {k: v for k, v in obj.__dict__.items() if not k.startswith("_")}
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def _ensure_json_safe(value: Any) -> Any:
    """Recursively convert any Stripe SDK objects nested inside to plain types."""
    if isinstance(value, dict):
        return {k: _ensure_json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_ensure_json_safe(v) for v in value]
    if hasattr(value, "to_dict_recursive") or hasattr(value, "to_dict"):
        try:
            return _ensure_json_safe(_stripe_object_default(value))
        except TypeError:
            return value
    return value


# ---------------------------------------------------------------------------
# Pack config
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TopupPack:
    id: str
    label: str
    amount_yuan: int
    amount_fen: int  # what we send to Stripe; CNY's smallest unit
    credits: int    # what we add to the balance on webhook
    description: str = ""


@dataclass(frozen=True)
class TopupPackConfig:
    currency: str
    min_custom_yuan: int
    max_custom_yuan: int
    packs: List[TopupPack]

    def find(self, pack_id: str) -> Optional[TopupPack]:
        for p in self.packs:
            if p.id == pack_id:
                return p
        return None

    def to_public_json(self) -> Dict[str, Any]:
        return {
            "currency": self.currency,
            "min_custom_yuan": self.min_custom_yuan,
            "max_custom_yuan": self.max_custom_yuan,
            "packs": [
                {
                    "id": p.id,
                    "label": p.label,
                    "amount_yuan": p.amount_yuan,
                    "amount_fen": p.amount_fen,
                    "credits": p.credits,
                    "description": p.description,
                }
                for p in self.packs
            ],
        }


def load_pack_config(path: Optional[str] = None) -> TopupPackConfig:
    if path is None:
        repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        path = os.path.join(repo_root, "config", "stripe_packs.json")
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    packs: List[TopupPack] = []
    for entry in raw.get("packs", []):
        packs.append(
            TopupPack(
                id=str(entry["id"]),
                label=str(entry.get("label", entry["id"])),
                amount_yuan=int(entry["amount_yuan"]),
                amount_fen=int(entry["amount_fen"]),
                credits=int(entry["credits"]),
                description=str(entry.get("description", "")),
            )
        )
    return TopupPackConfig(
        currency=str(raw.get("currency", "cny")).lower(),
        min_custom_yuan=int(raw.get("min_custom_yuan", 1)),
        max_custom_yuan=int(raw.get("max_custom_yuan", 9999)),
        packs=packs,
    )


# ---------------------------------------------------------------------------
# Gateway
# ---------------------------------------------------------------------------


class StripeGateway:
    """Façade that hides the Stripe SDK from the rest of the code.

    Build via ``StripeGateway.from_env()`` once at app start and reuse.
    """

    def __init__(
        self,
        secret_key: Optional[str],
        webhook_secret: Optional[str],
        publishable_key: Optional[str],
        success_url: str,
        cancel_url: str,
        mode: str = "test",
        pack_config: Optional[TopupPackConfig] = None,
    ) -> None:
        self.secret_key = secret_key
        self.webhook_secret = webhook_secret
        self.publishable_key = publishable_key
        self.success_url = success_url
        self.cancel_url = cancel_url
        self.mode = mode
        self.pack_config = pack_config or load_pack_config()

    # -- factories ------------------------------------------------------

    @classmethod
    def from_env(cls, env: Optional[Dict[str, str]] = None) -> "StripeGateway":
        env = env or os.environ  # type: ignore[assignment]
        mode = (env.get("STRIPE_MODE") or "test").strip().lower()
        if mode not in ("test", "live"):
            mode = "test"
        suffix = "LIVE" if mode == "live" else "TEST"
        return cls(
            secret_key=env.get(f"STRIPE_SECRET_KEY_{suffix}") or env.get("STRIPE_SECRET_KEY"),
            webhook_secret=env.get(f"STRIPE_WEBHOOK_SECRET_{suffix}") or env.get("STRIPE_WEBHOOK_SECRET"),
            publishable_key=env.get(f"STRIPE_PUBLISHABLE_KEY_{suffix}") or env.get("STRIPE_PUBLISHABLE_KEY"),
            success_url=env.get(
                "STRIPE_SUCCESS_URL",
                "/billing.html?status=success&session_id={CHECKOUT_SESSION_ID}",
            ),
            cancel_url=env.get("STRIPE_CANCEL_URL", "/billing.html?status=cancelled"),
            mode=mode,
        )

    @property
    def configured(self) -> bool:
        return bool(self.secret_key)

    @property
    def webhook_configured(self) -> bool:
        return bool(self.webhook_secret)

    # -- pack lookup ----------------------------------------------------

    def resolve_amount(
        self,
        pack_id: Optional[str] = None,
        custom_yuan: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Return ``{label, amount_fen, credits, currency}``.

        Either ``pack_id`` (one of the predefined SKUs) or ``custom_yuan``
        must be set. Raises ``ValueError`` on bad input.
        """
        cfg = self.pack_config
        if pack_id:
            pack = cfg.find(pack_id)
            if pack is None:
                raise ValueError(f"unknown pack_id: {pack_id}")
            return {
                "label": pack.label,
                "amount_fen": pack.amount_fen,
                "credits": pack.credits,
                "currency": cfg.currency,
                "pack_id": pack.id,
            }
        if custom_yuan is None:
            raise ValueError("must provide pack_id or custom_yuan")
        if not isinstance(custom_yuan, int) or custom_yuan <= 0:
            raise ValueError("custom_yuan must be a positive integer")
        if custom_yuan < cfg.min_custom_yuan or custom_yuan > cfg.max_custom_yuan:
            raise ValueError(
                f"custom_yuan {custom_yuan} outside allowed range "
                f"[{cfg.min_custom_yuan}, {cfg.max_custom_yuan}]"
            )
        amount_fen = custom_yuan * 100
        return {
            "label": f"自定义 ¥{custom_yuan}",
            "amount_fen": amount_fen,
            "credits": amount_fen,
            "currency": cfg.currency,
            "pack_id": None,
        }

    # -- checkout creation ---------------------------------------------

    def build_checkout_session(
        self,
        *,
        user_id: str,
        amount_fen: int,
        credits: int,
        currency: str,
        label: str,
        payment_method_types: Optional[List[str]] = None,
        success_url: Optional[str] = None,
        cancel_url: Optional[str] = None,
        idempotency_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a Stripe Checkout Session.

        Returns ``{id, url, amount_fen, credits, currency}``.
        """
        if not self.configured:
            raise StripeNotConfiguredError(
                "STRIPE_SECRET_KEY_* not set. Cannot create checkout session."
            )
        if amount_fen <= 0 or credits <= 0:
            raise ValueError("amount_fen and credits must be positive")

        try:
            import stripe  # noqa: F401  (lazy import)
        except ImportError as e:
            raise StripeNotConfiguredError(
                "stripe SDK not installed. Run: pip install stripe>=15"
            ) from e

        stripe.api_key = self.secret_key
        methods = payment_method_types or ["card", "wechat_pay"]
        kwargs: Dict[str, Any] = {
            "mode": "payment",
            "payment_method_types": methods,
            "line_items": [
                {
                    "quantity": 1,
                    "price_data": {
                        "currency": currency,
                        "unit_amount": amount_fen,
                        "product_data": {
                            "name": label,
                            "description": f"Add {credits} credits to BaZi Agent.",
                        },
                    },
                }
            ],
            "client_reference_id": user_id,
            "metadata": {
                "user_id": user_id,
                "credits": str(credits),
            },
            "success_url": success_url or self.success_url,
            "cancel_url": cancel_url or self.cancel_url,
        }
        if "wechat_pay" in methods:
            # Stripe requires this option for web checkout WeChat Pay flows.
            kwargs["payment_method_options"] = {
                "wechat_pay": {"client": "web"}
            }

        request_kwargs: Dict[str, Any] = {}
        if idempotency_key:
            request_kwargs["idempotency_key"] = idempotency_key

        session = stripe.checkout.Session.create(**kwargs, **request_kwargs)
        return {
            "id": session["id"],
            "url": session["url"],
            "amount_fen": amount_fen,
            "credits": credits,
            "currency": currency,
        }

    # -- webhook --------------------------------------------------------

    def verify_webhook(
        self,
        payload: bytes,
        signature_header: str,
    ) -> Dict[str, Any]:
        """Verify the Stripe-Signature header and return the parsed event.

        Raises ``StripeNotConfiguredError`` if the webhook secret is unset
        and ``StripeSignatureError`` on tampered/replayed signatures.
        """
        if not self.webhook_configured:
            raise StripeNotConfiguredError(
                "STRIPE_WEBHOOK_SECRET_* not set. Cannot verify webhooks."
            )

        try:
            import stripe
        except ImportError as e:
            raise StripeNotConfiguredError("stripe SDK not installed.") from e

        # SDK versions ≥ 8 expose ``SignatureVerificationError`` at the
        # package root; older versions exposed it as ``stripe.error.X``.
        # In stripe>=15 the legacy ``stripe.error`` is a getattr-only alias
        # so ``from stripe.error import X`` raises ModuleNotFoundError —
        # fetch via attribute access instead.
        sve = getattr(stripe, "SignatureVerificationError", None)
        if sve is None:
            error_mod = getattr(stripe, "error", None)
            sve = getattr(error_mod, "SignatureVerificationError", Exception)

        try:
            event = stripe.Webhook.construct_event(
                payload=payload,
                sig_header=signature_header,
                secret=self.webhook_secret,
            )
        except sve as e:  # type: ignore[misc]
            raise StripeSignatureError(str(e)) from e
        except ValueError as e:
            # Malformed JSON.
            raise StripeSignatureError(f"invalid payload: {e}") from e
        # ``event`` is a StripeObject; convert to a plain nested dict so the
        # rest of our code can use it without depending on the SDK's runtime
        # type. ``to_dict_recursive()`` was removed in stripe>=11; fall back
        # to a JSON round-trip which works on every recent version.
        for serializer in ("to_dict_recursive", "to_dict"):
            fn = getattr(event, serializer, None)
            if callable(fn):
                try:
                    out = fn()
                    if isinstance(out, dict):
                        return _ensure_json_safe(out)
                except Exception:
                    pass
        try:
            return json.loads(json.dumps(event, default=_stripe_object_default))
        except Exception:
            return {"_raw_event": str(event)}

    # -- event helpers --------------------------------------------------

    @staticmethod
    def parse_checkout_completed(event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Pull the fields we care about out of a checkout.session.completed event.

        Returns ``None`` for any other event type or a payment-not-yet-paid session.
        """
        if not isinstance(event, dict):
            return None
        if event.get("type") != "checkout.session.completed":
            return None
        session = (event.get("data") or {}).get("object") or {}
        if session.get("payment_status") not in ("paid", "no_payment_required"):
            return None
        amount_total = session.get("amount_total")
        currency = (session.get("currency") or "").lower()
        user_id = session.get("client_reference_id")
        metadata = session.get("metadata") or {}
        credits_meta = metadata.get("credits")
        try:
            credits = int(credits_meta) if credits_meta is not None else None
        except (TypeError, ValueError):
            credits = None
        if not user_id or amount_total is None:
            return None
        return {
            "session_id": session.get("id"),
            "user_id": str(user_id),
            "amount_fen": int(amount_total),
            "credits": credits if credits is not None else int(amount_total),
            "currency": currency,
            "customer_email": (
                session.get("customer_details", {}).get("email")
                if isinstance(session.get("customer_details"), dict)
                else session.get("customer_email")
            ),
            "payment_intent": session.get("payment_intent"),
        }
