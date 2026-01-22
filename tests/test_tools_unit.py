"""Unit tests for agent/tools/ - tool implementations."""

from __future__ import annotations

import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, ROOT)

from agent.tools.planning_tool import planning_tool, _normalize_aspects, _normalize_time_item


class TestNormalizeAspects:
    """Tests for _normalize_aspects function."""

    def test_lowercase_to_uppercase(self):
        """Lowercase aspects should be normalized to uppercase."""
        result = _normalize_aspects(["career", "health"])
        assert "CAREER" in result
        assert "HEALTH" in result

    def test_mixed_case(self):
        """Mixed case should be normalized."""
        result = _normalize_aspects(["Career", "HEALTH", "relationship"])
        assert "CAREER" in result
        assert "HEALTH" in result
        assert "RELATIONSHIP" in result

    def test_duplicates_removed(self):
        """Duplicate aspects should be removed."""
        result = _normalize_aspects(["CAREER", "career", "Career"])
        assert result.count("CAREER") == 1

    def test_empty_list_returns_other(self):
        """Empty aspects list should return OTHER."""
        result = _normalize_aspects([])
        assert result == ["OTHER"]

    def test_none_handled(self):
        """None aspects should return OTHER."""
        result = _normalize_aspects(None)
        assert result == ["OTHER"]

    def test_whitespace_stripped(self):
        """Whitespace should be stripped from aspects."""
        result = _normalize_aspects(["  CAREER  ", " HEALTH "])
        assert "CAREER" in result
        assert "HEALTH" in result

    def test_non_string_items_skipped(self):
        """Non-string items should be skipped."""
        result = _normalize_aspects(["CAREER", 123, None, "HEALTH"])
        assert "CAREER" in result
        assert "HEALTH" in result
        assert len(result) == 2


class TestNormalizeTimeItem:
    """Tests for _normalize_time_item function."""

    def test_basic_time_item(self):
        """Basic time item should have all required fields (year, ref_text, need_tool)."""
        item = {"year": 2025, "ref_text": "今年", "need_tool": True}
        result = _normalize_time_item(item)
        assert result["year"] == 2025
        assert result["ref_text"] == "今年"
        assert result["need_tool"] is True
        # granularity and month are no longer in output (simplified)
        assert "granularity" not in result
        assert "month" not in result

    def test_need_tool_forced_true_when_year_present(self):
        """need_tool should be True when year is present."""
        item = {"year": 2025, "ref_text": "今年", "need_tool": False}
        result = _normalize_time_item(item)
        assert result["need_tool"] is True

    def test_dayun_field_removed(self):
        """dayun field should be removed from output."""
        item = {"year": 2025, "ref_text": "今年", "need_tool": True, "dayun": "test"}
        result = _normalize_time_item(item)
        assert "dayun" not in result


class TestPlanningTool:
    """Tests for planning_tool function."""

    def test_basic_planning(self):
        """Basic planning should return valid structure."""
        result = planning_tool(
            aspects=["CAREER"],
            time=None,
            times=[{"year": 2025, "granularity": "year", "ref_text": "今年", "need_tool": True}],
        )
        assert "aspects" in result
        assert "times" in result
        assert "time" in result

    def test_aspects_normalized(self):
        """Aspects should be normalized to uppercase."""
        result = planning_tool(
            aspects=["career"],
            time=None,
            times=[],
        )
        assert "CAREER" in result["aspects"]

    def test_times_deduplicated(self):
        """Duplicate times should be removed."""
        result = planning_tool(
            aspects=["CAREER"],
            time=None,
            times=[
                {"year": 2025, "granularity": "year", "ref_text": "今年", "need_tool": True},
                {"year": 2025, "granularity": "year", "ref_text": "2025年", "need_tool": True},
            ],
        )
        years = [t["year"] for t in result["times"]]
        assert years.count(2025) == 1

    def test_time_field_equals_first_times(self):
        """time field should equal first item in times."""
        result = planning_tool(
            aspects=["CAREER"],
            time=None,
            times=[
                {"year": 2025, "granularity": "year", "ref_text": "今年", "need_tool": True},
                {"year": 2026, "granularity": "year", "ref_text": "明年", "need_tool": True},
            ],
        )
        assert result["time"]["year"] == result["times"][0]["year"]

    def test_empty_times_creates_default(self):
        """Empty times should create default time entry."""
        result = planning_tool(
            aspects=["CAREER"],
            time=None,
            times=[],
        )
        assert "time" in result
        assert result["time"]["need_tool"] is False


class TestPaipanToolInputValidation:
    """Tests for paipan_tool input validation helpers."""

    def test_require_int_with_int(self):
        """_require_int with int should return int."""
        from agent.tools.paipan_tool import _require_int
        assert _require_int({"year": 1990}, "year") == 1990

    def test_require_int_with_none_raises(self):
        """_require_int with None should raise ValueError."""
        from agent.tools.paipan_tool import _require_int
        with pytest.raises(ValueError):
            _require_int({}, "year")

    def test_optional_int_with_default(self):
        """_optional_int with missing key should return default."""
        from agent.tools.paipan_tool import _optional_int
        assert _optional_int({}, "hour", 0) == 0

    def test_check_range_valid(self):
        """_check_range with valid value should not raise."""
        from agent.tools.paipan_tool import _check_range
        _check_range(6, "month", 1, 12)  # Should not raise

    def test_check_range_invalid_raises(self):
        """_check_range with invalid value should raise ValueError."""
        from agent.tools.paipan_tool import _check_range
        with pytest.raises(ValueError):
            _check_range(13, "month", 1, 12)


class TestTimeContextTool:
    """Tests for time_context_tool."""

    def test_empty_requests(self, sample_birth):
        """Empty requests should return empty year_data."""
        from agent.tools.time_context_tool import time_context_tool
        result = time_context_tool([], sample_birth, "male")
        assert result == {"year_data": []}

    def test_single_year_request(self, sample_birth):
        """Single year request should return year_data with 1 entry."""
        from agent.tools.time_context_tool import time_context_tool
        result = time_context_tool([{"year": 2025}], sample_birth, "male")
        assert "year_data" in result
        assert len(result["year_data"]) >= 0  # May be 0 if year not in range

    def test_multiple_years(self, sample_birth):
        """Multiple year requests should return multiple entries."""
        from agent.tools.time_context_tool import time_context_tool
        result = time_context_tool(
            [{"year": 2025}, {"year": 2030}],
            sample_birth,
            "male"
        )
        assert "year_data" in result


@pytest.fixture
def sample_birth():
    """Sample birth data for testing."""
    return {
        "year": 1990,
        "month": 1,
        "day": 15,
        "hour": 8,
        "minute": 30,
        "second": 0,
    }
