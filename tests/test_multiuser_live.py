"""Multi-user live LLM test (concurrent requests with real LLM)."""

from __future__ import annotations

import datetime as dt
import os
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, ROOT)

from agent.orchestrator import run_turn
from agent.storage.conversation_store import append_event, load_recent_rounds
from agent.storage.paths import session_paths
from agent.storage.profile_store import save_profile


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


def _configure_live_env() -> tuple[bool, str, str]:
    load_env_file(os.path.join(ROOT, ".env"))
    os.environ.setdefault("LLM_PARALLEL_WORKERS", "4")
    os.environ.setdefault("LLM_DEBUG", "1")
    os.environ.setdefault("LLM_MAX_RETRIES", "3")
    os.environ.setdefault("LLM_TIMEOUT_SECONDS", "400")
    api_base = os.environ.get("LLM_API_BASE") or os.environ.get("OPENAI_API_BASE") or ""
    api_key = os.environ.get("LLM_API_KEY") or os.environ.get("OPENAI_API_KEY") or ""
    enabled = os.environ.get("LLM_MODE") != "stub" and bool(api_base) and bool(api_key)
    return enabled, api_base, api_key


def _require_live_env() -> tuple[str, str]:
    enabled, api_base, api_key = _configure_live_env()
    if not enabled:
        pytest.skip("llm live test skipped (missing LLM_API_BASE/LLM_API_KEY or LLM_MODE=stub)")
    return api_base, api_key


# Test user profiles with different birth data
TEST_USERS = [
    {
        "name": "user_1990_male",
        "birth": {"year": 1990, "month": 3, "day": 15, "hour": 8, "minute": 0, "second": 0},
        "gender": "male",
    },
    {
        "name": "user_1985_female",
        "birth": {"year": 1985, "month": 7, "day": 22, "hour": 14, "minute": 30, "second": 0},
        "gender": "female",
    },
    {
        "name": "user_2000_male",
        "birth": {"year": 2000, "month": 1, "day": 1, "hour": 0, "minute": 0, "second": 0},
        "gender": "male",
    },
]


def _run_single_user(user_config: dict, question: str, now: dt.datetime) -> dict:
    """Run a single user's question through the full pipeline."""
    run_id = uuid.uuid4().hex[:6]
    user_id = f"u_multiuser_{user_config['name']}_{run_id}"
    session_id = f"sess_{run_id}"

    profile_path, convo_path = session_paths(user_id, session_id=session_id)

    profile = {
        "user_id": user_id,
        "birth": user_config["birth"],
        "gender": user_config["gender"],
        "birth_time_unknown": False,
        "prompt_config": "lingyun_cat",
        "node_cache": {},
    }

    # Track events
    events = []

    def sink(event):
        event_type = event.get("type")
        if event_type == "llm_prompt":
            append_event(convo_path, {
                "ts": now.isoformat(),
                "type": "llm_prompt",
                "node": event.get("node"),
                "system_prompt": event.get("system_prompt", ""),
                "user_prompt": event.get("user_prompt", ""),
            })
        elif event_type == "llm_request":
            append_event(convo_path, {
                "ts": now.isoformat(),
                "type": "llm_request",
                "node": event.get("node"),
                "model": event.get("model"),
                "attempt": event.get("attempt"),
            })
        elif event_type == "llm_response":
            append_event(convo_path, {
                "ts": now.isoformat(),
                "type": "llm_response",
                "node": event.get("node"),
                "model": event.get("model"),
                "duration_ms": event.get("duration_ms"),
            })
        elif event_type == "llm_error":
            append_event(convo_path, {
                "ts": now.isoformat(),
                "type": "llm_error",
                "node": event.get("node"),
                "error": event.get("error"),
            })
        events.append(event)

    history_rounds = load_recent_rounds(convo_path, 5)
    append_event(convo_path, {"ts": now.isoformat(), "type": "user_message", "text": question})

    ts_start = time.perf_counter()
    result = run_turn(profile, question, now=now, event_sink=sink, stream=False, history_rounds=history_rounds)
    elapsed = time.perf_counter() - ts_start

    append_event(convo_path, {"ts": now.isoformat(), "type": "assistant_final", "text": result["response"]})
    save_profile(profile_path, profile)

    return {
        "user_id": user_id,
        "user_config": user_config,
        "profile": profile,
        "result": result,
        "events": events,
        "elapsed": elapsed,
        "convo_path": convo_path,
    }


def _run_multiuser_concurrent(users: list[dict], question: str, now: dt.datetime) -> list[dict]:
    """Run multiple users concurrently."""
    results = []

    with ThreadPoolExecutor(max_workers=len(users)) as executor:
        futures = {
            executor.submit(_run_single_user, user, question, now): user
            for user in users
        }

        for future in as_completed(futures):
            user = futures[future]
            try:
                result = future.result()
                results.append(result)
                print(f"  {user['name']}: completed in {result['elapsed']:.2f}s")
            except Exception as e:
                print(f"  {user['name']}: FAILED - {e}")
                results.append({
                    "user_config": user,
                    "error": str(e),
                })

    return results


