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

    # Full-chart text fields are required by the LLM-facing orchestrator
    # (mirrors the original bazi_langgraph_integrate hepan agent input).
    for key in ("paipan_text", "liupan_text", "guji_text"):
        assert key in result["person_a"]
        assert key in result["person_b"]
        assert isinstance(result["person_a"][key], str)
        assert isinstance(result["person_b"][key], str)
    assert result["person_a"]["paipan_text"], "paipan_text should be non-empty"
