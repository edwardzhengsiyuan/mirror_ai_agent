"""Planner tool for validating LLM outputs."""

from __future__ import annotations

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


def _normalize_aspects(aspects: Optional[List[str]]) -> List[str]:
    items = []
    for item in aspects or []:
        if not isinstance(item, str):
            continue
        key = item.strip().upper()
        if key in ALLOWED_ASPECTS and key not in items:
            items.append(key)
    return items or ["OTHER"]


def _normalize_time_item(time: Optional[Dict]) -> Dict:
    time = time or {}
    ref_text = time.get("ref_text")
    if not isinstance(ref_text, str):
        ref_text = None
    year = time.get("year")
    if not isinstance(year, int):
        year = None
    need_tool = time.get("need_tool")
    has_time_hint = ref_text or year
    if not isinstance(need_tool, bool):
        need_tool = bool(has_time_hint)
    elif not need_tool and has_time_hint:
        need_tool = True
    return {
        "need_tool": need_tool,
        "ref_text": ref_text,
        "year": year,
    }


def _normalize_times(time: Optional[Dict], times: Optional[List[Dict]]) -> List[Dict]:
    normalized: List[Dict] = []
    seen = set()

    def push(item: Dict) -> None:
        year = item.get("year")
        if year in seen:
            return
        seen.add(year)
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