@pytest.mark.llm_live
def test_multiuser_concurrent_live() -> None:
    """Test concurrent requests from multiple users with real LLM."""
    _require_live_env()

    question = "今年事业运势如何？"
    now = dt.datetime(2025, 6, 15, 10, 0, 0)

    print(f"\nRunning multi-user concurrent test with {len(TEST_USERS)} users...")
    ts_total = time.perf_counter()

    results = _run_multiuser_concurrent(TEST_USERS, question, now)

    total_elapsed = time.perf_counter() - ts_total
    print(f"Total elapsed: {total_elapsed:.2f}s")

    # Verify all users completed successfully
    successful = [r for r in results if "error" not in r]
    failed = [r for r in results if "error" in r]

    assert len(failed) == 0, f"Some users failed: {[f['user_config']['name'] for f in failed]}"
    assert len(successful) == len(TEST_USERS), f"Not all users completed: {len(successful)}/{len(TEST_USERS)}"

    # Verify each user got a proper response
    for r in successful:
        user_name = r["user_config"]["name"]
        profile = r["profile"]
        result = r["result"]

        # Check response exists
        assert result.get("response"), f"{user_name}: empty response"

        # Check core nodes were executed
        cache = profile.get("node_cache", {})
        for node in ["PAIPAN", "OVERALL", "CAREER"]:
            assert node in cache, f"{user_name}: missing cache node {node}"

        # Check LLM events were recorded
        events = r["events"]
        assert any(e.get("type") == "llm_request" for e in events), f"{user_name}: missing llm_request events"
        assert any(e.get("type") == "llm_response" for e in events), f"{user_name}: missing llm_response events"

        print(f"  {user_name}: verified OK (birth={profile['birth']['year']}, cached nodes={list(cache.keys())})")

    # Verify profiles are isolated (different birth years should produce different PAIPAN results)
    paipan_results = {}
    for r in successful:
        user_name = r["user_config"]["name"]
        birth_year = r["user_config"]["birth"]["year"]
        paipan = r["profile"]["node_cache"].get("PAIPAN", {}).get("output", {})
        paipan_results[user_name] = {
            "birth_year": birth_year,
            "has_paipan": bool(paipan),
        }

    # All should have different birth years
    birth_years = [p["birth_year"] for p in paipan_results.values()]
    assert len(set(birth_years)) == len(birth_years), "Test users should have unique birth years"

    print(f"\nMulti-user concurrent test PASSED ({len(successful)} users, {total_elapsed:.2f}s total)")


@pytest.mark.llm_live
def test_multiuser_sequential_live() -> None:
    """Test sequential requests from multiple users with real LLM (baseline comparison)."""
    _require_live_env()

    question = "今年感情运势如何？"
    now = dt.datetime(2025, 6, 15, 10, 0, 0)

    print(f"\nRunning multi-user sequential test with {len(TEST_USERS)} users...")
    ts_total = time.perf_counter()

    results = []
    for user in TEST_USERS:
        result = _run_single_user(user, question, now)
        results.append(result)
        print(f"  {user['name']}: completed in {result['elapsed']:.2f}s")

    total_elapsed = time.perf_counter() - ts_total
    print(f"Total elapsed (sequential): {total_elapsed:.2f}s")

    # Verify all completed
    for r in results:
        assert "error" not in r, f"User {r['user_config']['name']} failed: {r.get('error')}"
        assert r["result"].get("response"), f"User {r['user_config']['name']} got empty response"

    print(f"\nMulti-user sequential test PASSED ({len(results)} users, {total_elapsed:.2f}s total)")


def main() -> None:
    """Run multi-user tests directly."""
    enabled, api_base, api_key = _configure_live_env()
    if not enabled:
        print("llm live test skipped (missing LLM_API_BASE/LLM_API_KEY or LLM_MODE=stub)")
        return

    print(
        f"Multi-user live test starting "
        f"(base={api_base}, model_reasoning={os.environ.get('LLM_MODEL_REASONING', 'gpt-5')}, "
        f"model_fast={os.environ.get('LLM_MODEL_FAST', 'gpt-5-nano')})"
    )

    question = "今年事业运势如何？"
    now = dt.datetime(2025, 6, 15, 10, 0, 0)

    # Run sequential first (baseline)
    print(f"\n=== Sequential Test ({len(TEST_USERS)} users) ===")
    ts_seq = time.perf_counter()
    seq_results = []
    for user in TEST_USERS:
        result = _run_single_user(user, question, now)
        seq_results.append(result)
        print(f"  {user['name']}: {result['elapsed']:.2f}s")
    seq_total = time.perf_counter() - ts_seq
    print(f"Sequential total: {seq_total:.2f}s")

    # Run concurrent
    print(f"\n=== Concurrent Test ({len(TEST_USERS)} users) ===")
    ts_conc = time.perf_counter()
    conc_results = _run_multiuser_concurrent(TEST_USERS, question, now)
    conc_total = time.perf_counter() - ts_conc
    print(f"Concurrent total: {conc_total:.2f}s")

    # Summary
    print(f"\n=== Summary ===")
    print(f"Sequential: {seq_total:.2f}s ({len(seq_results)} users)")
    print(f"Concurrent: {conc_total:.2f}s ({len(conc_results)} users)")
    if seq_total > 0:
        speedup = seq_total / conc_total
        print(f"Speedup: {speedup:.2f}x")

    # Verify all passed
    all_passed = True
    for r in seq_results + conc_results:
        if "error" in r:
            print(f"FAILED: {r['user_config']['name']} - {r['error']}")
            all_passed = False

    if all_passed:
        print("\nAll multi-user tests PASSED")
    else:
        print("\nSome tests FAILED")
        sys.exit(1)


if __name__ == "__main__":
    main()
