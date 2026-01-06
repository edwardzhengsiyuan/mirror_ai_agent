"""State helpers for the CLI chatbot UI."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class NodeState:
    name: str
    status: str = "idle"
    output: str = ""
    expanded: bool = False


@dataclass
class ChatState:
    node_order: List[str]
    nodes: Dict[str, NodeState] = field(default_factory=dict)
    selected_index: int = 0
    view_mode: str = "nodes"
    running: bool = False
    messages: List[Dict[str, str]] = field(default_factory=list)
    system_log: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.nodes:
            self.nodes = {name: NodeState(name=name) for name in self.node_order}


def _format_output(node: str, output: Any) -> str:
    if output is None:
        return ""
    if node == "PAIPAN" and isinstance(output, dict):
        parts = [
            output.get("paipan_results", ""),
            output.get("liupan_results", ""),
            output.get("guji_results", ""),
        ]
        return "\n".join([p for p in parts if p])
    if node == "TIME_CONTEXT":
        try:
            return json.dumps(output, ensure_ascii=False, indent=2)
        except TypeError:
            return str(output)
    if isinstance(output, dict):
        content = output.get("content")
        if isinstance(content, str):
            return content
        try:
            return json.dumps(output, ensure_ascii=False, indent=2)
        except TypeError:
            return str(output)
    return str(output)


def apply_event(state: ChatState, event: Dict[str, Any]) -> None:
    etype = event.get("type")
    if etype == "user_message":
        state.messages.append({"role": "user", "text": event.get("text", "")})
        return
    if etype == "assistant_final":
        state.messages.append({"role": "assistant", "text": event.get("text", "")})
        state.running = False
        return
    if etype == "plan":
        plan = event.get("plan", {})
        aspects = ",".join(plan.get("aspects", []))
        time = plan.get("time", {})
        ref = time.get("ref_text") or ""
        state.system_log.append(f"plan: aspects={aspects} time={time.get('granularity')} {ref}".strip())
        return
    if etype == "tool_call":
        tool = event.get("tool", "")
        node = event.get("node", "")
        state.system_log.append(f"tool_call: {tool} ({node})")
        return
    if etype == "tool_result":
        tool = event.get("tool", "")
        node = event.get("node", "")
        state.system_log.append(f"tool_result: {tool} ({node})")
        return
    if etype == "time_context":
        matched = "matched" if event.get("value") else "none"
        state.system_log.append(f"time_context: {matched}")
        return
    if etype == "node_start":
        node = event.get("node", "")
        if node in state.nodes:
            state.nodes[node].status = "running"
            state.nodes[node].output = ""
        state.running = True
        return
    if etype == "node_cache_hit":
        node = event.get("node", "")
        output = event.get("output")
        if node in state.nodes:
            state.nodes[node].status = "cache"
            formatted = _format_output(node, output)
            if formatted:
                state.nodes[node].output = formatted
        return
    if etype == "node_delta":
        node = event.get("node", "")
        delta = event.get("delta", "")
        if node in state.nodes and delta:
            state.nodes[node].output += delta
        return
    if etype == "node_end":
        node = event.get("node", "")
        output = event.get("output")
        if node in state.nodes:
            status = "done"
            if isinstance(output, dict) and output.get("error"):
                status = "error"
            if event.get("cached"):
                status = "cache"
            state.nodes[node].status = status
            formatted = _format_output(node, output)
            if formatted:
                if not state.nodes[node].output:
                    state.nodes[node].output = formatted
                elif formatted not in state.nodes[node].output:
                    if len(formatted) >= len(state.nodes[node].output):
                        state.nodes[node].output = formatted
        return
