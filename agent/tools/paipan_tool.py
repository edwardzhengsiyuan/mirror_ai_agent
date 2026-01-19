"""Paipan tool wrapper."""

from __future__ import annotations

from typing import Any, Dict

from .time_context_tool import build_time_index


def _require_int(payload: Dict[str, Any], field: str) -> int:
    value = payload.get(field)
    if value is None:
        raise ValueError(f"missing birth.{field}")
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid birth.{field}={value!r}") from exc


def _optional_int(payload: Dict[str, Any], field: str, default: int = 0) -> int:
    value = payload.get(field, default)
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid birth.{field}={value!r}") from exc


def _check_range(value: int, field: str, min_value: int, max_value: int) -> None:
    if value < min_value or value > max_value:
        raise ValueError(f"invalid birth.{field}={value} (expected {min_value}-{max_value})")


def paipan_tool(inputs: Dict[str, Any]) -> Dict[str, Any]:
    """Run paipan and return structured outputs."""
    from lunar_python import Solar
    from bazi.main import BaziChartAnalyseFrame

    birth = inputs.get("birth", {})
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
    gender = inputs.get("gender", "male")
    time_unknown = bool(inputs.get("birth_time_unknown", False))

    lunar = Solar.fromYmdHms(year, month, day, hour, minute, second).getLunar()
    frame = BaziChartAnalyseFrame(lunar, gender, without_time=time_unknown)
    paipan_results, liupan_results, guji_results = frame.get_analysis_summary()
    time_index = build_time_index(frame.res, paipan_results, liupan_results)

    return {
        "paipan_results": paipan_results,
        "liupan_results": liupan_results,
        "guji_results": guji_results,
        "paipan_output": frame.res,
        "time_index": time_index,
    }
