"""Unit tests for the billing module (store + service + pricing)."""

from __future__ import annotations

import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import List

import pytest

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, ROOT)

from agent.billing import (
    BillingService,
    BillingStore,
    DailyLimitExceededError,
    DuplicateRequestError,
    EmailAlreadyRegisteredError,
    InflightLimitError,
    InsufficientFundsError,
    Pricing,
    RateLimitError,
    UnknownApiKeyError,
    UnknownUserError,
)


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def store(tmp_path) -> BillingStore:
    return BillingStore(str(tmp_path / "billing.db"))


@pytest.fixture
def service(store: BillingStore) -> BillingService:
    return BillingService(store, inflight_limit=2, rate_limit_per_minute=5)


# ---------------------------------------------------------------------------
# pricing
# ---------------------------------------------------------------------------


def test_pricing_default_when_endpoint_unknown() -> None:
    p = Pricing(default_credits=42, endpoints={}, variants={})
    assert p.cost("/v1/anything") == 42


def test_pricing_endpoint_match() -> None:
    p = Pricing(
        default_credits=10,
        endpoints={"/v1/cezi/ask": 30, "/v1/zwds/ask": 80},
        variants={},
    )
    assert p.cost("/v1/cezi/ask") == 30
    assert p.cost("/v1/zwds/ask") == 80
    assert p.cost("/v1/unknown") == 10


def test_pricing_variant_overrides_endpoint() -> None:
    p = Pricing(
        default_credits=10,
        endpoints={"/v1/zwds/ask": 80},
        variants={"/v1/zwds/ask?include_star_gong=true": 150},
    )
    assert p.cost("/v1/zwds/ask") == 80
    assert p.cost("/v1/zwds/ask", [("include_star_gong", True)]) == 150
    # bool True and string "true" must match the same variant key
    assert p.cost("/v1/zwds/ask", [("include_star_gong", "True")]) == 150
    # falsy variants fall back to base endpoint price
    assert p.cost("/v1/zwds/ask", [("include_star_gong", False)]) == 80


def test_pricing_load_from_repo_default(tmp_path) -> None:
    # The default config/pricing.json shipped in the repo must parse cleanly.
    p = Pricing.load()
    assert p.cost("/v1/cezi/ask") > 0
    assert p.cost("/v1/zwds/ask", [("include_star_gong", True)]) >= p.cost(
        "/v1/zwds/ask"
    )


# ---------------------------------------------------------------------------
# user + api key lifecycle
# ---------------------------------------------------------------------------


def test_create_user_with_initial_credits_and_key(service: BillingService) -> None:
    out = service.create_user(
        user_id="u1",
        display_name="Test",
        initial_credits=500,
    )
    assert out["user"]["balance_credits"] == 500
    assert out["api_key_plaintext"] is not None
    assert len(out["api_key_plaintext"]) >= 30


def test_authenticate_round_trip(service: BillingService) -> None:
    out = service.create_user(user_id="u1", initial_credits=0)
    plaintext = out["api_key_plaintext"]
    auth = service.authenticate(plaintext)
    assert auth["user_id"] == "u1"
    assert auth["balance_credits"] == 0


def test_authenticate_unknown_key_raises(service: BillingService) -> None:
    with pytest.raises(UnknownApiKeyError):
        service.authenticate("not-a-real-key")


def test_revoke_api_key_blocks_auth(service: BillingService) -> None:
    out = service.create_user(user_id="u1", initial_credits=0)
    plaintext = out["api_key_plaintext"]
    assert service.revoke_api_key(plaintext) is True
    with pytest.raises(UnknownApiKeyError):
        service.authenticate(plaintext)


def test_disabled_user_cannot_auth_or_charge(service: BillingService) -> None:
    out = service.create_user(user_id="u1", initial_credits=200)
    plaintext = out["api_key_plaintext"]
    service.admin_set_user_status("u1", "disabled")
    with pytest.raises(UnknownApiKeyError):
        service.authenticate(plaintext)
    with pytest.raises(InsufficientFundsError):
        service.charge("u1", "/v1/x", 10, request_id="r1")


def test_create_user_duplicate_raises(service: BillingService) -> None:
    service.create_user(user_id="u1", initial_credits=0)
    with pytest.raises(ValueError):
        service.create_user(user_id="u1", initial_credits=0)


