"""Cross-entry-point regressions using synthetic data only."""
import io
import json
import os

import pytest

import web_server
from agent.storage.locking import ProfileLease, profile_lock_path
from agent.storage import conversation_store
from agent.tools import llm_tool


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setattr(web_server, "load_env_file", lambda _: None)
    monkeypatch.setenv("LLM_MODE", "stub")
    monkeypatch.setenv("APP_SECRET_KEY", "synthetic-audit-secret-123456789012345")
    monkeypatch.setenv("DEMO_API_TOKEN", "audit-admin")
    monkeypatch.setenv("BILLING_DB_PATH", str(tmp_path / "billing.db"))
    monkeypatch.setenv("STRIPE_SECRET_KEY_TEST", "sk_test_synthetic")
    monkeypatch.setenv("STRIPE_MODE", "test")
    app = web_server.create_app(storage_root=str(tmp_path / "storage"))
    app.config["TESTING"] = True
    return app


@pytest.mark.parametrize("method", ["cezi", "najia", "hepan", "zwds"])
def test_all_conversation_writers_honor_profile_lease(app, tmp_path, method):
    birth = {"year": 1990, "month": 1, "day": 1, "hour": 8}
    person = {"birth": birth, "gender": "male"}
    payload = {"user_id": "audit-user", "session_id": "shared", "question": "test",
               "character": "山", "birth": birth, "person_a": person, "person_b": person}
    path = tmp_path / "storage/users/audit-user/profile.json"
    with ProfileLease(profile_lock_path(path)):
        response = app.test_client().post(f"/v1/{method}/ask", json=payload,
                                          headers={"Authorization": "Bearer audit-admin"})
    assert response.status_code == 409
    assert response.json["error"]["code"] == "profile_busy"
    assert not (path.parent / "conversations/shared.jsonl").exists()


@pytest.mark.parametrize("value", ["false", 0, [], {}])
def test_priced_boolean_rejects_wrong_types(app, value):
    response = app.test_client().post("/v1/najia/ask", json={"paraphrase": value})
    assert response.status_code == 400
    assert response.json["error"]["code"] == "invalid_paraphrase"


@pytest.mark.parametrize("reader", [conversation_store.load_recent_rounds,
    conversation_store.load_latest_llm_prompts, conversation_store.load_tool_invocations,
    conversation_store.load_responses, conversation_store.load_llm_traces])
def test_log_readers_skip_nonobject_records(tmp_path, reader):
    log = tmp_path / "events.jsonl"
    log.write_text('null\n[]\n42\n"text"\n{\n' +
        json.dumps({"type": "user_message", "text": "question"}) + '\n' +
        json.dumps({"type": "response", "text": "answer"}) + '\n', encoding="utf-8")
    result = reader(str(log))
    if reader is conversation_store.load_recent_rounds:
        assert result == [{"user": "question", "assistant": "answer"}]


@pytest.mark.parametrize("payload", [{}, [], {"choices": []},
    {"choices": [{"message": {"content": ""}}]},
    {"choices": [{"message": {"content": "   "}}]},
    {"choices": [{"message": {"content": 42}}]}])
def test_invalid_successful_model_response_is_failure(monkeypatch, payload):
    monkeypatch.setattr(llm_tool.urllib.request, "urlopen",
                        lambda *a, **k: io.BytesIO(json.dumps(payload).encode()))
    content, reasoning, error = llm_tool._do_llm_api_call(
        "https://synthetic.invalid/chat/completions", "fake", "model", "system", "user",
        1, 1, False, None, None, "TEST")
    assert content is None and error is not None


def test_valid_model_response_preserved(monkeypatch):
    payload = {"choices": [{"message": {"content": "answer"}}]}
    monkeypatch.setattr(llm_tool.urllib.request, "urlopen",
                        lambda *a, **k: io.BytesIO(json.dumps(payload).encode()))
    assert llm_tool._do_llm_api_call(
        "https://synthetic.invalid/chat/completions", "fake", "model", "system", "user",
        1, 1, False, None, None, "TEST") == ("answer", "", None)


@pytest.mark.parametrize("payload", [{"pack_id": 42}, {"pack_id": ["p"]},
    {"custom_yuan": True}, {"custom_yuan": 1.9}, {"custom_yuan": "10"},
    {"pack_id": "p", "custom_yuan": 10}])
def test_checkout_rejects_ambiguous_amounts_without_provider_call(app, payload, monkeypatch):
    from agent.billing.stripe_gateway import StripeGateway
    def unexpected(**kwargs):
        pytest.fail("Invalid request reached payment provider")
    monkeypatch.setattr(StripeGateway, "build_checkout_session", unexpected)
    client = app.test_client()
    registration = client.post("/v1/register", json={}).json
    response = client.post("/v1/checkout/create", json=payload,
                           headers={"Authorization": "Bearer " + registration["api_key"]})
    assert response.status_code == 400


