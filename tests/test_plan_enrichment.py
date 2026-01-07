from __future__ import annotations

import datetime as dt
import os
import sys

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, ROOT)

from agent import execution
from agent.orchestrator import run_turn


def test_plan_enriches_dayun_from_time_context(monkeypatch) -> None:
    monkeypatch.setenv("LLM_MODE", "stub")

    def fake_paipan(inputs):
        return {
            "paipan_results": "",
            "liupan_results": "",
            "guji_results": "",
            "paipan_output": {},
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
        if requests is None:
            return None
        return [
            {
                "index": req.get("index", idx),
                "matched": True,
                "dayun": {"name": "DAYUN_A", "start_year": 2028, "end_year": 2037},
                "year": {"year": 2035, "ganzhi": "YIMAO", "age": 35},
            }
            for idx, req in enumerate(requests)
        ]

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
    result = run_turn(profile, "2035年事业如何", now=now, event_sink=sink, stream=False)

    assert result["plan"]["time"]["dayun"] == "DAYUN_A"
    assert any(e.get("type") == "plan_update" for e in events)