# ---------------------------------------------------------------------------
# charge / settle / refund
# ---------------------------------------------------------------------------


def test_charge_then_settle_keeps_balance(service: BillingService) -> None:
    service.create_user(user_id="u1", initial_credits=300)
    receipt = service.charge("u1", "/v1/x", 100, request_id="r1")
    assert receipt.amount_credits == 100
    assert receipt.balance_after == 200
    assert receipt.status == "pending"
    assert service.get_balance("u1") == 200

    settled = service.settle("r1")
    assert settled is not None
    assert settled.status == "settled"
    assert service.get_balance("u1") == 200


def test_charge_then_refund_restores_balance(service: BillingService) -> None:
    service.create_user(user_id="u1", initial_credits=300)
    service.charge("u1", "/v1/x", 100, request_id="r1")
    assert service.get_balance("u1") == 200

    refunded = service.refund("r1", reason="upstream_error")
    assert refunded is not None
    assert refunded.status == "refunded"
    assert service.get_balance("u1") == 300

    # second refund is idempotent (no double-credit)
    again = service.refund("r1")
    assert again is not None
    assert again.status == "refunded"
    assert service.get_balance("u1") == 300


def test_settle_unknown_request_returns_none(service: BillingService) -> None:
    service.create_user(user_id="u1", initial_credits=10)
    assert service.settle("never-charged") is None


def test_refund_unknown_request_returns_none(service: BillingService) -> None:
    service.create_user(user_id="u1", initial_credits=10)
    assert service.refund("never-charged") is None


def test_insufficient_funds_blocks_charge(service: BillingService) -> None:
    service.create_user(user_id="u1", initial_credits=50)
    with pytest.raises(InsufficientFundsError):
        service.charge("u1", "/v1/x", 100, request_id="r1")
    assert service.get_balance("u1") == 50


def test_zero_cost_charge_is_allowed(service: BillingService) -> None:
    service.create_user(user_id="u1", initial_credits=0)
    receipt = service.charge("u1", "/v1/free", 0, request_id="r1")
    assert receipt.amount_credits == 0
    assert service.get_balance("u1") == 0
    service.settle("r1")


def test_duplicate_request_id_raises(service: BillingService) -> None:
    service.create_user(user_id="u1", initial_credits=300)
    service.charge("u1", "/v1/x", 100, request_id="r1")
    with pytest.raises(DuplicateRequestError) as excinfo:
        service.charge("u1", "/v1/x", 100, request_id="r1")
    # The exception must surface the existing balance for the caller to display.
    assert excinfo.value.balance_after == 200
    # Balance must NOT have been deducted twice.
    assert service.get_balance("u1") == 200


def test_unknown_user_charge_raises(service: BillingService) -> None:
    with pytest.raises(UnknownUserError):
        service.charge("nope", "/v1/x", 1, request_id="r1")


# ---------------------------------------------------------------------------
# inflight limits
# ---------------------------------------------------------------------------


def test_inflight_limit_enforced(service: BillingService) -> None:
    service.create_user(user_id="u1", initial_credits=10_000)
    service.charge("u1", "/v1/x", 10, request_id="r1")
    service.charge("u1", "/v1/x", 10, request_id="r2")
    with pytest.raises(InflightLimitError):
        service.charge("u1", "/v1/x", 10, request_id="r3")


def test_inflight_slot_freed_after_settle(service: BillingService) -> None:
    service.create_user(user_id="u1", initial_credits=10_000)
    service.charge("u1", "/v1/x", 10, request_id="r1")
    service.charge("u1", "/v1/x", 10, request_id="r2")
    service.settle("r1")
    # slot freed → third charge succeeds
    service.charge("u1", "/v1/x", 10, request_id="r3")


def test_inflight_slot_freed_after_refund(service: BillingService) -> None:
    service.create_user(user_id="u1", initial_credits=10_000)
    service.charge("u1", "/v1/x", 10, request_id="r1")
    service.charge("u1", "/v1/x", 10, request_id="r2")
    service.refund("r1", reason="bench")
    service.charge("u1", "/v1/x", 10, request_id="r3")


# ---------------------------------------------------------------------------
# daily_credits_limit
# ---------------------------------------------------------------------------


