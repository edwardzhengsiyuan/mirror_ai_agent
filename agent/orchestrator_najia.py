"""Orchestrator for Najia/Liuyao divination turns.

The system prompt mirrors the original
``bazi_langgraph_integrate/src/agents/najia_agent.py`` Langgraph agent:
``COMPREHENSIVE_SYSTEM_PROMPT`` = role line + the full ``najia/prompt.md``
analysis-rule template (≈15 KB).

If ``paraphrase=True`` is requested, after the technical analysis a second LLM
call rewrites the response in plain language, and the final answer is the
combined "occult result + technical analysis + plain-language explanation"
text — matching the original two-stage flow. Default is single-shot to keep
token cost predictable.
"""

from __future__ import annotations

import datetime as dt
import os
import time
from functools import lru_cache
from typing import Any, Dict, List, Optional

from .events import EventSink, emit_event
from .llm_config import default_model
from .tools.llm_tool import llm_report_tool
from .tools.najia_tool import najia_tool

PROMPTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "prompts", "templates")

NAJIA_BASE_ROLE = "你是一位经验丰富的六爻咨询师，擅长使用纳甲筮法为用户占卜。"

NAJIA_SYSTEM_PROMPT_FALLBACK = (
    NAJIA_BASE_ROLE
    + "\n\n请基于卦盘结构、六亲、世应、动爻、变卦、旬空等信息进行分析。"
)


@lru_cache(maxsize=4)
def _load_template(name: str) -> str:
    path = os.path.join(PROMPTS_DIR, name)
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return ""


def _build_system_prompt() -> str:
    rules = _load_template("najia.md")
    if not rules:
        return NAJIA_SYSTEM_PROMPT_FALLBACK
    return f"{NAJIA_BASE_ROLE}\n\n{rules}"


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
    """Build the (system, user) prompt pair for the Najia analysis call."""
    system_prompt = _build_system_prompt()

    question = najia_result.get("question", "")
    raw_text = najia_result.get("raw_text", "")

    parts: List[str] = [
        "当前用户提出的问题是：",
        question,
        "",
        "占卜的结果如下：",
        raw_text,
        "",
        "请根据上述信息，为用户提供详细的分析和解答。",
    ]
    if history_rounds:
        parts.extend(["", "近期对话：", _format_history(history_rounds)])

    user_prompt = "\n".join(parts)
    return {"system_prompt": system_prompt, "user_prompt": user_prompt}


def _build_paraphrase_prompt(previous_content: str) -> Dict[str, str]:
    system_prompt = _build_system_prompt()
    user_prompt = (
        "请用通俗的语言向用户解释卦象。\n\n"
        f"之前的分析内容如下：\n{previous_content}\n\n"
        "请用简单易懂的语言重新解释，避免使用过于专业的术语，让普通用户能够轻松理解。\n\n"
        "你的回复："
    )
    return {"system_prompt": system_prompt, "user_prompt": user_prompt}


def run_najia_turn(
    question: str,
    yao_values: Optional[List[int]] = None,
    now: dt.datetime | None = None,
    event_sink: EventSink | None = None,
    stream: bool = False,
    history_rounds: Optional[List[Dict[str, str]]] = None,
    model: str | None = None,
    node_model_overrides: Dict[str, str] | None = None,
    paraphrase: bool = False,
) -> Dict[str, Any]:
    """Execute one Najia/Liuyao turn.

    When ``paraphrase=True`` the orchestrator runs the original two-stage
    flow: a technical analysis call, then a plain-language rewrite. The final
    response combines both segments under labelled section headings.
    """
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
    technical_text = response_output.get("content") if isinstance(response_output, dict) else ""
    if not technical_text:
        technical_text = najia_result["raw_text"]

    paraphrase_text = ""
    if paraphrase and technical_text:
        paraphrase_prompt = _build_paraphrase_prompt(technical_text)
        emit_event(
            event_sink,
            {
                "type": "llm_prompt",
                "node": "NAJIA_PARAPHRASE",
                "system_prompt": paraphrase_prompt["system_prompt"],
                "user_prompt": paraphrase_prompt["user_prompt"],
            },
        )
        emit_event(event_sink, {"type": "tool_call", "tool": "llm_report_tool", "node": "NAJIA_PARAPHRASE"})
        paraphrase_output = llm_report_tool(
            paraphrase_prompt["system_prompt"],
            paraphrase_prompt["user_prompt"],
            model=model or default_model(),
            node="NAJIA_PARAPHRASE",
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
        emit_event(event_sink, {"type": "tool_result", "tool": "llm_report_tool", "node": "NAJIA_PARAPHRASE"})
        paraphrase_text = paraphrase_output.get("content") if isinstance(paraphrase_output, dict) else ""

    if paraphrase and paraphrase_text:
        response_text = (
            f"## 占卜结果:\n\n{najia_result['raw_text']}\n\n"
            f"## 分析解读:\n{technical_text}\n\n"
            f"## 通俗解释:\n{paraphrase_text}"
        )
    else:
        response_text = technical_text

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
