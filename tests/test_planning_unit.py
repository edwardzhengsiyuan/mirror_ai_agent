"""Unit tests for agent/planning.py - planning and time detection."""

from __future__ import annotations

import datetime as dt
import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, ROOT)

from agent.planning import (
    classify_aspects,
    detect_times,
    plan_with_rules,
    _parse_tool_call,
    _merge_times_from_question,
)


class TestClassifyAspects:
    """Tests for classify_aspects function."""

    def test_career_keyword(self):
        """Career-related keywords should map to CAREER."""
        assert "CAREER" in classify_aspects("事业运势如何")
        assert "CAREER" in classify_aspects("工作方面")

    def test_relationship_keyword(self):
        """Relationship keywords should map to RELATIONSHIP."""
        assert "RELATIONSHIP" in classify_aspects("感情怎么样")
        assert "RELATIONSHIP" in classify_aspects("婚姻运势")
        assert "RELATIONSHIP" in classify_aspects("桃花运")

    def test_health_keyword(self):
        """Health keywords should map to HEALTH."""
        assert "HEALTH" in classify_aspects("健康方面")
        assert "HEALTH" in classify_aspects("身体状况")

    def test_guiren_keyword(self):
        """Guiren keywords should map to GUIREN."""
        assert "GUIREN" in classify_aspects("贵人运")

    def test_liuqin_keyword(self):
        """Liuqin keywords should map to LIUQIN."""
        assert "LIUQIN" in classify_aspects("六亲关系")
        assert "LIUQIN" in classify_aspects("父母方面")

    def test_xingge_keyword(self):
        """Xingge keywords should map to XINGGE."""
        assert "XINGGE" in classify_aspects("性格特点")
        assert "XINGGE" in classify_aspects("气质如何")

    def test_multiple_aspects(self):
        """Multiple keywords should return multiple aspects."""
        result = classify_aspects("事业和感情怎么样")
        assert "CAREER" in result
        assert "RELATIONSHIP" in result

    def test_no_match_returns_other(self):
        """No matching keywords should return OTHER."""
        result = classify_aspects("你好")
        assert result == ["OTHER"]

    def test_empty_string_returns_other(self):
        """Empty string should return OTHER."""
        result = classify_aspects("")
        assert result == ["OTHER"]

    def test_财运_maps_to_other(self):
        """财运 should map to OTHER (financial is separate)."""
        result = classify_aspects("财运如何")
        assert "OTHER" in result


class TestDetectTimes:
    """Tests for detect_times function."""

    @pytest.fixture
    def now(self):
        return dt.datetime(2025, 6, 15, 10, 0, 0)

    def test_今年_relative(self, now):
        """今年 should map to current year."""
        result = detect_times("今年运势", now)
        assert len(result) >= 1
        time_item = result[0]
        assert time_item["year"] == 2025
        assert time_item["need_tool"] is True

    def test_明年_relative(self, now):
        """明年 should map to next year."""
        result = detect_times("明年怎么样", now)
        assert len(result) >= 1
        assert result[0]["year"] == 2026

    def test_去年_relative(self, now):
        """去年 should map to previous year."""
        result = detect_times("去年运势", now)
        assert len(result) >= 1
        assert result[0]["year"] == 2024

    def test_absolute_year(self, now):
        """Absolute year like 2035年 should be parsed."""
        result = detect_times("2035年事业如何", now)
        assert len(result) >= 1
        assert result[0]["year"] == 2035

    def test_year_month(self, now):
        """Year+month like 2026年3月 extracts year only (month not supported)."""
        result = detect_times("2026年3月感情", now)
        assert len(result) >= 1
        time_item = result[0]
        assert time_item["year"] == 2026
        # Month is no longer extracted - simplified to year-only
        assert "month" not in time_item

    def test_multiple_years(self, now):
        """Multiple years should all be detected."""
        result = detect_times("2035年和2045年健康", now)
        years = [t["year"] for t in result]
        assert 2035 in years
        assert 2045 in years

    def test_no_time_reference(self, now):
        """No time reference should return empty list."""
        result = detect_times("性格特点", now)
        assert result == []

    def test_duplicate_years_deduplicated(self, now):
        """Same year mentioned twice should be deduplicated."""
        result = detect_times("2030年事业2030年感情", now)
        years = [t["year"] for t in result]
        assert years.count(2030) == 1

    def test_ref_text_captured(self, now):
        """ref_text should capture the original text."""
        result = detect_times("今年运势", now)
        assert result[0]["ref_text"] == "今年"


