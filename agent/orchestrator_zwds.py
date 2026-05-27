"""Orchestrator for Ziwei Doushu (紫微斗数) divination turns.

Mirrors the original ``bazi_langgraph_integrate/src/agents/zwds_agent.py``
design: load ``zwds_prompt.md`` (and optionally ``zwds_star_gong.md``) as the
system prompt and feed the chart text + user question as the user prompt.

The original repo's system prompt always concatenated both ``prompt.md``
(≈7 KB) **and** ``star_gong.md`` (≈973 KB of star/palace lookup tables).
That balloon is opt-in here via the ``include_star_gong`` parameter (or the
``LLM_ZWDS_INCLUDE_STAR_GONG=1`` env var) — the default is the lean
prompt.md-only system prompt, which already lets the LLM produce competent
ZiWei readings using its built-in domain knowledge while keeping per-call
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
from .tools.zwds_tool import zwds_tool

PROMPTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "prompts", "templates")

ZWDS_BASE_ROLE = (
    "你是一位资深的紫微斗数咨询师，擅长使用三合、飞星四化等多个流派分析紫微斗数命盘。"
)

ZWDS_SYSTEM_PROMPT_FALLBACK = (
    ZWDS_BASE_ROLE
    + "\n\n请基于本命盘、大限、流年的星曜组合、宫位关系与四化飞星进行专业分析。"
)

ZWDS_TRAILER = (
    "请根据提供的紫微斗数排盘信息，进行专业的分析解读。分析时要全面深入，"
    "结合星曜组合、四化飞星、宫位关系等多个角度。"
)


@lru_cache(maxsize=4)
def _load_template(name: str) -> str:
    path = os.path.join(PROMPTS_DIR, name)
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return ""


def _env_truthy(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in ("1", "true", "yes")


def _build_system_prompt(include_star_gong: bool) -> str:
    rules = _load_template("zwds_prompt.md")
    if not rules:
        return ZWDS_SYSTEM_PROMPT_FALLBACK
    parts: List[str] = [ZWDS_BASE_ROLE, "", rules]
    if include_star_gong:
        star_gong = _load_template("zwds_star_gong.md")
        if star_gong:
            parts.extend(["", star_gong])
    parts.extend(["", ZWDS_TRAILER])
    return "\n".join(parts)


def _format_history(history_rounds: Optional[List[Dict[str, str]]]) -> str:
    if not history_rounds:
        return "无"
    lines: List[str] = []
    for idx, pair in enumerate(history_rounds, start=1):
        lines.append(f"Round {idx}")
        lines.append(f"User: {pair.get('user', '')}")
        lines.append(f"Assistant: {pair.get('assistant', '')}")
    return "\n".join(lines)


def build_zwds_prompt(
    question: str,
    zwds_result: Dict[str, Any],
    history_rounds: Optional[List[Dict[str, str]]] = None,
    include_star_gong: bool = False,
) -> Dict[str, str]:
    """Build the (system, user) prompt pair for the ZiWei LLM call."""
    system_prompt = _build_system_prompt(include_star_gong)

    birth = zwds_result.get("birth") or {}
    gender_cn = "男" if zwds_result.get("gender") == "male" else "女"
    birth_str = (
        f"{birth.get('year', '?')}年{birth.get('month', '?')}月{birth.get('day', '?')}日 "
        f"{birth.get('hour', 0):02d}:{birth.get('minute', 0):02d}"
    )
    raw_text = zwds_result.get("raw_text", "")
    target_years = zwds_result.get("target_years") or []

    parts: List[str] = [
        "# 紫微斗数排盘信息",
        "",
        "## 基本信息",
        f"- 出生时间：{birth_str}",
        f"- 性别：{gender_cn}",
    ]
    if target_years:
        parts.append(f"- 流年聚焦：{', '.join(str(y) for y in target_years)}")
    parts.extend(["", raw_text, ""])

    parts.extend(
        [
            "请根据以上紫微斗数排盘信息，从以下角度进行分析：",
            "1. 本命盘特点分析",
            "2. 大限运势分析",
            "3. 性格特征分析",
            "4. 事业发展方向",
            "5. 感情婚姻分析",
            "6. 财运健康分析",
            "7. 流年注意事项",
        ]
    )
    if question and question.strip():
        parts.extend(
            [
                "",
                "用户的具体问题（请优先回应，并自然融入紫微分析中）：",
                question.strip(),
            ]
        )
    if history_rounds:
        parts.extend(["", "近期对话：", _format_history(history_rounds)])

    user_prompt = "\n".join(parts)
    return {"system_prompt": system_prompt, "user_prompt": user_prompt}


def run_zwds_turn(
    question: str,
    birth: Dict[str, Any],
    gender: str = "male",
    target_years: Optional[List[int]] = None,
    now: dt.datetime | None = None,
    event_sink: EventSink | None = None,
    stream: bool = False,
    history_rounds: Optional[List[Dict[str, str]]] = None,
    model: str | None = None,
    node_model_overrides: Dict[str, str] | None = None,
    include_star_gong: Optional[bool] = None,
) -> Dict[str, Any]:
    """Execute one ZiWei Doushu turn.

    Args:
        question: user's question (free-form).
        birth: dict with year/month/day/hour[/minute/second].
        gender: "male" or "female".
        target_years: list of years to render flow-year analyses; defaults
            to the current civil year (matches the original main.py demo).
        include_star_gong: whether to inject the 973 KB star_gong.md lookup
            into the system prompt. ``None`` means honour the
            ``LLM_ZWDS_INCLUDE_STAR_GONG`` env var (default off).
    """
    now = now or dt.datetime.now()
    if include_star_gong is None:
        include_star_gong = _env_truthy("LLM_ZWDS_INCLUDE_STAR_GONG")

    tool_started = time.perf_counter()
    emit_event(event_sink, {"type": "tool_call", "tool": "zwds_tool", "node": "ZWDS"})
    zwds_result = zwds_tool(
        {
            "birth": birth,
            "gender": gender,
            "target_years": target_years,
        }
    )
    tool_duration_ms = int((time.perf_counter() - tool_started) * 1000)
    emit_event(event_sink, {"type": "tool_result", "tool": "zwds_tool", "node": "ZWDS"})
    emit_event(
        event_sink,
        {
            "type": "tool_invocation",
            "tool": "ZWDS",
            "input": {"birth": birth, "gender": gender, "target_years": target_years},
            "output": zwds_result,
            "duration_ms": tool_duration_ms,
        },
    )

    prompt = build_zwds_prompt(
        question,
        zwds_result,
        history_rounds=history_rounds,
        include_star_gong=include_star_gong,
    )
    emit_event(
        event_sink,
        {
            "type": "llm_prompt",
            "node": "ZWDS_RESPONSE",
            "system_prompt": prompt["system_prompt"],
            "user_prompt": prompt["user_prompt"],
        },
    )

    response_started = time.perf_counter()
    emit_event(event_sink, {"type": "tool_call", "tool": "llm_report_tool", "node": "ZWDS_RESPONSE"})
    response_output = llm_report_tool(
        prompt["system_prompt"],
        prompt["user_prompt"],
        model=model or default_model(),
        node="ZWDS_RESPONSE",
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
    emit_event(event_sink, {"type": "tool_result", "tool": "llm_report_tool", "node": "ZWDS_RESPONSE"})
    response_duration_ms = int((time.perf_counter() - response_started) * 1000)
    response_text = response_output.get("content") if isinstance(response_output, dict) else ""
    if not response_text:
        response_text = zwds_result["raw_text"]

    emit_event(
        event_sink,
        {
            "type": "response",
            "text": response_text,
            "input_summary": {
                "method": "zwds",
                "target_years": zwds_result.get("target_years"),
            },
            "llm_prompt": prompt,
            "duration_ms": response_duration_ms,
        },
    )

    return {
        "method": "zwds",
        "question": question,
        "time": now.isoformat(),
        "zwds": zwds_result,
        "response": response_text,
    }
