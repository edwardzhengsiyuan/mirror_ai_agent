"""Live LLM test (skips if env not configured)."""

from __future__ import annotations

import datetime as dt
import os
import sys
import time
import uuid

import pytest

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, ROOT)

from agent.models import DEFAULT_MODEL
from agent.orchestrator import run_turn
from agent.execution import ensure_node
from agent.storage.conversation_store import append_event, load_recent_rounds, log_event_to_conversation
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
    os.environ.setdefault("LLM_PARALLEL_WORKERS", "1")
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


def _run_llm_ping() -> None:
    api_base = os.environ.get("LLM_API_BASE") or os.environ.get("OPENAI_API_BASE")

    # Quick ping before any full pipeline work
    from agent.tools.llm_tool import llm_report_tool

    ts_ping = time.perf_counter()
    ping = llm_report_tool(
        "You are a helpful assistant.",
        "Reply with a short OK.",
        model=DEFAULT_MODEL,
        node="LLM_PING",
    )
    assert ping.get("type") == "report"
    assert ping.get("content"), "empty LLM ping content"
    print(f"llm ping ok in {time.perf_counter() - ts_ping:.2f}s (base={api_base})")


def _run_llm_single_node() -> None:
    ts_single = time.perf_counter()
    profile_single = {
        "user_id": "u_live_single",
        "birth": {
            "year": 1990,
            "month": 1,
            "day": 1,
            "hour": 8,
            "minute": 0,
            "second": 0,
        },
        "gender": "male",
        "birth_time_unknown": False,
        "prompt_config": "lingyun_cat",
        "node_cache": {},
    }
    paipan_inputs = {
        "birth": profile_single.get("birth", {}),
        "gender": profile_single.get("gender", "male"),
        "birth_time_unknown": profile_single.get("birth_time_unknown", False),
    }
    ensure_node(profile_single, "PAIPAN", paipan_inputs)
    overall_output = ensure_node(
        profile_single,
        "OVERALL",
        {"prompt_config": "lingyun_cat", "model": DEFAULT_MODEL},
    )
    assert overall_output.get("content"), "empty OVERALL content"
    assert "reasoning_content" in overall_output, "missing reasoning_content for OVERALL"
    assert "PAIPAN" in profile_single.get("node_cache", {}), "PAIPAN not cached"
    assert "OVERALL" in profile_single.get("node_cache", {}), "OVERALL not cached"
    print(f"llm single node ok in {time.perf_counter() - ts_single:.2f}s")


def _run_llm_full_pipeline() -> None:
    if os.environ.get("LLM_LIVE_FULL") != "1":
        pytest.skip("llm live full pipeline skipped (set LLM_LIVE_FULL=1 to run)")

    user_id = f"u_live_{int(time.time())}_{uuid.uuid4().hex[:6]}"
    profile_path, convo_path = session_paths(user_id, session_id=None)
    print(f"session profile={profile_path} convo={convo_path}")
    profile = {
        "user_id": user_id,
        "birth": {
            "year": 1990,
            "month": 1,
            "day": 1,
            "hour": 8,
            "minute": 0,
            "second": 0,
        },
        "gender": "male",
        "birth_time_unknown": False,
        "prompt_config": "lingyun_cat",
        "node_cache": {},
    }

    question = (
        "今年请综合看事业、感情、健康、贵人、六亲、性格和财运，"
        "并给出整体运势建议。"
    )

    now = dt.datetime(2025, 12, 20, 10, 0, 0)
    history_rounds = load_recent_rounds(convo_path, 5)
    append_event(convo_path, {"ts": now.isoformat(), "type": "user_message", "text": question})
    ts_full = time.perf_counter()
    events = []

    def sink(event):
        log_event_to_conversation(convo_path, event, ts=now.isoformat())
        events.append(event)

    result = run_turn(profile, question, now=now, event_sink=sink, stream=True, history_rounds=history_rounds)
    append_event(convo_path, {"ts": now.isoformat(), "type": "plan", "plan": result["plan"]})
    append_event(convo_path, {"ts": now.isoformat(), "type": "events", "count": len(events)})
    append_event(convo_path, {"ts": now.isoformat(), "type": "assistant_final", "text": result["response"]})
    # Verify core nodes executed and reasoning content exists for reasoning nodes
    cache = profile.get("node_cache", {})
    for node in ["PAIPAN", "OVERALL", "SHISHEN", "GEJU", "WUXING_PREFS"]:
        assert node in cache, f"missing cache node {node}"
    for node in ["OVERALL", "SHISHEN", "GEJU", "WUXING_PREFS"]:
        assert "reasoning_content" in cache[node]["output"], f"missing reasoning_content for {node}"
    assert any(e.get("type") == "llm_prompt" for e in events), "missing llm_prompt events"
    assert any(e.get("type") == "tool_call" and e.get("tool") == "paipan_tool" for e in events), "missing paipan tool_call"
    assert any(e.get("type") == "tool_call" and e.get("tool") == "llm_report_tool" for e in events), "missing llm tool_call"
    assert any(e.get("type") == "node_delta" for e in events), "missing streamed node_delta events"
    assert os.path.exists(convo_path), "conversation log missing"
    with open(convo_path, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]
    assert any("\"user_message\"" in line for line in lines), "user_message not logged"
    assert any("\"llm_prompt\"" in line for line in lines), "llm_prompt not logged"
    assert any("\"assistant_final\"" in line for line in lines), "assistant_final not logged"

    save_profile(profile_path, profile)
    print(f"llm full pipeline completed in {time.perf_counter() - ts_full:.2f}s")


@pytest.mark.llm_live
def test_llm_ping_live() -> None:
    _require_live_env()
    _run_llm_ping()


@pytest.mark.llm_live
def test_llm_single_node_live() -> None:
    _require_live_env()
    _run_llm_single_node()


@pytest.mark.llm_live
def test_llm_full_pipeline_live() -> None:
    _require_live_env()
    _run_llm_full_pipeline()


def main() -> None:
    enabled, api_base, api_key = _configure_live_env()
    if not enabled:
        print("llm live test skipped (missing LLM_API_BASE/LLM_API_KEY or LLM_MODE=stub)")
        return
    print(
        "llm live test starting "
        f"(base={api_base}, model={os.environ.get('LLM_MODEL', DEFAULT_MODEL)})"
    )
    _run_llm_ping()
    _run_llm_single_node()
    if os.environ.get("LLM_LIVE_FULL") != "1":
        print("llm live test skipped (set LLM_LIVE_FULL=1 to run full pipeline)")
        return
    _run_llm_full_pipeline()


if __name__ == "__main__":
    main()