class TestParseToolCall:
    """Tests for _parse_tool_call function."""

    def test_valid_json(self):
        """Valid JSON with tool call should return args dict."""
        content = '{"tool":"planning_tool","args":{"aspects":["CAREER"],"times":[]}}'
        result = _parse_tool_call(content)
        assert result is not None
        # Returns args dict, not full structure
        assert result["aspects"] == ["CAREER"]
        assert "times" in result

    def test_malformed_json_returns_none(self):
        """Malformed JSON should return None."""
        content = '{"tool": invalid}'
        result = _parse_tool_call(content)
        assert result is None

    def test_empty_string_returns_none(self):
        """Empty string should return None."""
        result = _parse_tool_call("")
        assert result is None

    def test_json_with_extra_text(self):
        """JSON embedded in text should not be extracted (requires valid JSON)."""
        content = 'Here is my analysis: {"tool":"planning_tool","args":{"aspects":["HEALTH"],"times":[]}}'
        result = _parse_tool_call(content)
        # Invalid JSON due to extra text prefix
        assert result is None

    def test_nested_json(self):
        """Nested JSON structure should be parsed, returning args."""
        content = json.dumps({
            "tool": "planning_tool",
            "args": {
                "aspects": ["CAREER"],
                "times": [{"year": 2025, "month": None, "granularity": "year", "need_tool": True, "ref_text": "今年"}]
            }
        })
        result = _parse_tool_call(content)
        assert result is not None
        # Returns args dict directly
        assert result["times"][0]["year"] == 2025

    def test_direct_plan_dict(self):
        """Direct plan dict without tool wrapper should also work."""
        content = '{"aspects":["CAREER"],"time":{"year":2025},"times":[]}'
        result = _parse_tool_call(content)
        assert result is not None
        assert result["aspects"] == ["CAREER"]


class TestMergeTimesFromQuestion:
    """Tests for _merge_times_from_question function."""

    @pytest.fixture
    def now(self):
        return dt.datetime(2025, 6, 15, 10, 0, 0)

    def test_empty_llm_times_uses_detected(self, now):
        """Empty LLM times should use detected times from question."""
        plan_result = {"aspects": ["CAREER"], "times": []}
        question = "2030年事业"
        result = _merge_times_from_question(plan_result, question, now)
        assert len(result.get("times", [])) >= 1
        assert result["times"][0]["year"] == 2030

    def test_llm_times_preserved(self, now):
        """LLM times should be preserved."""
        plan_result = {
            "aspects": ["CAREER"],
            "times": [{"year": 2025, "month": None, "granularity": "year", "need_tool": True, "ref_text": "今年"}]
        }
        question = "今年事业"
        result = _merge_times_from_question(plan_result, question, now)
        assert len(result.get("times", [])) >= 1
        assert result["times"][0]["year"] == 2025

    def test_deduplication_by_year(self, now):
        """Same year from LLM and detection should be deduplicated."""
        plan_result = {
            "aspects": ["CAREER"],
            "times": [{"year": 2030, "month": None, "granularity": "year", "need_tool": True, "ref_text": "2030年"}]
        }
        question = "2030年事业"
        result = _merge_times_from_question(plan_result, question, now)
        years = [t["year"] for t in result.get("times", [])]
        assert years.count(2030) == 1


class TestPlanWithRules:
    """Tests for plan_with_rules function."""

    @pytest.fixture
    def now(self):
        return dt.datetime(2025, 6, 15, 10, 0, 0)

    def test_basic_question(self, now):
        """Basic question should return valid plan structure."""
        result = plan_with_rules("今年事业怎么样", now)
        assert "aspects" in result
        assert "time" in result or "times" in result
        assert "CAREER" in result["aspects"]

    def test_no_time_reference(self, now):
        """Question without time should have need_tool=False."""
        result = plan_with_rules("性格特点", now)
        assert "aspects" in result
        # time.need_tool should be False when no time mentioned
        if "time" in result:
            assert result["time"]["need_tool"] is False

    def test_multiple_aspects(self, now):
        """Multiple aspects should all be detected."""
        result = plan_with_rules("事业感情健康", now)
        aspects = result["aspects"]
        assert "CAREER" in aspects
        assert "RELATIONSHIP" in aspects
        assert "HEALTH" in aspects
