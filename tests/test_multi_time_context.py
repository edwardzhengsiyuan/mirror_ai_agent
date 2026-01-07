from __future__ import annotations

import datetime as dt
import os
import sys

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, ROOT)

from agent import execution
from agent.orchestrator import run_turn


def test_multi_time_requests(monkeypatch) -> None:
    monkeypatch.setenv("LLM_MODE", "stub")

    def fake_paipan(inputs):
        return {
            "paipan_results": "",
            "liupan_results": "",
            "guji_results": "",
            "paipan_output": {},
            "time_index": {"dayun_list": [], "liunian_list": [], "liuyue_by_year": {}},
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
            {"index": req.get("index", idx), "matched": True, "year": {"year": req.get("target_year")}}
            for idx, req in enumerate(requests)
        ]

    monkeypatch.setattr(execution, "paipan_tool", fake_paipan)
    monkeypatch.setattr(execution, "time_context_tool", fake_time_context)

    profile = {
        "user_id": "u_test",
        "birth": {"year": 1990, "month": 1, "day": 1, "hour": 8, "minute": 0, "second": 0},
        "gender": "male",
        "birth_time_unknown": False,
        "prompt_config": "lingyun_cat",
        "node_cache": {},
    }
    now = dt.datetime(2025, 1, 1, 10, 0, 0)
    result = run_turn(profile, "2035年、2045年健康贵人怎么样", now=now, stream=False)

    assert len(result["plan"].get("times", [])) == 2
    assert isinstance(result["time_context"], list)
    assert len(result["time_context"]) == 2
