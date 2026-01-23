"""Conversation event logging."""

from __future__ import annotations

import datetime as dt
import json
import os
from typing import Any, Dict, List


def append_event(path: str, event: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False))
        f.write("\n")


def load_recent_rounds(path: str, max_rounds: int = 5) -> List[Dict[str, str]]:
    """Load recent user+assistant rounds from a conversation log.

    Supports both new 'response' event type and legacy 'assistant_final'.
    """
    if max_rounds <= 0 or not os.path.exists(path):
        return []
    rounds: List[Dict[str, str]] = []
    pending_user: str | None = None
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            etype = event.get("type")
            if etype == "user_message":
                pending_user = event.get("text", "")
            # Support both new 'response' and legacy 'assistant_final'
            elif etype in ("response", "assistant_final"):
                if pending_user is None:
                    continue
                rounds.append({"user": pending_user, "assistant": event.get("text", "")})
                pending_user = None
    if not rounds:
        return []
    return rounds[-max_rounds:]


def load_latest_llm_prompts(path: str) -> Dict[str, Dict[str, str]]:
    """Return latest LLM prompts per node from a conversation log."""
    if not os.path.exists(path):
        return {}
    latest: Dict[str, Dict[str, str]] = {}
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if event.get("type") != "llm_prompt":
                continue
            node = event.get("node")
            if not node:
                continue
            latest[str(node)] = {
                "system_prompt": event.get("system_prompt", ""),
                "user_prompt": event.get("user_prompt", ""),
            }
    return latest


def load_tool_invocations(
    path: str,
    tool: str | None = None,
) -> List[Dict[str, Any]]:
    """Load all tool invocations from a conversation log.

    Args:
        path: Path to the conversation JSONL file
        tool: Optional filter by tool name (PLANNER, TIME_CONTEXT)

    Returns:
        List of tool invocation events
    """
    if not os.path.exists(path):
        return []
    invocations: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if event.get("type") != "tool_invocation":
                continue
            if tool and event.get("tool") != tool:
                continue
            invocations.append(event)
    return invocations


def load_responses(path: str) -> List[Dict[str, Any]]:
    """Load all response events from a conversation log.

    Returns:
        List of response events (type='response')
    """
    if not os.path.exists(path):
        return []
    responses: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            # Support both new 'response' and legacy 'assistant_final'
            if event.get("type") in ("response", "assistant_final"):
                responses.append(event)
    return responses


def load_llm_traces(
    path: str,
    node: str | None = None,
) -> List[Dict[str, Any]]:
    """Load LLM request/response/error events from a conversation log.

    Args:
        path: Path to the conversation JSONL file
        node: Optional filter by node name (PLANNER, RESPONSE, CAREER, etc.)

    Returns:
        List of LLM trace events (llm_request, llm_response, llm_error)
    """
    if not os.path.exists(path):
        return []
    trace_types = ("llm_request", "llm_response", "llm_error")
    traces: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if event.get("type") not in trace_types:
                continue
            if node and event.get("node") != node:
                continue
            traces.append(event)
    return traces


def log_event_to_conversation(
    path: str,
    event: Dict[str, Any],
    ts: str | None = None,
) -> None:
    """Log a streaming event to conversation JSONL.

    Shared by web server and tests. Handles all standard event types:
    - llm_prompt: LLM call prompts (system/user) per node
    - llm_request: LLM API request details (always-on tracing)
    - llm_response: LLM API response (always-on tracing)
    - llm_error: LLM API errors (always-on tracing)
    - tool_invocation: Conversation-level tool calls (PLANNER, TIME_CONTEXT)
    - response: Final response generation

    Args:
        path: Path to the conversation JSONL file
        event: The event dict from event_sink callback
        ts: Optional timestamp override (defaults to now)
    """
    event_type = event.get("type")
    timestamp = ts or dt.datetime.now().isoformat()

    if event_type == "llm_prompt":
        append_event(path, {
            "ts": timestamp,
            "type": "llm_prompt",
            "node": event.get("node"),
            "system_prompt": event.get("system_prompt", ""),
            "user_prompt": event.get("user_prompt", ""),
        })
    elif event_type == "llm_request":
        append_event(path, {
            "ts": timestamp,
            "type": "llm_request",
            "node": event.get("node"),
            "model": event.get("model"),
            "attempt": event.get("attempt"),
            "url": event.get("url"),
            "timeout_seconds": event.get("timeout_seconds"),
            "system_prompt": event.get("system_prompt"),
            "user_prompt": event.get("user_prompt"),
            "stub": event.get("stub"),
        })
    elif event_type == "llm_response":
        append_event(path, {
            "ts": timestamp,
            "type": "llm_response",
            "node": event.get("node"),
            "model": event.get("model"),
            "content": event.get("content"),
            "reasoning_content": event.get("reasoning_content"),
            "raw": event.get("raw"),
            "duration_ms": event.get("duration_ms"),
            "stub": event.get("stub"),
        })
    elif event_type == "llm_error":
        append_event(path, {
            "ts": timestamp,
            "type": "llm_error",
            "node": event.get("node"),
            "model": event.get("model"),
            "attempt": event.get("attempt"),
            "error": event.get("error"),
            "error_type": event.get("error_type"),
        })
    elif event_type == "tool_invocation":
        append_event(path, {
            "ts": timestamp,
            "type": "tool_invocation",
            "tool": event.get("tool"),
            "invocation_id": event.get("invocation_id"),
            "input": event.get("input"),
            "output": event.get("output"),
            "duration_ms": event.get("duration_ms"),
            "llm_prompt": event.get("llm_prompt"),
        })
    elif event_type == "response":
        append_event(path, {
            "ts": timestamp,
            "type": "response",
            "text": event.get("text"),
            "input_summary": event.get("input_summary"),
            "llm_prompt": event.get("llm_prompt"),
            "duration_ms": event.get("duration_ms"),
        })
