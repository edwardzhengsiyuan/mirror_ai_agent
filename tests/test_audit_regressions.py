"""Regression cases from the repository audit; no external services or real data."""
from concurrent.futures import ThreadPoolExecutor
import datetime as dt
import json
import threading

import pytest

import web_server
from agent.billing import BillingService, BillingStore, DailyLimitExceededError, RateLimitError
from agent.storage import profile_store
from agent.storage.paths import session_paths


@pytest.fixture
def audit_app(tmp_path, monkeypatch):
    monkeypatch.setattr(web_server, "load_env_file", lambda _path: None)
    monkeypatch.setenv("DEMO_API_TOKEN", "audit-admin")
    monkeypatch.setenv("APP_SECRET_KEY", "audit-session-secret")
    monkeypatch.setenv("APP_COOKIE_SECURE", "0")
    monkeypatch.setenv("BILLING_DB_PATH", str(tmp_path / "billing.db"))
    monkeypatch.setenv("BILLING_RATE_LIMIT_PER_MIN", "1000")
    monkeypatch.setenv("REGISTER_INITIAL_CREDITS", "0")

    def run_turn(profile, question, **kwargs):
        return {"plan": {}, "time_context": None, "response": "ok", "outputs": {}}

    app = web_server.create_app(run_turn_func=run_turn, storage_root=str(tmp_path / "storage"))
    app.config["TESTING"] = True
    return app, BillingService(BillingStore(str(tmp_path / "billing.db")))


@pytest.mark.parametrize("path", ["/api/users", "/api/profile", "/api/sessions",
                                       "/api/history", "/api/session_metadata", "/api/models"])
def test_legacy_reads_require_admin(audit_app, path):
    app, service = audit_app
    key = service.create_user("reader")["api_key_plaintext"]
    client = app.test_client()
    for headers in ({}, {"Authorization": "Bearer " + key}):
        assert client.get(path, headers=headers).status_code == 401


@pytest.mark.parametrize("path", ["/api/users", "/api/sessions", "/api/ask", "/api/ask_stream"])
def test_legacy_writes_require_admin(audit_app, path):
    app, _ = audit_app
    assert app.test_client().post(path, json={}).status_code == 401


@pytest.mark.parametrize("bad_id", ["..", ".", "../outside", "a/b", "a\\b", "C:\\outside",
                                         "CON", "nul.txt", "u.", "u\n", 12, []])
def test_legacy_path_traversal_rejected(audit_app, bad_id):
    app, _ = audit_app
    response = app.test_client().post("/api/sessions", json={"user_id": bad_id},
                                     headers={"Authorization": "Bearer audit-admin"})
    assert response.status_code == 400


@pytest.mark.parametrize("payload", [[1], "hello", 1, True, None])
def test_json_must_be_object(audit_app, payload):
    app, _ = audit_app
    response = app.test_client().post("/v1/auth/register", data=json.dumps(payload),
                                     content_type="application/json")
    assert response.status_code == 400
    assert response.is_json


def test_malformed_and_oversized_json(audit_app):
    app, _ = audit_app
    client = app.test_client()
    assert client.post("/v1/register", data="{", content_type="application/json").status_code == 400
    assert client.post("/v1/register", data="x" * (1024 * 1024 + 1)).status_code == 413


@pytest.mark.parametrize("birth", [[], {"year": 2025, "month": 2, "day": 29},
                                         {"year": 2024, "month": 4, "day": 31},
                                         {"year": 0, "month": 1, "day": 1}])
def test_invalid_birth_rejected_before_persistence(audit_app, birth):
    app, _ = audit_app
    response = app.test_client().post("/api/users", json={"user_id": "invalid", "birth": birth},
                                     headers={"Authorization": "Bearer audit-admin"})
    assert response.status_code == 400


def test_session_ids_are_unique(audit_app):
    app, _ = audit_app
    client = app.test_client()
    sessions = [client.post("/api/sessions", json={"user_id": "u"},
                            headers={"Authorization": "Bearer audit-admin"}).get_json()["session_id"]
                for _ in range(8)]
    assert len(set(sessions)) == len(sessions)


