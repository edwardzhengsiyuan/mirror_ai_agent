"""Flask-side helpers for billing.

Designed to plug into ``web_server.create_app`` without dragging Flask into
the rest of the billing module. Two integration styles are supported:

1. **Decorator** for ordinary JSON endpoints::

       @app.route("/v1/hepan/ask", methods=["POST"])
       @billing.with_billing("/v1/hepan/ask")
       def hepan_ask(auth, charge):
           ...
           return jsonify(payload), 200

   The decorator handles auth, pricing, charge, and settle/refund based on
   the response status code.

2. **Manual primitives** for streaming endpoints (SSE worker threads must
   own the lifecycle themselves)::

       auth, err = billing.authenticate_request()
       if err:
           return err
       receipt, err = billing.try_charge(auth, "/v1/ask_stream", variant_params=...)
       if err:
           return err
       try:
           ... do work ...
           billing.service.settle(receipt.request_id)
       except Exception:
           billing.service.refund(receipt.request_id, "exception")
"""

from __future__ import annotations

import functools
import uuid
from typing import Any, Callable, Dict, Iterable, Optional, Tuple

from flask import Response, jsonify, request

from .errors import (
    DuplicateRequestError,
    InflightLimitError,
    InsufficientFundsError,
    RateLimitError,
    UnknownApiKeyError,
    UnknownUserError,
)
from .pricing import Pricing
from .service import BillingService, ChargeReceipt


_FLASK_ERROR = Tuple[Response, int]


def _bearer_token() -> str:
    header = request.headers.get("Authorization", "") or ""
    if not header.startswith("Bearer "):
        return ""
    return header.removeprefix("Bearer ").strip()


def _api_error(status: int, code: str, message: str, **details: Any) -> _FLASK_ERROR:
    payload: Dict[str, Any] = {"error": {"code": code, "message": message}}
    if details:
        payload["error"]["details"] = details
    return jsonify(payload), status


