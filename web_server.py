"""Minimal Flask server for the bazi agent web UI."""

from __future__ import annotations

import datetime as dt
import json
import os
import queue
import re
import threading
import time
import uuid
from typing import Any, Callable, Dict, Optional

from flask import Flask, Response, jsonify, request, send_from_directory

from agent.billing import (
    BillingService,
    BillingStore,
    Pricing,
    StripeGateway,
    StripeNotConfiguredError,
    StripeSignatureError,
)
from agent.billing.errors import (
    BillingError,
    DuplicateRequestError,
    InsufficientFundsError,
    UnknownApiKeyError,
    UnknownUserError,
)
from agent.billing.middleware import BillingHelpers
from agent.llm_config import available_models, configurable_nodes, default_model, validate_model
from agent.orchestrator_cezi import run_cezi_turn
from agent.orchestrator_hepan import run_hepan_turn
from agent.orchestrator_najia import run_najia_turn
from agent.orchestrator_zwds import run_zwds_turn
from agent.orchestrator import run_turn
from agent.storage.conversation_store import append_event, load_recent_rounds, load_latest_llm_prompts, log_event_to_conversation
from agent.storage.profile_store import load_profile, save_profile

SAFE_ID_RE = re.compile(r"^[A-Za-z0-9_.-]{1,80}$")


def load_env_file(path: str) -> None:
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip("\"").strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


