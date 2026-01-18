"""Planner tool for validating LLM outputs."""

from __future__ import annotations

import re
from typing import Dict, List, Optional

ALLOWED_ASPECTS = {
    "CAREER",
    "RELATIONSHIP",
    "HEALTH",
    "GUIREN",
    "LIUQIN",
    "XINGGE",
    "OTHER",
}

DAYUN_PATTERN = re.compile(r"[甲乙丙丁戊己庚辛壬癸][子丑寅卯辰巳午未申酉戌亥]")


def _normalize_aspects(aspects: Optional[List[str]]) -> List[str]:
    items = []
    for item in aspects or []:
        if not isinstance(item, str):
            continue
        key = item.strip().upper()
        if key in ALLOWED_ASPECTS and key not in items:
            items.append(key)
    return items or ["OTHER"]


def _normalize_dayun(dayun: str) -> Optional[str]:
    text = (dayun or "").strip()
    if not text:
        return None
    match = DAYUN_PATTERN.search(text)
    if match:
        return match.group(0)
    cleaned = re.sub(r"[0-9\\-–—\\s]+", "", text)
    return cleaned or None


def _normalize_time_item(time: Optional[Dict]) -> Dict:
    time = time or {}
    granularity = time.get("granularity")
    if granularity not in ("year", "month", "dayun", None):
        granularity = None
    ref_text = time.get("ref_text")
    if not isinstance(ref_text, str):
        ref_text = None
    year = time.get("year")
    if not isinstance(year, int):
        year = None
    month = time.get("month")
    if not isinstance(month, int):
        month = None
    dayun = time.get("dayun")
    if not isinstance(dayun, str):
        dayun = None
    else:
        dayun = _normalize_dayun(dayun)
    if granularity is None:
        if month:
            granularity = "month"
        elif dayun and not year:
            granularity = "dayun"
        elif year:
            granularity = "year"
    need_tool = time.get("need_tool")
    has_time_hint = any([ref_text, year, month, dayun])
    if not isinstance(need_tool, bool):
        need_tool = has_time_hint
    elif not need_tool and has_time_hint:
        need_tool = True
    return {
        "need_tool": need_tool,
        "granularity": granularity,
        "ref_text": ref_text,
        "year": year,
        "month": month,
        "dayun": dayun,
    }


def _normalize_times(time: Optional[Dict], times: Optional[List[Dict]]) -> List[Dict]:
    normalized: List[Dict] = []
    seen = set()

    def push(item: Dict) -> None:
        key = (item.get("granularity"), item.get("year"), item.get("month"), item.get("dayun"))
        if key in seen:
            return
        seen.add(key)
        if item.get("need_tool"):
            normalized.append(item)

    if isinstance(times, list):
        for entry in times:
            if isinstance(entry, dict):
                push(_normalize_time_item(entry))

    if isinstance(time, dict):
        push(_normalize_time_item(time))

    return normalized


def planning_tool(aspects: Optional[List[str]], time: Optional[Dict], times: Optional[List[Dict]] = None) -> Dict:
    normalized_times = _normalize_times(time, times)
    primary = normalized_times[0] if normalized_times else _normalize_time_item(time)
    return {
        "aspects": _normalize_aspects(aspects),
        "time": primary,
        "times": normalized_times,
    }
