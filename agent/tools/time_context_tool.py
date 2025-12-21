"""Time context extraction from paipan output."""

from __future__ import annotations

import datetime as dt
import re
from typing import Any, Dict, Optional


def _find_year(paipan_output: Dict[str, Any], year: int) -> Optional[Dict[str, Any]]:
    for yun in paipan_output.get("yun", []):
        for nian in yun.get("liunian", []):
            if nian.get("year") == year:
                return {"yun": yun, "nian": nian}
    return None


def time_context_tool(paipan_output: Dict[str, Any], ref_text: str, now: Optional[str] = None) -> Optional[Dict[str, Any]]:
    if not paipan_output:
        return None
    now_dt = dt.datetime.fromisoformat(now) if now else dt.datetime.now()

    if ref_text in ("今年", "明年", "去年"):
        offset = {"今年": 0, "明年": 1, "去年": -1}[ref_text]
        year = now_dt.year + offset
        hit = _find_year(paipan_output, year)
        if not hit:
            return None
        return {
            "granularity": "year",
            "matched": True,
            "dayun": {
                "name": f"{hit['yun'].get('gan', '')}{hit['yun'].get('zhi', '')}",
                "start_year": hit["yun"].get("year"),
                "end_year": (hit["yun"].get("year") or 0) + 9,
            },
            "year": {
                "year": year,
                "ganzhi": f"{hit['nian'].get('gan', '')}{hit['nian'].get('zhi', '')}",
            },
            "month": None,
            "source": "paipan.dayun_liunian_pan",
            "confidence": 0.85,
            "raw_match": ref_text,
        }

    m = re.search(r"(\d{4})年(\d{1,2})月", ref_text)
    if m:
        year = int(m.group(1))
        month = int(m.group(2))
        hit = _find_year(paipan_output, year)
        if not hit:
            return None
        month_hit = None
        for yue in hit["nian"].get("liuyue", []):
            if yue.get("month") == month:
                month_hit = yue
                break
        return {
            "granularity": "month",
            "matched": True,
            "dayun": {
                "name": f"{hit['yun'].get('gan', '')}{hit['yun'].get('zhi', '')}",
                "start_year": hit["yun"].get("year"),
                "end_year": (hit["yun"].get("year") or 0) + 9,
            },
            "year": {
                "year": year,
                "ganzhi": f"{hit['nian'].get('gan', '')}{hit['nian'].get('zhi', '')}",
            },
            "month": month_hit,
            "source": "paipan.dayun_liunian_pan",
            "confidence": 0.8,
            "raw_match": m.group(0),
        }

    m = re.search(r"(\d{4})年", ref_text)
    if m:
        year = int(m.group(1))
        hit = _find_year(paipan_output, year)
        if not hit:
            return None
        return {
            "granularity": "year",
            "matched": True,
            "dayun": {
                "name": f"{hit['yun'].get('gan', '')}{hit['yun'].get('zhi', '')}",
                "start_year": hit["yun"].get("year"),
                "end_year": (hit["yun"].get("year") or 0) + 9,
            },
            "year": {
                "year": year,
                "ganzhi": f"{hit['nian'].get('gan', '')}{hit['nian'].get('zhi', '')}",
            },
            "month": None,
            "source": "paipan.dayun_liunian_pan",
            "confidence": 0.8,
            "raw_match": m.group(0),
        }

    return None
