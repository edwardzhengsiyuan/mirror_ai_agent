"""Main orchestrator for a single turn."""

from __future__ import annotations

import datetime as dt
from typing import Any, Dict, List, Optional

from .deps import COMMON_PREREQS
from .events import EventSink, emit_event
from .execution import ensure_node, run_nodes_parallel
from .planning import plan
from .response import compose_response


def run_turn(
    profile: Dict[str, Any],
    question: str,
    now: dt.datetime | None = None,
    event_sink: EventSink | None = None,
    stream: bool = False,
    history_rounds: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    now = now or dt.datetime.now()
    paipan_inputs = {
        "birth": profile.get("birth", {}),
        "gender": profile.get("gender", "male"),
        "birth_time_unknown": profile.get("birth_time_unknown", False),
    }
    paipan_output = ensure_node(profile, "PAIPAN", paipan_inputs, event_sink=event_sink, stream=stream)
    dayun_list = paipan_output.get("dayun_list", []) if isinstance(paipan_output, dict) else []

    emit_event(event_sink, {"type": "node_start", "node": "PLANNER"})
    plan_result = plan(question, now=now, dayun_list=dayun_list, event_sink=event_sink, stream=stream)
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

    # Fetch year data if plan includes time requests
    time_context = None
    plan_times = plan_result.get("times", [])
    years = [t.get("year") for t in plan_times if t.get("need_tool") and t.get("year")]
    if years:
        time_context = ensure_node(
            profile,
            "TIME_CONTEXT",
            {
                "requests": [{"year": y} for y in years],
                "birth": profile.get("birth", {}),
                "gender": profile.get("gender", "male"),
                "birth_time_unknown": profile.get("birth_time_unknown", False),
            },
            event_sink=event_sink,
            stream=stream,
        )
        emit_event(event_sink, {"type": "time_context", "value": time_context})

    final_output = ensure_node(
        profile,
        "FINAL",
        {
            "prompt_config": prompt_config,
            "model": "reasoning",
            "question": question,
            "history_rounds": history_rounds or [],
        },
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
