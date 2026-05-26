"""Minimal Flask server for the bazi agent web UI."""

from __future__ import annotations

import datetime as dt
import json
import os
import queue
import re
import threading
import uuid
from typing import Any, Callable, Dict, Optional

from flask import Flask, Response, jsonify, request, send_from_directory

from agent.models import AVAILABLE_MODELS, DEFAULT_MODEL
from agent.orchestrator_hepan import run_hepan_turn
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

    def public_profile(profile: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "user_id": profile.get("user_id"),
            "birth": profile.get("birth"),
            "gender": profile.get("gender", "male"),
            "birth_time_unknown": bool(profile.get("birth_time_unknown", False)),
            "prompt_config": profile.get("prompt_config", "lingyun_cat"),
            "llm_model": profile.get("llm_model", DEFAULT_MODEL),
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
            llm_model = data.get("llm_model", DEFAULT_MODEL)
            if llm_model and llm_model not in AVAILABLE_MODELS:
                return None, api_error(400, "invalid_model", f"invalid model: {llm_model}")
            profile = {
                "user_id": user_id,
                "birth": birth,
                "gender": data.get("gender", "male"),
                "birth_time_unknown": bool(data.get("birth_time_unknown", False)),
                "prompt_config": data.get("prompt_config", "lingyun_cat"),
                "llm_model": llm_model or DEFAULT_MODEL,
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
            if llm_model and llm_model not in AVAILABLE_MODELS:
                return None, api_error(400, "invalid_model", f"invalid model: {llm_model}")
            profile["llm_model"] = llm_model or DEFAULT_MODEL
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
                        "bearerFormat": "demo-token",
                    }
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
                            "llm_model": {"type": "string", "example": DEFAULT_MODEL},
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
                            "llm_model": {"type": "string", "example": DEFAULT_MODEL},
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
                                },
                            }
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
                        "security": [{"bearerAuth": []}],
                        "requestBody": {
                            "required": True,
                            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/AskRequest"}}},
                        },
                        "responses": {
                            "200": {"description": "Answer", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/AskResponse"}}}},
                            "400": {"description": "Invalid request"},
                            "401": {"description": "Unauthorized"},
                        },
                    }
                },
                "/v1/ask_stream": {
                    "post": {
                        "summary": "Run a streaming BaZi Q&A turn using Server-Sent Events",
                        "security": [{"bearerAuth": []}],
                        "requestBody": {
                            "required": True,
                            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/AskRequest"}}},
                        },
                        "responses": {
                            "200": {
                                "description": "SSE stream. Events include session, node_status, plan, tool_invocation, answer_delta, answer, and error.",
                                "content": {"text/event-stream": {"schema": {"type": "string"}}},
                            },
                            "400": {"description": "Invalid request"},
                            "401": {"description": "Unauthorized"},
                        },
                    }
                },
                "/v1/hepan/ask": {
                    "post": {
                        "summary": "Run a synchronous BaZi HePan compatibility turn",
                        "security": [{"bearerAuth": []}],
                        "requestBody": {
                            "required": True,
                            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/HepanRequest"}}},
                        },
                        "responses": {
                            "200": {"description": "HePan answer", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/HepanResponse"}}}},
                            "400": {"description": "Invalid request"},
                            "401": {"description": "Unauthorized"},
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
        auth_error = require_demo_auth()
        if auth_error:
            return auth_error
        data = request.get_json(force=True) or {}
        prepared, error_response = run_v1_request(data)
        if error_response:
            return error_response
        assert prepared is not None

        profile = prepared["profile"]
        convo_path = prepared["convo_path"]

        def sink(event: Dict) -> None:
            log_event_to_conversation(convo_path, event)

        result = run_turn_func(
            profile,
            prepared["question"],
            now=prepared["now"],
            event_sink=sink,
            history_rounds=prepared["history_rounds"],
        )
        append_event(convo_path, {"ts": prepared["now"].isoformat(), "type": "plan", "plan": result["plan"]})
        if result["time_context"]:
            append_event(convo_path, {"ts": prepared["now"].isoformat(), "type": "time_context", "value": result["time_context"]})
        save_profile(profile_path(profile["user_id"]), profile)
        return jsonify(
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

    @app.route("/v1/ask_stream", methods=["POST"])
    def v1_ask_stream() -> Response:
        auth_error = require_demo_auth()
        if auth_error:
            return auth_error
        data = request.get_json(force=True) or {}
        prepared, error_response = run_v1_request(data, stream=True)
        if error_response:
            return error_response
        assert prepared is not None

        profile = prepared["profile"]
        convo_path = prepared["convo_path"]
        event_q: queue.Queue = queue.Queue()

        def sink(event: Dict) -> None:
            log_event_to_conversation(convo_path, event)
            public_event = public_stream_event(event)
            if public_event:
                event_q.put(public_event)

        def worker() -> None:
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
            except Exception as exc:
                event_q.put({"type": "error", "message": str(exc)})
            finally:
                event_q.put(None)

        threading.Thread(target=worker, daemon=True).start()

        def gen():
            yield f"data: {json.dumps({'type': 'session', 'request_id': prepared['request_id'], 'session_id': os.path.basename(convo_path)}, ensure_ascii=False)}\n\n"
            while True:
                event = event_q.get()
                if event is None:
                    break
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

        return Response(gen(), mimetype="text/event-stream")

    @app.route("/v1/hepan/ask", methods=["POST"])
    def v1_hepan_ask() -> Response:
        auth_error = require_demo_auth()
        if auth_error:
            return auth_error
        data = request.get_json(force=True) or {}
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

        def sink(event: Dict) -> None:
            log_event_to_conversation(convo_path, event)

        try:
            result = run_hepan_turn_func(
                question,
                data["person_a"],
                data["person_b"],
                now=now,
                event_sink=sink,
                history_rounds=context["history_rounds"],
                model=data.get("llm_model"),
            )
        except ValueError as exc:
            return api_error(400, "invalid_hepan_request", str(exc))

        return jsonify(
            {
                "request_id": request_id,
                "session_id": os.path.basename(convo_path),
                "user_id": context["user_id"],
                "method": "hepan",
                "answer": result["response"],
                "compatibility": result["hepan"]["compatibility"],
            }
        )

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
        llm_model = data.get("llm_model", DEFAULT_MODEL)
        if llm_model and llm_model not in AVAILABLE_MODELS:
            llm_model = DEFAULT_MODEL
        profile = {
            "user_id": user_id,
            "birth": birth,
            "gender": data.get("gender", "male"),
            "birth_time_unknown": bool(data.get("birth_time_unknown", False)),
            "prompt_config": data.get("prompt_config", "lingyun_cat"),
            "llm_model": llm_model,
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
            if llm_model and llm_model not in AVAILABLE_MODELS:
                return jsonify({"error": f"invalid model: {llm_model}"}), 400
            profile["llm_model"] = llm_model or DEFAULT_MODEL
        if "prompt_config" in data:
            profile["prompt_config"] = data["prompt_config"]
        if "bypass_cache" in data:
            profile["bypass_cache"] = bool(data["bypass_cache"])
        save_profile(path, profile)
        return jsonify({"success": True, "profile": profile})

    @app.route("/api/models", methods=["GET"])
    def get_models() -> Response:
        return jsonify({
            "models": AVAILABLE_MODELS,
            "default": DEFAULT_MODEL,
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

    return app


def main() -> None:
    app = create_app()
    app.run(host="0.0.0.0", port=8000, debug=False)


if __name__ == "__main__":
    main()
