"""Simplified time context tool - fetches year data directly."""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def time_context_tool(
    requests: List[Dict[str, Any]],
    birth: Dict[str, Any],
    gender: str,
    birth_time_unknown: bool = False,
) -> Dict[str, Any]:
    """Fetch year data by calling find_yun_liu_nian_liuyue for each requested year.

    Args:
        requests: List of {year: int} dicts specifying years to fetch
        birth: Birth info dict with year, month, day, hour, minute, second
        gender: "male" or "female"
        birth_time_unknown: Whether birth time is unknown

    Returns:
        Dict with "year_data" list: [{"year": int, "data": str}, ...]
    """
    year_data_results: List[Dict[str, Any]] = []

    if not birth or not gender:
        return {"year_data": year_data_results}

    try:
        from lunar_python import Solar
        from bazi.main import BaziChartAnalyseFrame

        year = birth.get("year")
        month = birth.get("month")
        day = birth.get("day")
        hour = birth.get("hour", 0)
        minute = birth.get("minute", 0)
        second = birth.get("second", 0)

        if not (year and month and day):
            return {"year_data": year_data_results}

        lunar = Solar.fromYmdHms(year, month, day, hour, minute, second).getLunar()
        frame = BaziChartAnalyseFrame(lunar, gender, without_time=birth_time_unknown)

        # Collect years from requests and fetch data
        years_to_fetch = set()
        for req in requests or []:
            req_year = req.get("year")
            if isinstance(req_year, int):
                years_to_fetch.add(req_year)

        for year_val in sorted(years_to_fetch):
            year_text = frame.find_yun_liu_nian_liuyue(year_val)
            if year_text:
                year_data_results.append({"year": year_val, "data": year_text})

    except Exception:
        # If we can't fetch year data, return empty list
        pass

    return {"year_data": year_data_results}
