"""Time context extraction from paipan/liupan text outputs."""

from __future__ import annotations

import datetime as dt
import re
from typing import Any, Dict, List, Optional

try:
    from bazi.core.property import Gan, Zhi, strip_ns
except Exception:  # pragma: no cover - best-effort optional import
    Gan = None  # type: ignore[assignment]
    Zhi = None  # type: ignore[assignment]

    def strip_ns(value):  # type: ignore[override]
        return value


_GANZHI_PATTERN = r"[甲乙丙丁戊己庚辛壬癸][子丑寅卯辰巳午未申酉戌亥]"
_DAYUN_PATTERN = re.compile(rf"({_GANZHI_PATTERN})(\d{{4}})")
_LIUNIAN_PATTERN = re.compile(rf"(?P<year>\d{{4}})(?P<ganzhi>{_GANZHI_PATTERN})")
_AGE_PATTERN = re.compile(r"(\d+)岁")
_DAYUN_REF_PATTERN = re.compile(rf"({_GANZHI_PATTERN})大运")


def _format_ganzhi(gan: Optional[str], zhi: Optional[str]) -> Optional[str]:
    if not isinstance(gan, str) or not isinstance(zhi, str):
        return None
    raw_gan = strip_ns(gan)
    raw_zhi = strip_ns(zhi)
    if Gan and Zhi:
        try:
            gan_obj = Gan[raw_gan] if raw_gan in Gan.__members__ else Gan.from_chinese(raw_gan)
            zhi_obj = Zhi[raw_zhi] if raw_zhi in Zhi.__members__ else Zhi.from_chinese(raw_zhi)
            return f"{gan_obj.chinese_name}{zhi_obj.chinese_name}"
        except Exception:
            pass
    return f"{raw_gan}{raw_zhi}"


def extract_dayun_list(paipan_results: str) -> List[Dict[str, Any]]:
    if not paipan_results:
        return []
    idx = paipan_results.find("【大运简排】")
    snippet = paipan_results[idx:] if idx != -1 else paipan_results
    items = []
    for match in _DAYUN_PATTERN.finditer(snippet):
        name = match.group(1)
        start_year = int(match.group(2))
        items.append({"name": name, "start_year": start_year})
    for i, item in enumerate(items):
        next_start = items[i + 1]["start_year"] if i + 1 < len(items) else None
        end_year = next_start - 1 if next_start else item["start_year"] + 9
        item["end_year"] = end_year
        item["step"] = i + 1
    return items


def extract_liunian_list(liupan_results: str) -> List[Dict[str, Any]]:
    if not liupan_results:
        return []
    items = []
    for line in liupan_results.splitlines():
        line = line.strip()
        if not line or line.startswith("起运前"):
            continue
        match = _LIUNIAN_PATTERN.search(line)
        if not match:
            continue
        year = int(match.group("year"))
        ganzhi = match.group("ganzhi")
        age_match = _AGE_PATTERN.search(line)
        age = int(age_match.group(1)) if age_match else None
        items.append({"year": year, "ganzhi": ganzhi, "age": age, "raw": line})
    return items


def build_time_index(
    paipan_output: Optional[Dict[str, Any]],
    paipan_results: str,
    liupan_results: str,
) -> Dict[str, Any]:
    text_dayun = extract_dayun_list(paipan_results)
    text_dayun_by_year = {item.get("start_year"): item for item in text_dayun if item.get("start_year")}
    structured_yun = paipan_output.get("yun", []) if isinstance(paipan_output, dict) else []

    dayun_list: List[Dict[str, Any]] = []
    liunian_list: List[Dict[str, Any]] = []
    liuyue_by_year: Dict[int, List[Dict[str, Any]]] = {}

    if structured_yun:
        for idx, dayun in enumerate(structured_yun):
            start_year = dayun.get("year")
            if not isinstance(start_year, int):
                continue
            next_start = None
            for later in structured_yun[idx + 1 :]:
                if isinstance(later.get("year"), int):
                    next_start = later["year"]
                    break
            end_year = next_start - 1 if next_start else start_year + 9
            name = None
            text_match = text_dayun_by_year.get(start_year)
            if text_match:
                name = text_match.get("name")
            dayun_list.append(
                {
                    "name": name,
                    "start_year": start_year,
                    "end_year": end_year,
                    "step": idx + 1,
                    "age_start": dayun.get("age"),
                }
            )
            for liunian in dayun.get("liunian", []) or []:
                year = liunian.get("year")
                if not isinstance(year, int):
                    continue
                gan = liunian.get("gan")
                zhi = liunian.get("zhi")
                ganzhi = _format_ganzhi(gan, zhi)
                liunian_list.append(
                    {
                        "year": year,
                        "ganzhi": ganzhi,
                        "age": liunian.get("age"),
                        "dayun": name,
                    }
                )
                liuyue = liunian.get("liuyue")
                if isinstance(liuyue, list):
                    liuyue_by_year[year] = liuyue
    else:
        dayun_list = text_dayun
        liunian_list = extract_liunian_list(liupan_results)

    return {
        "dayun_list": dayun_list,
        "liunian_list": liunian_list,
        "liuyue_by_year": liuyue_by_year,
    }


