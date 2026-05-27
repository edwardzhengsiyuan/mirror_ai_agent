"""HePan compatibility tool wrapper.

Returns the full per-person paipan/liupan/guji texts so the orchestrator can
feed them into the LLM (matching the original ``bazi_langgraph_integrate``
implementation), in addition to the structured compatibility scores used by the
frontend.
"""

from __future__ import annotations

import datetime as dt
from typing import Any, Dict

from .paipan_tool import _check_range, _optional_int, _require_int


def _normalize_person(person: Dict[str, Any], label: str) -> Dict[str, Any]:
    birth = person.get("birth", {})
    if not isinstance(birth, dict):
        raise ValueError(f"{label}.birth required")

    year = _require_int(birth, "year")
    month = _require_int(birth, "month")
    day = _require_int(birth, "day")
    hour = _optional_int(birth, "hour", 0)
    minute = _optional_int(birth, "minute", 0)
    second = _optional_int(birth, "second", 0)
    _check_range(month, "month", 1, 12)
    _check_range(day, "day", 1, 31)
    _check_range(hour, "hour", 0, 23)
    _check_range(minute, "minute", 0, 59)
    _check_range(second, "second", 0, 59)

    gender = person.get("gender", "male")
    if gender not in ("male", "female"):
        raise ValueError(f"{label}.gender invalid")

    return {
        "name": person.get("name") or label,
        "gender": gender,
        "birth": {
            "year": year,
            "month": month,
            "day": day,
            "hour": hour,
            "minute": minute,
            "second": second,
        },
        "birth_time_unknown": bool(person.get("birth_time_unknown", False)),
    }


def _build_frame(person: Dict[str, Any]):
    """Build a full BaziChartAnalyseFrame.

    The original Langgraph hepan implementation feeds the full
    ``(paipan, liupan, guji)`` text triple for both individuals into the LLM,
    so we need ``only_compatibility=False`` (to populate ``log_helper.ans``,
    ``self.liupan`` and ``self.guji``) and ``compute_dayun=True``.
    """
    from lunar_python import Solar
    from bazi.main import BaziChartAnalyseFrame

    birth = person["birth"]
    lunar = Solar.fromYmdHms(
        birth["year"],
        birth["month"],
        birth["day"],
        birth["hour"],
        birth["minute"],
        birth["second"],
    ).getLunar()
    return BaziChartAnalyseFrame(
        lunar,
        person["gender"],
        without_time=person["birth_time_unknown"],
        enable_terminal_output=False,
        compute_dayun=True,
        only_compatibility=False,
    )


def hepan_tool(inputs: Dict[str, Any]) -> Dict[str, Any]:
    """Run two-chart compatibility analysis and return structured outputs."""
    person_a = inputs.get("person_a")
    person_b = inputs.get("person_b")
    if not isinstance(person_a, dict):
        raise ValueError("person_a required")
    if not isinstance(person_b, dict):
        raise ValueError("person_b required")

    normalized_a = _normalize_person(person_a, "person_a")
    normalized_b = _normalize_person(person_b, "person_b")

    frame_a = _build_frame(normalized_a)
    frame_b = _build_frame(normalized_b)

    paipan_a, liupan_a, guji_a = frame_a.get_analysis_summary()
    paipan_b, liupan_b, guji_b = frame_b.get_analysis_summary()

    compatibility = frame_a.get_compatibility_analysis(frame_b.bazi_chart)

    person_a_out = {
        **normalized_a,
        "paipan_text": paipan_a,
        "liupan_text": liupan_a,
        "guji_text": guji_a,
    }
    person_b_out = {
        **normalized_b,
        "paipan_text": paipan_b,
        "liupan_text": liupan_b,
        "guji_text": guji_b,
    }

    return {
        "type": "hepan",
        "computed_at": dt.datetime.now(dt.UTC).isoformat().replace("+00:00", "Z"),
        "person_a": person_a_out,
        "person_b": person_b_out,
        "compatibility": compatibility,
    }
