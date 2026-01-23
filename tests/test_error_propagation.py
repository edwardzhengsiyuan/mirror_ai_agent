"""Tests for error propagation and workflow stopping on failure."""

from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, ROOT)

from agent import execution
from agent.execution import ensure_node, run_nodes_parallel, _hash_inputs


def test_failed_node_not_cached(monkeypatch) -> None:
    """Failed nodes should not be cached."""
    monkeypatch.setenv("LLM_MODE", "stub")
    monkeypatch.setenv("LLM_FORCE_ERROR", "OVERALL")

    profile = {"node_cache": {}}
    inputs = {"prompt_config": "lingyun_cat"}

    output = ensure_node(profile, "OVERALL", inputs)

    # Output should indicate failure
    assert output.get("error"), "output should be marked as error"

    # Cache should NOT contain the failed node
    assert "OVERALL" not in profile["node_cache"], "failed output should not be cached"


def test_workflow_stops_on_prerequisite_failure(monkeypatch) -> None:
    """Downstream nodes should be skipped when prerequisite fails."""
    monkeypatch.setenv("LLM_MODE", "stub")
    monkeypatch.setenv("LLM_FORCE_ERROR", "OVERALL")

    # Mock paipan_tool to return valid output
    def fake_paipan(inputs):
        return {
            "paipan_results": "test",
            "liupan_results": "",
            "guji_results": "",
            "paipan_output": {},
            "dayun_list": [],
        }

    monkeypatch.setattr(execution, "paipan_tool", fake_paipan)

    profile = {"node_cache": {}}

    # Run nodes including OVERALL (which will fail) and CAREER (depends on COMMON_PREREQS)
    outputs = run_nodes_parallel(
        profile,
        ["PAIPAN", "OVERALL", "SHISHEN", "GEJU", "WUXING_PREFS", "CAREER"],
        {
            "PAIPAN": {},
            "OVERALL": {"prompt_config": "lingyun_cat"},
            "SHISHEN": {"prompt_config": "lingyun_cat"},
            "GEJU": {"prompt_config": "lingyun_cat"},
            "WUXING_PREFS": {"prompt_config": "lingyun_cat"},
            "CAREER": {"prompt_config": "lingyun_cat"},
        },
    )

    # OVERALL should have failed
    assert outputs["OVERALL"].get("error"), "OVERALL should be marked as error"
    assert not outputs["OVERALL"].get("skipped"), "OVERALL should not be marked as skipped"

    # GEJU depends on OVERALL, should be skipped
    assert outputs["GEJU"].get("error"), "GEJU should be marked as error"
    assert outputs["GEJU"].get("skipped"), "GEJU should be marked as skipped"

    # WUXING_PREFS depends on OVERALL and GEJU, should be skipped
    assert outputs["WUXING_PREFS"].get("error"), "WUXING_PREFS should be marked as error"
    assert outputs["WUXING_PREFS"].get("skipped"), "WUXING_PREFS should be marked as skipped"

    # CAREER depends on COMMON_PREREQS (including OVERALL), should be skipped
    assert outputs["CAREER"].get("error"), "CAREER should be marked as error"
    assert outputs["CAREER"].get("skipped"), "CAREER should be marked as skipped"

    # Only PAIPAN and SHISHEN should have succeeded (they don't depend on OVERALL)
    assert not outputs["PAIPAN"].get("error"), "PAIPAN should succeed"
    assert not outputs["SHISHEN"].get("error"), "SHISHEN should succeed"


def test_error_response_on_critical_failure(monkeypatch) -> None:
    """User should see clean error message, not LLM_ERROR markers."""
    monkeypatch.setenv("LLM_MODE", "stub")
    monkeypatch.setenv("LLM_FORCE_ERROR", "OVERALL")

    # Mock paipan_tool to return valid output
    def fake_paipan(inputs):
        return {
            "paipan_results": "test",
            "liupan_results": "",
            "guji_results": "",
            "paipan_output": {},
            "dayun_list": [],
        }

    monkeypatch.setattr(execution, "paipan_tool", fake_paipan)

    from agent.orchestrator import run_turn
    import datetime as dt

    profile = {
        "user_id": "u_test",
        "birth": {"year": 1990, "month": 1, "day": 1, "hour": 8, "minute": 0, "second": 0},
        "gender": "male",
        "birth_time_unknown": False,
        "prompt_config": "lingyun_cat",
        "node_cache": {},
    }

    result = run_turn(profile, "今年事业如何", now=dt.datetime(2025, 1, 15))

    # Result should indicate error
    assert result.get("error"), "result should indicate error"
    assert result.get("failed_nodes"), "failed_nodes should be present"
    assert "OVERALL" in result["failed_nodes"], "OVERALL should be in failed_nodes"

    # Response should be clean Chinese error message, not raw error markers
    assert "无法完成分析" in result["response"], "response should have clean error message"
    assert "[LLM_ERROR:" not in result["response"], "response should not contain raw error markers"


def test_retry_succeeds_after_previous_failure(monkeypatch) -> None:
    """A node that failed should succeed on retry (not retrieve failed cache)."""
    monkeypatch.setenv("LLM_MODE", "stub")

    profile = {"node_cache": {}}
    inputs = {"prompt_config": "lingyun_cat"}
    inputs_hash = _hash_inputs(inputs)

    # Manually insert a failed cache entry (simulating previous failure)
    profile["node_cache"]["OVERALL"] = {
        "inputs_hash": inputs_hash,
        "output": {
            "type": "error",
            "content": "[LLM_ERROR:OVERALL] previous failure",
            "error": True,
        },
    }

    # Run ensure_node - should retry and succeed (in stub mode)
    output = ensure_node(profile, "OVERALL", inputs)

    # Output should succeed (stub mode returns success)
    assert not output.get("error"), "output should succeed on retry"

    # Cache should now contain successful output
    assert "OVERALL" in profile["node_cache"], "successful output should be cached"
    assert not profile["node_cache"]["OVERALL"]["output"].get("error"), "cached output should not be error"