def create_app(
    run_turn_func: Callable = run_turn,
    run_hepan_turn_func: Callable = run_hepan_turn,
    run_cezi_turn_func: Callable = run_cezi_turn,
    run_najia_turn_func: Callable = run_najia_turn,
    run_zwds_turn_func: Callable = run_zwds_turn,
    storage_root: Optional[str] = None,
) -> Flask:
    load_env_file(os.path.join(os.path.dirname(__file__), ".env"))
    app = Flask(__name__, static_folder="web", static_url_path="")

    root = storage_root or os.path.join(os.path.dirname(__file__), "storage")

    def user_root(user_id: str) -> str:
        return os.path.join(root, "users", user_id)

    def profile_path(user_id: str) -> str:
        return os.path.join(user_root(user_id), "profile.json")

    def conversation_dir(user_id: str) -> str:
        return os.path.join(user_root(user_id), "conversations")

    def ensure_user_dirs(user_id: str) -> None:
        os.makedirs(conversation_dir(user_id), exist_ok=True)

    def normalize_session_id(session_id: str) -> str:
        return session_id if session_id.endswith(".jsonl") else f"{session_id}.jsonl"

    def new_session_path(user_id: str) -> str:
        ensure_user_dirs(user_id)
        session_id = dt.datetime.now(dt.UTC).strftime("%Y%m%dT%H%M%S")
        return os.path.join(conversation_dir(user_id), f"{session_id}.jsonl")

    def normalize_history_n(value: Optional[object]) -> int:
        try:
            history_n = int(value) if value is not None else 5
        except (TypeError, ValueError):
            history_n = 5
        return max(0, history_n)

    def validate_birth(birth: Dict[str, object]) -> Optional[str]:
        required_fields = {
            "year": (None, None),
            "month": (1, 12),
            "day": (1, 31),
        }
        optional_fields = {
            "hour": (0, 23),
            "minute": (0, 59),
            "second": (0, 59),
        }

        for field, (min_value, max_value) in required_fields.items():
            if field not in birth or birth.get(field) is None:
                return f"birth.{field} required"
            try:
                value = int(birth.get(field))
            except (TypeError, ValueError):
                return f"birth.{field} invalid"
            if min_value is not None and (value < min_value or value > max_value):
                return f"birth.{field} out of range"

        for field, (min_value, max_value) in optional_fields.items():
            if field not in birth or birth.get(field) is None:
                continue
            try:
                value = int(birth.get(field))
            except (TypeError, ValueError):
                return f"birth.{field} invalid"
            if value < min_value or value > max_value:
                return f"birth.{field} out of range"

        return None

    def validate_person_payload(person: object, field: str) -> Optional[str]:
        if not isinstance(person, dict):
            return f"{field} required"
        birth = person.get("birth")
        if not isinstance(birth, dict):
            return f"{field}.birth required"
        birth_error = validate_birth(birth)
        if birth_error:
            return f"{field}.{birth_error}"
        gender = person.get("gender", "male")
        if gender not in ("male", "female"):
            return f"{field}.gender invalid"
        return None

    def current_default_model() -> str:
        return default_model()

    def node_model_overrides_schema() -> Dict[str, Any]:
        return {
            "type": "object",
            "additionalProperties": {
                "type": "string",
                "enum": available_models(),
            },
            "description": "Optional per-node model overrides. Node override takes priority over node defaults and the global llm_model.",
            "example": {"SHISHEN": "qwen3-max", "RESPONSE": current_default_model()},
        }

    def normalize_node_model_overrides(value: object):
        if value is None:
            return {}, None
        if not isinstance(value, dict):
            return None, "node_model_overrides must be an object"
        allowed_nodes = set(configurable_nodes())
        normalized: Dict[str, str] = {}
        for node, model in value.items():
            node_name = str(node).strip().upper()
            model_name = str(model).strip()
            if not node_name or not model_name:
                continue
            if allowed_nodes and node_name not in allowed_nodes:
                return None, f"invalid node: {node_name}"
            if not validate_model(model_name):
                return None, f"invalid model for {node_name}: {model_name}"
            normalized[node_name] = model_name
        return normalized, None

    def normalize_model_options(data: Dict[str, Any]):
        model = data.get("llm_model")
        if model and not validate_model(model):
            return None, api_error(400, "invalid_model", f"invalid model: {model}")
        node_overrides, node_overrides_error = normalize_node_model_overrides(data.get("node_model_overrides"))
        if node_overrides_error:
            return None, api_error(400, "invalid_node_model_overrides", node_overrides_error)
        return {"model": model, "node_model_overrides": node_overrides or None}, None

    def validate_safe_id(value: str, field: str) -> Optional[str]:
        if not value:
            return f"{field} required"
        if not SAFE_ID_RE.match(value):
            return f"{field} may only contain letters, numbers, underscore, dash, and dot"
        return None

    def api_error(status: int, code: str, message: str, details: Optional[Dict[str, object]] = None):
        payload: Dict[str, object] = {
            "error": {
                "code": code,
                "message": message,
            }
        }
        if details:
            payload["error"]["details"] = details
        return jsonify(payload), status

    def bearer_token() -> str:
        header = request.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            return ""
        return header.removeprefix("Bearer ").strip()

    def require_demo_auth():
        expected = os.environ.get("DEMO_API_TOKEN", "").strip()
        if not expected:
            return api_error(
                503,
                "auth_not_configured",
                "DEMO_API_TOKEN is not configured on the server.",
            )
        if bearer_token() != expected:
            return api_error(401, "unauthorized", "Valid Bearer token required.")
        return None

    # ------------------------------------------------------------------
    # billing wiring
    # ------------------------------------------------------------------

    billing_db_path = (
        os.environ.get("BILLING_DB_PATH")
        or os.path.join(root, "billing.db")
    )
    billing_store = BillingStore(billing_db_path)
    billing_pricing = Pricing.load()
    try:
        billing_inflight_limit = int(os.environ.get("BILLING_INFLIGHT_LIMIT", "2"))
    except ValueError:
        billing_inflight_limit = 2
    try:
        billing_rate_limit_per_min = int(os.environ.get("BILLING_RATE_LIMIT_PER_MIN", "10"))
    except ValueError:
        billing_rate_limit_per_min = 10
    billing_service = BillingService(
        billing_store,
        inflight_limit=billing_inflight_limit,
        rate_limit_per_minute=billing_rate_limit_per_min,
    )
    billing = BillingHelpers(
        billing_service,
        billing_pricing,
        admin_token_getter=lambda: os.environ.get("DEMO_API_TOKEN", ""),
    )

    stripe_gateway = StripeGateway.from_env()

    def _annotate_billing(response, charge, balance_after: Optional[int] = None):
        """Attach X-Charged-Credits / X-Balance-After / X-Request-Id headers."""
        if charge is None:
            return response
        if balance_after is None:
            try:
                balance_after = billing_service.get_balance(charge.user_id)
            except UnknownUserError:
                balance_after = charge.balance_after
        response.headers["X-Charged-Credits"] = str(charge.amount_credits)
        response.headers["X-Balance-After"] = str(balance_after)
        response.headers["X-Request-Id"] = charge.request_id
        return response

    def _begin_billed_request(endpoint_path: str,
                              variant_params: Optional[list] = None,
                              defer_charge: bool = True):
        """Authenticate and (optionally) charge a request.

        Returns ``(auth, ctx, err_response)``. ``err_response`` is non-None
        on auth/charge failure and should be returned immediately. ``ctx``
        is a dict the caller uses to ``settle`` / ``refund`` / ``annotate``.
        Admin bypass requests get a ctx where charge is a no-op.

        With ``defer_charge=True`` the charge is not performed yet — call
        ``ctx["charge"]()`` after validating the payload so a 400 doesn't
        spend the user's credits.
        """
        auth, err = billing.authenticate_request(allow_admin_bypass=True)
        if err is not None:
            return None, None, err
        is_admin = bool(auth.get("is_admin"))
        state: Dict[str, Any] = {
            "receipt": None,
            "is_admin": is_admin,
            "auth": auth,
            "endpoint": endpoint_path,
            "variant_params": list(variant_params or []),
            "llm_usage": {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "node_count": 0,
            },
            "started_perf": None,
        }

        def do_charge() -> Optional[Any]:
            if state["is_admin"] or state["receipt"] is not None:
                return None
            receipt, err_resp = billing.try_charge(
                auth=auth,
                endpoint=endpoint_path,
                variant_params=variant_params,
            )
            if err_resp is not None:
                return err_resp
            state["receipt"] = receipt
            return None

        def track_event(event: Dict[str, Any]) -> None:
            if not isinstance(event, dict):
                return
            if event.get("type") != "llm_usage":
                return
            usage = state["llm_usage"]
            usage["prompt_tokens"] += int(event.get("prompt_tokens", 0) or 0)
            usage["completion_tokens"] += int(event.get("completion_tokens", 0) or 0)
            usage["total_tokens"] += int(event.get("total_tokens", 0) or 0)
            usage["node_count"] += 1

        def wrap_sink(inner_sink):
            def sink(event: Dict[str, Any]) -> None:
                track_event(event)
                if inner_sink is not None:
                    inner_sink(event)
            return sink

        def _persist_meta() -> None:
            if state["receipt"] is None:
                return
            patch: Dict[str, Any] = {}
            usage = state["llm_usage"]
            if usage["node_count"] > 0:
                patch["llm_usage"] = dict(usage)
            if state.get("started_perf") is not None:
                patch["duration_ms"] = int(
                    (time.perf_counter() - state["started_perf"]) * 1000
                )
            if state["variant_params"]:
                patch["variant_params"] = state["variant_params"]
            if patch:
                try:
                    billing_service.update_charge_meta(
                        state["receipt"].request_id, **patch
                    )
                except Exception:
                    # Never fail a request because we couldn't persist meta.
                    pass

        def do_settle() -> None:
            if state["receipt"] is not None:
                _persist_meta()
                billing.settle(state["receipt"].request_id)

        def do_refund(reason: str = "error") -> None:
            if state["receipt"] is not None:
                _persist_meta()
                billing.refund(state["receipt"].request_id, reason)

        def do_annotate(response):
            return _annotate_billing(response, state["receipt"])

        # Track wall-clock from the moment we authenticated; close enough for
        # latency accounting and avoids needing every endpoint to thread it.
        state["started_perf"] = time.perf_counter()

        ctx = {
            "is_admin": is_admin,
            "auth": auth,
            "charge": do_charge,
            "settle": do_settle,
            "refund": do_refund,
            "annotate": do_annotate,
            "wrap_sink": wrap_sink,
            "state": state,
        }
        if not defer_charge and not is_admin:
            err_resp = do_charge()
            if err_resp is not None:
                return None, None, err_resp
        return auth, ctx, None

    def _resolved_user_id(ctx: Dict[str, Any], body_user_id: Optional[str], default: str = "demo_guest"):
        """Pick the user_id for a request.

        For admin (legacy DEMO_API_TOKEN) callers the body value wins, falling
        back to ``default``. For real users the auth-bound ``user_id`` always
        wins; if the body sent a different ``user_id`` we reject 403.
        """
        body_uid = (body_user_id or "").strip()
        if ctx["is_admin"]:
            user_id = body_uid or default
            id_error = validate_safe_id(user_id, "user_id")
            if id_error:
                return None, api_error(400, "invalid_user_id", id_error)
            return user_id, None
        auth_uid = ctx["auth"]["user_id"]
        if body_uid and body_uid != auth_uid:
            return None, api_error(
                403,
                "user_id_mismatch",
                f"user_id in body ({body_uid}) does not match authenticated user ({auth_uid}).",
            )
        return auth_uid, None

    def public_profile(profile: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "user_id": profile.get("user_id"),
            "birth": profile.get("birth"),
            "gender": profile.get("gender", "male"),
            "birth_time_unknown": bool(profile.get("birth_time_unknown", False)),
            "prompt_config": profile.get("prompt_config", "lingyun_cat"),
            "llm_model": profile.get("llm_model", current_default_model()),
            "node_model_overrides": profile.get("node_model_overrides", {}),
            "bypass_cache": bool(profile.get("bypass_cache", False)),
            "cached_nodes": sorted((profile.get("node_cache") or {}).keys()),
        }

    def upsert_profile_from_payload(data: Dict[str, Any]):
        user_id = (data.get("user_id") or "").strip()
        id_error = validate_safe_id(user_id, "user_id")
        if id_error:
            return None, api_error(400, "invalid_user_id", id_error)

        path = profile_path(user_id)
        profile_exists = os.path.exists(path)
        profile = load_profile(path) if profile_exists else None
        birth = data.get("birth")

        if profile is None:
            if not isinstance(birth, dict):
                return None, api_error(
                    400,
                    "birth_required",
                    "birth is required when creating a new user profile.",
                )
            birth_error = validate_birth(birth)
            if birth_error:
                return None, api_error(400, "invalid_birth", birth_error)
            llm_model = data.get("llm_model", current_default_model())
            if not validate_model(llm_model):
                return None, api_error(400, "invalid_model", f"invalid model: {llm_model}")
            node_overrides, node_overrides_error = normalize_node_model_overrides(data.get("node_model_overrides"))
            if node_overrides_error:
                return None, api_error(400, "invalid_node_model_overrides", node_overrides_error)
            profile = {
                "user_id": user_id,
                "birth": birth,
                "gender": data.get("gender", "male"),
                "birth_time_unknown": bool(data.get("birth_time_unknown", False)),
                "prompt_config": data.get("prompt_config", "lingyun_cat"),
                "llm_model": llm_model or current_default_model(),
                "node_model_overrides": node_overrides or {},
                "bypass_cache": bool(data.get("bypass_cache", False)),
                "node_cache": {},
            }
            ensure_user_dirs(user_id)
            save_profile(path, profile)
            return profile, None

        chart_changed = False
        if isinstance(birth, dict):
            birth_error = validate_birth(birth)
            if birth_error:
                return None, api_error(400, "invalid_birth", birth_error)
            if birth != profile.get("birth"):
                profile["birth"] = birth
                chart_changed = True

        if "gender" in data and data["gender"] != profile.get("gender"):
            profile["gender"] = data["gender"]
            chart_changed = True
        if "birth_time_unknown" in data:
            time_unknown = bool(data["birth_time_unknown"])
            if time_unknown != bool(profile.get("birth_time_unknown", False)):
                profile["birth_time_unknown"] = time_unknown
                chart_changed = True
        if "prompt_config" in data:
            profile["prompt_config"] = data["prompt_config"]
        if "llm_model" in data:
            llm_model = data["llm_model"]
            if not validate_model(llm_model):
                return None, api_error(400, "invalid_model", f"invalid model: {llm_model}")
            profile["llm_model"] = llm_model or current_default_model()
        if "node_model_overrides" in data:
            node_overrides, node_overrides_error = normalize_node_model_overrides(data.get("node_model_overrides"))
            if node_overrides_error:
                return None, api_error(400, "invalid_node_model_overrides", node_overrides_error)
            profile["node_model_overrides"] = node_overrides or {}
        if "bypass_cache" in data:
            profile["bypass_cache"] = bool(data["bypass_cache"])

        if chart_changed:
            profile["node_cache"] = {}
        profile.setdefault("node_cache", {})
        ensure_user_dirs(user_id)
        save_profile(path, profile)
        return profile, None

    def conversation_path_for_payload(user_id: str, session_id: Optional[str]) -> str:
        if session_id:
            session_id = normalize_session_id(session_id.strip())
            base_session_id = session_id[:-6] if session_id.endswith(".jsonl") else session_id
            id_error = validate_safe_id(base_session_id, "session_id")
            if id_error:
                raise ValueError(id_error)
            return os.path.join(conversation_dir(user_id), session_id)
        return new_session_path(user_id)

    def optional_conversation_context(data: Dict[str, Any]):
        user_id = (data.get("user_id") or "demo_guest").strip()
        id_error = validate_safe_id(user_id, "user_id")
        if id_error:
            return None, api_error(400, "invalid_user_id", id_error)
        try:
            convo_path = conversation_path_for_payload(user_id, data.get("session_id"))
        except ValueError as exc:
            return None, api_error(400, "invalid_session_id", str(exc))
        history_n = normalize_history_n(data.get("history_n"))
        return {
            "user_id": user_id,
            "convo_path": convo_path,
            "history_rounds": load_recent_rounds(convo_path, history_n),
        }, None

    def run_v1_request(data: Dict[str, Any], *, stream: bool = False):
        question = (data.get("question") or "").strip()
        if not question:
            return None, api_error(400, "question_required", "question required")

        profile, error_response = upsert_profile_from_payload(data)
        if error_response:
            return None, error_response
        assert profile is not None

        birth_error = validate_birth(profile.get("birth", {}) or {})
        if birth_error:
            return None, api_error(400, "invalid_birth", birth_error)

        try:
            convo_path = conversation_path_for_payload(profile["user_id"], data.get("session_id"))
        except ValueError as exc:
            return None, api_error(400, "invalid_session_id", str(exc))

        history_n = normalize_history_n(data.get("history_n"))
        history_rounds = load_recent_rounds(convo_path, history_n)
        now = dt.datetime.now()
        request_id = f"req_{uuid.uuid4().hex[:16]}"
        append_event(
            convo_path,
            {
                "ts": now.isoformat(),
                "type": "user_message",
                "text": question,
                "request_id": request_id,
                "api_version": "v1",
            },
        )
        return {
            "profile": profile,
            "question": question,
            "convo_path": convo_path,
            "history_rounds": history_rounds,
            "now": now,
            "request_id": request_id,
            "stream": stream,
        }, None

    def public_stream_event(event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        event_type = event.get("type")
        if event_type == "response_delta":
            return {
                "type": "answer_delta",
                "delta": event.get("delta", ""),
                "reasoning_delta": event.get("reasoning_delta", ""),
            }
        if event_type == "response":
            return {
                "type": "answer",
                "answer": event.get("text", ""),
                "duration_ms": event.get("duration_ms"),
            }
        if event_type == "plan":
            return {"type": "plan", "plan": event.get("plan")}
        if event_type == "time_context":
            return {"type": "time_context", "time_context": event.get("value")}
        if event_type == "tool_invocation":
            return {
                "type": "tool_invocation",
                "tool": event.get("tool"),
                "output": event.get("output"),
                "duration_ms": event.get("duration_ms"),
            }
        if event_type == "node_start":
            return {"type": "node_status", "node": event.get("node"), "status": "running"}
        if event_type == "node_end":
            status = "error" if (event.get("output") or {}).get("error") else "done"
            if event.get("cached"):
                status = "cached"
            return {
                "type": "node_status",
                "node": event.get("node"),
                "status": status,
                "duration_ms": event.get("duration_ms"),
            }
        if event_type == "node_failed":
            return {"type": "node_status", "node": event.get("node"), "status": "error"}
        if event_type == "node_skipped":
            return {
                "type": "node_status",
                "node": event.get("node"),
                "status": "skipped",
                "reason": event.get("reason"),
            }
        if event_type in ("workflow_error", "server_error"):
            return {
                "type": "error",
                "message": event.get("message") or event.get("error"),
                "failed_nodes": event.get("failed_nodes"),
                "skipped_nodes": event.get("skipped_nodes"),
            }
        return None

    def openapi_spec() -> Dict[str, Any]:
        server_url = request.host_url.rstrip("/")
        return {
            "openapi": "3.0.3",
            "info": {
                "title": "BaZi Agent Demo API",
                "version": "1.0.0",
                "description": "Packaged demo API for BaZi chart Q&A. Swagger is for customer evaluation and integration testing.",
            },
            "servers": [{"url": server_url}],
            "components": {
                "securitySchemes": {
                    "bearerAuth": {
                        "type": "http",
                        "scheme": "bearer",
                        "bearerFormat": "user_api_key | DEMO_API_TOKEN",
                        "description": (
                            "Send `Authorization: Bearer <token>` where `<token>` is either a "
                            "**user API key** (issued via POST /admin/users or POST /v1/api_keys; "
                            "billed per request) or `DEMO_API_TOKEN` (admin bypass for /admin/* "
                            "endpoints and legacy smoke tests; never billed)."
                        ),
                    }
                },
                "headers": {
                    "X-Charged-Credits": {
                        "description": "Credits deducted for this request. Only present on billed (non-admin) responses.",
                        "schema": {"type": "integer", "example": 30},
                    },
                    "X-Balance-After": {
                        "description": "User's remaining credit balance after settlement.",
                        "schema": {"type": "integer", "example": 970},
                    },
                    "X-Request-Id": {
                        "description": "Idempotency key for this request. Resend the same value to retry without double-charging (returns 409).",
                        "schema": {"type": "string", "example": "f3c1d8e9-..."},
                    },
                },
                "schemas": {
                    "Birth": {
                        "type": "object",
                        "required": ["year", "month", "day"],
                        "properties": {
                            "year": {"type": "integer", "example": 1990},
                            "month": {"type": "integer", "minimum": 1, "maximum": 12, "example": 1},
                            "day": {"type": "integer", "minimum": 1, "maximum": 31, "example": 1},
                            "hour": {"type": "integer", "minimum": 0, "maximum": 23, "example": 8},
                            "minute": {"type": "integer", "minimum": 0, "maximum": 59, "example": 0},
                            "second": {"type": "integer", "minimum": 0, "maximum": 59, "example": 0},
                        },
                    },
                    "AskRequest": {
                        "type": "object",
                        "required": ["user_id", "question"],
                        "properties": {
                            "user_id": {"type": "string", "example": "u_demo"},
                            "question": {"type": "string", "example": "今年事业怎么样？"},
                            "birth": {"$ref": "#/components/schemas/Birth"},
                            "gender": {"type": "string", "enum": ["male", "female"], "example": "male"},
                            "birth_time_unknown": {"type": "boolean", "default": False},
                            "session_id": {"type": "string", "example": "demo_session"},
                            "history_n": {"type": "integer", "default": 5},
                            "llm_model": {"type": "string", "enum": available_models(), "example": current_default_model()},
                            "node_model_overrides": node_model_overrides_schema(),
                            "bypass_cache": {"type": "boolean", "default": False},
                        },
                    },
                    "AskResponse": {
                        "type": "object",
                        "properties": {
                            "request_id": {"type": "string"},
                            "session_id": {"type": "string"},
                            "user_id": {"type": "string"},
                            "answer": {"type": "string"},
                            "plan": {"type": "object"},
                            "time_context": {"type": "object", "nullable": True},
                            "error": {"type": "boolean"},
                            "failed_nodes": {"type": "array", "items": {"type": "string"}},
                            "skipped_nodes": {"type": "array", "items": {"type": "string"}},
                        },
                    },
                    "Person": {
                        "type": "object",
                        "required": ["birth"],
                        "properties": {
                            "name": {"type": "string", "example": "A"},
                            "gender": {"type": "string", "enum": ["male", "female"], "example": "female"},
                            "birth": {"$ref": "#/components/schemas/Birth"},
                            "birth_time_unknown": {"type": "boolean", "default": False},
                        },
                    },
                    "HepanRequest": {
                        "type": "object",
                        "required": ["question", "person_a", "person_b"],
                        "properties": {
                            "user_id": {"type": "string", "example": "u_demo"},
                            "session_id": {"type": "string", "example": "hepan_demo"},
                            "history_n": {"type": "integer", "default": 5},
                            "question": {"type": "string", "example": "我们适合长期发展吗？"},
                            "person_a": {"$ref": "#/components/schemas/Person"},
                            "person_b": {"$ref": "#/components/schemas/Person"},
                            "llm_model": {"type": "string", "enum": available_models(), "example": current_default_model()},
                            "node_model_overrides": node_model_overrides_schema(),
                        },
                    },
                    "HepanResponse": {
                        "type": "object",
                        "properties": {
                            "request_id": {"type": "string"},
                            "session_id": {"type": "string"},
                            "user_id": {"type": "string"},
                            "method": {"type": "string", "example": "hepan"},
                            "answer": {"type": "string"},
                            "compatibility": {"type": "object"},
                        },
                    },
                    "CeziRequest": {
                        "type": "object",
                        "required": ["question", "character"],
                        "properties": {
                            "user_id": {"type": "string", "example": "u_demo"},
                            "session_id": {"type": "string", "example": "cezi_demo"},
                            "history_n": {"type": "integer", "default": 5},
                            "question": {"type": "string", "example": "这个项目合作能不能成？"},
                            "character": {"type": "string", "example": "合"},
                            "llm_model": {"type": "string", "enum": available_models(), "example": current_default_model()},
                            "node_model_overrides": node_model_overrides_schema(),
                        },
                    },
                    "CeziResponse": {
                        "type": "object",
                        "properties": {
                            "request_id": {"type": "string"},
                            "session_id": {"type": "string"},
                            "user_id": {"type": "string"},
                            "method": {"type": "string", "example": "cezi"},
                            "answer": {"type": "string"},
                            "character": {"type": "string"},
                        },
                    },
                    "NajiaRequest": {
                        "type": "object",
                        "required": ["question"],
                        "properties": {
                            "user_id": {"type": "string", "example": "u_demo"},
                            "session_id": {"type": "string", "example": "najia_demo"},
                            "history_n": {"type": "integer", "default": 5},
                            "question": {"type": "string", "example": "这个项目三个月内能不能推进成功？"},
                            "yao_values": {
                                "type": "array",
                                "items": {"type": "integer", "minimum": 0, "maximum": 7},
                                "minItems": 6,
                                "maxItems": 6,
                                "example": [0, 1, 2, 3, 4, 5],
                            },
                            "llm_model": {"type": "string", "enum": available_models(), "example": current_default_model()},
                            "node_model_overrides": node_model_overrides_schema(),
                        },
                    },
                    "NajiaResponse": {
                        "type": "object",
                        "properties": {
                            "request_id": {"type": "string"},
                            "session_id": {"type": "string"},
                            "user_id": {"type": "string"},
                            "method": {"type": "string", "example": "najia"},
                            "answer": {"type": "string"},
                            "gua": {"type": "object"},
                        },
                    },
                    "ZwdsRequest": {
                        "type": "object",
                        "required": ["question", "birth"],
                        "properties": {
                            "user_id": {"type": "string", "example": "u_demo"},
                            "session_id": {"type": "string", "example": "zwds_demo"},
                            "history_n": {"type": "integer", "default": 5},
                            "question": {
                                "type": "string",
                                "example": "今年我的事业和感情运势如何？",
                            },
                            "birth": {
                                "type": "object",
                                "required": ["year", "month", "day"],
                                "properties": {
                                    "year": {"type": "integer", "example": 1990},
                                    "month": {"type": "integer", "example": 5},
                                    "day": {"type": "integer", "example": 12},
                                    "hour": {"type": "integer", "default": 0},
                                    "minute": {"type": "integer", "default": 0},
                                    "second": {"type": "integer", "default": 0},
                                },
                            },
                            "gender": {"type": "string", "enum": ["male", "female"], "default": "male"},
                            "target_years": {
                                "type": "array",
                                "items": {"type": "integer"},
                                "description": "Years to render flow-year (流年) analyses for. Defaults to current civil year.",
                                "example": [2026],
                            },
                            "include_star_gong": {
                                "type": "boolean",
                                "default": False,
                                "description": "Whether to inject the ≈973 KB star_gong.md star/palace lookup into the system prompt.",
                            },
                            "llm_model": {
                                "type": "string",
                                "enum": available_models(),
                                "example": current_default_model(),
                            },
                            "node_model_overrides": node_model_overrides_schema(),
                        },
                    },
                    "ZwdsResponse": {
                        "type": "object",
                        "properties": {
                            "request_id": {"type": "string"},
                            "session_id": {"type": "string"},
                            "user_id": {"type": "string"},
                            "method": {"type": "string", "example": "zwds"},
                            "answer": {"type": "string"},
                            "chart": {"type": "object"},
                        },
                    },
                    "ProfileRequest": {
                        "allOf": [
                            {"$ref": "#/components/schemas/AskRequest"},
                            {
                                "type": "object",
                                "required": ["birth"],
                                "properties": {"question": {"readOnly": True}},
                            },
                        ]
                    },
                    "ErrorResponse": {
                        "type": "object",
                        "properties": {
                            "error": {
                                "type": "object",
                                "properties": {
                                    "code": {"type": "string"},
                                    "message": {"type": "string"},
                                    "details": {"type": "object", "additionalProperties": True},
                                },
                            }
                        },
                    },
                    "BalanceResponse": {
                        "type": "object",
                        "properties": {
                            "user_id": {"type": "string", "example": "u_alice"},
                            "balance_credits": {"type": "integer", "example": 970},
                            "daily_credits_limit": {"type": "integer", "nullable": True, "example": None},
                        },
                    },
                    "LedgerRow": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "integer"},
                            "user_id": {"type": "string"},
                            "request_id": {"type": "string"},
                            "endpoint": {"type": "string", "nullable": True, "example": "/v1/cezi/ask"},
                            "kind": {"type": "string", "enum": ["charge", "refund", "topup"]},
                            "amount_credits": {"type": "integer"},
                            "balance_after": {"type": "integer"},
                            "status": {"type": "string", "enum": ["pending", "settled", "refunded"]},
                            "meta_json": {"type": "string", "nullable": True},
                            "ts": {"type": "string", "example": "2026-05-27T13:14:15.123456Z"},
                        },
                    },
                    "UsageResponse": {
                        "type": "object",
                        "properties": {
                            "user_id": {"type": "string"},
                            "rows": {
                                "type": "array",
                                "items": {"$ref": "#/components/schemas/LedgerRow"},
                            },
                        },
                    },
                    "ApiKeyListItem": {
                        "type": "object",
                        "properties": {
                            "key_id": {"type": "string", "description": "12-char prefix of the key hash; safe to display.", "example": "a1b2c3d4e5f6"},
                            "label": {"type": "string", "nullable": True, "example": "phone-app"},
                            "created_at": {"type": "string"},
                            "last_seen_at": {"type": "string", "nullable": True},
                            "revoked": {"type": "boolean"},
                        },
                    },
                    "ApiKeyListResponse": {
                        "type": "object",
                        "properties": {
                            "user_id": {"type": "string"},
                            "api_keys": {
                                "type": "array",
                                "items": {"$ref": "#/components/schemas/ApiKeyListItem"},
                            },
                        },
                    },
                    "ApiKeyIssueRequest": {
                        "type": "object",
                        "properties": {"label": {"type": "string", "example": "phone-app"}},
                    },
                    "ApiKeyIssueResponse": {
                        "type": "object",
                        "properties": {
                            "user_id": {"type": "string"},
                            "api_key": {"type": "string", "description": "Plaintext API key. Shown only once — store immediately."},
                            "label": {"type": "string", "nullable": True},
                            "warning": {"type": "string"},
                        },
                    },
                    "AdminCreateUserRequest": {
                        "type": "object",
                        "required": ["user_id"],
                        "properties": {
                            "user_id": {"type": "string", "example": "u_alice"},
                            "display_name": {"type": "string", "example": "Alice"},
                            "initial_credits": {"type": "integer", "default": 0, "example": 1000},
                            "daily_credits_limit": {"type": "integer", "nullable": True, "default": None},
                            "issue_first_key": {"type": "boolean", "default": True},
                            "key_label": {"type": "string", "example": "primary"},
                        },
                    },
                    "AdminCreateUserResponse": {
                        "type": "object",
                        "properties": {
                            "user": {"type": "object"},
                            "api_key": {"type": "string", "nullable": True},
                            "warning": {"type": "string"},
                        },
                    },
                    "AdminUserListResponse": {
                        "type": "object",
                        "properties": {
                            "users": {"type": "array", "items": {"type": "object"}},
                        },
                    },
                    "AdminStatusRequest": {
                        "type": "object",
                        "required": ["status"],
                        "properties": {"status": {"type": "string", "enum": ["active", "disabled"]}},
                    },
                    "AdminTopupRequest": {
                        "type": "object",
                        "required": ["user_id", "amount_credits"],
                        "properties": {
                            "user_id": {"type": "string", "example": "u_alice"},
                            "amount_credits": {"type": "integer", "minimum": 1, "example": 500},
                            "request_id": {"type": "string", "description": "Optional idempotency key. Reusing returns duplicate=true without double-credit.", "example": "wechat-pay-20260527-0001"},
                            "note": {"type": "string", "example": "promo"},
                            "source": {"type": "string", "default": "admin"},
                        },
                    },
                    "AdminTopupResponse": {
                        "type": "object",
                        "properties": {
                            "user_id": {"type": "string"},
                            "amount_credits": {"type": "integer"},
                            "balance_credits": {"type": "integer"},
                            "request_id": {"type": "string"},
                            "duplicate": {"type": "boolean"},
                        },
                    },
                    "AdminLedgerResponse": {
                        "type": "object",
                        "properties": {
                            "rows": {
                                "type": "array",
                                "items": {"$ref": "#/components/schemas/LedgerRow"},
                            },
                        },
                    },
                    "PricingResponse": {
                        "type": "object",
                        "properties": {
                            "default_credits": {"type": "integer"},
                            "endpoints": {"type": "object", "additionalProperties": {"type": "integer"}},
                            "variants": {"type": "object", "additionalProperties": {"type": "integer"}},
                        },
                    },
                    "RegisterRequest": {
                        "type": "object",
                        "properties": {
                            "display_name": {"type": "string", "example": "Alice"},
                            "key_label": {"type": "string", "example": "primary"},
                        },
                    },
                    "RegisterResponse": {
                        "type": "object",
                        "properties": {
                            "user": {"type": "object"},
                            "api_key": {"type": "string", "description": "Plaintext API key, shown ONCE."},
                            "warning": {"type": "string"},
                        },
                    },
                    "TopupPack": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string", "example": "pack_30"},
                            "label": {"type": "string", "example": "标准包"},
                            "amount_yuan": {"type": "integer", "example": 30},
                            "amount_fen": {"type": "integer", "example": 3000},
                            "credits": {"type": "integer", "example": 3000},
                            "description": {"type": "string"},
                        },
                    },
                    "TopupPacksResponse": {
                        "type": "object",
                        "properties": {
                            "currency": {"type": "string", "example": "cny"},
                            "min_custom_yuan": {"type": "integer", "example": 1},
                            "max_custom_yuan": {"type": "integer", "example": 9999},
                            "packs": {"type": "array", "items": {"$ref": "#/components/schemas/TopupPack"}},
                            "stripe_configured": {"type": "boolean"},
                            "stripe_publishable_key": {"type": "string", "nullable": True},
                            "stripe_mode": {"type": "string", "enum": ["test", "live"]},
                        },
                    },
                    "CheckoutCreateRequest": {
                        "type": "object",
                        "description": "Provide exactly one of pack_id (preset SKU) or custom_yuan (1-9999 元).",
                        "properties": {
                            "pack_id": {"type": "string", "example": "pack_30"},
                            "custom_yuan": {"type": "integer", "minimum": 1, "maximum": 9999, "example": 50},
                        },
                    },
                    "CheckoutCreateResponse": {
                        "type": "object",
                        "properties": {
                            "checkout_url": {"type": "string", "format": "uri", "description": "Redirect the user's browser here."},
                            "session_id": {"type": "string"},
                            "amount_fen": {"type": "integer"},
                            "credits": {"type": "integer"},
                            "currency": {"type": "string"},
                        },
                    },
                    "StripeWebhookResponse": {
                        "type": "object",
                        "properties": {
                            "received": {"type": "boolean"},
                            "user_id": {"type": "string"},
                            "credits_added": {"type": "integer"},
                            "balance_credits": {"type": "integer"},
                            "duplicate": {"type": "boolean"},
                        },
                    },
                },
            },
            "paths": {
                "/health": {
                    "get": {
                        "summary": "Health check",
                        "responses": {"200": {"description": "Server status"}},
                    }
                },
                "/v1/users": {
                    "post": {
                        "summary": "Create or update a demo user profile",
                        "security": [{"bearerAuth": []}],
                        "requestBody": {
                            "required": True,
                            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ProfileRequest"}}},
                        },
                        "responses": {
                            "200": {"description": "Profile saved"},
                            "400": {"description": "Invalid request", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}}},
                            "401": {"description": "Unauthorized"},
                        },
                    }
                },
                "/v1/users/{user_id}": {
                    "get": {
                        "summary": "Get a demo user profile summary",
                        "security": [{"bearerAuth": []}],
                        "parameters": [{"name": "user_id", "in": "path", "required": True, "schema": {"type": "string"}}],
                        "responses": {
                            "200": {"description": "Profile summary"},
                            "404": {"description": "Profile not found"},
                        },
                    }
                },
                "/v1/ask": {
                    "post": {
                        "summary": "Run a synchronous BaZi Q&A turn",
                        "description": "Billed at 200 credits when authenticated with a user API key. Free when authenticated with `DEMO_API_TOKEN` (admin bypass).",
                        "security": [{"bearerAuth": []}],
                        "requestBody": {
                            "required": True,
                            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/AskRequest"}}},
                        },
                        "responses": {
                            "200": {
                                "description": "Answer.",
                                "headers": {
                                    "X-Charged-Credits": {"$ref": "#/components/headers/X-Charged-Credits"},
                                    "X-Balance-After": {"$ref": "#/components/headers/X-Balance-After"},
                                    "X-Request-Id": {"$ref": "#/components/headers/X-Request-Id"},
                                },
                                "content": {"application/json": {"schema": {"$ref": "#/components/schemas/AskResponse"}}},
                            },
                            "400": {"description": "Invalid request", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}}},
                            "401": {"description": "Unauthorized: bearer token missing or unknown."},
                            "402": {"description": "Insufficient funds: user balance below the endpoint's cost."},
                            "403": {"description": "user_id in body does not match the authenticated API key."},
                            "409": {"description": "Duplicate request_id (idempotency replay)."},
                            "429": {"description": "Rate-limited or in-flight cap reached."},
                        },
                    }
                },
                "/v1/ask_stream": {
                    "post": {
                        "summary": "Run a streaming BaZi Q&A turn using Server-Sent Events",
                        "description": "Billed at 200 credits when authenticated with a user API key. The stream emits `billing` events with `stage=charged` (start) and `stage=settled`/`refunded` (end), plus the usual `session`, `plan`, `node_status`, `tool_invocation`, `response_delta`, `response`, `error`.",
                        "security": [{"bearerAuth": []}],
                        "requestBody": {
                            "required": True,
                            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/AskRequest"}}},
                        },
                        "responses": {
                            "200": {
                                "description": "Server-Sent Events stream. See description for event types.",
                                "content": {"text/event-stream": {"schema": {"type": "string"}}},
                            },
                            "400": {"description": "Invalid request"},
                            "401": {"description": "Unauthorized"},
                            "402": {"description": "Insufficient funds."},
                            "403": {"description": "user_id mismatch."},
                            "429": {"description": "Rate-limited or in-flight cap reached."},
                        },
                    }
                },
                "/v1/hepan/ask": {
                    "post": {
                        "summary": "Run a synchronous BaZi HePan compatibility turn",
                        "description": "Billed at 100 credits.",
                        "security": [{"bearerAuth": []}],
                        "requestBody": {
                            "required": True,
                            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/HepanRequest"}}},
                        },
                        "responses": {
                            "200": {
                                "description": "HePan answer",
                                "headers": {
                                    "X-Charged-Credits": {"$ref": "#/components/headers/X-Charged-Credits"},
                                    "X-Balance-After": {"$ref": "#/components/headers/X-Balance-After"},
                                    "X-Request-Id": {"$ref": "#/components/headers/X-Request-Id"},
                                },
                                "content": {"application/json": {"schema": {"$ref": "#/components/schemas/HepanResponse"}}},
                            },
                            "400": {"description": "Invalid request"},
                            "401": {"description": "Unauthorized"},
                            "402": {"description": "Insufficient funds."},
                            "403": {"description": "user_id mismatch."},
                            "429": {"description": "Rate-limited or in-flight cap reached."},
                        },
                    }
                },
                "/v1/cezi/ask": {
                    "post": {
                        "summary": "Run a synchronous CeZi character-divination turn",
                        "description": "Billed at 30 credits — the cheapest billed endpoint, suitable for smoke tests.",
                        "security": [{"bearerAuth": []}],
                        "requestBody": {
                            "required": True,
                            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/CeziRequest"}}},
                        },
                        "responses": {
                            "200": {
                                "description": "CeZi answer",
                                "headers": {
                                    "X-Charged-Credits": {"$ref": "#/components/headers/X-Charged-Credits"},
                                    "X-Balance-After": {"$ref": "#/components/headers/X-Balance-After"},
                                    "X-Request-Id": {"$ref": "#/components/headers/X-Request-Id"},
                                },
                                "content": {"application/json": {"schema": {"$ref": "#/components/schemas/CeziResponse"}}},
                            },
                            "400": {"description": "Invalid request"},
                            "401": {"description": "Unauthorized"},
                            "402": {"description": "Insufficient funds."},
                            "403": {"description": "user_id mismatch."},
                            "429": {"description": "Rate-limited or in-flight cap reached."},
                        },
                    }
                },
                "/v1/najia/ask": {
                    "post": {
                        "summary": "Run a synchronous Liuyao/Najia divination turn",
                        "description": "Billed at 50 credits, or 80 credits when `paraphrase=true` (forces a second LLM pass that humanizes the raw 卦盘).",
                        "security": [{"bearerAuth": []}],
                        "requestBody": {
                            "required": True,
                            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/NajiaRequest"}}},
                        },
                        "responses": {
                            "200": {
                                "description": "Najia answer",
                                "headers": {
                                    "X-Charged-Credits": {"$ref": "#/components/headers/X-Charged-Credits"},
                                    "X-Balance-After": {"$ref": "#/components/headers/X-Balance-After"},
                                    "X-Request-Id": {"$ref": "#/components/headers/X-Request-Id"},
                                },
                                "content": {"application/json": {"schema": {"$ref": "#/components/schemas/NajiaResponse"}}},
                            },
                            "400": {"description": "Invalid request"},
                            "401": {"description": "Unauthorized"},
                            "402": {"description": "Insufficient funds."},
                            "403": {"description": "user_id mismatch."},
                            "429": {"description": "Rate-limited or in-flight cap reached."},
                        },
                    }
                },
                "/v1/zwds/ask": {
                    "post": {
                        "summary": "Run a synchronous Ziwei Doushu (紫微斗数) turn",
                        "description": "Billed at 80 credits, or 150 credits when `include_star_gong=true` (injects the ≈973 KB star/palace lookup).",
                        "security": [{"bearerAuth": []}],
                        "requestBody": {
                            "required": True,
                            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ZwdsRequest"}}},
                        },
                        "responses": {
                            "200": {
                                "description": "Zwds answer",
                                "headers": {
                                    "X-Charged-Credits": {"$ref": "#/components/headers/X-Charged-Credits"},
                                    "X-Balance-After": {"$ref": "#/components/headers/X-Balance-After"},
                                    "X-Request-Id": {"$ref": "#/components/headers/X-Request-Id"},
                                },
                                "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ZwdsResponse"}}},
                            },
                            "400": {"description": "Invalid request"},
                            "401": {"description": "Unauthorized"},
                            "402": {"description": "Insufficient funds."},
                            "403": {"description": "user_id mismatch."},
                            "429": {"description": "Rate-limited or in-flight cap reached."},
                        },
                    }
                },
                "/v1/balance": {
                    "get": {
                        "summary": "Get the balance of the authenticated user",
                        "description": "Requires a user API key. Admin tokens are rejected.",
                        "security": [{"bearerAuth": []}],
                        "responses": {
                            "200": {"description": "Balance", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/BalanceResponse"}}}},
                            "401": {"description": "Unauthorized"},
                        },
                    }
                },
                "/v1/usage": {
                    "get": {
                        "summary": "List recent ledger rows for the authenticated user",
                        "security": [{"bearerAuth": []}],
                        "parameters": [
                            {"name": "limit", "in": "query", "schema": {"type": "integer", "minimum": 1, "maximum": 500, "default": 50}},
                        ],
                        "responses": {
                            "200": {"description": "Usage", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/UsageResponse"}}}},
                            "401": {"description": "Unauthorized"},
                        },
                    }
                },
                "/v1/api_keys": {
                    "get": {
                        "summary": "List the authenticated user's API keys",
                        "security": [{"bearerAuth": []}],
                        "responses": {
                            "200": {"description": "Keys", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ApiKeyListResponse"}}}},
                            "401": {"description": "Unauthorized"},
                        },
                    },
                    "post": {
                        "summary": "Issue a new API key for the authenticated user",
                        "description": "Returned plaintext `api_key` is shown ONCE — store it immediately.",
                        "security": [{"bearerAuth": []}],
                        "requestBody": {
                            "required": False,
                            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ApiKeyIssueRequest"}}},
                        },
                        "responses": {
                            "200": {"description": "New key", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ApiKeyIssueResponse"}}}},
                            "401": {"description": "Unauthorized"},
                        },
                    },
                },
                "/v1/api_keys/{key_id}": {
                    "delete": {
                        "summary": "Revoke an API key by its 12-char prefix",
                        "security": [{"bearerAuth": []}],
                        "parameters": [
                            {"name": "key_id", "in": "path", "required": True, "schema": {"type": "string"}, "description": "First 12 hex chars of the key hash, as shown by GET /v1/api_keys."},
                        ],
                        "responses": {
                            "200": {"description": "Revoked"},
                            "404": {"description": "Key not found for this user"},
                            "401": {"description": "Unauthorized"},
                        },
                    }
                },
                "/admin/users": {
                    "post": {
                        "summary": "[admin] Create a billing user and (optionally) issue a first API key",
                        "security": [{"bearerAuth": []}],
                        "requestBody": {
                            "required": True,
                            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/AdminCreateUserRequest"}}},
                        },
                        "responses": {
                            "200": {"description": "User created", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/AdminCreateUserResponse"}}}},
                            "400": {"description": "Invalid request"},
                            "401": {"description": "Admin token required"},
                            "409": {"description": "user_id already exists"},
                        },
                    },
                    "get": {
                        "summary": "[admin] List all users",
                        "security": [{"bearerAuth": []}],
                        "parameters": [
                            {"name": "limit", "in": "query", "schema": {"type": "integer", "default": 200}},
                        ],
                        "responses": {
                            "200": {"description": "Users", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/AdminUserListResponse"}}}},
                            "401": {"description": "Admin token required"},
                        },
                    },
                },
                "/admin/users/{user_id}/status": {
                    "post": {
                        "summary": "[admin] Set a user's status to active|disabled",
                        "security": [{"bearerAuth": []}],
                        "parameters": [
                            {"name": "user_id", "in": "path", "required": True, "schema": {"type": "string"}},
                        ],
                        "requestBody": {
                            "required": True,
                            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/AdminStatusRequest"}}},
                        },
                        "responses": {
                            "200": {"description": "Status updated"},
                            "404": {"description": "Unknown user"},
                            "401": {"description": "Admin token required"},
                        },
                    }
                },
                "/admin/topup": {
                    "post": {
                        "summary": "[admin] Add credits to a user's balance",
                        "description": "Idempotent on `request_id`. Replay returns `duplicate=true` without re-crediting; useful when wiring real payment webhooks (use the payment processor's transaction ID as `request_id`).",
                        "security": [{"bearerAuth": []}],
                        "requestBody": {
                            "required": True,
                            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/AdminTopupRequest"}}},
                        },
                        "responses": {
                            "200": {"description": "Topup applied", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/AdminTopupResponse"}}}},
                            "400": {"description": "Invalid request"},
                            "404": {"description": "Unknown user"},
                            "401": {"description": "Admin token required"},
                        },
                    }
                },
                "/admin/ledger": {
                    "get": {
                        "summary": "[admin] Read recent ledger rows",
                        "security": [{"bearerAuth": []}],
                        "parameters": [
                            {"name": "user_id", "in": "query", "schema": {"type": "string"}, "description": "Filter to one user; omit for global feed."},
                            {"name": "limit", "in": "query", "schema": {"type": "integer", "default": 100, "maximum": 2000}},
                        ],
                        "responses": {
                            "200": {"description": "Ledger", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/AdminLedgerResponse"}}}},
                            "401": {"description": "Admin token required"},
                        },
                    }
                },
                "/admin/pricing": {
                    "get": {
                        "summary": "[admin] Inspect the active pricing table",
                        "security": [{"bearerAuth": []}],
                        "responses": {
                            "200": {"description": "Pricing", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/PricingResponse"}}}},
                            "401": {"description": "Admin token required"},
                        },
                    }
                },
                "/v1/register": {
                    "post": {
                        "summary": "Open a new user account (public)",
                        "description": (
                            "No auth required. Auto-generates a user_id like `u_<8hex>` and"
                            " returns a one-time plaintext API key. Starting balance is 0"
                            " credits unless the operator has set the `REGISTER_INITIAL_CREDITS`"
                            " env var. Designed to be called from `/register.html`."
                        ),
                        "requestBody": {
                            "required": False,
                            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/RegisterRequest"}}},
                        },
                        "responses": {
                            "200": {"description": "Account created", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/RegisterResponse"}}}},
                            "503": {"description": "Could not allocate a fresh user_id; transient — retry."},
                        },
                    }
                },
                "/v1/topup_packs": {
                    "get": {
                        "summary": "List available Stripe topup packs (catalog)",
                        "description": "Public catalog endpoint. Returns the configured packs from `config/stripe_packs.json` plus whether Stripe is configured server-side.",
                        "responses": {
                            "200": {"description": "Pack catalog", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/TopupPacksResponse"}}}},
                        },
                    }
                },
                "/v1/checkout/create": {
                    "post": {
                        "summary": "Create a Stripe Checkout Session for a topup",
                        "description": (
                            "Returns the hosted Checkout URL the user's browser should be"
                            " redirected to. Body must contain exactly one of `pack_id`"
                            " (preset SKU from /v1/topup_packs) or `custom_yuan` (1–9999元)."
                            " Admin tokens are rejected — this endpoint requires a real user"
                            " API key so the webhook knows who to credit."
                        ),
                        "security": [{"bearerAuth": []}],
                        "requestBody": {
                            "required": True,
                            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/CheckoutCreateRequest"}}},
                        },
                        "responses": {
                            "200": {"description": "Checkout session created", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/CheckoutCreateResponse"}}}},
                            "400": {"description": "Invalid pack_id / custom_yuan"},
                            "401": {"description": "User API key required"},
                            "502": {"description": "Stripe API error"},
                            "503": {"description": "Stripe not configured on this server"},
                        },
                    }
                },
                "/webhooks/stripe": {
                    "post": {
                        "summary": "Stripe webhook receiver (public; signed by Stripe)",
                        "description": (
                            "Stripe POSTs `checkout.session.completed` here after a user pays."
                            " Signature is verified via `STRIPE_WEBHOOK_SECRET_*`. On a paid"
                            " session we call `service.topup(user_id, credits, request_id="
                            "stripe:<session_id>)`, which is idempotent — Stripe's automatic"
                            " retries never double-credit. Other event types are accepted with"
                            " `{ignored_type}` so Stripe stops retrying."
                        ),
                        "requestBody": {
                            "required": True,
                            "content": {"application/json": {"schema": {"type": "object", "description": "Raw Stripe event payload."}}},
                        },
                        "responses": {
                            "200": {"description": "Event accepted (or ignored)", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/StripeWebhookResponse"}}}},
                            "400": {"description": "Stripe-Signature header missing or invalid"},
                            "503": {"description": "STRIPE_WEBHOOK_SECRET_* not configured"},
                        },
                    }
                },
            },
        }

    # Event logging uses shared function from conversation_store
    # (log_event_to_conversation imported at module level)

    @app.route("/health", methods=["GET"])
    def health() -> Response:
        return jsonify({
            "status": "ok",
            "service": "bazi-agent-api",
            "auth_configured": bool(os.environ.get("DEMO_API_TOKEN", "").strip()),
        })

    @app.route("/openapi.json", methods=["GET"])
    def openapi_json() -> Response:
        return jsonify(openapi_spec())

    @app.route("/docs", methods=["GET"])
    def swagger_docs() -> Response:
        html = """<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>BaZi Agent Demo API Docs</title>
    <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css" />
    <style>
      body { margin: 0; background: #f7f7f7; }
      .topbar { display: none; }
    </style>
  </head>
  <body>
    <div id="swagger-ui"></div>
    <script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
    <script>
      window.ui = SwaggerUIBundle({
        url: "/openapi.json",
        dom_id: "#swagger-ui",
        deepLinking: true,
        persistAuthorization: true,
      });
    </script>
  </body>
</html>
"""
        return Response(html, mimetype="text/html")

    @app.route("/")
    def index() -> Response:
        return send_from_directory(app.static_folder, "index.html")

    @app.route("/v1/users", methods=["POST"])
    def v1_upsert_user() -> Response:
        auth_error = require_demo_auth()
        if auth_error:
            return auth_error
        data = request.get_json(force=True) or {}
        if "birth" not in data:
            return api_error(400, "birth_required", "birth required")
        profile, error_response = upsert_profile_from_payload(data)
        if error_response:
            return error_response
        assert profile is not None
        return jsonify({"profile": public_profile(profile)})

    @app.route("/v1/users/<user_id>", methods=["GET"])
    def v1_get_user(user_id: str) -> Response:
        auth_error = require_demo_auth()
        if auth_error:
            return auth_error
        id_error = validate_safe_id(user_id, "user_id")
        if id_error:
            return api_error(400, "invalid_user_id", id_error)
        path = profile_path(user_id)
        if not os.path.exists(path):
            return api_error(404, "profile_not_found", "profile not found")
        return jsonify({"profile": public_profile(load_profile(path))})

    @app.route("/v1/ask", methods=["POST"])
    def v1_ask() -> Response:
        auth, ctx, err = _begin_billed_request("/v1/ask")
        if err:
            return err
        data = request.get_json(force=True) or {}
        resolved_uid, err = _resolved_user_id(ctx, data.get("user_id"), default="bazi_guest")
        if err:
            return err
        data["user_id"] = resolved_uid

        prepared, error_response = run_v1_request(data)
        if error_response:
            return error_response
        assert prepared is not None

        err = ctx["charge"]()
        if err:
            return err

        profile = prepared["profile"]
        convo_path = prepared["convo_path"]

        sink = ctx["wrap_sink"](lambda event: log_event_to_conversation(convo_path, event))

        try:
            result = run_turn_func(
                profile,
                prepared["question"],
                now=prepared["now"],
                event_sink=sink,
                history_rounds=prepared["history_rounds"],
            )
        except Exception:
            ctx["refund"]("endpoint_exception")
            raise
        append_event(convo_path, {"ts": prepared["now"].isoformat(), "type": "plan", "plan": result["plan"]})
        if result["time_context"]:
            append_event(convo_path, {"ts": prepared["now"].isoformat(), "type": "time_context", "value": result["time_context"]})
        save_profile(profile_path(profile["user_id"]), profile)

        if result.get("error"):
            ctx["refund"]("orchestrator_error")
        else:
            ctx["settle"]()

        response = jsonify(
            {
                "request_id": prepared["request_id"],
                "session_id": os.path.basename(convo_path),
                "user_id": profile["user_id"],
                "answer": result["response"],
                "plan": result["plan"],
                "time_context": result["time_context"],
                "error": bool(result.get("error", False)),
                "failed_nodes": result.get("failed_nodes", []),
                "skipped_nodes": result.get("skipped_nodes", []),
            }
        )
        return ctx["annotate"](response)

    @app.route("/v1/ask_stream", methods=["POST"])
    def v1_ask_stream() -> Response:
        auth, ctx, err = _begin_billed_request("/v1/ask_stream")
        if err:
            return err
        data = request.get_json(force=True) or {}
        resolved_uid, err = _resolved_user_id(ctx, data.get("user_id"), default="bazi_guest")
        if err:
            return err
        data["user_id"] = resolved_uid

        prepared, error_response = run_v1_request(data, stream=True)
        if error_response:
            return error_response
        assert prepared is not None

        err = ctx["charge"]()
        if err:
            return err

        profile = prepared["profile"]
        convo_path = prepared["convo_path"]
        event_q: queue.Queue = queue.Queue()

        receipt = ctx["state"]["receipt"]
        billing_kickoff_event = None
        if receipt is not None:
            billing_kickoff_event = {
                "type": "billing",
                "stage": "charged",
                "request_id": receipt.request_id,
                "amount_credits": receipt.amount_credits,
                "balance_after": receipt.balance_after,
                "endpoint": receipt.endpoint,
            }

        def base_sink(event: Dict) -> None:
            log_event_to_conversation(convo_path, event)
            public_event = public_stream_event(event)
            if public_event:
                event_q.put(public_event)

        sink = ctx["wrap_sink"](base_sink)

        def worker() -> None:
            settled = False
            try:
                result = run_turn_func(
                    profile,
                    prepared["question"],
                    now=prepared["now"],
                    event_sink=sink,
                    stream=True,
                    history_rounds=prepared["history_rounds"],
                )
                append_event(convo_path, {"ts": prepared["now"].isoformat(), "type": "plan", "plan": result["plan"]})
                if result["time_context"]:
                    append_event(
                        convo_path,
                        {"ts": prepared["now"].isoformat(), "type": "time_context", "value": result["time_context"]},
                    )
                save_profile(profile_path(profile["user_id"]), profile)
                if result.get("error"):
                    ctx["refund"]("orchestrator_error")
                else:
                    ctx["settle"]()
                    settled = True
            except Exception as exc:
                ctx["refund"]("endpoint_exception")
                event_q.put({"type": "error", "message": str(exc)})
            finally:
                if receipt is not None:
                    try:
                        balance_after = billing_service.get_balance(receipt.user_id)
                    except UnknownUserError:
                        balance_after = receipt.balance_after
                    event_q.put(
                        {
                            "type": "billing",
                            "stage": "settled" if settled else "refunded",
                            "request_id": receipt.request_id,
                            "amount_credits": receipt.amount_credits,
                            "balance_after": balance_after,
                            "endpoint": receipt.endpoint,
                        }
                    )
                event_q.put(None)

        threading.Thread(target=worker, daemon=True).start()

        def gen():
            yield f"data: {json.dumps({'type': 'session', 'request_id': prepared['request_id'], 'session_id': os.path.basename(convo_path)}, ensure_ascii=False)}\n\n"
            if billing_kickoff_event is not None:
                yield f"data: {json.dumps(billing_kickoff_event, ensure_ascii=False)}\n\n"
            while True:
                event = event_q.get()
                if event is None:
                    break
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

        return Response(gen(), mimetype="text/event-stream")

    @app.route("/v1/hepan/ask", methods=["POST"])
    def v1_hepan_ask() -> Response:
        auth, ctx, err = _begin_billed_request("/v1/hepan/ask")
        if err:
            return err
        data = request.get_json(force=True) or {}
        resolved_uid, err = _resolved_user_id(ctx, data.get("user_id"), default="hepan_guest")
        if err:
            return err
        data["user_id"] = resolved_uid

        question = (data.get("question") or "").strip()
        if not question:
            return api_error(400, "question_required", "question required")
        person_a_error = validate_person_payload(data.get("person_a"), "person_a")
        if person_a_error:
            return api_error(400, "invalid_person_a", person_a_error)
        person_b_error = validate_person_payload(data.get("person_b"), "person_b")
        if person_b_error:
            return api_error(400, "invalid_person_b", person_b_error)

        context, error_response = optional_conversation_context(data)
        if error_response:
            return error_response
        assert context is not None
        model_options, error_response = normalize_model_options(data)
        if error_response:
            return error_response
        assert model_options is not None

        err = ctx["charge"]()
        if err:
            return err

        now = dt.datetime.now()
        request_id = f"req_{uuid.uuid4().hex[:16]}"
        convo_path = context["convo_path"]
        append_event(
            convo_path,
            {
                "ts": now.isoformat(),
                "type": "user_message",
                "text": question,
                "request_id": request_id,
                "api_version": "v1",
                "method": "hepan",
            },
        )

        sink = ctx["wrap_sink"](lambda event: log_event_to_conversation(convo_path, event))

        try:
            result = run_hepan_turn_func(
                question,
                data["person_a"],
                data["person_b"],
                now=now,
                event_sink=sink,
                history_rounds=context["history_rounds"],
                model=model_options["model"],
                node_model_overrides=model_options["node_model_overrides"],
            )
        except ValueError as exc:
            ctx["refund"]("invalid_hepan_request")
            return api_error(400, "invalid_hepan_request", str(exc))
        except Exception:
            ctx["refund"]("endpoint_exception")
            raise

        response = jsonify(
            {
                "request_id": request_id,
                "session_id": os.path.basename(convo_path),
                "user_id": context["user_id"],
                "method": "hepan",
                "answer": result["response"],
                "compatibility": result["hepan"]["compatibility"],
            }
        )
        ctx["settle"]()
        return ctx["annotate"](response)

    @app.route("/v1/cezi/ask", methods=["POST"])
    def v1_cezi_ask() -> Response:
        auth, ctx, err = _begin_billed_request("/v1/cezi/ask")
        if err:
            return err
        data = request.get_json(force=True) or {}
        resolved_uid, err = _resolved_user_id(ctx, data.get("user_id"), default="cezi_guest")
        if err:
            return err
        data["user_id"] = resolved_uid

        question = (data.get("question") or "").strip()
        character = (data.get("character") or "").strip()
        if not question:
            return api_error(400, "question_required", "question required")
        if not character:
            return api_error(400, "character_required", "character required")

        context, error_response = optional_conversation_context(data)
        if error_response:
            return error_response
        assert context is not None
        model_options, error_response = normalize_model_options(data)
        if error_response:
            return error_response
        assert model_options is not None

        err = ctx["charge"]()
        if err:
            return err

        now = dt.datetime.now()
        request_id = f"req_{uuid.uuid4().hex[:16]}"
        convo_path = context["convo_path"]
        append_event(
            convo_path,
            {
                "ts": now.isoformat(),
                "type": "user_message",
                "text": question,
                "request_id": request_id,
                "api_version": "v1",
                "method": "cezi",
                "character": character,
            },
        )

        sink = ctx["wrap_sink"](lambda event: log_event_to_conversation(convo_path, event))

        try:
            result = run_cezi_turn_func(
                question,
                character,
                now=now,
                event_sink=sink,
                history_rounds=context["history_rounds"],
                model=model_options["model"],
                node_model_overrides=model_options["node_model_overrides"],
            )
        except ValueError as exc:
            ctx["refund"]("invalid_cezi_request")
            return api_error(400, "invalid_cezi_request", str(exc))
        except Exception:
            ctx["refund"]("endpoint_exception")
            raise

        response = jsonify(
            {
                "request_id": request_id,
                "session_id": os.path.basename(convo_path),
                "user_id": context["user_id"],
                "method": "cezi",
                "answer": result["response"],
                "character": result["character"],
            }
        )
        ctx["settle"]()
        return ctx["annotate"](response)

    @app.route("/v1/najia/ask", methods=["POST"])
    def v1_najia_ask() -> Response:
        data = request.get_json(force=True) or {}
        paraphrase = bool(data.get("paraphrase", False))
        variant_params = [("paraphrase", True)] if paraphrase else None
        auth, ctx, err = _begin_billed_request("/v1/najia/ask", variant_params=variant_params)
        if err:
            return err
        resolved_uid, err = _resolved_user_id(ctx, data.get("user_id"), default="najia_guest")
        if err:
            return err
        data["user_id"] = resolved_uid

        question = (data.get("question") or "").strip()
        if not question:
            return api_error(400, "question_required", "question required")

        context, error_response = optional_conversation_context(data)
        if error_response:
            return error_response
        assert context is not None
        model_options, error_response = normalize_model_options(data)
        if error_response:
            return error_response
        assert model_options is not None

        err = ctx["charge"]()
        if err:
            return err

        now = dt.datetime.now()
        request_id = f"req_{uuid.uuid4().hex[:16]}"
        convo_path = context["convo_path"]
        append_event(
            convo_path,
            {
                "ts": now.isoformat(),
                "type": "user_message",
                "text": question,
                "request_id": request_id,
                "api_version": "v1",
                "method": "najia",
                "paraphrase": paraphrase,
            },
        )

        sink = ctx["wrap_sink"](lambda event: log_event_to_conversation(convo_path, event))

        try:
            result = run_najia_turn_func(
                question,
                yao_values=data.get("yao_values"),
                now=now,
                event_sink=sink,
                history_rounds=context["history_rounds"],
                model=model_options["model"],
                node_model_overrides=model_options["node_model_overrides"],
                paraphrase=paraphrase,
            )
        except ValueError as exc:
            ctx["refund"]("invalid_najia_request")
            return api_error(400, "invalid_najia_request", str(exc))
        except Exception:
            ctx["refund"]("endpoint_exception")
            raise

        najia_result = result["najia"]
        response = jsonify(
            {
                "request_id": request_id,
                "session_id": os.path.basename(convo_path),
                "user_id": context["user_id"],
                "method": "najia",
                "answer": result["response"],
                "gua": {
                    "yao_values": najia_result["yao_values"],
                    "time_info": najia_result["time_info"],
                    "bengua": najia_result["bengua"],
                    "biangua": najia_result["biangua"],
                    "raw_text": najia_result["raw_text"],
                },
            }
        )
        ctx["settle"]()
        return ctx["annotate"](response)

    @app.route("/v1/zwds/ask", methods=["POST"])
    def v1_zwds_ask() -> Response:
        data = request.get_json(force=True) or {}
        include_star_gong_raw = data.get("include_star_gong")
        if include_star_gong_raw is not None and not isinstance(include_star_gong_raw, bool):
            # Charge resolution and full validation will reject it; surface early.
            return api_error(400, "invalid_include_star_gong", "include_star_gong must be bool")
        variant_params = (
            [("include_star_gong", True)] if include_star_gong_raw else None
        )
        auth, ctx, err = _begin_billed_request("/v1/zwds/ask", variant_params=variant_params)
        if err:
            return err
        resolved_uid, err = _resolved_user_id(ctx, data.get("user_id"), default="zwds_guest")
        if err:
            return err
        data["user_id"] = resolved_uid

        question = (data.get("question") or "").strip()
        if not question:
            return api_error(400, "question_required", "question required")

        birth = data.get("birth")
        if not isinstance(birth, dict):
            return api_error(400, "invalid_birth", "birth required")
        birth_error = validate_birth(birth)
        if birth_error:
            return api_error(400, "invalid_birth", birth_error)

        gender = data.get("gender", "male")
        if gender not in ("male", "female"):
            return api_error(400, "invalid_gender", "gender must be male|female")

        target_years = data.get("target_years")
        if target_years is not None:
            if not isinstance(target_years, list):
                return api_error(400, "invalid_target_years", "target_years must be list[int]")
            try:
                target_years = [int(y) for y in target_years]
            except (TypeError, ValueError):
                return api_error(400, "invalid_target_years", "target_years entries must be int")

        include_star_gong = include_star_gong_raw

        context, error_response = optional_conversation_context(data)
        if error_response:
            return error_response
        assert context is not None
        model_options, error_response = normalize_model_options(data)
        if error_response:
            return error_response
        assert model_options is not None

        err = ctx["charge"]()
        if err:
            return err

        now = dt.datetime.now()
        request_id = f"req_{uuid.uuid4().hex[:16]}"
        convo_path = context["convo_path"]
        append_event(
            convo_path,
            {
                "ts": now.isoformat(),
                "type": "user_message",
                "text": question,
                "request_id": request_id,
                "api_version": "v1",
                "method": "zwds",
            },
        )

        sink = ctx["wrap_sink"](lambda event: log_event_to_conversation(convo_path, event))

        try:
            result = run_zwds_turn_func(
                question,
                birth=birth,
                gender=gender,
                target_years=target_years,
                now=now,
                event_sink=sink,
                history_rounds=context["history_rounds"],
                model=model_options["model"],
                node_model_overrides=model_options["node_model_overrides"],
                include_star_gong=include_star_gong,
            )
        except ValueError as exc:
            ctx["refund"]("invalid_zwds_request")
            return api_error(400, "invalid_zwds_request", str(exc))
        except Exception:
            ctx["refund"]("endpoint_exception")
            raise

        zwds_result = result["zwds"]
        response = jsonify(
            {
                "request_id": request_id,
                "session_id": os.path.basename(convo_path),
                "user_id": context["user_id"],
                "method": "zwds",
                "answer": result["response"],
                "chart": {
                    "birth": zwds_result["birth"],
                    "gender": zwds_result["gender"],
                    "target_years": zwds_result["target_years"],
                    "benming_info": zwds_result["benming_info"],
                    "liunian_infos": zwds_result["liunian_infos"],
                    "raw_text": zwds_result["raw_text"],
                },
            }
        )
        ctx["settle"]()
        return ctx["annotate"](response)

    @app.route("/api/users", methods=["GET"])
    def list_users() -> Response:
        users = []
        users_root = os.path.join(root, "users")
        if os.path.exists(users_root):
            for name in sorted(os.listdir(users_root)):
                if os.path.exists(profile_path(name)):
                    users.append(name)
        return jsonify({"users": users})

    @app.route("/api/users", methods=["POST"])
    def create_user() -> Response:
        data = request.get_json(force=True) or {}
        user_id = (data.get("user_id") or "").strip()
        if not user_id:
            return jsonify({"error": "user_id required"}), 400
        birth = data.get("birth", {}) or {}
        birth_error = validate_birth(birth)
        if birth_error:
            return jsonify({"error": birth_error}), 400
        ensure_user_dirs(user_id)
        llm_model = data.get("llm_model", current_default_model())
        if not validate_model(llm_model):
            return jsonify({"error": f"invalid model: {llm_model}"}), 400
        node_overrides, node_overrides_error = normalize_node_model_overrides(data.get("node_model_overrides"))
        if node_overrides_error:
            return jsonify({"error": node_overrides_error}), 400
        profile = {
            "user_id": user_id,
            "birth": birth,
            "gender": data.get("gender", "male"),
            "birth_time_unknown": bool(data.get("birth_time_unknown", False)),
            "prompt_config": data.get("prompt_config", "lingyun_cat"),
            "llm_model": llm_model,
            "node_model_overrides": node_overrides or {},
            "node_cache": {},
        }
        save_profile(profile_path(user_id), profile)
        return jsonify({"user_id": user_id, "profile_path": profile_path(user_id)})

    @app.route("/api/profile", methods=["GET"])
    def get_profile() -> Response:
        user_id = (request.args.get("user_id") or "").strip()
        if not user_id:
            return jsonify({"error": "user_id required"}), 400
        path = profile_path(user_id)
        if not os.path.exists(path):
            return jsonify({"error": "profile not found"}), 404
        return jsonify(load_profile(path))

    @app.route("/api/profile", methods=["PUT"])
    def update_profile() -> Response:
        data = request.get_json(force=True) or {}
        user_id = (data.get("user_id") or "").strip()
        if not user_id:
            return jsonify({"error": "user_id required"}), 400
        path = profile_path(user_id)
        if not os.path.exists(path):
            return jsonify({"error": "profile not found"}), 404
        profile = load_profile(path)
        # Update allowed fields
        if "llm_model" in data:
            llm_model = data["llm_model"]
            if not validate_model(llm_model):
                return jsonify({"error": f"invalid model: {llm_model}"}), 400
            profile["llm_model"] = llm_model or current_default_model()
        if "node_model_overrides" in data:
            node_overrides, node_overrides_error = normalize_node_model_overrides(data.get("node_model_overrides"))
            if node_overrides_error:
                return jsonify({"error": node_overrides_error}), 400
            profile["node_model_overrides"] = node_overrides or {}
        if "prompt_config" in data:
            profile["prompt_config"] = data["prompt_config"]
        if "bypass_cache" in data:
            profile["bypass_cache"] = bool(data["bypass_cache"])
        save_profile(path, profile)
        return jsonify({"success": True, "profile": profile})

    @app.route("/api/models", methods=["GET"])
    def get_models() -> Response:
        return jsonify({
            "models": available_models(),
            "default": current_default_model(),
            "configurable_nodes": configurable_nodes(),
        })

    @app.route("/api/sessions", methods=["GET"])
    def list_sessions() -> Response:
        user_id = (request.args.get("user_id") or "").strip()
        if not user_id:
            return jsonify({"error": "user_id required"}), 400
        convo_dir = conversation_dir(user_id)
        sessions = []
        if os.path.exists(convo_dir):
            sessions = sorted([p for p in os.listdir(convo_dir) if p.endswith(".jsonl")])
        return jsonify({"sessions": sessions})

    def get_first_message_preview(convo_path: str, max_len: int = 50) -> str:
        """Extract the first user message as a preview for the conversation list."""
        try:
            with open(convo_path, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        event = json.loads(line)
                        if event.get("type") == "user_message":
                            text = event.get("text", "").strip()
                            if text:
                                return text[:max_len] + ("..." if len(text) > max_len else "")
                    except json.JSONDecodeError:
                        continue
        except (OSError, IOError):
            pass
        return ""

    @app.route("/api/session_metadata", methods=["GET"])
    def get_session_metadata() -> Response:
        """Return session list with first message preview for conversation sidebar."""
        user_id = (request.args.get("user_id") or "").strip()
        if not user_id:
            return jsonify({"error": "user_id required"}), 400
        convo_dir = conversation_dir(user_id)
        sessions = []
        if os.path.exists(convo_dir):
            for fname in sorted(os.listdir(convo_dir), reverse=True):
                if not fname.endswith(".jsonl"):
                    continue
                preview = get_first_message_preview(os.path.join(convo_dir, fname))
                sessions.append({
                    "session_id": fname,
                    "preview": preview,
                    "timestamp": fname.replace(".jsonl", "")
                })
        return jsonify({"sessions": sessions})

    @app.route("/api/sessions", methods=["POST"])
    def create_session() -> Response:
        data = request.get_json(force=True) or {}
        user_id = (data.get("user_id") or "").strip()
        if not user_id:
            return jsonify({"error": "user_id required"}), 400
        ensure_user_dirs(user_id)
        session_id = data.get("session_id")
        if session_id:
            session_id = normalize_session_id(session_id)
            convo_path = os.path.join(conversation_dir(user_id), session_id)
        else:
            convo_path = new_session_path(user_id)
        open(convo_path, "a", encoding="utf-8").close()
        return jsonify({"session_id": os.path.basename(convo_path), "path": convo_path})

    @app.route("/api/history", methods=["GET"])
    def get_history() -> Response:
        user_id = (request.args.get("user_id") or "").strip()
        session_id = (request.args.get("session_id") or "").strip()
        include_inputs = (request.args.get("include_inputs") or "").strip().lower() in ("1", "true", "yes")
        if not user_id or not session_id:
            return jsonify({"error": "user_id and session_id required"}), 400
        convo_path = os.path.join(conversation_dir(user_id), normalize_session_id(session_id))
        if not os.path.exists(convo_path):
            return jsonify({"error": "session not found"}), 404
        messages = []
        tool_invocations = []
        # events: ordered list of all displayable events
        events = []
        with open(convo_path, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                event_type = event.get("type")
                if event_type == "user_message":
                    msg = {"role": "user", "text": event.get("text", "")}
                    messages.append(msg)
                    events.append({"type": "message", "data": msg})
                elif event_type == "response":
                    # New response format with input_summary
                    msg = {
                        "role": "assistant",
                        "text": event.get("text", ""),
                        "input_summary": event.get("input_summary"),
                        "llm_prompt": event.get("llm_prompt"),
                    }
                    messages.append(msg)
                    events.append({"type": "message", "data": msg})
                elif event_type == "assistant_final":
                    # Legacy format - only add if no response was added for this turn
                    if not messages or messages[-1].get("role") != "assistant":
                        msg = {"role": "assistant", "text": event.get("text", "")}
                        messages.append(msg)
                        events.append({"type": "message", "data": msg})
                elif event_type == "tool_invocation":
                    tool_invocations.append(event)
                    events.append({"type": "tool_invocation", "data": event})
        payload: Dict[str, object] = {"messages": messages, "events": events}
        if include_inputs:
            payload["llm_prompts"] = load_latest_llm_prompts(convo_path)
        if tool_invocations:
            payload["tool_invocations"] = tool_invocations
        return jsonify(payload)

    @app.route("/api/ask", methods=["POST"])
    def ask_once() -> Response:
        data = request.get_json(force=True) or {}
        user_id = (data.get("user_id") or "").strip()
        question = (data.get("question") or "").strip()
        session_id = data.get("session_id")
        history_n = normalize_history_n(data.get("history_n"))
        if not user_id or not question:
            return jsonify({"error": "user_id and question required"}), 400
        ensure_user_dirs(user_id)
        profile = load_profile(profile_path(user_id))
        birth_error = validate_birth(profile.get("birth", {}) or {})
        if birth_error:
            return jsonify({"error": birth_error}), 400
        convo_path = os.path.join(
            conversation_dir(user_id),
            normalize_session_id(session_id) if session_id else os.path.basename(new_session_path(user_id)),
        )
        history_rounds = load_recent_rounds(convo_path, history_n)
        now = dt.datetime.now()
        append_event(convo_path, {"ts": now.isoformat(), "type": "user_message", "text": question})

        def sink(event: Dict) -> None:
            log_event_to_conversation(convo_path, event)

        result = run_turn_func(profile, question, now=now, event_sink=sink, history_rounds=history_rounds)
        # Note: tool_invocation events are logged via sink, plan/time_context kept for backward compatibility
        append_event(convo_path, {"ts": now.isoformat(), "type": "plan", "plan": result["plan"]})
        if result["time_context"]:
            append_event(convo_path, {"ts": now.isoformat(), "type": "time_context", "value": result["time_context"]})
        save_profile(profile_path(user_id), profile)
        return jsonify(
            {
                "session_id": os.path.basename(convo_path),
                "plan": result["plan"],
                "time_context": result["time_context"],
                "response": result["response"],
            }
        )

    @app.route("/api/ask_stream", methods=["POST"])
    def ask_stream() -> Response:
        data = request.get_json(force=True) or {}
        user_id = (data.get("user_id") or "").strip()
        question = (data.get("question") or "").strip()
        session_id = data.get("session_id")
        history_n = normalize_history_n(data.get("history_n"))
        if not user_id or not question:
            return jsonify({"error": "user_id and question required"}), 400
        ensure_user_dirs(user_id)
        profile = load_profile(profile_path(user_id))
        birth_error = validate_birth(profile.get("birth", {}) or {})
        if birth_error:
            return jsonify({"error": birth_error}), 400
        if session_id:
            session_id = normalize_session_id(session_id)
            convo_path = os.path.join(conversation_dir(user_id), session_id)
        else:
            convo_path = new_session_path(user_id)
            session_id = os.path.basename(convo_path)

        history_rounds = load_recent_rounds(convo_path, history_n)
        event_q: queue.Queue = queue.Queue()

        def sink(event: Dict) -> None:
            log_event_to_conversation(convo_path, event)
            event_q.put(event)

        def worker() -> None:
            now = dt.datetime.now()
            try:
                append_event(convo_path, {"ts": now.isoformat(), "type": "user_message", "text": question})
                result = run_turn_func(
                    profile,
                    question,
                    now=now,
                    event_sink=sink,
                    stream=True,
                    history_rounds=history_rounds,
                )
                # Note: tool_invocation events are logged via sink
                # Keep plan/time_context for backward compatibility
                append_event(convo_path, {"ts": now.isoformat(), "type": "plan", "plan": result["plan"]})
                if result["time_context"]:
                    append_event(
                        convo_path, {"ts": now.isoformat(), "type": "time_context", "value": result["time_context"]}
                    )
                save_profile(profile_path(user_id), profile)
            except Exception as exc:
                event_q.put({"type": "server_error", "error": str(exc)})
            finally:
                event_q.put(None)

        threading.Thread(target=worker, daemon=True).start()

        def gen():
            yield f"data: {json.dumps({'type': 'session', 'session_id': session_id}, ensure_ascii=False)}\n\n"
            while True:
                event = event_q.get()
                if event is None:
                    break
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

        return Response(gen(), mimetype="text/event-stream")

    # ======================================================================
    # Billing endpoints (user self-service + admin)
    # ======================================================================

    @app.route("/v1/balance", methods=["GET"])
    def v1_balance() -> Response:
        auth, err = billing.authenticate_request(allow_admin_bypass=False)
        if err:
            return err
        try:
            bal = billing_service.get_balance(auth["user_id"])
        except UnknownUserError as exc:
            return api_error(404, "unknown_user", str(exc))
        return jsonify(
            {
                "user_id": auth["user_id"],
                "balance_credits": bal,
                "daily_credits_limit": auth.get("daily_credits_limit"),
            }
        )

    @app.route("/v1/usage", methods=["GET"])
    def v1_usage() -> Response:
        auth, err = billing.authenticate_request(allow_admin_bypass=False)
        if err:
            return err
        try:
            limit = int(request.args.get("limit", "50"))
        except ValueError:
            return api_error(400, "invalid_limit", "limit must be int")
        limit = max(1, min(500, limit))
        rows = billing_service.list_usage(auth["user_id"], limit=limit)
        return jsonify({"user_id": auth["user_id"], "rows": rows})

    @app.route("/v1/api_keys", methods=["GET"])
    def v1_list_api_keys() -> Response:
        auth, err = billing.authenticate_request(allow_admin_bypass=False)
        if err:
            return err
        keys = billing_service.list_api_keys(auth["user_id"])
        # Never echo the plaintext or full hash; surface a short prefix and metadata.
        public = [
            {
                "key_id": k["api_key_hash"][:12],
                "label": k.get("label"),
                "created_at": k.get("created_at"),
                "last_seen_at": k.get("last_seen_at"),
                "revoked": bool(k.get("revoked")),
            }
            for k in keys
        ]
        return jsonify({"user_id": auth["user_id"], "api_keys": public})

    @app.route("/v1/api_keys", methods=["POST"])
    def v1_issue_api_key() -> Response:
        auth, err = billing.authenticate_request(allow_admin_bypass=False)
        if err:
            return err
        data = request.get_json(force=True, silent=True) or {}
        label = (data.get("label") or "").strip() or None
        try:
            plaintext = billing_service.issue_api_key(auth["user_id"], label=label)
        except UnknownUserError as exc:
            return api_error(404, "unknown_user", str(exc))
        return jsonify(
            {
                "user_id": auth["user_id"],
                "api_key": plaintext,
                "label": label,
                "warning": "Store this key now; it will not be shown again.",
            }
        )

    @app.route("/v1/api_keys/<key_id>", methods=["DELETE"])
    def v1_revoke_api_key(key_id: str) -> Response:
        auth, err = billing.authenticate_request(allow_admin_bypass=False)
        if err:
            return err
        # ``key_id`` here is the prefix shown by GET /v1/api_keys (first 12 hex chars).
        # We look up the user's keys and match by that prefix to avoid exposing
        # full hashes or plaintexts in URLs.
        user_keys = billing_service.list_api_keys(auth["user_id"])
        match = next(
            (k for k in user_keys if k["api_key_hash"].startswith(key_id)),
            None,
        )
        if match is None:
            return api_error(404, "key_not_found", "no api key with that prefix for this user.")
        revoked = billing_service.revoke_api_key(match["api_key_hash"])
        return jsonify({"user_id": auth["user_id"], "key_id": key_id, "revoked": bool(revoked)})

    # --- self-service registration ---------------------------------------

    @app.route("/v1/register", methods=["POST"])
    def v1_register() -> Response:
        """Public endpoint: open a fresh user account with a random user_id.

        No auth. Returns the one-time API key plaintext. Display name and
        a starter credit grant can be set via env vars (kept zero by
        default so we don't give away credits).
        """
        data = request.get_json(force=True, silent=True) or {}
        try:
            initial = int(os.environ.get("REGISTER_INITIAL_CREDITS", "0"))
        except ValueError:
            initial = 0
        if initial < 0:
            initial = 0
        # 8 hex chars = ~4 billion combinations; collision retry below.
        for attempt in range(5):
            user_id = "u_" + uuid.uuid4().hex[:8]
            try:
                out = billing_service.create_user(
                    user_id=user_id,
                    display_name=(data.get("display_name") or None),
                    initial_credits=initial,
                    issue_first_key=True,
                    key_label=(data.get("key_label") or "primary"),
                )
                break
            except ValueError:
                if attempt == 4:
                    return api_error(503, "register_collision", "could not allocate a fresh user_id; try again")
                continue
        return jsonify(
            {
                "user": out["user"],
                "api_key": out.get("api_key_plaintext"),
                "warning": "Save the api_key now — it will not be shown again.",
            }
        )

    # --- topup packs (catalog) -------------------------------------------

    @app.route("/v1/topup_packs", methods=["GET"])
    def v1_topup_packs() -> Response:
        """Public catalog endpoint: list available Stripe topup packs."""
        cfg = stripe_gateway.pack_config
        body = cfg.to_public_json()
        body["stripe_configured"] = stripe_gateway.configured
        body["stripe_publishable_key"] = stripe_gateway.publishable_key or None
        body["stripe_mode"] = stripe_gateway.mode
        body["payment_methods"] = list(stripe_gateway.payment_method_types)
        return jsonify(body)

    # --- Stripe checkout creation ----------------------------------------

    @app.route("/v1/checkout/create", methods=["POST"])
    def v1_checkout_create() -> Response:
        """Authenticated user creates a Stripe Checkout Session.

        Body: ``{pack_id?: str, custom_yuan?: int}`` — exactly one required.
        Returns ``{checkout_url, session_id, amount_fen, credits, currency}``.
        Admin tokens cannot create checkouts (since there's no real user_id
        bound to admin).
        """
        auth, err = billing.authenticate_request(allow_admin_bypass=False)
        if err is not None:
            return err
        if not stripe_gateway.configured:
            return api_error(
                503,
                "stripe_not_configured",
                "Stripe SDK is not configured on this server. Contact the admin.",
            )
        data = request.get_json(force=True, silent=True) or {}
        pack_id = (data.get("pack_id") or "").strip() or None
        custom_yuan = data.get("custom_yuan")
        if custom_yuan is not None:
            try:
                custom_yuan = int(custom_yuan)
            except (TypeError, ValueError):
                return api_error(400, "invalid_custom_yuan", "custom_yuan must be int")
        try:
            amount = stripe_gateway.resolve_amount(pack_id=pack_id, custom_yuan=custom_yuan)
        except ValueError as e:
            return api_error(400, "invalid_amount", str(e))
        try:
            session = stripe_gateway.build_checkout_session(
                user_id=auth["user_id"],
                amount_fen=amount["amount_fen"],
                credits=amount["credits"],
                currency=amount["currency"],
                label=amount["label"],
            )
        except StripeNotConfiguredError as e:
            return api_error(503, "stripe_not_configured", str(e))
        except Exception as e:  # noqa: BLE001 — anything Stripe raises bubbles up here
            return api_error(502, "stripe_error", f"checkout creation failed: {e}")
        return jsonify(
            {
                "checkout_url": session["url"],
                "session_id": session["id"],
                "amount_fen": session["amount_fen"],
                "credits": session["credits"],
                "currency": session["currency"],
            }
        )

    # --- Stripe webhook --------------------------------------------------

    @app.route("/webhooks/stripe", methods=["POST"])
    def webhooks_stripe() -> Response:
        """Receive Stripe webhooks (checkout.session.completed → topup).

        Signature verification is mandatory. Idempotent on
        ``checkout_session.id`` so Stripe retries don't double-credit.
        """
        if not stripe_gateway.webhook_configured:
            return api_error(503, "stripe_webhook_not_configured", "STRIPE_WEBHOOK_SECRET_* missing")
        signature = request.headers.get("Stripe-Signature", "")
        payload = request.get_data()
        try:
            event = stripe_gateway.verify_webhook(payload, signature)
        except StripeSignatureError as e:
            return api_error(400, "stripe_signature_invalid", str(e))
        except StripeNotConfiguredError as e:
            return api_error(503, "stripe_webhook_not_configured", str(e))

        event_type = event.get("type", "")
        if event_type != "checkout.session.completed":
            # Not interested — but still 200 OK so Stripe stops retrying.
            return jsonify({"received": True, "ignored_type": event_type})

        parsed = stripe_gateway.parse_checkout_completed(event)
        if parsed is None:
            return jsonify({"received": True, "ignored_reason": "session not paid or missing fields"})

        try:
            receipt = billing_service.topup(
                parsed["user_id"],
                parsed["credits"],
                request_id=f"stripe:{parsed['session_id']}",
                meta={
                    "source": "stripe",
                    "session_id": parsed["session_id"],
                    "currency": parsed["currency"],
                    "amount_fen": parsed["amount_fen"],
                    "customer_email": parsed.get("customer_email"),
                    "payment_intent": parsed.get("payment_intent"),
                },
            )
            duplicate = False
            balance_after = receipt.balance_after
        except DuplicateRequestError as dup:
            # Stripe retries are expected; surface 200 OK so it stops.
            duplicate = True
            balance_after = dup.balance_after
        except UnknownUserError as e:
            return api_error(404, "unknown_user", str(e))
        return jsonify(
            {
                "received": True,
                "user_id": parsed["user_id"],
                "credits_added": parsed["credits"],
                "balance_credits": balance_after,
                "duplicate": duplicate,
            }
        )

    # --- admin -----------------------------------------------------------

    @app.route("/admin/users", methods=["POST"])
    def admin_create_user() -> Response:
        err = billing.require_admin()
        if err:
            return err
        data = request.get_json(force=True, silent=True) or {}
        user_id = (data.get("user_id") or "").strip()
        id_error = validate_safe_id(user_id, "user_id")
        if id_error:
            return api_error(400, "invalid_user_id", id_error)
        try:
            initial_credits = int(data.get("initial_credits", 0))
        except (TypeError, ValueError):
            return api_error(400, "invalid_initial_credits", "initial_credits must be int")
        if initial_credits < 0:
            return api_error(400, "invalid_initial_credits", "initial_credits must be >= 0")
        daily_limit = data.get("daily_credits_limit")
        if daily_limit is not None:
            try:
                daily_limit = int(daily_limit)
            except (TypeError, ValueError):
                return api_error(400, "invalid_daily_limit", "daily_credits_limit must be int")
            if daily_limit < 0:
                return api_error(400, "invalid_daily_limit", "daily_credits_limit must be >= 0")
        try:
            out = billing_service.create_user(
                user_id=user_id,
                display_name=(data.get("display_name") or None),
                initial_credits=initial_credits,
                daily_credits_limit=daily_limit,
                issue_first_key=bool(data.get("issue_first_key", True)),
                key_label=(data.get("key_label") or None),
            )
        except ValueError as exc:
            return api_error(409, "user_exists", str(exc))
        return jsonify(
            {
                "user": out["user"],
                "api_key": out.get("api_key_plaintext"),
                "warning": "If api_key is non-null, store it now; it will not be shown again.",
            }
        )

    @app.route("/admin/users", methods=["GET"])
    def admin_list_users() -> Response:
        err = billing.require_admin()
        if err:
            return err
        try:
            limit = int(request.args.get("limit", "200"))
        except ValueError:
            return api_error(400, "invalid_limit", "limit must be int")
        users = billing_service.admin_list_users(limit=max(1, min(1000, limit)))
        return jsonify({"users": users})

    @app.route("/admin/users/<user_id>/status", methods=["POST"])
    def admin_set_user_status(user_id: str) -> Response:
        err = billing.require_admin()
        if err:
            return err
        data = request.get_json(force=True, silent=True) or {}
        status = (data.get("status") or "").strip()
        if status not in ("active", "disabled"):
            return api_error(400, "invalid_status", "status must be 'active' or 'disabled'")
        try:
            billing_service.admin_set_user_status(user_id, status)
        except UnknownUserError as exc:
            return api_error(404, "unknown_user", str(exc))
        return jsonify({"user_id": user_id, "status": status})

    @app.route("/admin/topup", methods=["POST"])
    def admin_topup() -> Response:
        err = billing.require_admin()
        if err:
            return err
        data = request.get_json(force=True, silent=True) or {}
        user_id = (data.get("user_id") or "").strip()
        if not user_id:
            return api_error(400, "user_id_required", "user_id required")
        try:
            amount = int(data.get("amount_credits", 0))
        except (TypeError, ValueError):
            return api_error(400, "invalid_amount", "amount_credits must be int")
        if amount <= 0:
            return api_error(400, "invalid_amount", "amount_credits must be > 0")
        explicit_request_id = (data.get("request_id") or "").strip() or None
        try:
            receipt = billing_service.topup(
                user_id,
                amount,
                request_id=explicit_request_id,
                meta={"note": data.get("note"), "source": data.get("source", "admin")},
            )
        except UnknownUserError as exc:
            return api_error(404, "unknown_user", str(exc))
        except DuplicateRequestError as exc:
            return jsonify(
                {
                    "user_id": user_id,
                    "amount_credits": amount,
                    "balance_credits": exc.balance_after,
                    "request_id": exc.request_id,
                    "duplicate": True,
                }
            )
        return jsonify(
            {
                "user_id": user_id,
                "amount_credits": amount,
                "balance_credits": receipt.balance_after,
                "request_id": receipt.request_id,
                "duplicate": False,
            }
        )

    @app.route("/admin/ledger", methods=["GET"])
    def admin_ledger() -> Response:
        err = billing.require_admin()
        if err:
            return err
        user_id = request.args.get("user_id") or None
        try:
            limit = int(request.args.get("limit", "100"))
        except ValueError:
            return api_error(400, "invalid_limit", "limit must be int")
        rows = billing_service.admin_list_ledger(user_id=user_id, limit=max(1, min(2000, limit)))
        return jsonify({"rows": rows})

    @app.route("/admin/pricing", methods=["GET"])
    def admin_pricing() -> Response:
        err = billing.require_admin()
        if err:
            return err
        return jsonify(billing_pricing.as_dict())

    return app


def main() -> None:
    app = create_app()
    host = os.environ.get("HOST", "0.0.0.0")
    try:
        port = int(os.environ.get("PORT", "8000"))
    except ValueError:
        port = 8000
    app.run(host=host, port=port, debug=False)


if __name__ == "__main__":
    main()