def test_daily_limit_blocks_when_exceeded(store: BillingStore) -> None:
    svc = BillingService(store, inflight_limit=10, rate_limit_per_minute=10_000)
    svc.store.create_user("u1", initial_credits=10_000, daily_credits_limit=100)
    # First two charges fit in the budget exactly.
    svc.charge("u1", "/v1/x", 50, request_id="r1")
    svc.charge("u1", "/v1/x", 50, request_id="r2")
    # Third one would exceed → blocked.
    with pytest.raises(DailyLimitExceededError) as excinfo:
        svc.charge("u1", "/v1/x", 1, request_id="r3")
    assert excinfo.value.used == 100
    assert excinfo.value.limit == 100
    # Crucially, the underlying balance is untouched (still 10_000 - 100).
    assert svc.get_balance("u1") == 9_900


def test_daily_limit_zero_or_none_means_no_limit(store: BillingStore) -> None:
    svc = BillingService(store, inflight_limit=10, rate_limit_per_minute=10_000)
    svc.store.create_user("u_none", initial_credits=10_000, daily_credits_limit=None)
    svc.store.create_user("u_zero", initial_credits=10_000, daily_credits_limit=0)
    for i in range(20):
        svc.charge("u_none", "/v1/x", 100, request_id=f"none-{i}")
        svc.settle(f"none-{i}")
        svc.charge("u_zero", "/v1/x", 100, request_id=f"zero-{i}")
        svc.settle(f"zero-{i}")
    # No DailyLimitExceededError raised even after 2_000 credits spent each.
    assert svc.get_balance("u_none") == 8_000
    assert svc.get_balance("u_zero") == 8_000


def test_daily_limit_refund_frees_today_budget(store: BillingStore) -> None:
    svc = BillingService(store, inflight_limit=10, rate_limit_per_minute=10_000)
    svc.store.create_user("u1", initial_credits=10_000, daily_credits_limit=100)
    svc.charge("u1", "/v1/x", 100, request_id="r1")
    with pytest.raises(DailyLimitExceededError):
        svc.charge("u1", "/v1/x", 1, request_id="r-blocked")
    # Refund r1 → today's net = 0, so we can charge again.
    svc.refund("r1", reason="test")
    svc.charge("u1", "/v1/x", 100, request_id="r2")


# ---------------------------------------------------------------------------
# rate limiting (sliding 60s)
# ---------------------------------------------------------------------------


def test_rate_limit_blocks_after_threshold(store: BillingStore) -> None:
    svc = BillingService(store, inflight_limit=10, rate_limit_per_minute=3)
    for _ in range(3):
        svc.check_rate_limit("scope-A")
    with pytest.raises(RateLimitError):
        svc.check_rate_limit("scope-A")
    # different scope is independent
    svc.check_rate_limit("scope-B")


# ---------------------------------------------------------------------------
# topup
# ---------------------------------------------------------------------------


def test_topup_increments_balance_and_writes_ledger(service: BillingService) -> None:
    service.create_user(user_id="u1", initial_credits=0)
    receipt = service.topup("u1", 1000, meta={"channel": "manual"})
    assert receipt.amount_credits == 1000
    assert receipt.balance_after == 1000
    usage = service.list_usage("u1", limit=10)
    kinds = [row["kind"] for row in usage]
    assert "topup" in kinds


def test_topup_idempotent_on_request_id(service: BillingService) -> None:
    service.create_user(user_id="u1", initial_credits=0)
    service.topup("u1", 500, request_id="topup-1")
    with pytest.raises(DuplicateRequestError):
        service.topup("u1", 500, request_id="topup-1")
    # balance must reflect a single topup
    assert service.get_balance("u1") == 500


# ---------------------------------------------------------------------------
# concurrent charge — never go negative
# ---------------------------------------------------------------------------


def test_concurrent_charges_never_oversell(store: BillingStore) -> None:
    """Fire many concurrent charges; total deducted == granted balance."""
    # Bypass inflight gate for this stress test: large limit, short rate window.
    svc = BillingService(store, inflight_limit=10_000, rate_limit_per_minute=10_000)
    svc.create_user(user_id="u1", initial_credits=500)

    successes: List[str] = []
    failures = 0
    lock = threading.Lock()

    def attempt(idx: int) -> None:
        nonlocal failures
        try:
            r = svc.charge("u1", "/v1/x", 100, request_id=f"r-{idx}")
            with lock:
                successes.append(r.request_id)
        except (InsufficientFundsError, InflightLimitError):
            with lock:
                failures += 1

    with ThreadPoolExecutor(max_workers=8) as ex:
        list(ex.map(attempt, range(20)))

    assert len(successes) == 5  # 500 / 100
    assert failures == 15
    assert svc.get_balance("u1") == 0