def test_storage_paths_reject_traversal():
    for kwargs in ({"user_id": ".."}, {"user_id": "u", "session_id": "../bad"},
                   {"user_id": "u", "profile_name": "../bad"}):
        with pytest.raises(ValueError):
            session_paths(**kwargs)


def test_profile_write_failure_keeps_previous_file(tmp_path, monkeypatch):
    path = str(tmp_path / "profile.json")
    profile_store.save_profile(path, {"old": True})
    with pytest.raises(TypeError):
        profile_store.save_profile(path, {"bad": object()})
    assert profile_store.load_profile(path) == {"old": True}

    def fail_replace(*args):
        raise OSError("disk error")

    monkeypatch.setattr(profile_store.os, "replace", fail_replace)
    with pytest.raises(OSError):
        profile_store.save_profile(path, {"new": True})
    assert profile_store.load_profile(path) == {"old": True}
    assert list(tmp_path.glob(".profile-*.tmp")) == []


def test_concurrent_rate_limit_reservations(tmp_path):
    service = BillingService(BillingStore(str(tmp_path / "billing.db")), rate_limit_per_minute=3)
    barrier = threading.Barrier(12)

    def attempt(_):
        barrier.wait()
        try:
            service.check_rate_limit("shared")
            return True
        except RateLimitError:
            return False

    with ThreadPoolExecutor(max_workers=12) as pool:
        assert sum(pool.map(attempt, range(12))) == 3


def test_previous_day_refund_does_not_expand_today_limit(tmp_path):
    service = BillingService(BillingStore(str(tmp_path / "billing.db")))
    service.create_user("u", initial_credits=1000, daily_credits_limit=100)
    service.charge("u", "/v1/ask", 100, request_id="yesterday")
    yesterday = (dt.datetime.now(dt.UTC) - dt.timedelta(days=1)).isoformat()
    with service.store.transaction() as conn:
        conn.execute("UPDATE ledger SET ts = ? WHERE request_id = 'yesterday'", (yesterday,))
    service.refund("yesterday")
    with pytest.raises(DailyLimitExceededError):
        service.charge("u", "/v1/ask", 101)


def test_settle_refunded_charge_reports_actual_state(tmp_path):
    service = BillingService(BillingStore(str(tmp_path / "billing.db")))
    service.create_user("u", initial_credits=100)
    service.charge("u", "/v1/ask", 10, request_id="r")
    service.refund("r")
    assert service.settle("r").status == "refunded"
    assert service.get_balance("u") == 100


def test_key_rotation_rolls_back_revocation_on_insert_error(tmp_path, monkeypatch):
    service = BillingService(BillingStore(str(tmp_path / "billing.db"), app_secret="rotation-test-secret"))
    original = service.create_user("u")["api_key_plaintext"]
    import agent.billing.store as store_module
    monkeypatch.setattr(store_module, "generate_api_key", lambda: original)
    import sqlite3
    with pytest.raises(sqlite3.IntegrityError):
        service.rotate_user_api_key("u")
    assert service.authenticate(original)["user_id"] == "u"


def test_password_change_invalidates_other_sessions(audit_app):
    app, _ = audit_app
    client = app.test_client()
    assert client.post("/v1/auth/register", json={"email": "audit@example.com",
                                                 "password": "before-secret"}).status_code == 201
    stolen = client.get_cookie("mirror_session").value
    other = app.test_client()
    other.set_cookie("mirror_session", stolen)
    assert other.get("/v1/me").status_code == 200
    assert client.post("/v1/me/password", json={"old_password": "before-secret",
                                               "new_password": "after-secret"}).status_code == 200
    assert client.get("/v1/me").status_code == 200
    assert other.get("/v1/me").status_code == 401


