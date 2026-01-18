from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, ROOT)

from agent.tools.planning_tool import planning_tool


def test_need_tool_overridden_when_time_fields_present() -> None:
    result = planning_tool(
        ["HEALTH"],
        None,
        times=[{"need_tool": False, "granularity": "year", "ref_text": "2035年", "year": 2035}],
    )
    assert result["times"][0]["need_tool"] is True


def test_dayun_normalized_to_ganzhi_only() -> None:
    result = planning_tool(
        ["HEALTH"],
        None,
        times=[
            {
                "need_tool": True,
                "granularity": "dayun",
                "ref_text": "己巳 2029-2038",
                "dayun": "己巳 2029-2038",
            }
        ],
    )
    assert result["times"][0]["dayun"] == "己巳"
