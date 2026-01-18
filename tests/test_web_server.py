from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, ROOT)

from web_server import create_app


def test_web_api_flow(tmp_path) -> None:
    def fake_run_turn(profile, question, now=None, event_sink=None, stream=False, history_rounds=None):
        if event_sink:
            event_sink({"type": "llm_prompt", "node": "OVERALL", "system_prompt": "sys", "user_prompt": "user"})
            event_sink({"type": "plan", "plan": {"aspects": ["CAREER"], "time": {"need_tool": False}}})
            if stream:
                event_sink({"type": "node_start", "node": "OVERALL"})
                event_sink({"type": "node_delta", "node": "OVERALL", "delta": "stub"})
                event_sink(
                    {
                        "type": "node_end",
                        "node": "OVERALL",
                        "output": {"type": "report", "content": "final"},
                    }
                )
        return {"plan": {"aspects": ["CAREER"], "time": {"need_tool": False}}, "time_context": None, "response": "ok", "outputs": {}}

    app = create_app(run_turn_func=fake_run_turn, storage_root=str(tmp_path))
    client = app.test_client()

    resp = client.post(
        "/api/users",
        json={
            "user_id": "u_test",
            "birth": {"year": 1990, "month": 1, "day": 1, "hour": 8, "minute": 0, "second": 0},
            "gender": "male",
            "birth_time_unknown": False,
        },
    )
    assert resp.status_code == 200

    resp = client.get("/api/users")
    data = resp.get_json()
    assert "u_test" in data["users"]

    resp = client.post("/api/sessions", json={"user_id": "u_test"})
    session_id = resp.get_json()["session_id"]
    assert session_id.endswith(".jsonl")

    resp = client.get(f"/api/history?user_id=u_test&session_id={session_id}")
    assert resp.status_code == 200

    resp = client.post(
        "/api/ask_stream",
        json={"user_id": "u_test", "question": "hi", "session_id": session_id, "history_n": 2},
        buffered=True,
    )
    body = b"".join(resp.response).decode("utf-8")
    assert "data:" in body
    assert "assistant_final" in body

    convo_path = os.path.join(tmp_path, "users", "u_test", "conversations", session_id)
    with open(convo_path, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]
    assert any("\"llm_prompt\"" in line for line in lines), "llm_prompt not logged"

    resp = client.get(f"/api/history?user_id=u_test&session_id={session_id}&include_inputs=1")
    data = resp.get_json()
    assert "llm_prompts" in data
    assert "OVERALL" in data["llm_prompts"]
