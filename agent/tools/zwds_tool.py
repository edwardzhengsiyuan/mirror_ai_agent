"""Ziwei Doushu (紫微斗数) chart tool wrapper.

Builds a ``zwds.basic.Chart`` for the given birth info and renders the
benming (本命盘) plus optional flow-year/major-luck (大限/流年) sections as a
unified text block — matching the original
``bazi_langgraph_integrate/src/zwds/main.py`` usage pattern.
"""

from __future__ import annotations

import datetime as dt
from typing import Any, Dict, List, Optional

from .paipan_tool import _check_range, _optional_int, _require_int


def _normalize_target_years(value: Any, current_year: int) -> List[int]:
    if value is None:
        return [current_year]
    if isinstance(value, int):
        return [value]
    if isinstance(value, list):
        years: List[int] = []
        for idx, item in enumerate(value):
            try:
                years.append(int(item))
            except (TypeError, ValueError) as exc:
                raise ValueError(f"target_years[{idx}] invalid") from exc
        if not years:
            return [current_year]
        return years
    raise ValueError("target_years must be int or list[int]")


def zwds_tool(inputs: Dict[str, Any]) -> Dict[str, Any]:
    """Run a Ziwei Doushu paipan and return structured chart text.

    Args:
        inputs:
            birth: dict with year/month/day/hour/minute/second
            gender: "male" or "female"
            birth_time_unknown: bool (currently passed through but unused
                because zwds.basic.Chart needs a real hour to seat the
                ming/shen palaces)
            target_years: optional list[int] of years to render flow-year
                analyses for; defaults to the current civil year.

    Returns:
        Dict containing benming_info, liunian_infos (list per target year),
        raw_text (concatenated for prompt injection), and metadata.
    """
    from lunar_python import Solar
    from zwds import Chart

    birth = inputs.get("birth", {})
    if not isinstance(birth, dict):
        raise ValueError("birth required")

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
    if gender not in ("male", "female"):
        raise ValueError("gender invalid (expected male|female)")

    target_years = _normalize_target_years(
        inputs.get("target_years"), current_year=dt.datetime.now().year
    )

    lunar = Solar.fromYmdHms(year, month, day, hour, minute, second).getLunar()
    chart = Chart(lunar, gender)
    chart.set_chart_benming()

    benming_info = chart.get_benming_info()

    liunian_infos: List[Dict[str, Any]] = []
    for ty in target_years:
        try:
            text = chart.get_liunian_daxian_info_comb(ty)
        except Exception as exc:  # noqa: BLE001 — engine raises raw on bad year
            text = f"\n\n# {ty}年分析失败：{exc}"
        liunian_infos.append({"year": ty, "text": text})

    raw_text_parts: List[str] = [benming_info]
    raw_text_parts.extend(item["text"] for item in liunian_infos)
    raw_text = "".join(raw_text_parts)

    return {
        "type": "zwds",
        "computed_at": dt.datetime.now(dt.UTC).isoformat().replace("+00:00", "Z"),
        "birth": {
            "year": year,
            "month": month,
            "day": day,
            "hour": hour,
            "minute": minute,
            "second": second,
        },
        "gender": gender,
        "target_years": target_years,
        "benming_info": benming_info,
        "liunian_infos": liunian_infos,
        "raw_text": raw_text,
    }