def test_disabled_user_cannot_reuse_session(audit_app):
    app, service = audit_app
    client = app.test_client()
    user = client.post("/v1/auth/register", json={"email": "disabled@example.com",
                                                 "password": "before-secret"}).get_json()["user"]
    service.admin_set_user_status(user["user_id"], "disabled")
    assert client.get("/v1/me").status_code == 401
    assert client.post("/v1/me/api_key/rotate").status_code == 401


def test_post_execution_save_error_refunds(audit_app, monkeypatch):
    app, service = audit_app
    key = service.create_user("u", initial_credits=2000)["api_key_plaintext"]
    original_save = web_server.save_profile
    writes = 0

    def save(path, profile):
        nonlocal writes
        writes += 1
        if writes == 2:
            raise OSError("simulated disk full after model completed")
        original_save(path, profile)

    monkeypatch.setattr(web_server, "save_profile", save)
    with pytest.raises(OSError):
        app.test_client().post("/v1/ask", headers={"Authorization": "Bearer " + key},
                               json={"question": "hello", "birth": {"year": 1990, "month": 1, "day": 1}})
    assert service.get_balance("u") == 2000
    rows = service.list_usage("u")
    assert any(row["kind"] == "charge" and row["status"] == "refunded" for row in rows)


@pytest.mark.parametrize("request_id", ["stripe:cs_example", "other::refund", "topup-example"])
def test_client_cannot_reserve_internal_ledger_ids(audit_app, request_id):
    _, service = audit_app
    service.create_user("u", initial_credits=100)
    with pytest.raises(ValueError):
        service.charge("u", "/v1/ask", 10, request_id=request_id)
    assert service.get_balance("u") == 100


