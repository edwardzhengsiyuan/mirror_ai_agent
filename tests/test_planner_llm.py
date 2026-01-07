from __future__ import annotations

import datetime as dt
import os
import sys

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, ROOT)

from agent import planning


def test_planner_llm_tool_call(monkeypatch) -> None:
    def fake_llm(system_prompt, user_prompt, model=None, node=None, sleep_ms=None, stream=False, on_delta=None):
        return {
            "type": "report",
            "content": '{"tool":"planning_tool","args":{"aspects":["career"],"times":[{"need_tool":true,"granularity":"year","ref_text":"今年","year":2025}]}}',
            "structured": {},
            "reasoning_content": "",
            "error": False,
        }

    monkeypatch.setattr(planning, "llm_report_tool", fake_llm)
    now = dt.datetime(2025, 1, 1, 12, 0, 0)
    result = planning.plan_with_llm("今年事业怎么样", now=now)
    assert result["aspects"] == ["CAREER"]
    assert result["time"]["need_tool"] is True
    assert result["time"]["year"] == 2025
    assert len(result.get("times", [])) == 1
