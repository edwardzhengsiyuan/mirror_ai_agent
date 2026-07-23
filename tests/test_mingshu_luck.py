from __future__ import annotations

import json
from pathlib import Path

from mingshu.luck_analysis import build_luck_analysis
from mingshu.luck_pages import render_luck_html


ROOT = Path(__file__).resolve().parents[1]


def _facts() -> dict:
    return json.loads((ROOT / "output/mingshu/opening-real/facts.json").read_text(encoding="utf-8"))


def test_combined_preference_distinguishes_pattern_tiaohou_and_stems() -> None:
    result = build_luck_analysis(_facts())
    assert result["preference"]["priority_basis"] == "balanced"
    assert result["preference"]["tiaohou"]["primary_gods"] == ["甲", "庚"]
    assert result["preference"]["tiaohou"]["caution_gods"] == ["癸"]
    stems = {item["name"]: item for item in result["preference"]["stems"]}
    assert stems["庚"]["tone"] == "优先"
    assert stems["甲"]["tone"] == "有助"
    assert stems["癸"]["tone"] == "谨慎"
    assert stems["丙"]["tone"] == "谨慎"


def test_luck_analysis_uses_all_nine_cycles_and_ninety_real_years() -> None:
    result = build_luck_analysis(_facts())
    assert len(result["cycles"]) == 9
    assert len(result["years"]) == 90
    assert result["years"][0]["year"] == 1998
    assert result["years"][-1]["year"] == 2087
    assert all(len(item["years"]) == 10 for item in result["cycles"])
    assert all(25 <= item["score"] <= 82 for item in result["cycles"])
    assert all(25 <= item["score"] <= 82 for item in result["years"])
    assert sum(len(item["months"]) for item in result["years"]) == 1080
    assert all(len(item["months"]) == 12 for item in result["years"])
    assert all(item["ten_god_readings"] for item in result["years"])
    assert all(item["overlap_notes"] for item in result["years"])
    assert all("relation_details" in item for item in result["years"])
    assert all("shensha" in item for item in result["years"])
    assert all(len(item["wuxing_shift"]["series"]) == 5 for item in result["cycles"])
    assert all(
        abs(sum(row["adjusted"] for row in item["wuxing_shift"]["series"]) - 100) < 0.05
        for item in result["cycles"]
    )
    assert all(
        abs(sum(row["delta"] for row in item["wuxing_shift"]["series"])) < 0.05
        for item in result["cycles"]
    )
    assert (
        result["cycles"][0]["wuxing_shift"]["series"]
        != result["cycles"][1]["wuxing_shift"]["series"]
    )

    year_2025 = next(item for item in result["years"] if item["year"] == 2025)
    assert len(year_2025["months"]) == 12
    assert all(month["ganzhi"] for month in year_2025["months"])
    assert all(month["focus"] for month in year_2025["months"])


def test_luck_chapter_has_one_page_per_year_and_continuous_numbering() -> None:
    html = render_luck_html(_facts())
    assert html.count('class="spread"') == 60
    assert html.count('class="page ') == 120
    assert html.count('class="page recto year-page"') + html.count('class="page verso year-page"') == 90
    assert 'data-page="50"' in html
    assert 'data-page="169"' in html
    assert html.count("cycle-profile") == 9
    assert html.count('class="page recto cycle-timeline"') + html.count('class="page verso cycle-timeline"') == 9
    assert html.count('class="month-rhythm"') == 90
    assert html.count('--month-score:') == 1080
    for phrase in ("十二月内部节奏", "关系较密集", "相对可用", "宜留余地", "本年神煞"):
        assert phrase in html
    for phrase in ("五行喜忌", "格局调候交点", "十天干细分", "大运 · 总体走势", "流年分析", "1998", "2087"):
        assert phrase in html
    assert html.count("本运加入后的五行力量") == 9
    assert html.count("一运十年，岁岁不同") == 9
    assert "十年不是一条平线" not in html
    for banned in ("先说人话", "一句话带走", "一年一页", "结构化编辑稿", "咨询师"):
        assert banned not in html
