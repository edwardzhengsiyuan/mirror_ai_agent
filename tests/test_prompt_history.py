from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, ROOT)

from agent.nodes.prompt_builder import build_prompt, build_response_prompt
from agent.storage.conversation_store import load_recent_rounds, load_latest_llm_prompts


def test_load_recent_rounds(tmp_path) -> None:
    convo_path = tmp_path / "demo.jsonl"
    events = [
        {"type": "user_message", "text": "u1"},
        {"type": "assistant_final", "text": "a1"},
        {"type": "user_message", "text": "u2"},
        {"type": "assistant_final", "text": "a2"},
        {"type": "user_message", "text": "u3"},
    ]
    with open(convo_path, "w", encoding="utf-8") as f:
        for event in events:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
    rounds = load_recent_rounds(str(convo_path), 1)
    assert rounds == [{"user": "u2", "assistant": "a2"}]


def test_final_prompt_includes_history() -> None:
    cache = {
        "PAIPAN": {"output": {"paipan_results": "", "liupan_results": "", "guji_results": ""}},
        "OVERALL": {"output": {"content": "overall"}},
    }
    history = [{"user": "以前的问题", "assistant": "之前的回答"}]
    # FINAL was renamed to Response - use build_response_prompt
    prompt = build_response_prompt(
        cache=cache,
        time_context=None,
        prompt_config="lingyun_cat",
        question="现在的问题",
        history_rounds=history
    )
    user_prompt = prompt["user_prompt"]
    # New layout uses a Chinese "对话历史" heading and Round-prefixed entries.
    assert "对话历史" in user_prompt
    assert "Round 1" in user_prompt
    assert "以前的问题" in user_prompt
    assert "之前的回答" in user_prompt


def test_load_latest_llm_prompts(tmp_path) -> None:
    convo_path = tmp_path / "demo.jsonl"
    events = [
        {"type": "llm_prompt", "node": "OVERALL", "system_prompt": "sys1", "user_prompt": "user1"},
        {"type": "llm_prompt", "node": "OVERALL", "system_prompt": "sys2", "user_prompt": "user2"},
        {"type": "llm_prompt", "node": "CAREER", "system_prompt": "sys3", "user_prompt": "user3"},
    ]
    with open(convo_path, "w", encoding="utf-8") as f:
        for event in events:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
    latest = load_latest_llm_prompts(str(convo_path))
    assert latest["OVERALL"]["system_prompt"] == "sys2"
    assert latest["OVERALL"]["user_prompt"] == "user2"
    assert latest["CAREER"]["system_prompt"] == "sys3"
