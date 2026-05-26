from __future__ import annotations

import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, ROOT)

from agent.tools.cezi_tool import cezi_tool


def test_cezi_tool_accepts_single_chinese_character() -> None:
    result = cezi_tool({"character": "合", "question": "合作能不能成？"})
    assert result["type"] == "cezi"
    assert result["character"] == "合"
    assert result["question"] == "合作能不能成？"


@pytest.mark.parametrize("character", ["", "合作", "A"])
def test_cezi_tool_rejects_invalid_character(character: str) -> None:
    with pytest.raises(ValueError):
        cezi_tool({"character": character, "question": "合作能不能成？"})
