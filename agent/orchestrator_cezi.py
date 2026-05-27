"""Orchestrator for CeZi character divination turns.

The system prompt is loaded from ``cezi.md`` (≈15 KB of character-divination
theory and instructions), matching the original
``bazi_langgraph_integrate/src/agents/cezi_agent.py`` Langgraph agent.
"""

from __future__ import annotations

import datetime as dt
import os
import time
from functools import lru_cache
from typing import Any, Dict, List, Optional

from .events import EventSink, emit_event
from .llm_config import default_model
from .tools.cezi_tool import cezi_tool
from .tools.llm_tool import llm_report_tool

PROMPTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "prompts", "templates")

CEZI_SYSTEM_PROMPT_FALLBACK = (
    "你是一位擅长测字的咨询师，请结合字形、偏旁、拆字与语境联想分析用户所问之事。"
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


def build_cezi_prompt(
    cezi_result: Dict[str, Any],
    history_rounds: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, str]:
    """Build the (system, user) prompt pair for the CeZi LLM call."""
    system_prompt = _load_template("cezi.md") or CEZI_SYSTEM_PROMPT_FALLBACK

    character = cezi_result.get("character", "")
    question = cezi_result.get("question", "")

    parts: List[str] = [
        f"这是用户要测的字：{character}",
        "",
        f"这是用户的问题：{question}",
        "",
        "请根据测字的规则，对这个字进行分析，并回答用户的问题。",
    ]
    if history_rounds:
        parts.extend(["", "近期对话：", _format_history(history_rounds)])

    user_prompt = "\n".join(parts)
    return {"system_prompt": system_prompt, "user_prompt": user_prompt}


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
