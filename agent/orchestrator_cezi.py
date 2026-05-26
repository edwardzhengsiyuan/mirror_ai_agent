"""Orchestrator for CeZi character divination turns."""

from __future__ import annotations

import datetime as dt
import json
import time
from typing import Any, Dict, List, Optional

from .events import EventSink, emit_event
from .llm_config import default_model
from .tools.cezi_tool import cezi_tool
from .tools.llm_tool import llm_report_tool

CEZI_SYSTEM_PROMPT = """你是一位擅长测字的咨询师。
你会结合字形、偏旁、拆字、增减笔、语境联想与用户所问之事进行分析。
请保持解释清楚、审慎，不要使用恐吓式或绝对化表达。
"""

CEZI_USER_PROMPT_TEMPLATE = """请根据下面的测字请求回答用户。

要求：
1. 围绕用户给出的字和问题展开，不要泛泛而谈。
2. 至少从字形/结构、含义联想、与问题的对应关系三个角度分析。
3. 最后给出简短建议。

近期对话：
{history}

测字请求：
{cezi_json}
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


def build_cezi_prompt(
    cezi_result: Dict[str, Any],
    history_rounds: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, str]:
    user_prompt = CEZI_USER_PROMPT_TEMPLATE.format(
        history=_format_history(history_rounds),
        cezi_json=json.dumps(cezi_result, ensure_ascii=False, indent=2),
    )
    return {"system_prompt": CEZI_SYSTEM_PROMPT, "user_prompt": user_prompt}


def run_cezi_turn(
    question: str,
    character: str,
    now: dt.datetime | None = None,
    event_sink: EventSink | None = None,
    stream: bool = False,
    history_rounds: Optional[List[Dict[str, str]]] = None,
    model: str | None = None,
    node_model_overrides: Dict[str, str] | None = None,
) -> Dict[str, Any]:
    """Execute one CeZi turn."""
    now = now or dt.datetime.now()
    tool_started = time.perf_counter()
    emit_event(event_sink, {"type": "tool_call", "tool": "cezi_tool", "node": "CEZI"})
    cezi_result = cezi_tool({"question": question, "character": character})
    tool_duration_ms = int((time.perf_counter() - tool_started) * 1000)
    emit_event(event_sink, {"type": "tool_result", "tool": "cezi_tool", "node": "CEZI"})
    emit_event(
        event_sink,
        {
            "type": "tool_invocation",
            "tool": "CEZI",
            "input": {"question": question, "character": character},
            "output": cezi_result,
            "duration_ms": tool_duration_ms,
        },
    )

    prompt = build_cezi_prompt(cezi_result, history_rounds)
    emit_event(
        event_sink,
        {
            "type": "llm_prompt",
            "node": "CEZI_RESPONSE",
            "system_prompt": prompt["system_prompt"],
            "user_prompt": prompt["user_prompt"],
        },
    )

    response_started = time.perf_counter()
    emit_event(event_sink, {"type": "tool_call", "tool": "llm_report_tool", "node": "CEZI_RESPONSE"})
    response_output = llm_report_tool(
        prompt["system_prompt"],
        prompt["user_prompt"],
        model=model or default_model(),
        node="CEZI_RESPONSE",
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
    emit_event(event_sink, {"type": "tool_result", "tool": "llm_report_tool", "node": "CEZI_RESPONSE"})
    response_duration_ms = int((time.perf_counter() - response_started) * 1000)
    response_text = response_output.get("content") if isinstance(response_output, dict) else ""
    if not response_text:
        response_text = f"已收到测字请求：以“{character}”字测“{question}”。"

    emit_event(
        event_sink,
        {
            "type": "response",
            "text": response_text,
            "input_summary": {
                "method": "cezi",
                "character": character,
                "question": question,
            },
            "llm_prompt": prompt,
            "duration_ms": response_duration_ms,
        },
    )

    return {
        "method": "cezi",
        "question": question,
        "character": character,
        "time": now.isoformat(),
        "cezi": cezi_result,
        "response": response_text,
    }
