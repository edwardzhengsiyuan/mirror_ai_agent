"""Paipan tool wrapper."""

from __future__ import annotations

from typing import Any, Dict

from lunar_python import Solar

from bazi.main import BaziChartAnalyseFrame


def paipan_tool(inputs: Dict[str, Any]) -> Dict[str, Any]:
    """Run paipan and return structured outputs."""
    birth = inputs.get("birth", {})
    year = int(birth.get("year"))
    month = int(birth.get("month"))
    day = int(birth.get("day"))
    hour = int(birth.get("hour", 0))
    minute = int(birth.get("minute", 0))
    second = int(birth.get("second", 0))
    gender = inputs.get("gender", "male")
    time_unknown = bool(inputs.get("birth_time_unknown", False))

    lunar = Solar.fromYmdHms(year, month, day, hour, minute, second).getLunar()
    frame = BaziChartAnalyseFrame(lunar, gender, without_time=time_unknown)
    paipan_results, liupan_results, guji_results = frame.get_analysis_summary()

    return {
        "paipan_results": paipan_results,
        "liupan_results": liupan_results,
        "guji_results": guji_results,
        "paipan_output": frame.res,
    }