# ---------------------------------------------------------------------------
# usage history
# ---------------------------------------------------------------------------


def test_list_usage_returns_recent_first(service: BillingService) -> None:
    service.create_user(user_id="u1", initial_credits=1000)
    service.charge("u1", "/v1/x", 100, request_id="r1")
    service.settle("r1")
    service.charge("u1", "/v1/y", 50, request_id="r2")
    service.refund("r2", reason="oops")

    rows = service.list_usage("u1", limit=10)
    assert rows[0]["kind"] == "refund"  # most recent
    kinds = [r["kind"] for r in rows]
    assert kinds.count("charge") == 2
    assert kinds.count("refund") == 1


# ---------------------------------------------------------------------------
# basic store smoke (schema sanity)
# ---------------------------------------------------------------------------


def test_store_recreate_is_idempotent(tmp_path) -> None:
    path = str(tmp_path / "billing.db")
    BillingStore(path)
    # second open must not blow up on existing tables/indexes
    s2 = BillingStore(path)
    assert s2.list_users() == []


def test_update_charge_meta_merges_into_meta_json(service: BillingService) -> None:
    service.create_user(user_id="u1", initial_credits=500)
    service.charge("u1", "/v1/x", 50, request_id="r1", meta={"variant": "x=1"})
    assert service.update_charge_meta(
        "r1",
        llm_usage={"prompt_tokens": 1234, "completion_tokens": 567, "node_count": 3},
        duration_ms=2500,
    )
    rows = service.list_usage("u1", limit=5)
    charge_row = next(r for r in rows if r["kind"] == "charge")
    import json as _json
    meta = _json.loads(charge_row["meta_json"])
    assert meta["variant"] == "x=1"  # original preserved
    assert meta["duration_ms"] == 2500
    assert meta["llm_usage"]["prompt_tokens"] == 1234
    assert meta["llm_usage"]["node_count"] == 3


def test_update_charge_meta_unknown_request_returns_false(service: BillingService) -> None:
    assert service.update_charge_meta("never-charged", duration_ms=1) is False


# ---------------------------------------------------------------------------
# email + password + plaintext schema (Phase 1.1: auth foundation)
# ---------------------------------------------------------------------------


def test_store_migrates_pre_auth_database(tmp_path) -> None:
    """A DB created before the auth feature must gain the new columns on open."""
    import sqlite3

    db_path = str(tmp_path / "billing.db")
    # Hand-craft a database with the *original* schema (no email / password /
    # verified_at / plaintext columns). This mimics what existing production
    # billing.db files look like before the upgrade.
    with sqlite3.connect(db_path) as conn:
        conn.executescript(
            """
            CREATE TABLE users (
                user_id              TEXT PRIMARY KEY,
                display_name         TEXT,
                balance_credits      INTEGER NOT NULL DEFAULT 0,
                status               TEXT NOT NULL DEFAULT 'active',
                daily_credits_limit  INTEGER,
                created_at           TEXT NOT NULL,
                updated_at           TEXT NOT NULL
            );
            CREATE TABLE api_keys (
                api_key_hash   TEXT PRIMARY KEY,
                user_id        TEXT NOT NULL,
                label          TEXT,
                created_at     TEXT NOT NULL,
                last_seen_at   TEXT,
                revoked        INTEGER NOT NULL DEFAULT 0
            );
            """
        )
        # seed one legacy user so the migration runs against non-empty tables
        conn.execute(
            "INSERT INTO users (user_id, balance_credits, status, created_at, updated_at)"
            " VALUES ('u_legacy', 0, 'active', '2025-01-01T00:00:00Z', '2025-01-01T00:00:00Z')"
        )

    # Open via BillingStore. The migration step should add the new columns.
    store = BillingStore(db_path)
    user = store.get_user("u_legacy")
    assert user is not None
    # Legacy user keeps its data and gains NULL slots for the new columns.
    assert user["email"] is None
    assert user["password_hash"] is None
    assert user["verified_at"] is None

    # New users with email/password are accepted on the migrated schema.
    store.create_user(
        user_id="u_new",
        email="new@example.com",
        password_hash="hash:abc",
    )
    fetched = store.get_user("u_new")
    assert fetched is not None
    assert fetched["email"] == "new@example.com"
    assert fetched["password_hash"] == "hash:abc"

    # api_keys.plaintext column also exists after migration.
    _, _ = store.issue_api_key("u_new", label="primary", store_plaintext=True)
    current = store.get_current_user_api_key("u_new")
    assert current is not None and current["plaintext"]

    # Reopening the store again must be a no-op (idempotent migration).
    BillingStore(db_path)


