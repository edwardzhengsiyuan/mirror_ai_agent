"""Parallel execution tests."""

from __future__ import annotations

import os
import sys
import os
import time

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, ROOT)

from agent.execution import run_nodes_parallel, _hash_inputs


def build_profile(paipan_inputs: dict) -> dict:
    inputs_hash = _hash_inputs(paipan_inputs)
    return {
        "node_cache": {
            "PAIPAN": {
                "created_at": "2025-01-01T00:00:00Z",
                "inputs_hash": inputs_hash,
                "output": {
                    "paipan_results": "dummy",
                    "liupan_results": "dummy",
                    "guji_results": "dummy",
                    "paipan_output": {},
                },
                "meta": {},
            }
        }
    }


def main() -> None:
    os.environ["LLM_MODE"] = "stub"
    paipan_inputs = {
        "birth": {"year": 1990, "month": 1, "day": 1, "hour": 8, "minute": 0, "second": 0},
        "gender": "male",
        "birth_time_unknown": False,
    }
    profile = build_profile(paipan_inputs)

    inputs = {
        "PAIPAN": paipan_inputs,
        "OVERALL": {"prompt_config": "lingyun_cat", "sleep_ms": 50},
        "SHISHEN": {"prompt_config": "lingyun_cat", "sleep_ms": 50},
        "GEJU": {"prompt_config": "lingyun_cat", "sleep_ms": 50},
        "WUXING_PREFS": {"prompt_config": "lingyun_cat", "sleep_ms": 50},
        "CAREER": {"prompt_config": "lingyun_cat", "sleep_ms": 300},
        "RELATIONSHIP": {"prompt_config": "lingyun_cat", "sleep_ms": 300},
        "HEALTH": {"prompt_config": "lingyun_cat", "sleep_ms": 300},
    }

    nodes = ["CAREER", "RELATIONSHIP", "HEALTH"]

    start = time.perf_counter()
    outputs = run_nodes_parallel(profile, nodes, inputs)
    elapsed = time.perf_counter() - start

    assert "CAREER" in outputs and "RELATIONSHIP" in outputs and "HEALTH" in outputs
    assert elapsed < 1.2, f"parallel run too slow: {elapsed:.2f}s"

    start2 = time.perf_counter()
    outputs2 = run_nodes_parallel(profile, nodes, inputs)
    elapsed2 = time.perf_counter() - start2
    assert elapsed2 < 0.3, f"cache hit run too slow: {elapsed2:.2f}s"

    assert outputs2["CAREER"]["structured"]["node"] == "CAREER"
    assert outputs2["RELATIONSHIP"]["structured"]["node"] == "RELATIONSHIP"
    assert outputs2["HEALTH"]["structured"]["node"] == "HEALTH"

    print("parallel execution ok")


if __name__ == "__main__":
    main()
