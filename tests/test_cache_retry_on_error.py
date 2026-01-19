from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, ROOT)

from agent import execution
from agent.execution import ensure_node


def test_retry_when_cached_error(monkeypatch) -> None:
    monkeypatch.setenv("LLM_MODE", "stub")
    profile = {"node_cache": {}}
    inputs = {"prompt_config": "lingyun_cat"}

    # Seed cache with an errored output (simulated failure)
    inputs_hash = execution._hash_inputs(inputs)
    profile["node_cache"]["OVERALL"] = {
        "inputs_hash": inputs_hash,
        "output": {
            "type": "report",
            "content": "[LLM_ERROR:OVERALL] simulated failure",
            "structured": {"node": "OVERALL", "summary": "error"},
            "reasoning_content": "",
            "error": True,
        },
    }

    output = ensure_node(profile, "OVERALL", inputs)
    assert not output.get("error"), "failed output should be retried and replaced"
    assert profile["node_cache"]["OVERALL"]["inputs_hash"] == inputs_hash