def test_missing_llm_credentials_do_not_produce_successful_stub(monkeypatch):
    from agent.tools import llm_tool
    monkeypatch.setenv("LLM_MODE", "auto")
    monkeypatch.setattr(llm_tool, "_load_env_file", lambda path: None)
    monkeypatch.setattr(llm_tool, "resolve_llm_settings", lambda *args, **kwargs: {})
    for name in ("LLM_API_BASE", "OPENAI_API_BASE", "LLM_API_KEY", "OPENAI_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    result = llm_tool.llm_report_tool("system", "user")
    assert result["error"]
    assert not result.get("stub")


def test_node_start_sink_failure_releases_inflight_slot(monkeypatch):
    from agent import execution
    profile = {"node_cache": {}}

    def sink(event):
        if event["type"] == "node_start":
            raise OSError("log disk full")

    output = execution.ensure_node(profile, "PAIPAN", {}, event_sink=sink)
    assert output["error"]
    key = execution._inflight_key(profile, "PAIPAN", execution._cache_key_inputs({}))
    assert key not in execution._IN_FLIGHT
    monkeypatch.setattr(execution, "paipan_tool", lambda inputs: {"ok": True})
    assert execution.ensure_node(profile, "PAIPAN", {}) == {"ok": True}


def test_final_bazi_response_failure_is_reported(monkeypatch, sample_profile):
    from agent import orchestrator
    monkeypatch.setattr(orchestrator, "ensure_node", lambda *args, **kwargs: {})
    monkeypatch.setattr(orchestrator, "run_tool", lambda *args, **kwargs: ({"aspects": [], "times": []}, "id", 0, None))
    monkeypatch.setattr(orchestrator, "run_nodes_parallel", lambda *args, **kwargs: {})
    monkeypatch.setattr(orchestrator, "run_response", lambda *args, **kwargs: ({"error": True, "content": "[LLM_ERROR:RESPONSE] secret upstream detail"}, 0, None))
    result = orchestrator.run_turn(sample_profile, "hello")
    assert result["error"]
    assert result["failed_nodes"] == ["RESPONSE"]
    assert "secret" not in result["response"]


@pytest.mark.parametrize("method", ["cezi", "hepan", "najia", "zwds"])
def test_divination_error_outputs_trigger_refunds(audit_app, monkeypatch, method, tmp_path):
    import importlib
    module = importlib.import_module("agent.orchestrator_" + method)
    monkeypatch.setattr(module, "llm_report_tool", lambda *args, **kwargs: {"error": True, "content": "[LLM_ERROR:X] secret"})
    # Keep real orchestration and the HTTP billing lifecycle, replace only chart engines.
    charts = {
        "cezi": {"character": "字", "question": "hello"},
        "hepan": {"compatibility": {"score": {}}, "person_a": {}, "person_b": {}},
        "najia": {"raw_text": "chart", "bengua": {"fullname": "a"}, "biangua": {"fullname": "b"},
                  "yao_values": [0, 1, 2, 3, 4, 5], "time_info": {}},
        "zwds": {"raw_text": "chart", "target_years": [], "birth": {}, "gender": "male",
                 "benming_info": "chart", "liunian_infos": []},
    }
    monkeypatch.setattr(module, method + "_tool", lambda *args, **kwargs: charts[method])
    prompt_name = {"cezi": "build_cezi_prompt", "hepan": "build_hepan_prompt", "najia": "build_najia_prompt", "zwds": "build_zwds_prompt"}[method]
    monkeypatch.setattr(module, prompt_name, lambda *args, **kwargs: {"system_prompt": "s", "user_prompt": "u"})
    app = web_server.create_app(storage_root=str(tmp_path / "storage"))
    _, service = audit_app
    key = service.create_user("failure", initial_credits=2000)["api_key_plaintext"]
    birth = {"year": 1990, "month": 1, "day": 1}
    payload = {"question": "hello", "character": "字", "birth": birth,
               "person_a": {"birth": birth}, "person_b": {"birth": birth}}
    response = app.test_client().post(f"/v1/{method}/ask", json=payload,
                                     headers={"Authorization": "Bearer " + key})
    assert response.status_code == 200, response.get_json()
    assert response.get_json()["error"] is True
    assert "secret" not in response.get_json()["answer"]
    assert response.headers["X-Charged-Credits"] == "0"
    assert service.get_balance("failure") == 2000


def test_profile_lease_excludes_other_processes_and_releases(tmp_path):
    import subprocess
    import sys
    from agent.storage.locking import ProfileLease
    path = str(tmp_path / "profile.lock")
    script = "from agent.storage.locking import ProfileLease; import sys; ProfileLease(sys.argv[1]).release()"
    lease = ProfileLease(path)
    try:
        result = subprocess.run([sys.executable, "-c", script, path], capture_output=True)
        assert result.returncode != 0
        assert b"ProfileBusyError" in result.stderr
    finally:
        lease.release()
    assert subprocess.run([sys.executable, "-c", script, path], capture_output=True).returncode == 0


def test_same_profile_cannot_be_changed_during_stream(audit_app, tmp_path):
    app, service = audit_app
    key = service.create_user("stream-user", initial_credits=2000)["api_key_plaintext"]
    started, finish = threading.Event(), threading.Event()

    def slow_turn(profile, question, **kwargs):
        started.set()
        assert finish.wait(5)
        return {"plan": {}, "time_context": None, "response": "ok"}

    app = web_server.create_app(run_turn_func=slow_turn, storage_root=str(tmp_path / "storage"))
    headers = {"Authorization": "Bearer " + key}
    client = app.test_client()
    response = client.post("/v1/ask_stream", headers=headers,
                           json={"question": "hi", "birth": {"year": 1990, "month": 1, "day": 1}})
    try:
        assert started.wait(3)
        blocked = app.test_client().post("/v1/ask", headers=headers,
                                         json={"question": "hi", "birth": {"year": 2000, "month": 1, "day": 1}})
        assert blocked.status_code == 409
        assert blocked.get_json()["error"]["code"] == "profile_busy"
    finally:
        finish.set()
        list(response.response)
        response.close()
    allowed = client.post("/v1/ask", headers=headers,
                          json={"question": "hi", "birth": {"year": 2000, "month": 1, "day": 1}})
    assert allowed.status_code == 200


def test_logout_revokes_copied_cookie_but_allows_fresh_login(audit_app):
    app, _ = audit_app
    credentials = {"email": "logout@example.com", "password": "logout-secret"}
    client = app.test_client()
    assert client.post("/v1/auth/register", json=credentials).status_code == 201
    stolen = client.get_cookie("mirror_session").value
    assert client.post("/v1/auth/logout").status_code == 200
    other = app.test_client()
    other.set_cookie("mirror_session", stolen)
    assert other.get("/v1/me").status_code == 401
    assert client.post("/v1/auth/login", json=credentials).status_code == 200
    assert client.get_cookie("mirror_session").value != stolen
    assert client.get("/v1/me").status_code == 200


def test_auth_limits_ignore_untrusted_forwarded_ip(audit_app, monkeypatch, tmp_path):
    monkeypatch.setenv("AUTH_LOGIN_PER_MIN", "2")
    monkeypatch.setenv("APP_TRUSTED_PROXY_HOPS", "0")
    app = web_server.create_app(storage_root=str(tmp_path / "storage"))
    client = app.test_client()
    for index in range(2):
        assert client.post("/v1/auth/login", json={"email": f"u{index}@example.com", "password": "wrong"},
                           headers={"X-Forwarded-For": f"192.0.2.{index}"}).status_code == 401
    response = client.post("/v1/auth/login", json={"email": "new@example.com", "password": "wrong"},
                           headers={"X-Forwarded-For": "192.0.2.99"})
    assert response.status_code == 429
    assert response.headers["Retry-After"] == "60"


def test_login_account_limit_survives_ip_change(audit_app, monkeypatch, tmp_path):
    monkeypatch.setenv("AUTH_LOGIN_PER_MIN", "1")
    app = web_server.create_app(storage_root=str(tmp_path / "storage"))
    client = app.test_client()
    payload = {"email": "same@example.com", "password": "wrong"}
    assert client.post("/v1/auth/login", json=payload,
                       environ_overrides={"REMOTE_ADDR": "192.0.2.1"}).status_code == 401
    payload["email"] = "SAME@example.com"
    assert client.post("/v1/auth/login", json=payload,
                       environ_overrides={"REMOTE_ADDR": "192.0.2.2"}).status_code == 429


def test_unpaid_request_does_not_persist_profile_or_message(audit_app, tmp_path):
    app, service = audit_app
    key = service.create_user("no-credit")["api_key_plaintext"]
    response = app.test_client().post("/v1/ask", headers={"Authorization": "Bearer " + key},
                                     json={"question": "hi", "birth": {"year": 1990, "month": 1, "day": 1}})
    assert response.status_code == 402
    root = tmp_path / "storage" / "users" / "no-credit"
    assert not (root / "profile.json").exists()
    assert not list(root.rglob("*.jsonl"))


def test_duplicate_request_cannot_overwrite_profile(audit_app, tmp_path):
    app, service = audit_app
    key = service.create_user("retry-user", initial_credits=2000)["api_key_plaintext"]
    headers = {"Authorization": "Bearer " + key, "X-Request-Id": "same-request"}
    payload = {"question": "hi", "birth": {"year": 1990, "month": 1, "day": 1}}
    client = app.test_client()
    assert client.post("/v1/ask", headers=headers, json=payload).status_code == 200
    root = tmp_path / "storage" / "users" / "retry-user"
    before = {str(path): path.read_bytes() for path in root.rglob("*") if path.is_file() and path.suffix != ".lock"}
    payload["birth"]["year"] = 2000
    assert client.post("/v1/ask", headers=headers, json=payload).status_code == 409
    after = {str(path): path.read_bytes() for path in root.rglob("*") if path.is_file() and path.suffix != ".lock"}
    assert after == before


def test_cache_tracks_rendered_content_and_birth_but_not_model(monkeypatch, sample_profile):
    from agent import execution
    monkeypatch.delenv("LLM_BYPASS_CACHE", raising=False)
    template = ["v1"]
    calls = []
    sample_profile["node_cache"]["PAIPAN"] = {"output": {"content": "old chart"}}

    def prompt(node, cache, **kwargs):
        return {"system_prompt": template[0], "user_prompt": cache["PAIPAN"]["output"]["content"]}

    def llm(*args, **kwargs):
        calls.append(args)
        return {"content": f"response-{len(calls)}"}

    monkeypatch.setattr(execution, "build_prompt", prompt)
    monkeypatch.setattr(execution, "llm_report_tool", llm)
    inputs = {"prompt_config": "lingyun_cat", "model": "first"}
    first = execution.ensure_node(sample_profile, "OVERALL", inputs)
    assert execution.ensure_node(sample_profile, "OVERALL", {**inputs, "model": "second"}) == first
    template[0] = "v2"
    assert execution.ensure_node(sample_profile, "OVERALL", inputs) != first
    sample_profile["node_cache"]["PAIPAN"]["output"]["content"] = "new chart"
    execution.ensure_node(sample_profile, "OVERALL", inputs)
    sample_profile["birth"]["year"] = 2000
    execution.ensure_node(sample_profile, "OVERALL", inputs)
    assert len(calls) == 4


def test_ledger_collision_cannot_leak_balance_or_hide_topup(audit_app):
    from agent.billing.errors import DuplicateRequestError
    _, service = audit_app
    service.create_user("private", initial_credits=1000)
    service.create_user("other", initial_credits=100)
    service.charge("private", "/v1/ask", 10, request_id="collision")
    with pytest.raises(DuplicateRequestError) as exc:
        service.charge("other", "/v1/ask", 10, request_id="collision")
    assert exc.value.balance_after == 100
    with pytest.raises(ValueError, match="conflicts"):
        service.topup("other", 100, request_id="collision")
    service.topup("other", 20, request_id="topup-test")
    with pytest.raises(ValueError, match="conflicts"):
        service.topup("other", 30, request_id="topup-test")
    assert service.get_balance("other") == 120


def test_legacy_refund_id_collision_does_not_prevent_refund(audit_app):
    _, service = audit_app
    service.create_user("refund-user", initial_credits=100)
    service.charge("refund-user", "/v1/ask", 20, request_id="original")
    # Emulate a ledger identifier accepted before the reserved-ID validation existed.
    service.topup("refund-user", 1, request_id="original::refund")
    assert service.refund("original").status == "refunded"
    assert service.get_balance("refund-user") == 101
    service.refund("original")
    assert service.get_balance("refund-user") == 101
    assert len([row for row in service.list_usage("refund-user") if row["kind"] == "refund"]) == 1


@pytest.mark.parametrize("action,expected_balance", [("refund", 100), ("settle", 80)])
def test_manual_reconciliation_requires_ack_and_keeps_audit(audit_app, tmp_path, capsys, action, expected_balance):
    from scripts.reconcile_billing import main
    _, service = audit_app
    service.create_user("recovery-user", initial_credits=100)
    service.charge("recovery-user", "/v1/ask", 20, request_id="pending", meta={"original": True})
    args = ["--db", str(tmp_path / "billing.db")]
    assert main(args) == 0
    assert json.loads(capsys.readouterr().out)[0]["request_id"] == "pending"
    resolution = [*args, "--action", action, "--request-id", "pending", "--reason", "Verified service logs"]
    with pytest.raises(SystemExit):
        main(resolution)
    assert service.get_balance("recovery-user") == 80
    assert main([*resolution, "--service-stopped"]) == 0
    assert service.get_balance("recovery-user") == expected_balance
    charge = next(row for row in service.list_usage("recovery-user") if row["kind"] == "charge")
    meta = json.loads(charge["meta_json"])
    assert meta["original"] is True
    assert meta["manual_resolution"]["action"] == action
    assert meta["manual_resolution"]["reason"] == "Verified service logs"
    assert service.store.list_pending_charges() == []
    with pytest.raises(SystemExit):
        main([*resolution, "--service-stopped"])
    assert service.get_balance("recovery-user") == expected_balance


@pytest.mark.parametrize("limits", [{"max_events": 1}, {"max_bytes": 8}])
def test_stream_buffer_limits_close_without_blocking(limits):
    from agent.streaming import EventBuffer
    buffer = EventBuffer(**limits)
    buffer.put({"type": "delta", "text": "one"})
    buffer.put({"type": "delta", "text": "two"})
    assert buffer.get()["code"] == "stream_overflow"
    assert buffer.get() is None
    buffer.put({"type": "delta", "text": "ignored"})
    assert buffer.get() is None


def test_stream_heartbeat_and_disconnect_release_buffer():
    from agent.streaming import EventBuffer, sse_events
    buffer = EventBuffer()
    events = sse_events(buffer, heartbeat_seconds=0.001)
    assert next(events) == ": heartbeat\n\n"
    buffer.put({"type": "delta", "text": "hello"})
    assert "hello" in next(events)
    events.close()
    buffer.put({"type": "delta", "text": "ignored"})
    assert buffer.get() is None


def test_stream_reports_pending_when_database_refund_fails(audit_app, monkeypatch, tmp_path):
    _, service = audit_app
    key = service.create_user("pending-stream", initial_credits=2000)["api_key_plaintext"]

    def broken_turn(*args, **kwargs):
        raise RuntimeError("simulated model failure")

    def broken_refund(*args, **kwargs):
        raise OSError("simulated database failure")

    monkeypatch.setattr(BillingService, "refund", broken_refund)
    app = web_server.create_app(run_turn_func=broken_turn, storage_root=str(tmp_path / "storage"))
    response = app.test_client().post("/v1/ask_stream", buffered=True,
                                     headers={"Authorization": "Bearer " + key},
                                     json={"question": "hi", "birth": {"year": 1990, "month": 1, "day": 1}})
    events = [json.loads(line[6:]) for line in response.get_data(as_text=True).splitlines()
              if line.startswith("data: ")]
    billing_events = [event for event in events if event["type"] == "billing"]
    assert [event["stage"] for event in billing_events] == ["charged", "pending"]
    assert service.store.list_pending_charges()[0]["user_id"] == "pending-stream"
    assert any(event["type"] == "error" for event in events)


def test_disconnected_stream_finishes_and_releases_profile(audit_app, tmp_path):
    import time
    from agent.storage.locking import ProfileLease, ProfileBusyError
    _, service = audit_app
    key = service.create_user("disconnect", initial_credits=2000)["api_key_plaintext"]
    started, finish = threading.Event(), threading.Event()

    def delayed_turn(profile, question, **kwargs):
        started.set()
        assert finish.wait(5)
        kwargs["event_sink"]({"type": "response", "text": "finished after disconnect"})
        return {"plan": {}, "time_context": None, "response": "ok"}

    app = web_server.create_app(run_turn_func=delayed_turn, storage_root=str(tmp_path / "storage"))
    response = app.test_client().post("/v1/ask_stream", buffered=False,
                                     headers={"Authorization": "Bearer " + key},
                                     json={"question": "hi", "birth": {"year": 1990, "month": 1, "day": 1}})
    assert started.wait(3)
    response.close()
    finish.set()
    deadline = time.monotonic() + 5
    while True:
        try:
            lease = ProfileLease(str(tmp_path / "storage" / "users" / "disconnect" / "profile.json.lock"))
            lease.release()
            break
        except ProfileBusyError:
            assert time.monotonic() < deadline
            time.sleep(0.01)
    charge = next(row for row in service.list_usage("disconnect") if row["kind"] == "charge")
    assert charge["status"] == "settled"
    assert service.get_balance("disconnect") == 1500
    assert "finished after disconnect" in next((tmp_path / "storage" / "users" / "disconnect").rglob("*.jsonl")).read_text(encoding="utf-8")
