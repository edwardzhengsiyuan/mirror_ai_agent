"""Main orchestrator for a single turn."""

from __future__ import annotations

import datetime as dt
from typing import Any, Dict

from .deps import COMMON_PREREQS
from .execution import ensure_node, run_nodes_parallel
from .planning import plan
from .response import compose_response


def run_turn(profile: Dict[str, Any], question: str, now: dt.datetime | None = None) -> Dict[str, Any]:
    now = now or dt.datetime.now()
    plan_result = plan(question, now=now)
    aspects = plan_result["aspects"]

    nodes = set(COMMON_PREREQS)
    nodes.update(aspects)
    nodes.add("PAIPAN")

    paipan_inputs = {
        "birth": profile.get("birth", {}),
        "gender": profile.get("gender", "male"),
        "birth_time_unknown": profile.get("birth_time_unknown", False),
    }
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
    )

    time_context = None
    if plan_result["time"]["need_tool"]:
        time_context = ensure_node(
            profile,
            "TIME_CONTEXT",
            {
                "paipan_output": outputs["PAIPAN"].get("paipan_output", {}),
                "ref_text": plan_result["time"]["ref_text"],
                "now": now.isoformat(),
            },
        )

    response_text = compose_response(question, plan_result, outputs, time_context)
    return {
        "plan": plan_result,
        "outputs": outputs,
        "time_context": time_context,
        "response": response_text,
    }
