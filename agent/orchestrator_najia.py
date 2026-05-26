"""Orchestrator for Najia/Liuyao divination turns."""

from __future__ import annotations

import datetime as dt
import json
import time
from typing import Any, Dict, List, Optional

from .events import EventSink, emit_event
from .llm_config import default_model
from .tools.llm_tool import llm_report_tool
from .tools.najia_tool import najia_tool

NAJIA_SYSTEM_PROMPT = """你是一位擅长六爻纳甲的咨询师。
请基于卦盘结构、六亲、世应、动爻、变卦、旬空等信息进行分析。
表达要清楚、审慎，避免恐吓和绝对化断语。
"""

NAJIA_USER_PROMPT_TEMPLATE = """请根据下面的六爻纳甲卦盘回答用户问题。

要求：
1. 先说明本卦、变卦、世应和动爻的总体含义。
2. 再结合用户问题判断用神方向，说明有利与不利因素。
3. 给出趋势判断和行动建议。
4. 如果信息不足，请明确说明不确定处。

近期对话：
{history}

卦盘：
{najia_json}
"""


def _format_history(history_rounds: Optional[List[Dict[str, str]]]) -> str:
    if not history_rounds:
        return "无"
    lines: List[str] = []
    for idx, pair in enumerate(history_rounds, start=1):
        lines.append(f"Round {idx}")
        lines.append(f"User: {pair.get('user', '')}")
        lines.append(f"Assistant: {pair.get('assistant', '')}")
    return "\n".join(lines)


def build_najia_prompt(
    najia_result: Dict[str, Any],
    history_rounds: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, str]:
    user_prompt = NAJIA_USER_PROMPT_TEMPLATE.format(
        history=_format_history(history_rounds),
        najia_json=json.dumps(najia_result, ensure_ascii=False, indent=2),
    )
    return {"system_prompt": NAJIA_SYSTEM_PROMPT, "user_prompt": user_prompt}


def run_najia_turn(
    question: str,
    yao_values: Optional[List[int]] = None,
    now: dt.datetime | None = None,
    event_sink: EventSink | None = None,
    stream: bool = False,
    history_rounds: Optional[List[Dict[str, str]]] = None,
    model: str | None = None,
    node_model_overrides: Dict[str, str] | None = None,
) -> Dict[str, Any]:
    """Execute one Najia/Liuyao turn."""
    now = now or dt.datetime.now()
    tool_started = time.perf_counter()
    emit_event(event_sink, {"type": "tool_call", "tool": "najia_tool", "node": "NAJIA"})
    najia_result = najia_tool({"question": question, "yao_values": yao_values})
    tool_duration_ms = int((time.perf_counter() - tool_started) * 1000)
    emit_event(event_sink, {"type": "tool_result", "tool": "najia_tool", "node": "NAJIA"})
    emit_event(
        event_sink,
        {
            "type": "tool_invocation",
            "tool": "NAJIA",
            "input": {"question": question, "yao_values": yao_values},
            "output": najia_result,
            "duration_ms": tool_duration_ms,
        },
    )

    prompt = build_najia_prompt(najia_result, history_rounds)
    emit_event(
        event_sink,
        {
            "type": "llm_prompt",
            "node": "NAJIA_RESPONSE",
            "system_prompt": prompt["system_prompt"],
            "user_prompt": prompt["user_prompt"],
        },
    )

    response_started = time.perf_counter()
    emit_event(event_sink, {"type": "tool_call", "tool": "llm_report_tool", "node": "NAJIA_RESPONSE"})
    response_output = llm_report_tool(
        prompt["system_prompt"],
        prompt["user_prompt"],
        model=model or default_model(),
        node="NAJIA_RESPONSE",
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
    emit_event(event_sink, {"type": "tool_result", "tool": "llm_report_tool", "node": "NAJIA_RESPONSE"})
    response_duration_ms = int((time.perf_counter() - response_started) * 1000)
    response_text = response_output.get("content") if isinstance(response_output, dict) else ""
    if not response_text:
        response_text = najia_result["raw_text"]

    emit_event(
        event_sink,
        {
            "type": "response",
            "text": response_text,
            "input_summary": {
                "method": "najia",
                "bengua": najia_result["bengua"]["fullname"],
                "biangua": najia_result["biangua"]["fullname"],
            },
            "llm_prompt": prompt,
            "duration_ms": response_duration_ms,
        },
    )

    return {
        "method": "najia",
        "question": question,
        "time": now.isoformat(),
        "najia": najia_result,
        "response": response_text,
    }
