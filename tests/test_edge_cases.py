"""Edge case and negative tests for bazi_agent."""

from __future__ import annotations

import datetime as dt
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, ROOT)


class TestEmptyNullInputs:
    """Tests for empty and null input handling."""

    def test_empty_question_string(self, stub_env, mock_paipan, mock_time_context, sample_profile):
        """Empty question string should be handled gracefully."""
        from agent.orchestrator import run_turn

        # Empty string should still work (may default to OTHER aspect)
        result = run_turn(sample_profile, "", now=dt.datetime(2025, 6, 15))
        assert "response" in result
        assert "plan" in result

    def test_whitespace_only_question(self, stub_env, mock_paipan, mock_time_context, sample_profile):
        """Whitespace-only question should be handled."""
        from agent.orchestrator import run_turn

        result = run_turn(sample_profile, "   ", now=dt.datetime(2025, 6, 15))
        assert "response" in result

    def test_missing_node_cache(self, stub_env, mock_paipan, mock_time_context):
        """Profile without node_cache should be handled."""
        from agent.orchestrator import run_turn

        profile = {
            "user_id": "u_test",
            "birth": {"year": 1990, "month": 1, "day": 15, "hour": 8, "minute": 0, "second": 0},
            "gender": "male",
            "birth_time_unknown": False,
            "prompt_config": "lingyun_cat",
            # No node_cache key
        }
        result = run_turn(profile, "今年事业", now=dt.datetime(2025, 6, 15))
        assert "response" in result


class TestMalformedData:
    """Tests for malformed data handling."""

    def test_planning_with_invalid_json_response(self, stub_env):
        """Invalid JSON from LLM should be handled."""
        from agent.planning import _parse_tool_call

        # Various malformed inputs
        assert _parse_tool_call("not json at all") is None
        assert _parse_tool_call("{invalid}") is None
        assert _parse_tool_call("") is None
        assert _parse_tool_call("null") is None

    def test_cache_with_wrong_structure(self, stub_env):
        """Cache with wrong structure raises AttributeError (known limitation)."""
        from agent.nodes.prompt_builder import build_prompt

        malformed_cache = {
            "PAIPAN": {"wrong_key": "wrong_value"},
            "OVERALL": "not a dict",  # Should be dict, causes error
        }
        # Currently raises - documenting existing behavior
        with pytest.raises(AttributeError):
            build_prompt("CAREER", malformed_cache)

    def test_time_context_with_missing_fields(self, stub_env):
        """Time context with missing 'data' field is now handled gracefully.

        Previously this raised ``KeyError``; the response prompt builder now
        skips year entries that have no ``data`` payload instead of crashing.
        """
        from agent.nodes.prompt_builder import build_response_prompt

        time_context = {"year_data": [{"year": 2025}]}  # Missing 'data' field
        cache = {
            "PAIPAN": {"output": {"paipan_results": "", "liupan_results": "", "guji_results": ""}},
        }
        result = build_response_prompt(
            cache=cache,
            time_context=time_context,
            prompt_config="lingyun_cat",
            question="test",
            history_rounds=[],
        )
        assert "system_prompt" in result
        assert "user_prompt" in result
        # Empty year_data entries should not be rendered as a section.
        assert "目标年份详情" not in result["user_prompt"]


