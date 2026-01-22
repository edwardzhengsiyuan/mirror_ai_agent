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
        times=[{"need_tool": False, "ref_text": "2035年", "year": 2035}],
    )
    assert result["times"][0]["need_tool"] is True


def test_time_item_has_expected_fields() -> None:
    result = planning_tool(
        ["CAREER"],
        None,
        times=[{"need_tool": True, "ref_text": "2026", "year": 2026}],
    )
    time_item = result["times"][0]
    assert "need_tool" in time_item
    assert "ref_text" in time_item
    assert "year" in time_item
    # granularity and month are no longer in the output (simplified)
    assert "granularity" not in time_item
    assert "month" not in time_item
