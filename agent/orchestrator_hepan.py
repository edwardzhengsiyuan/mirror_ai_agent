"""Orchestrator for BaZi HePan compatibility turns.

The system prompt and user-prompt structure mirror the original
``bazi_langgraph_integrate/src/agents/bazi_hepan_agent.py`` Langgraph agent:

* ``hepan.md`` is loaded as the full system prompt (≈16 KB of compatibility
  theory and instructions).
* The user prompt contains both individuals' full paipan / liupan / guji
  texts, plus the user's question and recent dialogue history.
"""

from __future__ import annotations

import datetime as dt
import os
import time
from functools import lru_cache
from typing import Any, Dict, List, Optional

from .events import EventSink, emit_event
from .llm_config import default_model
from .tools.hepan_tool import hepan_tool
from .tools.llm_tool import llm_report_tool

PROMPTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "prompts", "templates")

HEPAN_SYSTEM_PROMPT_FALLBACK = (
    "你是一位擅长八字合盘的咨询师，请基于两人完整命盘进行匹配度分析。"
)


@lru_cache(maxsize=4)
def _load_template(name: str) -> str:
    path = os.path.join(PROMPTS_DIR, name)
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return ""


def _format_history(history_rounds: Optional[List[Dict[str, str]]]) -> str:
    if not history_rounds:
        return "无"
    lines: List[str] = []
    for idx, pair in enumerate(history_rounds, start=1):
        lines.append(f"Round {idx}")
        lines.append(f"User: {pair.get('user', '')}")
        lines.append(f"Assistant: {pair.get('assistant', '')}")
    return "\n".join(lines)


def _person_block(label: str, person: Dict[str, Any]) -> str:
    name = person.get("name") or label
    birth = person.get("birth") or {}
    gender_cn = "男" if person.get("gender") == "male" else "女"
    birth_str = (
        f"{birth.get('year', '?')}-{birth.get('month', '?')}-{birth.get('day', '?')} "
        f"{birth.get('hour', 0):02d}:{birth.get('minute', 0):02d}"
    )
    paipan = person.get("paipan_text") or ""
    liupan = person.get("liupan_text") or ""
    guji = person.get("guji_text") or ""
    return (
        f"【{label}：{name}（{gender_cn}，公历 {birth_str}）的命盘】\n"
        f"排盘结果：\n{paipan}\n\n"
        f"流年大运：\n{liupan}\n\n"
        f"古籍参考：\n{guji}"
    )


def build_hepan_prompt(
    question: str,
    hepan_result: Dict[str, Any],
    history_rounds: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, str]:
    """Build the (system, user) prompt pair for the HePan LLM call."""
    system_prompt = _load_template("hepan.md") or HEPAN_SYSTEM_PROMPT_FALLBACK

    person_a = hepan_result.get("person_a", {})
    person_b = hepan_result.get("person_b", {})

    parts: List[str] = [
        _person_block("第一个人", person_a),
        "",
        _person_block("第二个人", person_b),
        "",
        "请根据八字合婚的规则，从六个方面进行分析，给各个面向打分，并给出最终分数和建议。",
    ]
    if question and question.strip():
        parts.extend(
            [
                "",
                "用户的具体问题（请优先回应，并自然融入合婚分析中）：",
                question.strip(),
            ]
        )
    if history_rounds:
        parts.extend(["", "近期对话：", _format_history(history_rounds)])

    user_prompt = "\n".join(parts)
    return {"system_prompt": system_prompt, "user_prompt": user_prompt}


def run_hepan_turn(
    question: str,
    person_a: Dict[str, Any],
    person_b: Dict[str, Any],
    now: dt.datetime | None = None,
    event_sink: EventSink | None = None,
    stream: bool = False,
    history_rounds: Optional[List[Dict[str, str]]] = None,
    model: str | None = None,
    node_model_overrides: Dict[str, str] | None = None,
) -> Dict[str, Any]:
    """Execute one HePan compatibility turn."""
    now = now or dt.datetime.now()
    tool_started = time.perf_counter()
    emit_event(event_sink, {"type": "tool_call", "tool": "hepan_tool", "node": "HEPAN"})
    hepan_result = hepan_tool({"person_a": person_a, "person_b": person_b})
    tool_duration_ms = int((time.perf_counter() - tool_started) * 1000)
    emit_event(event_sink, {"type": "tool_result", "tool": "hepan_tool", "node": "HEPAN"})
    emit_event(
        event_sink,
        {
            "type": "tool_invocation",
            "tool": "HEPAN",
            "input": {"person_a": person_a, "person_b": person_b},
            "output": hepan_result,
            "duration_ms": tool_duration_ms,
        },
    )

    prompt = build_hepan_prompt(question, hepan_result, history_rounds)
    emit_event(
        event_sink,
        {
            "type": "llm_prompt",
            "node": "HEPAN_RESPONSE",
            "system_prompt": prompt["system_prompt"],
            "user_prompt": prompt["user_prompt"],
        },
    )

    response_started = time.perf_counter()
    emit_event(event_sink, {"type": "tool_call", "tool": "llm_report_tool", "node": "HEPAN_RESPONSE"})
    response_output = llm_report_tool(
        prompt["system_prompt"],
        prompt["user_prompt"],
        model=model or default_model(),
        node="HEPAN_RESPONSE",
        node_model_overrides=node_model_overrides,
        stream=stream,
        on_delta=(
            lambda chunk: emit_event(
                event_sink,
                {
                    "type": "response_delta",
                    "delta": chunk.get("content", ""),
                    "reasoning_delta": chunk.get("reasoning_content", ""),
                },
            )
        )
        if event_sink
        else None,
        event_sink=event_sink,
    )
    emit_event(event_sink, {"type": "tool_result", "tool": "llm_report_tool", "node": "HEPAN_RESPONSE"})
    response_duration_ms = int((time.perf_counter() - response_started) * 1000)
    response_text = response_output.get("content") if isinstance(response_output, dict) else ""
    if not response_text:
        score = hepan_result.get("compatibility", {}).get("score", {}).get("overall")
        response_text = f"合盘已完成，综合分数为 {score}。"

    emit_event(
        event_sink,
        {
            "type": "response",
            "text": response_text,
            "input_summary": {
                "method": "hepan",
                "score": hepan_result.get("compatibility", {}).get("score"),
            },
            "llm_prompt": prompt,
            "duration_ms": response_duration_ms,
        },
    )

    return {
        "method": "hepan",
        "question": question,
        "time": now.isoformat(),
        "hepan": hepan_result,
        "response": response_text,
    }
