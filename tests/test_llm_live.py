"""Live LLM test (skips if env not configured)."""

from __future__ import annotations

import datetime as dt
import os
import sys
import time
import uuid

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, ROOT)

from agent.orchestrator import run_turn
from agent.execution import ensure_node
from agent.storage.conversation_store import append_event
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


def main() -> None:
    load_env_file(os.path.join(ROOT, ".env"))
    os.environ.setdefault("LLM_PARALLEL_WORKERS", "1")
    os.environ.setdefault("LLM_DEBUG", "1")
    os.environ.setdefault("LLM_MAX_RETRIES", "3")
    os.environ.setdefault("LLM_TIMEOUT_SECONDS", "120")
    os.environ.setdefault("LLM_TRACE", "1")
    api_base = os.environ.get("LLM_API_BASE") or os.environ.get("OPENAI_API_BASE")
    api_key = os.environ.get("LLM_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if os.environ.get("LLM_MODE") == "stub" or not api_base or not api_key:
        print("llm live test skipped (missing LLM_API_BASE/LLM_API_KEY or LLM_MODE=stub)")
        return

    # Quick ping before any full pipeline work
    from agent.tools.llm_tool import llm_report_tool

    print(
        "llm live test starting "
        f"(base={api_base}, model_reasoning={os.environ.get('LLM_MODEL_REASONING', 'gpt-5')}, "
        f"model_fast={os.environ.get('LLM_MODEL_FAST', 'gpt-5-nano')})"
    )
    ts_ping = time.perf_counter()
    ping = llm_report_tool(
        "You are a helpful assistant.",
        "Reply with a short OK.",
        model="reasoning",
        node="LLM_PING",
    )
    assert ping.get("type") == "report"
    assert ping.get("content"), "empty LLM ping content"
    print(f"llm ping ok in {time.perf_counter() - ts_ping:.2f}s")

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
        {"prompt_config": "lingyun_cat", "model": "reasoning"},
    )
    assert overall_output.get("content"), "empty OVERALL content"
    assert "reasoning_content" in overall_output, "missing reasoning_content for OVERALL"
    assert "PAIPAN" in profile_single.get("node_cache", {}), "PAIPAN not cached"
    assert "OVERALL" in profile_single.get("node_cache", {}), "OVERALL not cached"
    print(f"llm single node ok in {time.perf_counter() - ts_single:.2f}s")

    if os.environ.get("LLM_LIVE_FULL") != "1":
        print("llm live test skipped (set LLM_LIVE_FULL=1 to run full pipeline)")
        return

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
    append_event(convo_path, {"ts": now.isoformat(), "type": "user_message", "text": question})
    ts_full = time.perf_counter()
    print("llm full pipeline starting...")
    result = run_turn(profile, question, now=now)
    append_event(convo_path, {"ts": now.isoformat(), "type": "plan", "plan": result["plan"]})
    append_event(convo_path, {"ts": now.isoformat(), "type": "assistant_final", "text": result["response"]})
    print(f"llm full pipeline completed in {time.perf_counter() - ts_full:.2f}s")

    # Verify core nodes executed and reasoning content exists for reasoning nodes
    cache = profile.get("node_cache", {})
    for node in ["PAIPAN", "OVERALL", "SHISHEN", "GEJU", "WUXING_PREFS"]:
        assert node in cache, f"missing cache node {node}"
    for node in ["OVERALL", "SHISHEN", "GEJU", "WUXING_PREFS"]:
        assert "reasoning_content" in cache[node]["output"], f"missing reasoning_content for {node}"

    save_profile(profile_path, profile)
    print("llm live test ok")


if __name__ == "__main__":
    main()
