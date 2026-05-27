"""Tests for HePan / CeZi / Najia orchestrator prompt assembly.

These tests stub the LLM call so they remain fast and offline. They are the
regression guard that the migrated divination prompts (hepan.md / cezi.md /
najia.md from the original bazi_langgraph_integrate repo) actually reach the
LLM, and that the per-divination user prompts include the right structured
context (full per-person paipan/liupan/guji for hepan, raw gua text for najia,
and the user character + question for cezi).
"""

from __future__ import annotations

import os
import sys
from typing import Any, Dict, List

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, ROOT)

from agent import orchestrator_cezi, orchestrator_hepan, orchestrator_najia


def _stub_llm_factory(captured: List[Dict[str, str]]):
    """Return a llm_report_tool stub that records every call."""

    def _stub(system_prompt: str, user_prompt: str, **_kwargs):
        captured.append({"system_prompt": system_prompt, "user_prompt": user_prompt})
        return {
            "type": "report",
            "content": "[STUB] divination response",
            "structured": None,
            "reasoning_content": None,
            "stub": True,
            "error": False,
        }

    return _stub


def test_hepan_prompt_uses_full_charts_and_real_system_prompt(monkeypatch) -> None:
    captured: List[Dict[str, str]] = []
    monkeypatch.setattr(orchestrator_hepan, "llm_report_tool", _stub_llm_factory(captured))

    result = orchestrator_hepan.run_hepan_turn(
        question="我们能在三年内一起买房吗？",
        person_a={
            "name": "Alice",
            "gender": "female",
            "birth": {"year": 1990, "month": 1, "day": 1, "hour": 8},
        },
        person_b={
            "name": "Bob",
            "gender": "male",
            "birth": {"year": 1991, "month": 2, "day": 2, "hour": 9},
        },
    )

    assert len(captured) == 1
    call = captured[0]

    # System prompt must come from hepan.md (≈16KB), not the legacy 1-line
    # placeholder. Anything > 4KB indicates the file was loaded.
    assert len(call["system_prompt"]) > 4000, (
        f"hepan.md was not loaded (system_prompt only {len(call['system_prompt'])} chars)"
    )

    user = call["user_prompt"]
    assert "Alice" in user
    assert "Bob" in user
    assert "排盘结果" in user
    assert "流年大运" in user
    assert "古籍参考" in user
    assert "我们能在三年内一起买房吗" in user
    # The orchestrator should still succeed and propagate the LLM response.
    assert result["response"] == "[STUB] divination response"
    assert result["hepan"]["person_a"]["paipan_text"]


def test_cezi_prompt_uses_real_system_prompt(monkeypatch) -> None:
    captured: List[Dict[str, str]] = []
    monkeypatch.setattr(orchestrator_cezi, "llm_report_tool", _stub_llm_factory(captured))

    result = orchestrator_cezi.run_cezi_turn(
        question="合作能不能成？",
        character="合",
    )

    assert len(captured) == 1
    call = captured[0]

    # System prompt must come from cezi.md (≈15KB).
    assert len(call["system_prompt"]) > 4000, (
        f"cezi.md was not loaded (system_prompt only {len(call['system_prompt'])} chars)"
    )

    user = call["user_prompt"]
    assert "这是用户要测的字：合" in user
    assert "这是用户的问题：合作能不能成" in user
    assert result["response"] == "[STUB] divination response"


def test_najia_prompt_uses_real_system_prompt(monkeypatch) -> None:
    captured: List[Dict[str, str]] = []
    monkeypatch.setattr(orchestrator_najia, "llm_report_tool", _stub_llm_factory(captured))

    result = orchestrator_najia.run_najia_turn(
        question="这个项目三个月内能不能推进成功？",
        yao_values=[0, 1, 2, 3, 4, 5],
    )

    assert len(captured) == 1
    call = captured[0]

    # System prompt = base role + najia.md (≈15KB rules).
    assert "六爻咨询师" in call["system_prompt"]
    assert len(call["system_prompt"]) > 4000, (
        f"najia.md was not loaded (system_prompt only {len(call['system_prompt'])} chars)"
    )

    user = call["user_prompt"]
    assert "当前用户提出的问题是" in user
    assert "占卜的结果如下" in user
    assert "本卦" in user
    assert "变卦" in user
    assert result["response"] == "[STUB] divination response"


def test_najia_paraphrase_two_stage_runs_two_llm_calls(monkeypatch) -> None:
    captured: List[Dict[str, str]] = []
    monkeypatch.setattr(orchestrator_najia, "llm_report_tool", _stub_llm_factory(captured))

    result = orchestrator_najia.run_najia_turn(
        question="未来半年的创业运势如何？",
        yao_values=[0, 1, 2, 3, 4, 5],
        paraphrase=True,
    )

    assert len(captured) == 2, "paraphrase mode should trigger a second LLM call"
    paraphrase_user = captured[1]["user_prompt"]
    assert "请用通俗的语言向用户解释卦象" in paraphrase_user
    assert "之前的分析内容如下" in paraphrase_user
    assert "## 占卜结果" in result["response"]
    assert "## 分析解读" in result["response"]
    assert "## 通俗解释" in result["response"]