class BillingHelpers:
    """Bundle of helpers wired to a single :class:`BillingService` + price book."""

    def __init__(
        self,
        service: BillingService,
        pricing: Pricing,
        admin_token_getter: Callable[[], str],
    ) -> None:
        self.service = service
        self.pricing = pricing
        self._admin_token_getter = admin_token_getter

    # ------------------------------------------------------------------
    # auth
    # ------------------------------------------------------------------

    def authenticate_request(
        self,
        enforce_rate_limit: bool = True,
        allow_admin_bypass: bool = False,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[_FLASK_ERROR]]:
        """Resolve the bearer token to an auth context.

        When ``allow_admin_bypass=True`` and the token equals the configured
        admin token, the returned auth dict has ``is_admin=True`` and
        ``user_id=None`` and rate-limit/billing should be skipped by the
        caller. The default (``False``) only accepts user API keys.
        """
        token = _bearer_token()
        if not token:
            return None, _api_error(401, "unauthorized", "Bearer token required.")
        if allow_admin_bypass:
            expected_admin = (self._admin_token_getter() or "").strip()
            if expected_admin and token == expected_admin:
                return {"user_id": None, "is_admin": True, "key_hash": None}, None
        try:
            auth = self.service.authenticate(token)
        except UnknownApiKeyError as e:
            return None, _api_error(401, "unauthorized", str(e))
        auth["is_admin"] = False
        if enforce_rate_limit:
            try:
                self.service.check_rate_limit(scope=f"key:{auth['key_hash']}")
            except RateLimitError as e:
                return None, _api_error(
                    429,
                    "rate_limited",
                    str(e),
                    limit=e.limit,
                    window_seconds=e.window_seconds,
                )
        return auth, None

    def require_admin(self) -> Optional[_FLASK_ERROR]:
        expected = (self._admin_token_getter() or "").strip()
        if not expected:
            return _api_error(
                503,
                "admin_not_configured",
                "Admin token (DEMO_API_TOKEN) is not set on the server.",
            )
        if _bearer_token() != expected:
            return _api_error(401, "unauthorized", "Valid admin Bearer token required.")
        return None

    # ------------------------------------------------------------------
    # charge / settle / refund (for SSE-style manual control)
    # ------------------------------------------------------------------

    def resolve_request_id(self) -> str:
        explicit = (request.headers.get("X-Request-Id") or "").strip()
        if explicit:
            return explicit
        return str(uuid.uuid4())

    def try_charge(
        self,
        auth: Dict[str, Any],
        endpoint: str,
        variant_params: Optional[Iterable[Tuple[str, Any]]] = None,
        request_id: Optional[str] = None,
        meta: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Optional[ChargeReceipt], Optional[_FLASK_ERROR]]:
        cost = self.pricing.cost(endpoint, variant_params)
        rid = request_id or self.resolve_request_id()
        try:
            receipt = self.service.charge(
                user_id=auth["user_id"],
                endpoint=endpoint,
                amount_credits=cost,
                request_id=rid,
                meta=meta,
            )
            return receipt, None
        except DuplicateRequestError as e:
            return None, _api_error(
                409,
                "duplicate_request",
                "request_id already used; retry with a fresh value to charge again.",
                request_id=e.request_id,
                balance_credits=e.balance_after,
            )
        except InflightLimitError as e:
            return None, _api_error(
                429,
                "inflight_limit",
                str(e),
                limit=e.limit,
                current=e.current,
            )
        except InsufficientFundsError as e:
            return None, _api_error(
                402,
                "insufficient_funds",
                str(e),
                cost_credits=cost,
                endpoint=endpoint,
            )
        except UnknownUserError as e:
            return None, _api_error(404, "unknown_user", str(e))

    def settle(self, request_id: str) -> Optional[ChargeReceipt]:
        return self.service.settle(request_id)

    def refund(self, request_id: str, reason: Optional[str] = None) -> Optional[ChargeReceipt]:
        return self.service.refund(request_id, reason)

    # ------------------------------------------------------------------
    # decorator for non-streaming endpoints
    # ------------------------------------------------------------------

    def with_billing(
        self,
        endpoint: str,
        variant_extractor: Optional[Callable[[Dict[str, Any]], Iterable[Tuple[str, Any]]]] = None,
        allow_admin_bypass: bool = True,
    ) -> Callable[..., Any]:
        """Decorator that authenticates, charges, then settles or refunds.

        The wrapped function is invoked as ``f(auth, charge, **route_kwargs)``.
        When ``auth['is_admin']`` is true, ``charge`` is ``None`` and no
        balance change happens (admin bypass).

        ``variant_extractor(payload)`` may return additional ``(name, value)``
        pairs used for variant pricing lookup. ``payload`` is the parsed JSON
        request body (``{}`` if not parseable).
        """

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            @functools.wraps(func)
            def wrapper(*args: Any, **kwargs: Any):
                auth, err = self.authenticate_request(
                    allow_admin_bypass=allow_admin_bypass,
                )
                if err:
                    return err
                if auth.get("is_admin"):
                    return func(auth, None, *args, **kwargs)
                payload: Dict[str, Any] = {}
                if request.is_json:
                    try:
                        payload = request.get_json(force=True, silent=True) or {}
                    except Exception:
                        payload = {}
                variants: Optional[Iterable[Tuple[str, Any]]] = None
                if variant_extractor is not None:
                    try:
                        extracted = variant_extractor(payload) or []
                    except Exception:
                        extracted = []
                    variants = [
                        (str(k), v)
                        for (k, v) in extracted
                        if k is not None and v is not None
                    ]
                receipt, err = self.try_charge(
                    auth=auth,
                    endpoint=endpoint,
                    variant_params=variants,
                )
                if err:
                    return err

                try:
                    response_obj = func(auth, receipt, *args, **kwargs)
                except Exception:
                    self.refund(receipt.request_id, "endpoint_exception")
                    raise

                status_code = self._extract_status_code(response_obj)
                if 200 <= status_code < 400:
                    settled = self.settle(receipt.request_id) or receipt
                    return self._inject_billing_headers(response_obj, receipt, settled)
                self.refund(receipt.request_id, f"status_{status_code}")
                return response_obj

            return wrapper

        return decorator

    # ------------------------------------------------------------------
    # response helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_status_code(response_obj: Any) -> int:
        if isinstance(response_obj, tuple) and len(response_obj) >= 2:
            try:
                return int(response_obj[1])
            except (TypeError, ValueError):
                return 200
        if isinstance(response_obj, Response):
            return int(response_obj.status_code)
        return 200

    @staticmethod
    def _inject_billing_headers(
        response_obj: Any,
        charge: ChargeReceipt,
        settled: ChargeReceipt,
    ) -> Any:
        body = response_obj
        status = 200
        headers: Dict[str, str] = {}
        if isinstance(response_obj, tuple):
            if len(response_obj) == 2:
                body, status = response_obj  # type: ignore[misc]
            elif len(response_obj) == 3:
                body, status, headers = response_obj  # type: ignore[assignment]
                headers = dict(headers or {})
        elif isinstance(response_obj, Response):
            response_obj.headers["X-Charged-Credits"] = str(charge.amount_credits)
            response_obj.headers["X-Balance-After"] = str(settled.balance_after)
            response_obj.headers["X-Request-Id"] = charge.request_id
            return response_obj
        headers.setdefault("X-Charged-Credits", str(charge.amount_credits))
        headers.setdefault("X-Balance-After", str(settled.balance_after))
        headers.setdefault("X-Request-Id", charge.request_id)
        return body, status, headers
