from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, ROOT)

from agent.tools.hepan_tool import hepan_tool


def test_hepan_tool_returns_compatibility_shape() -> None:
    result = hepan_tool(
        {
            "person_a": {
                "name": "A",
                "gender": "female",
                "birth": {"year": 1990, "month": 1, "day": 1, "hour": 8},
            },
            "person_b": {
                "name": "B",
                "gender": "male",
                "birth": {"year": 1991, "month": 2, "day": 2, "hour": 9},
            },
        }
    )

    assert result["type"] == "hepan"
    compatibility = result["compatibility"]
    assert "score" in compatibility
    assert "overall" in compatibility["score"]
    assert "shengxiao_hehun" in compatibility
    assert "wuxing_vector" in compatibility
    assert "a_wang_b" in compatibility
    assert "b_wang_a" in compatibility