@pytest.mark.parametrize("ending,valid", [(b"", False), (b"data: {broken}\n", False),
    (b"data: [DONE]\n", True),
    (b'data: {"choices":[{"delta":{},"finish_reason":"stop"}]}\n', True)])
def test_model_stream_requires_valid_completion(monkeypatch, ending, valid):
    body = b'data: {"choices":[{"delta":{"content":"answer"}}]}\n' + ending
    monkeypatch.setattr(llm_tool.urllib.request, "urlopen", lambda *a, **k: io.BytesIO(body))
    content, reasoning, error = llm_tool._do_llm_api_call(
        "https://synthetic.invalid/chat/completions", "fake", "model", "system", "user",
        1, 1, True, None, None, "TEST")
    assert (error is None) == valid
    assert content == ("answer" if valid else None)


def test_key_migration_backup_preserves_data_and_is_private(tmp_path, monkeypatch):
    import sqlite3
    from contextlib import closing
    from agent.billing import BillingStore
    from scripts.secure_billing_keys import main
    monkeypatch.setenv("APP_SECRET_KEY", "synthetic-backup-secret-123456789012")
    db, backup = tmp_path / "billing.db", tmp_path / "backup.db"
    store = BillingStore(str(db))
    store.create_user("synthetic-user")
    old_mask = os.umask(0o022)
    try:
        assert main(["--db", str(db), "--backup", str(backup), "--service-stopped"]) == 0
    finally:
        os.umask(old_mask)
    if os.name != "nt":
        assert backup.stat().st_mode & 0o077 == 0
    with closing(sqlite3.connect(backup)) as connection:
        assert connection.execute("SELECT user_id FROM users").fetchone()[0] == "synthetic-user"
    original = backup.read_bytes()
    with pytest.raises(SystemExit):
        main(["--db", str(db), "--backup", str(backup), "--service-stopped"])
    assert backup.read_bytes() == original


@pytest.mark.parametrize("stream", [False, True])
def test_empty_model_answer_refunds_http_request(app, tmp_path, monkeypatch, stream):
    monkeypatch.setenv("REGISTER_INITIAL_CREDITS", "1000")
    monkeypatch.setenv("LLM_MODE", "live")
    monkeypatch.setattr(llm_tool, "_load_env_file", lambda _: None)
    monkeypatch.setattr(llm_tool, "resolve_llm_settings", lambda *a, **k: {
        "model": "synthetic", "api_base": "https://synthetic.invalid", "api_key": "fake"})
    monkeypatch.setattr(llm_tool.urllib.request, "urlopen",
                        lambda *a, **k: io.BytesIO(b'{"choices":[{"message":{"content":""}}]}'))
    def turn(*args, **kwargs):
        report = llm_tool.llm_report_tool("system", "user")
        return {"plan": {}, "time_context": None, "response": report["content"],
                "error": report["error"], "outputs": {}}
    app = web_server.create_app(run_turn_func=turn, storage_root=str(tmp_path / "storage"))
    client = app.test_client()
    registration = client.post("/v1/register", json={}).json
    headers = {"Authorization": "Bearer " + registration["api_key"]}
    path = "/v1/ask_stream" if stream else "/v1/ask"
    response = client.post(path, json={"question": "test",
        "birth": {"year": 1990, "month": 1, "day": 1, "hour": 8}}, headers=headers)
    assert response.status_code == 200
    if stream:
        assert '"stage": "refunded"' in response.get_data(as_text=True)
    else:
        assert response.json["error"] is True
        assert response.headers["X-Charged-Credits"] == "0"
    assert client.get("/v1/balance", headers=headers).json["balance_credits"] == 1000


@pytest.mark.parametrize("path", ["/v1/auth/login", "/v1/auth/register",
    "/v1/auth/logout", "/v1/me/password", "/v1/me/api_key/rotate"])
@pytest.mark.parametrize("origin", ["https://untrusted.example", "null"])
def test_browser_cross_origin_auth_mutation_rejected(app, path, origin):
    response = app.test_client().post(path, data='{"email":"synthetic@example.com"}',
        content_type="text/plain", headers={"Origin": origin})
    assert response.status_code == 403
    assert response.json["error"]["code"] == "cross_origin_request"
    assert "Set-Cookie" not in response.headers


def test_same_origin_portal_registration_still_works(app):
    response = app.test_client().post("/v1/auth/register",
        json={"email": "synthetic@example.com", "password": "synthetic-password"},
        headers={"Origin": "http://localhost"})
    assert response.status_code == 201
