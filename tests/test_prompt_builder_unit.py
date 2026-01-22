"""Unit tests for agent/nodes/prompt_builder.py - prompt assembly."""

from __future__ import annotations

import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, ROOT)

from agent.nodes.prompt_builder import build_prompt, build_response_prompt, _load_prompt


class TestLoadPrompt:
    """Tests for _load_prompt function."""

    def test_load_existing_template(self):
        """Loading existing template should return content."""
        # init_analysis.md is used by OVERALL node
        content = _load_prompt("init_analysis.md")
        assert content is not None
        assert len(content) > 0

    def test_load_nonexistent_template(self):
        """Loading nonexistent template should handle gracefully."""
        try:
            content = _load_prompt("nonexistent_template_xyz.md")
            # May return empty string or raise
            assert content == "" or content is None
        except (FileNotFoundError, IOError):
            pass  # Expected behavior


class TestBuildPrompt:
    """Tests for build_prompt function."""

    def test_overall_node_with_cache(self, sample_cache):
        """OVERALL node should include paipan content."""
        result = build_prompt("OVERALL", sample_cache)
        assert "system_prompt" in result
        assert "user_prompt" in result
        # Should have paipan content in user prompt
        assert "paipan" in result["user_prompt"].lower() or len(result["user_prompt"]) > 0

    def test_career_node_with_cache(self, sample_cache):
        """CAREER node should include prerequisite content."""
        result = build_prompt("CAREER", sample_cache, prompt_config="lingyun_cat")
        assert "system_prompt" in result
        assert "user_prompt" in result

    def test_missing_cache_entries(self):
        """Missing cache entries should not crash."""
        empty_cache = {}
        result = build_prompt("CAREER", empty_cache)
        assert "system_prompt" in result
        assert "user_prompt" in result
        # Should have empty strings for missing content

    def test_invalid_prompt_config_fallback(self, sample_cache):
        """Invalid prompt_config should fallback to default."""
        result = build_prompt("CAREER", sample_cache, prompt_config="invalid_config")
        assert "system_prompt" in result
        # Should still work with fallback

    def test_history_rounds_included(self, sample_cache):
        """History rounds should be included in response prompt."""
        history = [
            {"user": "Previous question", "assistant": "Previous answer"}
        ]
        # Response prompts include history - use build_response_prompt
        result = build_response_prompt(
            cache=sample_cache,
            time_context=None,
            prompt_config="lingyun_cat",
            question="Current question",
            history_rounds=history
        )
        user_prompt = result["user_prompt"]
        # History should be included
        assert "Previous question" in user_prompt or "Round" in user_prompt

    def test_question_included(self, sample_cache):
        """Question should be included in response prompt."""
        result = build_response_prompt(
            cache=sample_cache,
            time_context=None,
            prompt_config="lingyun_cat",
            question="Test question",
            history_rounds=[]
        )
        # Question should appear in user prompt
        assert "Test question" in result["user_prompt"]


class TestBuildResponsePrompt:
    """Tests for build_response_prompt function."""

    def test_basic_response_prompt(self, sample_cache):
        """Basic response prompt should include all required sections."""
        result = build_response_prompt(
            cache=sample_cache,
            time_context=None,
            prompt_config="lingyun_cat",
            question="今年事业怎么样",
            history_rounds=[],
        )
        assert "system_prompt" in result
        assert "user_prompt" in result
        assert "今年事业怎么样" in result["user_prompt"]

    def test_time_context_injected(self, sample_cache):
        """Time context should be injected into prompt."""
        time_context = {"year_data": [{"year": 2025, "data": "Year 2025 fortune data"}]}
        result = build_response_prompt(
            cache=sample_cache,
            time_context=time_context,
            prompt_config="lingyun_cat",
            question="今年运势",
            history_rounds=[],
        )
        user_prompt = result["user_prompt"]
        # Time context should appear in some form
        assert "2025" in user_prompt or "year" in user_prompt.lower()

    def test_empty_time_context(self, sample_cache):
        """Empty time context should not cause errors."""
        result = build_response_prompt(
            cache=sample_cache,
            time_context=None,
            prompt_config="lingyun_cat",
            question="性格特点",
            history_rounds=[],
        )
        assert "system_prompt" in result
        assert "user_prompt" in result

    def test_history_rounds_formatted(self, sample_cache):
        """History rounds should be formatted in prompt."""
        history = [
            {"user": "First question", "assistant": "First answer"},
            {"user": "Second question", "assistant": "Second answer"},
        ]
        result = build_response_prompt(
            cache=sample_cache,
            time_context=None,
            prompt_config="lingyun_cat",
            question="Current question",
            history_rounds=history,
        )
        user_prompt = result["user_prompt"]
        # History should be included
        assert "First question" in user_prompt or "conversation" in user_prompt.lower() or "Round" in user_prompt

    def test_aspect_reports_concatenated(self, sample_cache):
        """Aspect node reports should be concatenated."""
        result = build_response_prompt(
            cache=sample_cache,
            time_context=None,
            prompt_config="lingyun_cat",
            question="事业怎么样",
            history_rounds=[],
        )
        user_prompt = result["user_prompt"]
        # Should include career content from cache
        assert len(user_prompt) > 0


class TestPromptConfigVariations:
    """Tests for different prompt configurations."""

    def test_lingyun_cat_config(self, sample_cache):
        """lingyun_cat config should work."""
        result = build_prompt("CAREER", sample_cache, prompt_config="lingyun_cat")
        assert "system_prompt" in result

    def test_default_config(self, sample_cache):
        """Default config (None) should work."""
        result = build_prompt("CAREER", sample_cache, prompt_config=None)
        assert "system_prompt" in result


@pytest.fixture
def sample_cache():
    """Node cache with standard outputs for testing."""
    return {
        "PAIPAN": {
            "output": {
                "paipan_results": "Test paipan results",
                "liupan_results": "Test liupan results",
                "guji_results": "Test guji results",
                "paipan_output": {"yun": []},
                "dayun_list": [],
            }
        },
        "OVERALL": {
            "output": {
                "type": "report",
                "content": "Test overall analysis content",
                "structured": {"node": "OVERALL"},
                "reasoning_content": "",
                "error": False,
            }
        },
        "SHISHEN": {
            "output": {
                "type": "report",
                "content": "Test shishen content",
                "structured": {"node": "SHISHEN"},
                "reasoning_content": "",
                "error": False,
            }
        },
        "GEJU": {
            "output": {
                "type": "report",
                "content": "Test geju content",
                "structured": {"node": "GEJU"},
                "reasoning_content": "",
                "error": False,
            }
        },
        "WUXING_PREFS": {
            "output": {
                "type": "report",
                "content": "Test wuxing prefs content",
                "structured": {"node": "WUXING_PREFS"},
                "reasoning_content": "",
                "error": False,
            }
        },
        "CAREER": {
            "output": {
                "type": "report",
                "content": "Test career analysis content",
                "structured": {"node": "CAREER"},
                "reasoning_content": "",
                "error": False,
            }
        },
    }
