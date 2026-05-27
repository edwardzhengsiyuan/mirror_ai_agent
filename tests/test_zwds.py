"""Unit tests for the Ziwei Doushu (紫微斗数) tool and orchestrator."""

from __future__ import annotations

import os
import sys
from typing import Any, Dict, List

import pytest

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, ROOT)

from agent import orchestrator_zwds
from agent.tools.zwds_tool import zwds_tool


# ---------------------------------------------------------------------------
# Tool-level tests
# ---------------------------------------------------------------------------


def test_zwds_tool_returns_chart_text() -> None:
    result = zwds_tool(
        {
            "birth": {"year": 1990, "month": 5, "day": 12, "hour": 8},
            "gender": "male",
            "target_years": [2026],
        }
    )

    assert result["type"] == "zwds"
    assert result["gender"] == "male"
    assert result["target_years"] == [2026]
    assert "本命盘报告" in result["benming_info"]
    assert len(result["liunian_infos"]) == 1
    assert result["liunian_infos"][0]["year"] == 2026
    assert "2026年分析结果" in result["liunian_infos"][0]["text"]
    assert result["raw_text"].startswith(result["benming_info"])


def test_zwds_tool_defaults_to_current_year_when_target_years_omitted() -> None:
    import datetime as dt

    result = zwds_tool(
        {
            "birth": {"year": 1990, "month": 5, "day": 12, "hour": 8},
            "gender": "female",
        }
    )

    current_year = dt.datetime.now().year
    assert result["target_years"] == [current_year]
    assert len(result["liunian_infos"]) == 1


@pytest.mark.parametrize(
    "payload, exc_match",
    [
        ({"birth": {"year": 1990, "month": 13, "day": 1}}, "month"),
        ({"birth": {"year": 1990, "month": 1, "day": 32}}, "day"),
        ({"birth": {"year": 1990, "month": 1, "day": 1}, "gender": "neuter"}, "gender"),
    ],
)
def test_zwds_tool_validates_inputs(payload: Dict[str, Any], exc_match: str) -> None:
    with pytest.raises(ValueError, match=exc_match):
        zwds_tool(payload)


# ---------------------------------------------------------------------------
# Orchestrator-level tests (LLM stubbed)
# ---------------------------------------------------------------------------


def _stub_llm_factory(captured: List[Dict[str, str]]):
    def _stub(system_prompt: str, user_prompt: str, **_kwargs):
        captured.append({"system_prompt": system_prompt, "user_prompt": user_prompt})
        return {
            "type": "report",
            "content": "[STUB] zwds response",
            "structured": None,
            "reasoning_content": None,
            "stub": True,
            "error": False,
        }

    return _stub


def test_zwds_orchestrator_uses_real_prompt_md_by_default(monkeypatch) -> None:
    captured: List[Dict[str, str]] = []
    monkeypatch.setattr(orchestrator_zwds, "llm_report_tool", _stub_llm_factory(captured))
    monkeypatch.delenv("LLM_ZWDS_INCLUDE_STAR_GONG", raising=False)

    result = orchestrator_zwds.run_zwds_turn(
        question="今年我的事业和感情运势如何？",
        birth={"year": 1990, "month": 5, "day": 12, "hour": 8},
        gender="male",
        target_years=[2026],
    )

    assert len(captured) == 1
    call = captured[0]

    # Lean default: prompt.md (~7KB UTF-8, ~2.2K chars) loaded,
    # star_gong.md (~973KB) NOT loaded.
    assert "紫微斗数" in call["system_prompt"]
    assert 2000 < len(call["system_prompt"]) < 50_000, (
        f"Default zwds system prompt should be ~prompt.md size, got {len(call['system_prompt'])}"
    )
    # And star_gong.md content (e.g. its leading "1.紫微星" heading) should NOT
    # be present unless explicitly requested.
    assert "1.紫微星" not in call["system_prompt"]

    user = call["user_prompt"]
    assert "紫微斗数排盘信息" in user
    assert "本命盘报告" in user
    assert "2026年分析结果" in user
    assert "今年我的事业和感情运势如何" in user

    assert result["response"] == "[STUB] zwds response"
    assert result["zwds"]["target_years"] == [2026]


def test_zwds_orchestrator_includes_star_gong_when_requested(monkeypatch) -> None:
    captured: List[Dict[str, str]] = []
    monkeypatch.setattr(orchestrator_zwds, "llm_report_tool", _stub_llm_factory(captured))

    orchestrator_zwds.run_zwds_turn(
        question="测试",
        birth={"year": 1990, "month": 5, "day": 12, "hour": 8},
        gender="male",
        include_star_gong=True,
    )

    assert len(captured) == 1
    sys_prompt = captured[0]["system_prompt"]
    # star_gong.md alone is ≈973 KB UTF-8 / ≈325K Chinese chars, so the
    # prompt should be far above any reasonable plain prompt.md threshold.
    assert len(sys_prompt) > 100_000, (
        f"Expected star_gong.md to be injected, got {len(sys_prompt)} chars"
    )
    assert "1.紫微星" in sys_prompt


def test_zwds_orchestrator_respects_env_var_for_star_gong(monkeypatch) -> None:
    captured: List[Dict[str, str]] = []
    monkeypatch.setattr(orchestrator_zwds, "llm_report_tool", _stub_llm_factory(captured))
    monkeypatch.setenv("LLM_ZWDS_INCLUDE_STAR_GONG", "1")

    orchestrator_zwds.run_zwds_turn(
        question="测试",
        birth={"year": 1990, "month": 5, "day": 12, "hour": 8},
        gender="male",
    )

    assert len(captured) == 1
    assert len(captured[0]["system_prompt"]) > 100_000
