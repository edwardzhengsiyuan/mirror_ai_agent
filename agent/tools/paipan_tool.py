"""Paipan tool wrapper."""

from __future__ import annotations

from typing import Any, Dict, List


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


def _extract_dayun_list(yun_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Extract dayun list from frame.res['yun'] structure."""
    # Map pinyin codes to Chinese characters
    gan_map = {
        "GAN:JIA": "甲", "GAN:YI": "乙", "GAN:BING": "丙", "GAN:DING": "丁",
        "GAN:WU": "戊", "GAN:JI": "己", "GAN:GENG": "庚", "GAN:XIN": "辛",
        "GAN:REN": "壬", "GAN:GUI": "癸",
    }
    zhi_map = {
        "ZHI:ZI": "子", "ZHI:CHOU": "丑", "ZHI:YIN": "寅", "ZHI:MAO": "卯",
        "ZHI:CHEN": "辰", "ZHI:SI": "巳", "ZHI:WU": "午", "ZHI:WEI": "未",
        "ZHI:SHEN": "申", "ZHI:YOU": "酉", "ZHI:XU": "戌", "ZHI:HAI": "亥",
    }

    dayun_list = []
    for idx, item in enumerate(yun_data):
        start_year = item.get("year")
        if not isinstance(start_year, int):
            continue

        # Get ganzhi name
        gan = item.get("gan", "")
        zhi = item.get("zhi", "")
        gan_char = gan_map.get(gan, "")
        zhi_char = zhi_map.get(zhi, "")
        name = f"{gan_char}{zhi_char}" if gan_char and zhi_char else "起运前"

        # Calculate end year from next dayun
        next_start = None
        for later in yun_data[idx + 1:]:
            if isinstance(later.get("year"), int):
                next_start = later["year"]
                break
        end_year = next_start - 1 if next_start else start_year + 9

        dayun_list.append({
            "name": name,
            "start_year": start_year,
            "end_year": end_year,
            "step": idx + 1,
            "age_start": item.get("age"),
        })

    return dayun_list


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

    # Extract dayun list directly from structured data
    dayun_list = _extract_dayun_list(frame.res.get("yun", []))

    return {
        "paipan_results": paipan_results,
        "liupan_results": liupan_results,
        "guji_results": guji_results,
        "paipan_output": frame.res,
        "dayun_list": dayun_list,
    }
