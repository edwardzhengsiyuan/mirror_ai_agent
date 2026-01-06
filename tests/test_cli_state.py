from __future__ import annotations

import sys
import os

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, ROOT)

from agent.ui.state import ChatState, apply_event


def test_apply_event_updates_state() -> None:
    state = ChatState(node_order=["PAIPAN", "OVERALL"])

    apply_event(state, {"type": "node_start", "node": "OVERALL"})
    assert state.nodes["OVERALL"].status == "running"

    apply_event(state, {"type": "node_delta", "node": "OVERALL", "delta": "hello"})
    assert "hello" in state.nodes["OVERALL"].output

    apply_event(
        state,
        {
            "type": "node_end",
            "node": "OVERALL",
            "output": {"type": "report", "content": "final content"},
        },
    )
    assert state.nodes["OVERALL"].status == "done"
    assert "final content" in state.nodes["OVERALL"].output

    apply_event(state, {"type": "tool_call", "tool": "paipan_tool", "node": "PAIPAN"})
    assert state.system_log[-1].startswith("tool_call")
