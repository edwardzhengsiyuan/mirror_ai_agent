"""Minimal Flask server for the bazi agent web UI."""

from __future__ import annotations

import datetime as dt
import json
import os
import queue
import threading
from typing import Callable, Dict, Optional

from flask import Flask, Response, jsonify, request, send_from_directory

from agent.models import AVAILABLE_MODELS, DEFAULT_MODEL
from agent.orchestrator import run_turn
from agent.storage.conversation_store import append_event, load_recent_rounds, load_latest_llm_prompts, log_event_to_conversation
from agent.storage.profile_store import load_profile, save_profile


def create_app(
    run_turn_func: Callable = run_turn,
    storage_root: Optional[str] = None,
) -> Flask:
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

    # Event logging uses shared function from conversation_store
    # (log_event_to_conversation imported at module level)

    @app.route("/")
    def index() -> Response:
        return send_from_directory(app.static_folder, "index.html")

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
