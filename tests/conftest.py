"""Shared pytest fixtures for bazi_agent tests."""

from __future__ import annotations

import datetime as dt
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, ROOT)


@pytest.fixture
def stub_env(monkeypatch):
    """Set LLM_MODE=stub for offline testing."""
    monkeypatch.setenv("LLM_MODE", "stub")
    monkeypatch.setenv("LLM_PLANNER_MODE", "rule")
    return monkeypatch


@pytest.fixture
def sample_birth():
    """Standard birth data for testing."""
    return {
        "year": 1990,
        "month": 1,
        "day": 15,
        "hour": 8,
        "minute": 30,
        "second": 0,
    }


@pytest.fixture
def sample_profile(sample_birth):
    """Standard test profile dict."""
    return {
        "user_id": "u_test",
        "birth": sample_birth,
        "gender": "male",
        "birth_time_unknown": False,
        "prompt_config": "lingyun_cat",
        "node_cache": {},
    }


@pytest.fixture
def sample_cache():
    """Node cache with standard outputs for testing prompt building."""
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
        "GEJU_ROUTER": {
            "output": {
                "type": "report",
                "content": '{"category": "NORMAL", "patterns": [{"type": "NORMAL", "name": "正官格", "reasoning": "Test router reasoning"}]}',
                "structured": {"node": "GEJU_ROUTER"},
                "reasoning_content": "",
                "error": False,
            }
        },
        "GEJU_ANALYSIS": {
            "output": {
                "type": "report",
                "content": "Test geju analysis content",
                "structured": {"node": "GEJU_ANALYSIS"},
                "reasoning_content": "",
                "error": False,
            }
        },
        "GEJU_LEVEL": {
            "output": {
                "type": "report",
                "content": "Test geju level content",
                "structured": {"node": "GEJU_LEVEL"},
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
                "content": "Test career content",
                "structured": {"node": "CAREER"},
                "reasoning_content": "",
                "error": False,
            }
        },
    }


@pytest.fixture
def mock_paipan(monkeypatch):
    """Mock paipan_tool to avoid bazi engine dependency."""
    from agent import execution

    def fake_paipan(inputs):
        return {
            "paipan_results": "Mocked paipan results",
            "liupan_results": "Mocked liupan results",
            "guji_results": "Mocked guji results",
            "paipan_output": {"yun": []},
            "dayun_list": [],
        }

    monkeypatch.setattr(execution, "paipan_tool", fake_paipan)
    return fake_paipan


@pytest.fixture
def mock_time_context(monkeypatch):
    """Mock time_context_tool to avoid bazi engine dependency."""
    from agent import execution

    def fake_time_context(requests, birth, gender, birth_time_unknown=False):
        if not requests:
            return {"year_data": []}
        return {
            "year_data": [
                {"year": req.get("year"), "data": f"Year {req.get('year')} data"}
                for req in requests
            ]
        }

    monkeypatch.setattr(execution, "time_context_tool", fake_time_context)
    return fake_time_context


@pytest.fixture
def now():
    """Standard datetime for testing."""
    return dt.datetime(2025, 6, 15, 10, 0, 0)
