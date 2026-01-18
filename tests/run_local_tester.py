"""Local tester to exercise all nodes and time contexts."""

from __future__ import annotations

import datetime as dt
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, ROOT)

from agent.orchestrator import run_turn
from agent.storage.conversation_store import append_event, load_recent_rounds
from agent.storage.profile_store import load_profile, save_profile

PROFILE_PATH = os.path.join(ROOT, "storage", "profile_demo.json")
CONVO_PATH = os.path.join(ROOT, "storage", "conversations", "demo.jsonl")


def ensure_profile() -> None:
    if os.path.exists(PROFILE_PATH):
        return
    profile = {
        "user_id": "u_demo",
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
    save_profile(PROFILE_PATH, profile)


def log_event(event: dict) -> None:
    append_event(CONVO_PATH, event)


def run_case(question: str, now: dt.datetime) -> None:
    profile = load_profile(PROFILE_PATH)
    before_cache = dict(profile.get("node_cache", {}))
    before_keys = set(before_cache.keys())

    history_rounds = load_recent_rounds(CONVO_PATH, 5)
    log_event({"ts": now.isoformat(), "type": "user_message", "text": question})
    events = []

    def sink(event: dict) -> None:
        if event.get("type") == "llm_prompt":
            log_event(
                {
                    "ts": now.isoformat(),
                    "type": "llm_prompt",
                    "node": event.get("node"),
                    "system_prompt": event.get("system_prompt", ""),
                    "user_prompt": event.get("user_prompt", ""),
                }
            )
        events.append(event)

    result = run_turn(profile, question, now=now, event_sink=sink, history_rounds=history_rounds)
    log_event({"ts": now.isoformat(), "type": "plan", "plan": result["plan"]})
    log_event({"ts": now.isoformat(), "type": "outputs", "keys": list(result["outputs"].keys())})
    if result["time_context"]:
        log_event({"ts": now.isoformat(), "type": "time_context", "value": result["time_context"]})
    log_event({"ts": now.isoformat(), "type": "assistant_final", "text": result["response"]})

    save_profile(PROFILE_PATH, profile)

    cache_keys = list(profile.get("node_cache", {}).keys())
    added_keys = [k for k in cache_keys if k not in before_keys]
    changed_keys = []
    for key in before_keys:
        if key in profile.get("node_cache", {}):
            before_hash = before_cache[key].get("inputs_hash")
            after_hash = profile["node_cache"][key].get("inputs_hash")
            if before_hash != after_hash:
                changed_keys.append(key)
    print("Question:", question)
    print("Plan:", json.dumps(result["plan"], ensure_ascii=False))
    print("Cache keys:", cache_keys)
    print("New cache entries:", added_keys)
    print("Changed cache entries:", changed_keys)
    print("Response head:", result["response"].split("\n")[0])
    print("---")
    return added_keys, changed_keys


def assert_cache_hits(added_keys: list, changed_keys: list, expected_new: set, expected_changed: set) -> None:
    added_set = set(added_keys)
    changed_set = set(changed_keys)
    assert added_set == expected_new, f"new cache mismatch: got {added_set}, expected {expected_new}"
    assert changed_set == expected_changed, f"changed cache mismatch: got {changed_set}, expected {expected_changed}"


def main() -> None:
    os.environ.setdefault("LLM_MODE", "stub")
    if os.path.exists(PROFILE_PATH):
        os.remove(PROFILE_PATH)
    if os.path.exists(CONVO_PATH):
        os.remove(CONVO_PATH)
    ensure_profile()
    now = dt.datetime(2025, 12, 20, 10, 0, 0)

    questions = [
        (
            "今年事业怎么样",
            {"PAIPAN", "OVERALL", "SHISHEN", "GEJU", "WUXING_PREFS", "CAREER", "TIME_CONTEXT", "FINAL"},
            set(),
        ),
        ("2026年3月感情如何", {"RELATIONSHIP"}, {"TIME_CONTEXT", "FINAL"}),
        ("2024年健康需要注意什么", {"HEALTH"}, {"TIME_CONTEXT", "FINAL"}),
        ("财运如何", {"OTHER"}, {"FINAL"}),
        ("贵人方面有帮助吗", {"GUIREN"}, {"FINAL"}),
        ("六亲关系如何", {"LIUQIN"}, {"FINAL"}),
        ("我性格特点是什么", {"XINGGE"}, {"FINAL"}),
        ("总体运势如何", set(), {"FINAL"}),
    ]

    for q, expected_new, expected_changed in questions:
        added, changed = run_case(q, now)
        assert_cache_hits(added, changed, expected_new, expected_changed)
        now = now + dt.timedelta(minutes=5)

    profile = load_profile(PROFILE_PATH)
    summary = {}
    for key, entry in profile.get("node_cache", {}).items():
        summary[key] = {
            "created_at": entry.get("created_at"),
            "inputs_hash": entry.get("inputs_hash"),
        }
    print("Cache summary:", json.dumps(summary, ensure_ascii=False))
    print("Conversation log:", CONVO_PATH)
    print("Profile path:", PROFILE_PATH)


if __name__ == "__main__":
    main()
