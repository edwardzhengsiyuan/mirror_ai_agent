"""Ad-hoc smoke: run_najia_turn(paraphrase=True) end-to-end.

The /v1/najia/ask endpoint does not expose ``paraphrase``. This script calls
``run_najia_turn`` directly with paraphrase=True, captures the event stream,
and asserts:
1. NAJIA_RESPONSE and NAJIA_PARAPHRASE LLM calls both fired (non-stub).
2. Final response text concatenates 占卜结果 / 分析解读 / 通俗解释 sections.
3. No llm_error events.
"""

from __future__ import annotations

import os
import sys
import time
from typing import Any, Dict, List

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from agent.orchestrator_najia import run_najia_turn  # noqa: E402


def main() -> int:
    events: List[Dict[str, Any]] = []
    sink = events.append

    started = time.time()
    result = run_najia_turn(
        question="这个项目三个月内能不能推进成功？",
        yao_values=[0, 1, 2, 3, 4, 5],
        event_sink=sink,
        stream=False,
        paraphrase=True,
    )
    elapsed = time.time() - started

    text = result.get("response", "")
    print(f"[najia/paraphrase] elapsed={elapsed:.1f}s response_len={len(text)}")

    nodes_with_response = sorted(
        {ev.get("node") for ev in events if ev.get("type") == "llm_response"}
    )
    print(f"[events] llm_response nodes: {nodes_with_response}")

    llm_errors = [ev for ev in events if ev.get("type") == "llm_error"]
    if llm_errors:
        print(f"[events] llm_errors={len(llm_errors)} last={llm_errors[-1]}")

    failures: List[str] = []
    if "NAJIA_RESPONSE" not in nodes_with_response:
        failures.append("missing NAJIA_RESPONSE llm_response event")
    if "NAJIA_PARAPHRASE" not in nodes_with_response:
        failures.append("missing NAJIA_PARAPHRASE llm_response event")
    for label in ("占卜结果", "分析解读", "通俗解释"):
        if label not in text:
            failures.append(f"final response missing section header '{label}'")
    if llm_errors:
        failures.append(f"got {len(llm_errors)} llm_error events")
    if any(text.startswith(p) for p in ("[LLM_PLACEHOLDER", "[LLM_ERROR")):
        failures.append("response is stubbed/error placeholder")

    print("\n--- response preview ---")
    print(text[:600] + ("..." if len(text) > 600 else ""))

    if failures:
        print("\n[FAIL] " + "; ".join(failures))
        return 1
    print("\n[PASS] najia paraphrase=True")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
