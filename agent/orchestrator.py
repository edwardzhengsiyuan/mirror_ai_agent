"""Main orchestrator for a single turn."""

from __future__ import annotations

import datetime as dt
from typing import Any, Dict, List, Optional

from .deps import COMMON_PREREQS
from .events import EventSink, emit_event
from .execution import ensure_node, run_nodes_parallel
from .planning import plan
from .tools.time_context_tool import build_time_index
from .response import compose_response


def _coerce_plan_times(plan_result: Dict[str, Any]) -> List[Dict[str, Any]]:
    times = plan_result.get("times")
    if isinstance(times, list):
        return times
    time = plan_result.get("time")
    if isinstance(time, dict) and time.get("need_tool"):
        return [time]
    return []


def _maybe_enrich_plan_times(plan_result: Dict[str, Any], time_contexts: List[Optional[Dict[str, Any]]]) -> bool:
    """Fill missing plan time fields (e.g., dayun) from resolved time_context list."""
    times = _coerce_plan_times(plan_result)
    updated = False
    for ctx in time_contexts:
        if not ctx:
            continue
        idx = ctx.get("index")
        if not isinstance(idx, int) or idx >= len(times):
            continue
        time = times[idx]
        if isinstance(ctx.get("dayun"), dict):
            name = ctx["dayun"].get("name")
            if isinstance(name, str) and name and time.get("dayun") != name:
                time["dayun"] = name
                updated = True
        if time.get("year") is None and isinstance(ctx.get("year"), dict):
            year = ctx["year"].get("year")
            if isinstance(year, int):
                time["year"] = year
                updated = True
        if time.get("month") is None and isinstance(ctx.get("month"), dict):
            month = ctx["month"].get("month")
            if isinstance(month, int):
                time["month"] = month
                updated = True
    if times:
        plan_result["times"] = times
        plan_result["time"] = times[0]
    return updated


def run_turn(
    profile: Dict[str, Any],
    question: str,
    now: dt.datetime | None = None,
    event_sink: EventSink | None = None,
    stream: bool = False,
) -> Dict[str, Any]:
    now = now or dt.datetime.now()
    paipan_inputs = {
        "birth": profile.get("birth", {}),
        "gender": profile.get("gender", "male"),
        "birth_time_unknown": profile.get("birth_time_unknown", False),
    }
    paipan_output = ensure_node(profile, "PAIPAN", paipan_inputs, event_sink=event_sink, stream=stream)
    time_index = paipan_output.get("time_index") if isinstance(paipan_output, dict) else None
    if not time_index:
        time_index = build_time_index(
            paipan_output.get("paipan_output", {}) if isinstance(paipan_output, dict) else {},
            paipan_output.get("paipan_results", "") if isinstance(paipan_output, dict) else "",
            paipan_output.get("liupan_results", "") if isinstance(paipan_output, dict) else "",
        )
        if isinstance(paipan_output, dict):
            paipan_output["time_index"] = time_index

    emit_event(event_sink, {"type": "node_start", "node": "PLANNER"})
    plan_result = plan(question, now=now, time_index=time_index, event_sink=event_sink, stream=stream)
    emit_event(event_sink, {"type": "node_end", "node": "PLANNER", "output": plan_result})
    aspects = plan_result["aspects"]
    emit_event(event_sink, {"type": "plan", "plan": plan_result, "question": question})

    nodes = set(COMMON_PREREQS)
    nodes.update(aspects)
    prompt_config = profile.get("prompt_config", "lingyun_cat")
    outputs = run_nodes_parallel(
        profile,
        list(nodes),
        {
            "PAIPAN": paipan_inputs,
            "OVERALL": {"prompt_config": prompt_config, "model": "reasoning"},
            "SHISHEN": {"prompt_config": prompt_config, "model": "reasoning"},
            "GEJU": {"prompt_config": prompt_config, "model": "reasoning"},
            "WUXING_PREFS": {"prompt_config": prompt_config, "model": "reasoning"},
            "CAREER": {"prompt_config": prompt_config},
            "RELATIONSHIP": {"prompt_config": prompt_config},
            "HEALTH": {"prompt_config": prompt_config},
            "GUIREN": {"prompt_config": prompt_config},
            "LIUQIN": {"prompt_config": prompt_config},
            "XINGGE": {"prompt_config": prompt_config},
            "OTHER": {"prompt_config": prompt_config},
        },
        event_sink=event_sink,
        stream=stream,
        skip_nodes={"PAIPAN"},
        precomputed_outputs={"PAIPAN": paipan_output},
    )
    outputs["PAIPAN"] = paipan_output

    time_context = None
    plan_times = _coerce_plan_times(plan_result)
    if plan_times:
        requests = []
        for idx, entry in enumerate(plan_times):
            if not entry.get("need_tool"):
                continue
            requests.append(
                {
                    "index": idx,
                    "ref_text": entry.get("ref_text"),
                    "target_year": entry.get("year"),
                    "target_month": entry.get("month"),
                    "target_dayun": entry.get("dayun"),
                }
            )
        if requests:
            time_index = time_index or {}
            time_context = ensure_node(
                profile,
                "TIME_CONTEXT",
                {
                    "requests": requests,
                    "now": now.isoformat(),
                    "dayun_list": time_index.get("dayun_list", []),
                    "liunian_list": time_index.get("liunian_list", []),
                    "liuyue_by_year": time_index.get("liuyue_by_year", {}),
                },
                event_sink=event_sink,
                stream=stream,
            )
            emit_event(event_sink, {"type": "time_context", "value": time_context})
            if isinstance(time_context, list) and _maybe_enrich_plan_times(plan_result, time_context):
                emit_event(event_sink, {"type": "plan_update", "plan": plan_result})

    final_output = ensure_node(
        profile,
        "FINAL",
        {"prompt_config": prompt_config, "model": "reasoning", "question": question},
        event_sink=event_sink,
        stream=stream,
    )
    outputs["FINAL"] = final_output
    response_text = final_output.get("content") if isinstance(final_output, dict) else None
    if not response_text:
        response_text = compose_response(question, plan_result, outputs, time_context)
    return {
        "plan": plan_result,
        "outputs": outputs,
        "time_context": time_context,
        "response": response_text,
    }
