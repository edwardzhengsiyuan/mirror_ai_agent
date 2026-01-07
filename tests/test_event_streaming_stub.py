from __future__ import annotations

import datetime as dt
import os
import sys

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, ROOT)

from agent import execution
from agent.orchestrator import run_turn


def test_streaming_events_stub(monkeypatch) -> None:
    monkeypatch.setenv("LLM_MODE", "stub")

    def fake_paipan(inputs):
        return {
            "paipan_results": "paipan",
            "liupan_results": "liupan",
            "guji_results": "guji",
            "paipan_output": {"yun": []},
        }

    def fake_time_context(
        dayun_list,
        liunian_list,
        ref_text,
        now,
        target_year=None,
        target_month=None,
        target_dayun=None,
        liuyue_by_year=None,
        requests=None,
    ):
        if requests is not None:
            results = []
            for idx, req in enumerate(requests):
                results.append(
                    {
                        "matched": True,
                        "granularity": "year",
                        "raw_match": req.get("ref_text"),
                        "index": req.get("index", idx),
                    }
                )
            return results
        return {"matched": True, "granularity": "year", "raw_match": ref_text}

    monkeypatch.setattr(execution, "paipan_tool", fake_paipan)
    monkeypatch.setattr(execution, "time_context_tool", fake_time_context)

    events = []

    def sink(event):
        events.append(event)

    profile = {
        "user_id": "u_test",
        "birth": {"year": 1990, "month": 1, "day": 1, "hour": 8, "minute": 0, "second": 0},
        "gender": "male",
        "birth_time_unknown": False,
        "prompt_config": "lingyun_cat",
        "node_cache": {},
    }
    now = dt.datetime(2025, 1, 1, 10, 0, 0)
    run_turn(profile, "今年事业怎么样", now=now, event_sink=sink, stream=True)

    assert any(e["type"] == "plan" for e in events)
    assert any(e["type"] == "node_start" and e["node"] == "PLANNER" for e in events)
    assert any(e["type"] == "tool_call" and e["tool"] == "paipan_tool" for e in events)
    assert any(e["type"] == "llm_prompt" and e["node"] == "OVERALL" for e in events)
    assert any(e["type"] == "node_start" and e["node"] == "OVERALL" for e in events)
    assert any(e["type"] == "node_delta" and e["node"] == "OVERALL" for e in events)
    assert any(e["type"] == "node_end" and e["node"] == "CAREER" for e in events)
    assert any(e["type"] == "node_end" and e["node"] == "FINAL" for e in events)
