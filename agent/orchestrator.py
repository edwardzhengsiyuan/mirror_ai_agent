"""Main orchestrator for a single turn."""

from __future__ import annotations

import datetime as dt
from typing import Any, Dict, List, Optional

from .deps import COMMON_PREREQS
from .events import EventSink, emit_event
from .execution import ensure_node, run_nodes_parallel, run_tool, run_response
from .models import DEFAULT_MODEL
from .response import compose_response


def run_turn(
    profile: Dict[str, Any],
    question: str,
    now: dt.datetime | None = None,
    event_sink: EventSink | None = None,
    stream: bool = False,
    history_rounds: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """Execute a single conversation turn.

    Flow:
    1. PAIPAN node (persistent, cached in profile)
    2. PLANNER tool (conversation-level, not cached)
    3. Persistent nodes DAG (cached in profile)
    4. TIME_CONTEXT tool (conversation-level, not cached)
    5. Response generation (conversation-level, not cached)
    """
    now = now or dt.datetime.now()
    tool_invocations: List[Dict[str, Any]] = []

    # 1. Execute PAIPAN node (persistent, cached in profile)
    paipan_inputs = {
        "birth": profile.get("birth", {}),
        "gender": profile.get("gender", "male"),
        "birth_time_unknown": profile.get("birth_time_unknown", False),
    }
    paipan_output = ensure_node(profile, "PAIPAN", paipan_inputs, event_sink=event_sink, stream=stream)
    dayun_list = paipan_output.get("dayun_list", []) if isinstance(paipan_output, dict) else []

    # 2. Execute PLANNER tool (conversation-level, not cached)
    planner_inputs = {
        "question": question,
        "now": now,
        "dayun_list": dayun_list,
        "history_rounds": history_rounds or [],
    }
    plan_result, planner_invocation_id, planner_duration_ms, planner_llm_prompt = run_tool(
        "PLANNER",
        planner_inputs,
        event_sink=event_sink,
        stream=stream,
    )
    aspects = plan_result.get("aspects", [])

    # Emit tool_invocation event for PLANNER
    planner_invocation = {
        "tool": "PLANNER",
        "invocation_id": planner_invocation_id,
        "input": {
            "question": question,
            "now": now.isoformat() if now else None,
            "dayun_list": dayun_list,
            "history_rounds": history_rounds or [],
        },
        "output": plan_result,
        "duration_ms": planner_duration_ms,
    }
    if planner_llm_prompt:
        planner_invocation["llm_prompt"] = planner_llm_prompt
    tool_invocations.append(planner_invocation)
    emit_event(event_sink, {"type": "tool_invocation", **planner_invocation})

    # Also emit plan event for backward compatibility
    emit_event(event_sink, {"type": "plan", "plan": plan_result, "question": question})

    # 3. Execute persistent nodes DAG (cached in profile)
    nodes = set(COMMON_PREREQS)
    nodes.update(aspects)
    prompt_config = profile.get("prompt_config", "lingyun_cat")
    llm_model = profile.get("llm_model", DEFAULT_MODEL)
    outputs = run_nodes_parallel(
        profile,
        list(nodes),
        {
            "PAIPAN": paipan_inputs,
            "OVERALL": {"prompt_config": prompt_config, "model": llm_model},
            "SHISHEN": {"prompt_config": prompt_config, "model": llm_model},
            "GEJU_ROUTER": {"prompt_config": prompt_config, "model": llm_model},
            "GEJU_ANALYSIS": {"prompt_config": prompt_config, "model": llm_model},
            "GEJU_LEVEL": {"prompt_config": prompt_config, "model": llm_model},
            "WUXING_PREFS": {"prompt_config": prompt_config, "model": llm_model},
            "CAREER": {"prompt_config": prompt_config, "model": llm_model},
            "RELATIONSHIP": {"prompt_config": prompt_config, "model": llm_model},
            "HEALTH": {"prompt_config": prompt_config, "model": llm_model},
            "GUIREN": {"prompt_config": prompt_config, "model": llm_model},
            "LIUQIN": {"prompt_config": prompt_config, "model": llm_model},
            "XINGGE": {"prompt_config": prompt_config, "model": llm_model},
            "OTHER": {"prompt_config": prompt_config, "model": llm_model},
        },
        event_sink=event_sink,
        stream=stream,
        skip_nodes={"PAIPAN"},
        precomputed_outputs={"PAIPAN": paipan_output},
    )
    outputs["PAIPAN"] = paipan_output

    # Check for critical failures - return error response instead of generating with bad data
    failed_nodes = [
        n for n, o in outputs.items()
        if isinstance(o, dict) and o.get("error") and not o.get("skipped")
    ]
    skipped_nodes = [
        n for n, o in outputs.items()
        if isinstance(o, dict) and o.get("skipped")
    ]
    if failed_nodes:
        error_response = f"无法完成分析，以下节点执行失败：{', '.join(sorted(failed_nodes))}。请稍后重试。"
        emit_event(
            event_sink,
            {
                "type": "workflow_error",
                "failed_nodes": failed_nodes,
                "skipped_nodes": skipped_nodes,
                "message": error_response,
            },
        )
        return {
            "plan": plan_result,
            "outputs": outputs,
            "time_context": None,
            "response": error_response,
            "tool_invocations": tool_invocations,
            "error": True,
            "failed_nodes": failed_nodes,
            "skipped_nodes": skipped_nodes,
        }

    # 4. Execute TIME_CONTEXT tool if needed (conversation-level, not cached)
    time_context = None
    plan_times = plan_result.get("times", [])
    years = [t.get("year") for t in plan_times if t.get("need_tool") and t.get("year")]
    if years:
        tc_inputs = {
            "requests": [{"year": y} for y in years],
            "birth": profile.get("birth", {}),
            "gender": profile.get("gender", "male"),
            "birth_time_unknown": profile.get("birth_time_unknown", False),
        }
        time_context, tc_invocation_id, tc_duration_ms, tc_llm_prompt = run_tool(
            "TIME_CONTEXT",
            tc_inputs,
            event_sink=event_sink,
            stream=stream,
        )

        # Emit tool_invocation event for TIME_CONTEXT
        tc_invocation = {
            "tool": "TIME_CONTEXT",
            "invocation_id": tc_invocation_id,
            "input": tc_inputs,
            "output": time_context,
            "duration_ms": tc_duration_ms,
        }
        if tc_llm_prompt:
            tc_invocation["llm_prompt"] = tc_llm_prompt
        tool_invocations.append(tc_invocation)
        emit_event(event_sink, {"type": "tool_invocation", **tc_invocation})

        # Also emit time_context event for backward compatibility
        emit_event(event_sink, {"type": "time_context", "value": time_context})

    # 5. Generate Response (conversation-level, not cached)
    response_inputs = {
        "prompt_config": prompt_config,
        "model": llm_model,
        "question": question,
        "history_rounds": history_rounds or [],
        "time_context": time_context,
    }
    response_output, response_duration_ms, response_llm_prompt = run_response(
        profile,
        response_inputs,
        event_sink=event_sink,
        stream=stream,
    )

    response_text = response_output.get("content") if isinstance(response_output, dict) else None
    if not response_text:
        response_text = compose_response(question, plan_result, outputs, time_context)

    # Build input summary for response event
    input_summary = {
        "question": question,
        "aspects": aspects,
        "time_context_summary": _summarize_time_context(time_context) if time_context else None,
        "node_summaries": _summarize_nodes(outputs, aspects),
    }

    # Emit response event
    emit_event(
        event_sink,
        {
            "type": "response",
            "text": response_text,
            "input_summary": input_summary,
            "llm_prompt": response_llm_prompt,
            "duration_ms": response_duration_ms,
        },
    )

    return {
        "plan": plan_result,
        "outputs": outputs,
        "time_context": time_context,
        "response": response_text,
        "tool_invocations": tool_invocations,
    }


def _summarize_time_context(time_context: Dict[str, Any]) -> str:
    """Create a brief summary of time context for UI display."""
    year_data = time_context.get("year_data", [])
    if not year_data:
        return ""
    years = [str(yd.get("year", "")) for yd in year_data]
    return f"{', '.join(years)}年"


def _summarize_nodes(outputs: Dict[str, Any], aspects: List[str]) -> Dict[str, str]:
    """Create brief summaries of node outputs for UI display."""
    summaries = {}
    # Include COMMON_PREREQS summaries
    for node in COMMON_PREREQS:
        content = outputs.get(node, {})
        if isinstance(content, dict):
            content = content.get("content", "")
        if content:
            # Take first 100 chars as summary
            summaries[node] = content[:100] + "..." if len(content) > 100 else content
    # Include aspect summaries
    for aspect in aspects:
        content = outputs.get(aspect, {})
        if isinstance(content, dict):
            content = content.get("content", "")
        if content:
            summaries[aspect] = content[:100] + "..." if len(content) > 100 else content
    return summaries