def _find_dayun(dayun_list: List[Dict[str, Any]], year: Optional[int], name: Optional[str]) -> Optional[Dict[str, Any]]:
    if year is not None:
        for item in dayun_list:
            start = item.get("start_year")
            end = item.get("end_year")
            if start is None or end is None:
                continue
            if start <= year <= end:
                return item
        if name:
            for item in dayun_list:
                if item.get("name") == name:
                    return item
        return None
    if name:
        for item in dayun_list:
            if item.get("name") == name:
                return item
    return None


def _find_liunian(liunian_list: List[Dict[str, Any]], year: Optional[int]) -> Optional[Dict[str, Any]]:
    if year is None:
        return None
    for item in liunian_list:
        if item.get("year") == year:
            return item
    return None


def _find_liuyue(liuyue_by_year: Dict[int, List[Dict[str, Any]]], year: Optional[int], month: Optional[int]):
    if year is None or month is None:
        return None
    for item in liuyue_by_year.get(year, []) or []:
        if item.get("month") == month:
            return item
    return None


def _resolve_year(ref_text: str, now: Optional[str]) -> Optional[int]:
    if now:
        try:
            now_dt = dt.datetime.fromisoformat(now)
        except ValueError:
            if now.endswith("Z"):
                now_dt = dt.datetime.fromisoformat(now[:-1] + "+00:00")
            else:
                now_dt = dt.datetime.now()
    else:
        now_dt = dt.datetime.now()

    if ref_text in ("今年", "明年", "去年"):
        offset = {"今年": 0, "明年": 1, "去年": -1}[ref_text]
        return now_dt.year + offset

    m = re.search(r"(\d{4})年(\d{1,2})月", ref_text)
    if m:
        return int(m.group(1))

    m = re.search(r"(\d{4})年", ref_text)
    if m:
        return int(m.group(1))

    return None


def _resolve_time_context(
    dayun_list: List[Dict[str, Any]],
    liunian_list: List[Dict[str, Any]],
    liuyue_by_year: Dict[int, List[Dict[str, Any]]],
    ref_text: str,
    now: Optional[str] = None,
    target_year: Optional[int] = None,
    target_month: Optional[int] = None,
    target_dayun: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    ref_text = ref_text or ""
    if not dayun_list and not liunian_list:
        return None
    if not target_dayun:
        match = _DAYUN_REF_PATTERN.search(ref_text or "")
        if match:
            target_dayun = match.group(1)
    year = target_year or _resolve_year(ref_text, now)
    dayun = _find_dayun(dayun_list, year, target_dayun)
    liunian = _find_liunian(liunian_list, year)
    liuyue = _find_liuyue(liuyue_by_year, year, target_month)

    if not dayun and not liunian and not liuyue:
        return None

    granularity = "year"
    if target_dayun and not year:
        granularity = "dayun"
    if target_month:
        granularity = "month"

    return {
        "granularity": granularity,
        "matched": True,
        "dayun": dayun,
        "year": liunian,
        "month": {"month": target_month, "liuyue": liuyue} if target_month else None,
        "source": "paipan_output" if liuyue_by_year else "paipan_results/liupan_results",
        "confidence": 0.75,
        "raw_match": ref_text,
    }


def time_context_tool(
    dayun_list: List[Dict[str, Any]],
    liunian_list: List[Dict[str, Any]],
    ref_text: str,
    now: Optional[str] = None,
    target_year: Optional[int] = None,
    target_month: Optional[int] = None,
    target_dayun: Optional[str] = None,
    liuyue_by_year: Optional[Dict[int, List[Dict[str, Any]]]] = None,
    requests: Optional[List[Dict[str, Any]]] = None,
) -> Optional[Dict[str, Any]] | List[Optional[Dict[str, Any]]]:
    liuyue_by_year = liuyue_by_year or {}
    if requests is not None:
        results: List[Optional[Dict[str, Any]]] = []
        for idx, req in enumerate(requests):
            ctx = _resolve_time_context(
                dayun_list,
                liunian_list,
                liuyue_by_year,
                req.get("ref_text") or "",
                now=req.get("now", now),
                target_year=req.get("target_year"),
                target_month=req.get("target_month"),
                target_dayun=req.get("target_dayun"),
            )
            if ctx:
                ctx["index"] = req.get("index", idx)
            results.append(ctx)
        return results
    return _resolve_time_context(
        dayun_list,
        liunian_list,
        liuyue_by_year,
        ref_text,
        now=now,
        target_year=target_year,
        target_month=target_month,
        target_dayun=target_dayun,
    )
