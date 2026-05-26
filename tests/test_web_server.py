from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, ROOT)

from web_server import create_app


def _fake_turn(profile, question, now=None, event_sink=None, stream=False, history_rounds=None):
    if event_sink:
        event_sink({"type": "plan", "plan": {"aspects": ["CAREER"], "time": {"need_tool": False}, "times": []}})
        if stream:
            event_sink({"type": "node_start", "node": "OVERALL"})
            event_sink({"type": "response_delta", "delta": "o"})
        event_sink({"type": "response", "text": "ok", "duration_ms": 1})
    return {
        "plan": {"aspects": ["CAREER"], "time": {"need_tool": False}, "times": []},
        "time_context": None,
        "response": "ok",
        "outputs": {},
    }


def _fake_hepan_turn(
    question,
    person_a,
    person_b,
    now=None,
    event_sink=None,
    stream=False,
    history_rounds=None,
    model=None,
    node_model_overrides=None,
):
    if event_sink:
        event_sink({
            "type": "tool_invocation",
            "tool": "HEPAN",
            "output": {"type": "hepan"},
            "duration_ms": 1,
        })
        event_sink({"type": "response", "text": "hepan ok", "duration_ms": 1})
    return {
        "method": "hepan",
        "response": "hepan ok",
        "hepan": {
            "compatibility": {
                "score": {"overall": 66.0},
                "shengxiao_hehun": {},
                "wuxing_vector": {},
                "a_wang_b": [],
                "b_wang_a": [],
            }
        },
    }


def _fake_cezi_turn(
    question,
    character,
    now=None,
    event_sink=None,
    stream=False,
    history_rounds=None,
    model=None,
    node_model_overrides=None,
):
    if event_sink:
        event_sink({
            "type": "tool_invocation",
            "tool": "CEZI",
            "output": {"type": "cezi", "character": character},
            "duration_ms": 1,
        })
        event_sink({"type": "response", "text": "cezi ok", "duration_ms": 1})
    return {
        "method": "cezi",
        "response": "cezi ok",
        "character": character,
        "cezi": {"type": "cezi", "character": character, "question": question},
    }


def _fake_najia_turn(
    question,
    yao_values=None,
    now=None,
    event_sink=None,
    stream=False,
    history_rounds=None,
    model=None,
    node_model_overrides=None,
):
    values = yao_values or [0, 1, 2, 3, 4, 5]
    if event_sink:
        event_sink({
            "type": "tool_invocation",
            "tool": "NAJIA",
            "output": {"type": "najia", "yao_values": values},
            "duration_ms": 1,
        })
        event_sink({"type": "response", "text": "najia ok", "duration_ms": 1})
    return {
        "method": "najia",
        "response": "najia ok",
        "najia": {
            "type": "najia",
            "yao_values": values,
            "time_info": {},
            "bengua": {"fullname": "本卦"},
            "biangua": {"fullname": "变卦"},
            "raw_text": "raw",
        },
    }


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
                # Emit response event (replaced assistant_final)
                event_sink({"type": "response", "text": "ok"})
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
    # assistant_final was renamed to response event type
    assert "response" in body

    convo_path = os.path.join(tmp_path, "users", "u_test", "conversations", session_id)
    with open(convo_path, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]
    assert any("\"llm_prompt\"" in line for line in lines), "llm_prompt not logged"

    resp = client.get(f"/api/history?user_id=u_test&session_id={session_id}&include_inputs=1")
    data = resp.get_json()
    assert "llm_prompts" in data
    assert "OVERALL" in data["llm_prompts"]


def test_models_api_uses_route_config(tmp_path) -> None:
    app = create_app(run_turn_func=_fake_turn, storage_root=str(tmp_path))
    client = app.test_client()

    resp = client.get("/api/models")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["models"] == ["gemini-3.1-pro-preview", "gemini-3-flash-preview", "qwen3-max"]
    assert data["default"] == "gemini-3.1-pro-preview"
    assert "SHISHEN" in data["configurable_nodes"]
    assert "RESPONSE" in data["configurable_nodes"]
    assert "gpt-5-mini" not in data["models"]
    assert "claude-sonnet-4-6" not in data["models"]


def test_profile_node_model_overrides(tmp_path) -> None:
    app = create_app(run_turn_func=_fake_turn, storage_root=str(tmp_path))
    client = app.test_client()

    resp = client.post(
        "/api/users",
        json={
            "user_id": "bad_model",
            "birth": {"year": 1990, "month": 1, "day": 1},
            "llm_model": "gpt-5-mini",
        },
    )
    assert resp.status_code == 400

    resp = client.post(
        "/api/users",
        json={
            "user_id": "u_test",
            "birth": {"year": 1990, "month": 1, "day": 1},
            "node_model_overrides": {"shishen": "qwen3-max", "response": "gemini-3.1-pro-preview"},
        },
    )
    assert resp.status_code == 200

    profile = client.get("/api/profile?user_id=u_test").get_json()
    assert profile["node_model_overrides"] == {
        "SHISHEN": "qwen3-max",
        "RESPONSE": "gemini-3.1-pro-preview",
    }

    resp = client.put(
        "/api/profile",
        json={"user_id": "u_test", "node_model_overrides": {"CAREER": "gpt-5-mini"}},
    )
    assert resp.status_code == 400
    assert "invalid model" in resp.get_json()["error"]


