from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, ROOT)

from agent.tools.time_context_tool import extract_dayun_list, extract_liunian_list, time_context_tool


def test_time_context_from_text_lists() -> None:
    paipan_results = "【大运简排】：乙亥2008甲戌2018癸酉2028壬申2038"
    liupan_results = (
        "【流年大运排盘】：\n"
        "起运前\n"
        "2008戊子【食官】19岁；\n"
        "2009己丑【伤伤】20岁；\n"
        "2010庚寅【才枭】21岁；\n"
    )
    dayun_list = extract_dayun_list(paipan_results)
    liunian_list = extract_liunian_list(liupan_results)
    assert dayun_list[0]["name"] == "乙亥"
    assert dayun_list[0]["start_year"] == 2008
    assert liunian_list[0]["year"] == 2008

    ctx = time_context_tool(dayun_list, liunian_list, ref_text="2009年", now=None, target_year=2009)
    assert ctx["dayun"]["name"] == "乙亥"
    assert ctx["year"]["ganzhi"] == "己丑"


def test_dayun_prefers_year_match_over_name() -> None:
    dayun_list = [
        {"name": "甲子", "start_year": 2000, "end_year": 2009},
        {"name": "乙丑", "start_year": 2010, "end_year": 2019},
    ]
    liunian_list = [{"year": 2012, "ganzhi": "壬辰", "age": 13}]
    ctx = time_context_tool(dayun_list, liunian_list, ref_text="2012年", now=None, target_year=2012, target_dayun="甲子")
    assert ctx["dayun"]["name"] == "乙丑"


def test_resolve_year_accepts_zulu_timestamp() -> None:
    dayun_list = [{"name": "甲子", "start_year": 2020, "end_year": 2029}]
    liunian_list = [{"year": 2025, "ganzhi": "乙巳", "age": 30}]
    ctx = time_context_tool(dayun_list, liunian_list, ref_text="今年", now="2025-01-01T00:00:00Z")
    assert ctx["year"]["year"] == 2025
