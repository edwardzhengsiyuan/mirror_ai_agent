from __future__ import annotations

import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, ROOT)

from agent import execution
from agent.execution import ensure_node


def test_inflight_isolated_across_profiles(monkeypatch) -> None:
    calls: list[int] = []

    def fake_paipan(inputs):
        time.sleep(0.1)
        year = int(inputs.get("birth", {}).get("year", 0))
        calls.append(year)
        return {
            "paipan_results": str(year),
            "liupan_results": "",
            "guji_results": "",
            "paipan_output": {},
        }

    monkeypatch.setattr(execution, "paipan_tool", fake_paipan)

    profile_a = {"user_id": "u_a", "node_cache": {}}
    profile_b = {"user_id": "u_b", "node_cache": {}}

    inputs_a = {
        "birth": {"year": 1990, "month": 1, "day": 1},
        "gender": "male",
        "birth_time_unknown": False,
    }
    inputs_b = {
        "birth": {"year": 2000, "month": 1, "day": 1},
        "gender": "female",
        "birth_time_unknown": False,
    }

    with ThreadPoolExecutor(max_workers=2) as executor:
        fut_a = executor.submit(ensure_node, profile_a, "PAIPAN", inputs_a)
        fut_b = executor.submit(ensure_node, profile_b, "PAIPAN", inputs_b)
        out_a = fut_a.result()
        out_b = fut_b.result()

    assert out_a["paipan_results"] == "1990"
    assert out_b["paipan_results"] == "2000"
    assert len(calls) == 2