def test_v1_docs_and_auth(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DEMO_API_TOKEN", "secret")
    app = create_app(
        run_turn_func=_fake_turn,
        run_hepan_turn_func=_fake_hepan_turn,
        run_cezi_turn_func=_fake_cezi_turn,
        storage_root=str(tmp_path),
    )
    client = app.test_client()

    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json()["auth_configured"] is True

    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    spec = resp.get_json()
    assert "/v1/ask" in spec["paths"]
    assert "/v1/ask_stream" in spec["paths"]
    assert "/v1/hepan/ask" in spec["paths"]
    assert "/v1/cezi/ask" in spec["paths"]
    assert "/v1/najia/ask" in spec["paths"]

    resp = client.get("/docs")
    assert resp.status_code == 200
    assert b"SwaggerUIBundle" in resp.data

    resp = client.post("/v1/ask", json={"user_id": "u_demo", "question": "hi"})
    assert resp.status_code == 401


def test_v1_ask_creates_profile_and_returns_public_shape(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DEMO_API_TOKEN", "secret")
    app = create_app(run_turn_func=_fake_turn, storage_root=str(tmp_path))
    client = app.test_client()
    headers = {"Authorization": "Bearer secret"}

    resp = client.post(
        "/v1/ask",
        headers=headers,
        json={
            "user_id": "u_demo",
            "birth": {"year": 1990, "month": 1, "day": 1, "hour": 8, "minute": 0, "second": 0},
            "gender": "male",
            "session_id": "demo_session",
            "question": "hi",
        },
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["answer"] == "ok"
    assert data["session_id"] == "demo_session.jsonl"
    assert data["user_id"] == "u_demo"
    assert "outputs" not in data

    profile_path = os.path.join(tmp_path, "users", "u_demo", "profile.json")
    assert os.path.exists(profile_path)

    resp = client.get("/v1/users/u_demo", headers=headers)
    assert resp.status_code == 200
    profile = resp.get_json()["profile"]
    assert profile["user_id"] == "u_demo"
    assert "node_cache" not in profile


def test_v1_stream_filters_internal_events(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DEMO_API_TOKEN", "secret")
    app = create_app(run_turn_func=_fake_turn, storage_root=str(tmp_path))
    client = app.test_client()

    resp = client.post(
        "/v1/ask_stream",
        headers={"Authorization": "Bearer secret"},
        json={
            "user_id": "u_demo",
            "birth": {"year": 1990, "month": 1, "day": 1},
            "question": "hi",
        },
        buffered=True,
    )
    assert resp.status_code == 200
    body = b"".join(resp.response).decode("utf-8")
    assert "answer_delta" in body
    assert "node_status" in body
    assert "system_prompt" not in body


def test_v1_hepan_ask_returns_public_shape(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DEMO_API_TOKEN", "secret")
    app = create_app(run_turn_func=_fake_turn, run_hepan_turn_func=_fake_hepan_turn, storage_root=str(tmp_path))
    client = app.test_client()

    payload = {
        "user_id": "u_demo",
        "session_id": "hepan_session",
        "question": "我们适合长期发展吗？",
        "person_a": {
            "name": "A",
            "gender": "female",
            "birth": {"year": 1990, "month": 1, "day": 1, "hour": 8},
        },
        "person_b": {
            "name": "B",
            "gender": "male",
            "birth": {"year": 1991, "month": 2, "day": 2, "hour": 9},
        },
    }
    resp = client.post("/v1/hepan/ask", headers={"Authorization": "Bearer secret"}, json=payload)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["method"] == "hepan"
    assert data["answer"] == "hepan ok"
    assert data["compatibility"]["score"]["overall"] == 66.0
    assert data["session_id"] == "hepan_session.jsonl"


def test_v1_cezi_ask_returns_public_shape(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DEMO_API_TOKEN", "secret")
    app = create_app(run_turn_func=_fake_turn, run_cezi_turn_func=_fake_cezi_turn, storage_root=str(tmp_path))
    client = app.test_client()

    resp = client.post(
        "/v1/cezi/ask",
        headers={"Authorization": "Bearer secret"},
        json={
            "user_id": "u_demo",
            "session_id": "cezi_session",
            "question": "这个项目合作能不能成？",
            "character": "合",
        },
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["method"] == "cezi"
    assert data["answer"] == "cezi ok"
    assert data["character"] == "合"
    assert data["session_id"] == "cezi_session.jsonl"


def test_v1_najia_ask_returns_public_shape(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DEMO_API_TOKEN", "secret")
    app = create_app(run_turn_func=_fake_turn, run_najia_turn_func=_fake_najia_turn, storage_root=str(tmp_path))
    client = app.test_client()

    resp = client.post(
        "/v1/najia/ask",
        headers={"Authorization": "Bearer secret"},
        json={
            "user_id": "u_demo",
            "session_id": "najia_session",
            "question": "这个项目三个月内能不能推进成功？",
            "yao_values": [0, 1, 2, 3, 4, 5],
        },
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["method"] == "najia"
    assert data["answer"] == "najia ok"
    assert data["gua"]["yao_values"] == [0, 1, 2, 3, 4, 5]
    assert data["session_id"] == "najia_session.jsonl"
