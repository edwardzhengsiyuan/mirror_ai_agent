"""End-to-end style tests for billing-aware HTTP endpoints.

These tests exercise ``web_server.create_app`` with stubbed orchestrators and
a per-test SQLite billing DB, then drive Flask's ``test_client`` to assert
that:

* admin token requests bypass billing entirely (no charge).
* user API key requests are charged the correct number of credits.
* failures (404 / 400 / orchestrator exception) trigger a refund.
* the SSE endpoint emits ``billing`` events and finishes with ``stage=settled``.
* user self-service endpoints (balance / usage / api_keys) work.
* admin endpoints (create user / topup / list / pricing) work.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict, List

import pytest

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, ROOT)

from web_server import create_app


ADMIN_TOKEN = "admin-test-token"


# ---------------------------------------------------------------------------
# stub orchestrators
# ---------------------------------------------------------------------------


def _fake_turn(profile, question, now=None, event_sink=None, stream=False, history_rounds=None):
    plan = {"aspects": ["CAREER"], "time": {"need_tool": False}, "times": []}
    if event_sink:
        event_sink({"type": "plan", "plan": plan})
        if stream:
            event_sink({"type": "response_delta", "delta": "o"})
        event_sink({"type": "response", "text": "stub-bazi", "duration_ms": 1})
    return {
        "plan": plan,
        "time_context": None,
        "response": "stub-bazi",
        "outputs": {},
        "tool_invocations": [],
    }


def _fake_hepan_turn(question, person_a, person_b, **kwargs):
    sink = kwargs.get("event_sink")
    if sink:
        sink({"type": "response", "text": "stub-hepan"})
    return {
        "method": "hepan",
        "response": "stub-hepan",
        "hepan": {"compatibility": {"score": {"overall": 70.0}}},
    }


def _fake_cezi_turn(question, character, **kwargs):
    sink = kwargs.get("event_sink")
    if sink:
        sink({"type": "response", "text": "stub-cezi"})
    return {
        "method": "cezi",
        "response": "stub-cezi",
        "character": character,
        "cezi": {"type": "cezi", "character": character, "question": question},
    }


def _fake_najia_turn(question, yao_values=None, **kwargs):
    values = yao_values or [0, 1, 2, 3, 4, 5]
    sink = kwargs.get("event_sink")
    if sink:
        sink({"type": "response", "text": "stub-najia"})
    return {
        "method": "najia",
        "response": "stub-najia",
        "najia": {
            "type": "najia",
            "yao_values": values,
            "time_info": {},
            "bengua": {"fullname": "本卦"},
            "biangua": {"fullname": "变卦"},
            "raw_text": "raw",
        },
    }


def _fake_zwds_turn(question, birth=None, gender="male", target_years=None, **kwargs):
    sink = kwargs.get("event_sink")
    if sink:
        sink({"type": "response", "text": "stub-zwds"})
    return {
        "method": "zwds",
        "response": "stub-zwds",
        "zwds": {
            "type": "zwds",
            "birth": birth or {},
            "gender": gender,
            "target_years": target_years or [],
            "benming_info": "本命",
            "liunian_infos": [],
            "raw_text": "raw",
        },
    }


def _exploding_cezi_turn(question, character, **kwargs):
    raise RuntimeError("simulated downstream failure")


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setenv("DEMO_API_TOKEN", ADMIN_TOKEN)
    monkeypatch.setenv("BILLING_DB_PATH", str(tmp_path / "billing.db"))
    monkeypatch.setenv("BILLING_INFLIGHT_LIMIT", "2")
    monkeypatch.setenv("BILLING_RATE_LIMIT_PER_MIN", "1000")  # disable for tests
    return create_app(
        run_turn_func=_fake_turn,
        run_hepan_turn_func=_fake_hepan_turn,
        run_cezi_turn_func=_fake_cezi_turn,
        run_najia_turn_func=_fake_najia_turn,
        run_zwds_turn_func=_fake_zwds_turn,
        storage_root=str(tmp_path / "storage"),
    )


@pytest.fixture
def client(app):
    return app.test_client()


def _admin(token=ADMIN_TOKEN):
    return {"Authorization": f"Bearer {token}"}


def _create_user(client, user_id="u_alice", credits=1000) -> str:
    resp = client.post(
        "/admin/users",
        headers=_admin(),
        json={
            "user_id": user_id,
            "display_name": "Alice",
            "initial_credits": credits,
        },
    )
    assert resp.status_code == 200, resp.get_json()
    body = resp.get_json()
    assert body["user"]["balance_credits"] == credits
    api_key = body["api_key"]
    assert api_key
    return api_key


def _user(api_key: str):
    return {"Authorization": f"Bearer {api_key}"}


def _ledger_kinds(client, user_id: str) -> List[str]:
    resp = client.get("/admin/ledger", headers=_admin(), query_string={"user_id": user_id})
    assert resp.status_code == 200, resp.get_json()
    return [row["kind"] for row in resp.get_json()["rows"]]


# ---------------------------------------------------------------------------
# admin / auth basics
# ---------------------------------------------------------------------------


def test_admin_create_user_returns_one_time_key(client) -> None:
    resp = client.post(
        "/admin/users",
        headers=_admin(),
        json={"user_id": "u_alice", "initial_credits": 250},
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["user"]["user_id"] == "u_alice"
    assert body["user"]["balance_credits"] == 250
    assert body["api_key"]


def test_admin_create_user_duplicate_returns_409(client) -> None:
    _create_user(client, "u_alice", credits=10)
    resp = client.post(
        "/admin/users",
        headers=_admin(),
        json={"user_id": "u_alice", "initial_credits": 10},
    )
    assert resp.status_code == 409


def test_admin_topup_increments_balance(client) -> None:
    api_key = _create_user(client, "u_alice", credits=100)
    resp = client.post(
        "/admin/topup",
        headers=_admin(),
        json={"user_id": "u_alice", "amount_credits": 500, "note": "promo"},
    )
    assert resp.status_code == 200
    assert resp.get_json()["balance_credits"] == 600

    # Same request_id is idempotent: returns duplicate=True without re-charging.
    resp = client.post(
        "/admin/topup",
        headers=_admin(),
        json={
            "user_id": "u_alice",
            "amount_credits": 500,
            "request_id": "topup-abc",
        },
    )
    assert resp.status_code == 200
    assert resp.get_json()["balance_credits"] == 1100  # 600 + 500
    resp_dup = client.post(
        "/admin/topup",
        headers=_admin(),
        json={
            "user_id": "u_alice",
            "amount_credits": 500,
            "request_id": "topup-abc",
        },
    )
    assert resp_dup.status_code == 200
    body = resp_dup.get_json()
    assert body["duplicate"] is True
    assert body["balance_credits"] == 1100  # unchanged

    # Confirm via /v1/balance
    bal = client.get("/v1/balance", headers=_user(api_key))
    assert bal.status_code == 200
    assert bal.get_json()["balance_credits"] == 1100


def test_admin_endpoints_require_admin_token(client) -> None:
    api_key = _create_user(client, "u_alice", credits=10)
    resp = client.post("/admin/topup", headers=_user(api_key),
                       json={"user_id": "u_alice", "amount_credits": 1})
    assert resp.status_code == 401


def test_user_endpoints_reject_admin_token(client) -> None:
    _create_user(client, "u_alice", credits=10)
    # admin token is not a user api key -> /v1/balance should reject
    resp = client.get("/v1/balance", headers=_admin())
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# admin bypass on business endpoints
# ---------------------------------------------------------------------------


def test_admin_bypass_does_not_charge(client) -> None:
    """Existing e2e-style smoke tests use DEMO_API_TOKEN; that path stays free."""
    resp = client.post(
        "/v1/cezi/ask",
        headers=_admin(),
        json={
            "user_id": "u_admin_test",
            "question": "ok?",
            "character": "合",
        },
    )
    assert resp.status_code == 200, resp.get_json()
    assert resp.get_json()["answer"] == "stub-cezi"
    # No X-Charged-Credits header set on admin-bypass responses.
    assert resp.headers.get("X-Charged-Credits") is None


# ---------------------------------------------------------------------------
# user-key flow: charge + settle on success
# ---------------------------------------------------------------------------


def test_cezi_charges_user_and_settles_on_success(client) -> None:
    api_key = _create_user(client, "u_alice", credits=200)
    resp = client.post(
        "/v1/cezi/ask",
        headers=_user(api_key),
        json={"question": "ok?", "character": "合"},
    )
    assert resp.status_code == 200, resp.get_json()
    # /v1/cezi/ask defaults to 30 credits in config/pricing.json
    assert resp.headers["X-Charged-Credits"] == "30"
    assert resp.headers["X-Balance-After"] == "170"
    # balance reflects deduction
    bal = client.get("/v1/balance", headers=_user(api_key))
    assert bal.get_json()["balance_credits"] == 170
    # ledger shows a settled charge (no refund)
    kinds = _ledger_kinds(client, "u_alice")
    assert "charge" in kinds
    assert "refund" not in kinds


def test_zwds_star_gong_variant_costs_more(client) -> None:
    api_key = _create_user(client, "u_alice", credits=1000)
    base = client.post(
        "/v1/zwds/ask",
        headers=_user(api_key),
        json={
            "question": "Q",
            "birth": {"year": 1990, "month": 5, "day": 12, "hour": 8},
            "gender": "male",
        },
    )
    assert base.status_code == 200, base.get_json()
    base_charge = int(base.headers["X-Charged-Credits"])

    star = client.post(
        "/v1/zwds/ask",
        headers=_user(api_key),
        json={
            "question": "Q",
            "birth": {"year": 1990, "month": 5, "day": 12, "hour": 8},
            "gender": "male",
            "include_star_gong": True,
        },
    )
    assert star.status_code == 200, star.get_json()
    star_charge = int(star.headers["X-Charged-Credits"])
    assert star_charge > base_charge


def test_najia_paraphrase_variant_costs_more(client) -> None:
    api_key = _create_user(client, "u_alice", credits=1000)
    base = client.post(
        "/v1/najia/ask",
        headers=_user(api_key),
        json={"question": "Q", "yao_values": [0, 1, 2, 3, 4, 5]},
    )
    assert base.status_code == 200, base.get_json()
    base_charge = int(base.headers["X-Charged-Credits"])

    full = client.post(
        "/v1/najia/ask",
        headers=_user(api_key),
        json={"question": "Q", "yao_values": [0, 1, 2, 3, 4, 5], "paraphrase": True},
    )
    assert full.status_code == 200, full.get_json()
    full_charge = int(full.headers["X-Charged-Credits"])
    assert full_charge > base_charge


# ---------------------------------------------------------------------------
# refund paths
# ---------------------------------------------------------------------------


def test_validation_error_does_not_charge(client) -> None:
    api_key = _create_user(client, "u_alice", credits=200)
    resp = client.post(
        "/v1/cezi/ask",
        headers=_user(api_key),
        json={"question": "", "character": "合"},  # missing question
    )
    assert resp.status_code == 400
    # balance untouched (charge was deferred until after validation)
    bal = client.get("/v1/balance", headers=_user(api_key))
    assert bal.get_json()["balance_credits"] == 200
    # ledger has no charge row
    assert "charge" not in _ledger_kinds(client, "u_alice")


def test_orchestrator_exception_refunds_charge(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DEMO_API_TOKEN", ADMIN_TOKEN)
    monkeypatch.setenv("BILLING_DB_PATH", str(tmp_path / "billing.db"))
    monkeypatch.setenv("BILLING_RATE_LIMIT_PER_MIN", "1000")
    app = create_app(
        run_turn_func=_fake_turn,
        run_hepan_turn_func=_fake_hepan_turn,
        run_cezi_turn_func=_exploding_cezi_turn,
        run_najia_turn_func=_fake_najia_turn,
        run_zwds_turn_func=_fake_zwds_turn,
        storage_root=str(tmp_path / "storage"),
    )
    client = app.test_client()
    api_key = _create_user(client, "u_alice", credits=200)

    resp = client.post(
        "/v1/cezi/ask",
        headers=_user(api_key),
        json={"question": "ok?", "character": "合"},
    )
    # Flask returns 500 for unhandled exceptions
    assert resp.status_code == 500
    # but balance was refunded
    bal = client.get("/v1/balance", headers=_user(api_key))
    assert bal.get_json()["balance_credits"] == 200

    kinds = _ledger_kinds(client, "u_alice")
    assert "charge" in kinds and "refund" in kinds


# ---------------------------------------------------------------------------
# auth gating: insufficient funds + user_id mismatch
# ---------------------------------------------------------------------------


def test_insufficient_funds_returns_402(client) -> None:
    api_key = _create_user(client, "u_alice", credits=10)
    resp = client.post(
        "/v1/cezi/ask",
        headers=_user(api_key),
        json={"question": "ok?", "character": "合"},
    )
    assert resp.status_code == 402
    body = resp.get_json()
    assert body["error"]["code"] == "insufficient_funds"
    assert body["error"]["details"]["cost_credits"] >= 1


def test_user_id_mismatch_returns_403(client) -> None:
    api_key = _create_user(client, "u_alice", credits=200)
    resp = client.post(
        "/v1/cezi/ask",
        headers=_user(api_key),
        json={"user_id": "u_bob", "question": "ok?", "character": "合"},
    )
    assert resp.status_code == 403
    assert resp.get_json()["error"]["code"] == "user_id_mismatch"


# ---------------------------------------------------------------------------
# user self-service api key endpoints
# ---------------------------------------------------------------------------


def test_user_can_issue_and_revoke_api_keys(client) -> None:
    api_key = _create_user(client, "u_alice", credits=10)

    issue = client.post("/v1/api_keys", headers=_user(api_key), json={"label": "phone-app"})
    assert issue.status_code == 200
    body = issue.get_json()
    second_key = body["api_key"]
    assert second_key != api_key
    assert body["label"] == "phone-app"

    listing = client.get("/v1/api_keys", headers=_user(second_key))
    assert listing.status_code == 200
    keys = listing.get_json()["api_keys"]
    assert len(keys) == 2
    second_id = next(k["key_id"] for k in keys if k["label"] == "phone-app")

    rev = client.delete(f"/v1/api_keys/{second_id}", headers=_user(api_key))
    assert rev.status_code == 200
    assert rev.get_json()["revoked"] is True
    # revoked key cannot be used
    bal = client.get("/v1/balance", headers=_user(second_key))
    assert bal.status_code == 401


# ---------------------------------------------------------------------------
# /v1/usage
# ---------------------------------------------------------------------------


def test_usage_listing_records_recent_charges(client) -> None:
    api_key = _create_user(client, "u_alice", credits=500)
    for _ in range(2):
        resp = client.post(
            "/v1/cezi/ask",
            headers=_user(api_key),
            json={"question": "Q", "character": "合"},
        )
        assert resp.status_code == 200
    usage = client.get("/v1/usage", headers=_user(api_key)).get_json()
    kinds = [row["kind"] for row in usage["rows"]]
    assert kinds.count("charge") == 2
    assert kinds.count("topup") == 1


# ---------------------------------------------------------------------------
# pricing endpoint
# ---------------------------------------------------------------------------


def test_admin_can_inspect_pricing(client) -> None:
    resp = client.get("/admin/pricing", headers=_admin())
    assert resp.status_code == 200
    body = resp.get_json()
    assert "default_credits" in body
    assert "endpoints" in body


# ---------------------------------------------------------------------------
# SSE billing event lifecycle
# ---------------------------------------------------------------------------


def _parse_sse(body: bytes) -> List[Dict[str, Any]]:
    events: List[Dict[str, Any]] = []
    for raw in body.decode("utf-8").splitlines():
        if not raw.startswith("data:"):
            continue
        chunk = raw[len("data:"):].strip()
        if not chunk:
            continue
        try:
            events.append(json.loads(chunk))
        except json.JSONDecodeError:
            continue
    return events


def test_ask_stream_emits_billing_settled(client) -> None:
    api_key = _create_user(client, "u_alice", credits=1000)
    # Seed profile so /v1/ask_stream finds birth info.
    seed = client.post(
        "/v1/users",
        headers=_admin(),
        json={
            "user_id": "u_alice",
            "birth": {"year": 1992, "month": 6, "day": 15, "hour": 14},
            "gender": "female",
        },
    )
    assert seed.status_code == 200, seed.get_json()

    resp = client.post(
        "/v1/ask_stream",
        headers=_user(api_key),
        json={"question": "今年事业怎么样？", "history_n": 0},
    )
    assert resp.status_code == 200
    events = _parse_sse(resp.data)
    types = [e.get("type") for e in events]
    assert "session" in types
    billing_events = [e for e in events if e.get("type") == "billing"]
    assert any(e.get("stage") == "charged" for e in billing_events)
    assert any(e.get("stage") == "settled" for e in billing_events)

    final = next(e for e in billing_events if e.get("stage") == "settled")
    assert final["amount_credits"] == 200  # /v1/ask_stream price
    assert final["balance_after"] == 800
