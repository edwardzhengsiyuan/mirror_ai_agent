from __future__ import annotations

import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, ROOT)

from agent.tools.najia_tool import najia_tool


def test_najia_tool_returns_hexagram_shape() -> None:
    result = najia_tool(
        {
            "question": "这个项目三个月内能不能推进成功？",
            "yao_values": [0, 1, 2, 3, 4, 5],
        }
    )

    assert result["type"] == "najia"
    assert result["yao_values"] == [0, 1, 2, 3, 4, 5]
    assert result["bengua"]["fullname"]
    assert result["biangua"]["fullname"]
    assert len(result["bengua"]["lines"]) == 6
    assert len(result["biangua"]["lines"]) == 6
    assert "本卦" in result["raw_text"]
    assert "变卦" in result["raw_text"]


@pytest.mark.parametrize("values", [[0, 1], [0, 1, 2, 3, 4, 8], "bad"])
def test_najia_tool_rejects_invalid_yao_values(values) -> None:
    with pytest.raises(ValueError):
        najia_tool({"question": "项目如何？", "yao_values": values})