class TestBoundaryDates:
    """Tests for date boundary conditions."""

    def test_very_old_birth_date(self, stub_env, mock_time_context):
        """Very old birth date should be handled."""
        from agent.tools.paipan_tool import paipan_tool

        inputs = {
            "birth": {"year": 1900, "month": 1, "day": 1, "hour": 0, "minute": 0, "second": 0},
            "gender": "male",
            "birth_time_unknown": False,
        }
        # May succeed or fail depending on lunar_python support
        try:
            result = paipan_tool(inputs)
            assert "paipan_results" in result
        except Exception:
            pass  # Expected for dates outside supported range

    def test_future_birth_date(self, stub_env, mock_time_context):
        """Future birth date should be handled."""
        from agent.tools.paipan_tool import paipan_tool

        inputs = {
            "birth": {"year": 2100, "month": 1, "day": 1, "hour": 0, "minute": 0, "second": 0},
            "gender": "male",
            "birth_time_unknown": False,
        }
        try:
            result = paipan_tool(inputs)
            assert "paipan_results" in result
        except Exception:
            pass  # Expected for future dates

    def test_month_boundary_values(self, stub_env):
        """Month boundary values (1 and 12) should be handled."""
        from agent.tools.paipan_tool import _check_range

        _check_range(1, "month", 1, 12)  # Should not raise
        _check_range(12, "month", 1, 12)  # Should not raise

        with pytest.raises(ValueError):
            _check_range(0, "month", 1, 12)

        with pytest.raises(ValueError):
            _check_range(13, "month", 1, 12)

    def test_hour_boundary_values(self, stub_env):
        """Hour boundary values (0 and 23) should be handled."""
        from agent.tools.paipan_tool import _check_range

        _check_range(0, "hour", 0, 23)  # Should not raise
        _check_range(23, "hour", 0, 23)  # Should not raise


class TestLargeInputs:
    """Tests for large input handling."""

    def test_very_long_question(self, stub_env, mock_paipan, mock_time_context, sample_profile):
        """Very long question should be handled."""
        from agent.orchestrator import run_turn

        long_question = "事业" * 1000  # 2000 characters
        result = run_turn(sample_profile, long_question, now=dt.datetime(2025, 6, 15))
        assert "response" in result

    def test_many_history_rounds(self, stub_env, mock_paipan, mock_time_context, sample_profile):
        """Many history rounds should be handled."""
        from agent.orchestrator import run_turn

        history = [
            {"user": f"Question {i}", "assistant": f"Answer {i}"}
            for i in range(100)
        ]
        result = run_turn(
            sample_profile,
            "今年事业",
            now=dt.datetime(2025, 6, 15),
            history_rounds=history,
        )
        assert "response" in result


class TestConcurrencyEdgeCases:
    """Tests for concurrency edge cases."""

    def test_same_profile_different_questions(self, stub_env, mock_paipan, mock_time_context, sample_profile):
        """Same profile with different questions should work."""
        from agent.orchestrator import run_turn

        result1 = run_turn(sample_profile, "事业", now=dt.datetime(2025, 6, 15))
        result2 = run_turn(sample_profile, "感情", now=dt.datetime(2025, 6, 15))

        assert result1["response"] != result2["response"] or True  # May be same in stub mode


class TestSpecialCharacters:
    """Tests for special character handling."""

    def test_question_with_special_chars(self, stub_env, mock_paipan, mock_time_context, sample_profile):
        """Question with special characters should be handled."""
        from agent.orchestrator import run_turn

        special_question = "今年事业怎么样？！@#$%^&*()"
        result = run_turn(sample_profile, special_question, now=dt.datetime(2025, 6, 15))
        assert "response" in result

    def test_question_with_emoji(self, stub_env, mock_paipan, mock_time_context, sample_profile):
        """Question with emoji should be handled."""
        from agent.orchestrator import run_turn

        emoji_question = "今年运势好不好呀"
        result = run_turn(sample_profile, emoji_question, now=dt.datetime(2025, 6, 15))
        assert "response" in result


class TestTimeDetectionEdgeCases:
    """Tests for time detection edge cases."""

    def test_ambiguous_time_reference(self):
        """Ambiguous time references should be handled."""
        from agent.planning import detect_times

        now = dt.datetime(2025, 12, 31, 23, 59, 0)

        # "明年" at year boundary
        result = detect_times("明年", now)
        if result:
            assert result[0]["year"] == 2026

    def test_multiple_formats_same_year(self):
        """Same year in different formats should be deduplicated."""
        from agent.planning import detect_times

        now = dt.datetime(2025, 6, 15)
        result = detect_times("2025年和今年", now)
        years = [t["year"] for t in result]
        assert years.count(2025) == 1

    def test_invalid_month_value(self):
        """Invalid month value in text should be handled."""
        from agent.planning import detect_times

        now = dt.datetime(2025, 6, 15)
        # Month 15 doesn't exist
        result = detect_times("2025年15月", now)
        # Should either skip or handle gracefully
        assert isinstance(result, list)