def test_create_user_with_email_and_password(store: BillingStore) -> None:
    user = store.create_user(
        user_id="u1",
        email="alice@example.com",
        password_hash="hash:alice",
    )
    assert user["email"] == "alice@example.com"
    assert user["password_hash"] == "hash:alice"
    assert user["verified_at"] is None  # not verified yet


def test_create_user_duplicate_email_raises(store: BillingStore) -> None:
    store.create_user(user_id="u1", email="dup@example.com", password_hash="h")
    with pytest.raises(EmailAlreadyRegisteredError):
        store.create_user(user_id="u2", email="dup@example.com", password_hash="h")


def test_create_user_null_emails_do_not_collide(store: BillingStore) -> None:
    # Partial unique index must allow multiple NULL emails (legacy users).
    store.create_user(user_id="u1")
    store.create_user(user_id="u2")
    assert store.get_user("u1") is not None
    assert store.get_user("u2") is not None


def test_get_user_by_email(store: BillingStore) -> None:
    store.create_user(user_id="u1", email="bob@example.com", password_hash="h")
    found = store.get_user_by_email("bob@example.com")
    assert found is not None and found["user_id"] == "u1"
    assert store.get_user_by_email("never@example.com") is None
    assert store.get_user_by_email("") is None


def test_update_user_password(store: BillingStore) -> None:
    store.create_user(user_id="u1", email="c@example.com", password_hash="old")
    assert store.update_user_password("u1", "new") is True
    assert store.get_user("u1")["password_hash"] == "new"
    # Unknown user is a no-op (returns False).
    assert store.update_user_password("u_missing", "x") is False


def test_issue_api_key_store_plaintext_flag(store: BillingStore) -> None:
    store.create_user(user_id="u1")
    # Default: legacy behaviour, do NOT persist plaintext.
    pt1, _ = store.issue_api_key("u1")
    row = store.get_current_user_api_key("u1")
    assert row is not None and row["plaintext"] is None
    # Opt-in: dashboard flow, plaintext stored.
    pt2, _ = store.issue_api_key("u1", store_plaintext=True)
    row = store.get_current_user_api_key("u1")  # latest key
    assert row is not None and row["plaintext"] == pt2


def test_revoke_all_user_api_keys_wipes_plaintext(store: BillingStore) -> None:
    store.create_user(user_id="u1")
    store.issue_api_key("u1", store_plaintext=True)
    store.issue_api_key("u1", store_plaintext=True)
    revoked = store.revoke_all_user_api_keys("u1")
    assert revoked == 2
    # All keys revoked + plaintext nulled out, so dashboard has nothing to show.
    assert store.get_current_user_api_key("u1") is None
    rows = store.list_api_keys("u1")
    assert all(r["revoked"] == 1 and r["plaintext"] is None for r in rows)


def test_get_current_user_api_key_returns_latest_active(store: BillingStore) -> None:
    store.create_user(user_id="u1")
    pt_old, hash_old = store.issue_api_key("u1", store_plaintext=True)
    # Issue a second key. Sleep is unnecessary because list_api_keys orders by
    # created_at DESC and the issuer writes ISO microsecond timestamps.
    pt_new, hash_new = store.issue_api_key("u1", store_plaintext=True)
    current = store.get_current_user_api_key("u1")
    assert current is not None
    assert current["plaintext"] == pt_new
    # Revoke the new one, the old becomes "current" again.
    assert store.revoke_api_key(hash_new) is True
    current = store.get_current_user_api_key("u1")
    assert current is not None and current["plaintext"] == pt_old
