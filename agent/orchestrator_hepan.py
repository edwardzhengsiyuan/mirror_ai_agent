"""Orchestrator for BaZi HePan compatibility turns."""

from __future__ import annotations

import datetime as dt
import json
import time
from typing import Any, Dict, List, Optional

from .events import EventSink, emit_event
from .models import DEFAULT_MODEL
from .tools.hepan_tool import hepan_tool
from .tools.llm_tool import llm_report_tool

HEPAN_SYSTEM_PROMPT = (
    "你是一位擅长八字合盘的咨询师。请基于结构化合盘结果，"
    "用克制、清晰、便于客户理解的语言分析两个人的关系匹配度。"
)

HEPAN_USER_PROMPT_TEMPLATE = """请根据下面的八字合盘结构化结果，回答用户问题。

要求：
1. 先给出整体判断和分数解释。
2. 再分别说明五行互补/相似、生肖关系、互看神煞对关系的影响。
3. 结论要包含相处建议，避免绝对化断语。
4. 如果用户问题很具体，优先回应具体问题。

用户问题：
{question}

近期对话：
{history}

合盘结果：
{hepan_json}
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


def build_hepan_prompt(
    question: str,
    hepan_result: Dict[str, Any],
    history_rounds: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, str]:
    user_prompt = HEPAN_USER_PROMPT_TEMPLATE.format(
        question=question,
        history=_format_history(history_rounds),
        hepan_json=json.dumps(hepan_result, ensure_ascii=False, indent=2),
    )
    return {"system_prompt": HEPAN_SYSTEM_PROMPT, "user_prompt": user_prompt}


def run_hepan_turn(
    question: str,
    person_a: Dict[str, Any],
    person_b: Dict[str, Any],
    now: dt.datetime | None = None,
    event_sink: EventSink | None = None,
    stream: bool = False,
    history_rounds: Optional[List[Dict[str, str]]] = None,
    model: str | None = None,
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
        model=model or DEFAULT_MODEL,
        node="HEPAN_RESPONSE",
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
