"""Minimal Flask server for the bazi agent web UI."""

from __future__ import annotations

import datetime as dt
import json
import os
import queue
import threading
from typing import Callable, Dict, Optional

from flask import Flask, Response, jsonify, request, send_from_directory

from agent.orchestrator import run_turn
from agent.storage.conversation_store import append_event, load_recent_rounds, load_latest_llm_prompts
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

    def log_llm_prompt(convo_path: str, event: Dict) -> None:
        if event.get("type") != "llm_prompt":
            return
        append_event(
            convo_path,
            {
                "ts": dt.datetime.now().isoformat(),
                "type": "llm_prompt",
                "node": event.get("node"),
                "system_prompt": event.get("system_prompt", ""),
                "user_prompt": event.get("user_prompt", ""),
            },
        )

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
        profile = {
            "user_id": user_id,
            "birth": birth,
            "gender": data.get("gender", "male"),
            "birth_time_unknown": bool(data.get("birth_time_unknown", False)),
            "prompt_config": data.get("prompt_config", "lingyun_cat"),
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
        with open(convo_path, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if event.get("type") == "user_message":
                    messages.append({"role": "user", "text": event.get("text", "")})
                elif event.get("type") == "assistant_final":
                    messages.append({"role": "assistant", "text": event.get("text", "")})
        payload: Dict[str, object] = {"messages": messages}
        if include_inputs:
            payload["llm_prompts"] = load_latest_llm_prompts(convo_path)
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
            log_llm_prompt(convo_path, event)

        result = run_turn_func(profile, question, now=now, event_sink=sink, history_rounds=history_rounds)
        append_event(convo_path, {"ts": now.isoformat(), "type": "plan", "plan": result["plan"]})
        if result["time_context"]:
            append_event(convo_path, {"ts": now.isoformat(), "type": "time_context", "value": result["time_context"]})
        append_event(convo_path, {"ts": now.isoformat(), "type": "assistant_final", "text": result["response"]})
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
            log_llm_prompt(convo_path, event)
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
                append_event(convo_path, {"ts": now.isoformat(), "type": "plan", "plan": result["plan"]})
                if result["time_context"]:
                    append_event(
                        convo_path, {"ts": now.isoformat(), "type": "time_context", "value": result["time_context"]}
                    )
                append_event(convo_path, {"ts": now.isoformat(), "type": "assistant_final", "text": result["response"]})
                save_profile(profile_path(user_id), profile)
                event_q.put({"type": "assistant_final", "text": result["response"]})
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
