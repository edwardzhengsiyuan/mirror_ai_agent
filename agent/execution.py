"""Execution layer for nodes with caching."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from typing import Any, Dict, List, Optional, Tuple

from .deps import DEPS, CONVERSATION_TOOLS, toposort
from .events import EventSink, emit_event, emit_text_chunks
from .nodes.prompt_builder import build_prompt, build_response_prompt
from .planning import plan
from .tools.llm_tool import llm_report_tool
from .tools.paipan_tool import paipan_tool
from .tools.time_context_tool import time_context_tool

_LOCK = threading.Lock()
_IN_FLIGHT: Dict[tuple, threading.Event] = {}


def _debug(msg: str) -> None:
    if os.environ.get("LLM_DEBUG", "").lower() not in ("1", "true", "yes"):
        return
    ts = dt.datetime.now(dt.UTC).isoformat().replace("+00:00", "Z")
    print(f"[DEBUG execution] {ts} {msg}", flush=True)


def _hash_inputs(inputs: Dict[str, Any]) -> str:
    payload = json.dumps(inputs, ensure_ascii=True, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _profile_scope(profile: Dict[str, Any]) -> str:
    return f"obj:{id(profile)}"


def _inflight_key(profile: Dict[str, Any], node: str, inputs_hash: str) -> tuple:
    return (_profile_scope(profile), node, inputs_hash)


def _is_failure_output(output: Any) -> bool:
    if not isinstance(output, dict):
        return False
    if output.get("error"):
        return True
    content = output.get("content", "")
    return isinstance(content, str) and content.startswith("[LLM_ERROR:")


def _error_output(node: str, exc: Exception) -> Dict[str, Any]:
    return {
        "type": "error",
        "content": f"[NODE_ERROR:{node}] {exc}",
        "structured": {"node": node, "summary": "node error"},
        "reasoning_content": "",
        "error": True,
    }


def _format_tool_output(node: str, output: Dict[str, Any]) -> str:
    if node == "PAIPAN":
        parts = [
            output.get("paipan_results", ""),
            output.get("liupan_results", ""),
            output.get("guji_results", ""),
        ]
        return "\n".join([p for p in parts if p])
    if node == "TIME_CONTEXT":
        return json.dumps(output, ensure_ascii=False, indent=2)
    return json.dumps(output, ensure_ascii=False, indent=2)


def ensure_node(
    profile: Dict[str, Any],
    node: str,
    inputs: Dict[str, Any],
    event_sink: Optional[EventSink] = None,
    stream: bool = False,
) -> Dict[str, Any]:
    cache = profile.setdefault("node_cache", {})
    inputs_hash = _hash_inputs(inputs)
    inflight_key = _inflight_key(profile, node, inputs_hash)
    with _LOCK:
        if node in cache and cache[node].get("inputs_hash") == inputs_hash:
            cached_output = cache[node]["output"]
            if _is_failure_output(cached_output):
                _debug(f"cache contains failure for {node}, will retry hash={inputs_hash[:8]}")
                cache.pop(node, None)
            else:
                _debug(f"cache hit for {node} hash={inputs_hash[:8]}")
                emit_event(
                    event_sink,
                    {
                        "type": "node_cache_hit",
                        "node": node,
                        "inputs_hash": inputs_hash,
                        "output": cached_output,
                    },
                )
                emit_event(
                    event_sink,
                    {
                        "type": "node_end",
                        "node": node,
                        "output": cached_output,
                        "cached": True,
                    },
                )
                return cached_output
        if inflight_key in _IN_FLIGHT:
            event = _IN_FLIGHT[inflight_key]
            _debug(f"waiting on inflight node {node} hash={inputs_hash[:8]}")
        else:
            event = threading.Event()
            _IN_FLIGHT[inflight_key] = event
            _debug(f"start node {node} hash={inputs_hash[:8]}")
            event = None
    if event is not None:
        event.wait()
        with _LOCK:
            _debug(f"join inflight node {node} hash={inputs_hash[:8]}")
            cached_entry = cache.get(node)
            if cached_entry and cached_entry.get("inputs_hash") == inputs_hash:
                return cached_entry.get("output")
        return _error_output(node, RuntimeError("inflight completed without cached output"))

    started_at = dt.datetime.now(dt.UTC).isoformat().replace("+00:00", "Z")
    started_ts = time.perf_counter()
    emit_event(
        event_sink,
        {
            "type": "node_start",
            "node": node,
            "inputs_hash": inputs_hash,
        },
    )
    output: Any
    try:
        if node == "PAIPAN":
            emit_event(event_sink, {"type": "tool_call", "tool": "paipan_tool", "node": node})
            output = paipan_tool(inputs)
            emit_event(event_sink, {"type": "tool_result", "tool": "paipan_tool", "node": node})
            if stream:
                emit_text_chunks(
                    _format_tool_output(node, output),
                    lambda delta: emit_event(event_sink, {"type": "node_delta", "node": node, "delta": delta}),
                )
        elif node == "TIME_CONTEXT":
            emit_event(event_sink, {"type": "tool_call", "tool": "time_context_tool", "node": node})
            output = time_context_tool(
                requests=inputs.get("requests", []),
                birth=inputs.get("birth", {}),
                gender=inputs.get("gender", "male"),
                birth_time_unknown=inputs.get("birth_time_unknown", False),
            )
            emit_event(event_sink, {"type": "tool_result", "tool": "time_context_tool", "node": node})
            if output and stream:
                emit_text_chunks(
                    _format_tool_output(node, output),
                    lambda delta: emit_event(event_sink, {"type": "node_delta", "node": node, "delta": delta}),
                )
        else:
            prompt_config = inputs.get("prompt_config", "lingyun_cat")
            prompt = build_prompt(
                node,
                cache,
                prompt_config=prompt_config,
                question=inputs.get("question"),
                history_rounds=inputs.get("history_rounds"),
            )
            system_prompt = prompt.get("system_prompt", "")
            user_prompt = prompt.get("user_prompt", "")
            sleep_ms = inputs.get("sleep_ms")
            emit_event(
                event_sink,
                {
                    "type": "llm_prompt",
                    "node": node,
                    "system_prompt": system_prompt,
                    "user_prompt": user_prompt,
                },
            )
            emit_event(event_sink, {"type": "tool_call", "tool": "llm_report_tool", "node": node})
            output = llm_report_tool(
                system_prompt,
                user_prompt,
                model=inputs.get("model"),
                node=node,
                sleep_ms=sleep_ms,
                stream=stream,
                on_delta=(
                    lambda chunk: emit_event(
                        event_sink,
                        {
                            "type": "node_delta",
                            "node": node,
                            "delta": chunk.get("content", ""),
                            "reasoning_delta": chunk.get("reasoning_content", ""),
                        },
                    )
                )
                if event_sink
                else None,
            )
            emit_event(event_sink, {"type": "tool_result", "tool": "llm_report_tool", "node": node})
    except Exception as exc:
        _debug(f"node {node} error: {exc}")
        output = _error_output(node, exc)

    ended_at = dt.datetime.now(dt.UTC).isoformat().replace("+00:00", "Z")
    duration_ms = int((time.perf_counter() - started_ts) * 1000)
    entry = {
        "created_at": dt.datetime.now(dt.UTC).isoformat().replace("+00:00", "Z"),
        "inputs_hash": inputs_hash,
        "output": output,
        "meta": {
            "started_at": started_at,
            "ended_at": ended_at,
            "duration_ms": duration_ms,
        },
    }
    with _LOCK:
        cache[node] = entry
        inflight = _IN_FLIGHT.pop(inflight_key, None)
        if inflight:
            inflight.set()
    summary = list(output.keys()) if isinstance(output, dict) else type(output).__name__
    _debug(f"completed node {node} duration={duration_ms}ms output_keys={summary}")
    emit_event(
        event_sink,
        {
            "type": "node_end",
            "node": node,
            "output": output,
            "duration_ms": duration_ms,
        },
    )
    return output


def run_tool(
    tool_name: str,
    inputs: Dict[str, Any],
    event_sink: Optional[EventSink] = None,
    stream: bool = False,
) -> Tuple[Dict[str, Any], str, int, Optional[Dict[str, str]]]:
    """Execute a conversation-level tool (no caching).

    Tools like PLANNER and TIME_CONTEXT are conversation-level operations
    that should not be cached in profile.node_cache. Each invocation is
    recorded independently in the conversation JSONL.

    Args:
        tool_name: Either "PLANNER" or "TIME_CONTEXT"
        inputs: Tool-specific inputs
        event_sink: Optional event sink for streaming
        stream: Whether to stream output

    Returns:
        Tuple of (output, invocation_id, duration_ms, llm_prompt)
        - output: The tool's output dict
        - invocation_id: Unique ID for this invocation
        - duration_ms: Execution duration in milliseconds
        - llm_prompt: The LLM prompt used (if applicable), or None
    """
    if tool_name not in CONVERSATION_TOOLS:
        raise ValueError(f"Unknown conversation tool: {tool_name}. Must be one of {CONVERSATION_TOOLS}")

    invocation_id = f"inv_{uuid.uuid4().hex[:12]}"
    started_ts = time.perf_counter()
    llm_prompt: Optional[Dict[str, str]] = None
    output: Dict[str, Any]

    _debug(f"run_tool {tool_name} invocation_id={invocation_id}")

    try:
        if tool_name == "PLANNER":
            emit_event(event_sink, {"type": "tool_call", "tool": "planner", "invocation_id": invocation_id})
            output = plan(
                question=inputs.get("question", ""),
                now=inputs.get("now"),
                dayun_list=inputs.get("dayun_list", []),
                event_sink=event_sink,
                stream=stream,
            )
            emit_event(event_sink, {"type": "tool_result", "tool": "planner", "invocation_id": invocation_id})
        elif tool_name == "TIME_CONTEXT":
            emit_event(event_sink, {"type": "tool_call", "tool": "time_context_tool", "invocation_id": invocation_id})
            output = time_context_tool(
                requests=inputs.get("requests", []),
                birth=inputs.get("birth", {}),
                gender=inputs.get("gender", "male"),
                birth_time_unknown=inputs.get("birth_time_unknown", False),
            )
            emit_event(event_sink, {"type": "tool_result", "tool": "time_context_tool", "invocation_id": invocation_id})
        else:
            output = {"error": f"Unknown tool: {tool_name}"}
    except Exception as exc:
        _debug(f"run_tool {tool_name} error: {exc}")
        output = {"error": str(exc)}

    duration_ms = int((time.perf_counter() - started_ts) * 1000)
    _debug(f"run_tool {tool_name} completed duration={duration_ms}ms")

    return output, invocation_id, duration_ms, llm_prompt


def run_response(
    profile: Dict[str, Any],
    inputs: Dict[str, Any],
    event_sink: Optional[EventSink] = None,
    stream: bool = False,
) -> Tuple[Dict[str, Any], int, Dict[str, str]]:
    """Generate final response (no caching).

    Response is a conversation-level entity that should not be cached
    in profile.node_cache. Each response is recorded independently
    in the conversation JSONL.

    Args:
        profile: User profile with node_cache
        inputs: Should contain:
            - prompt_config: str
            - question: str
            - history_rounds: list
            - time_context: dict (passed directly, not from cache)
            - model: optional model override

    Returns:
        Tuple of (output, duration_ms, llm_prompt)
        - output: The LLM response output dict
        - duration_ms: Execution duration in milliseconds
        - llm_prompt: The LLM prompt used
    """
    cache = profile.get("node_cache", {})
    prompt_config = inputs.get("prompt_config", "lingyun_cat")
    question = inputs.get("question")
    history_rounds = inputs.get("history_rounds")
    time_context = inputs.get("time_context")
    model = inputs.get("model")

    started_ts = time.perf_counter()

    prompt = build_response_prompt(
        cache,
        time_context=time_context,
        prompt_config=prompt_config,
        question=question,
        history_rounds=history_rounds,
    )
    system_prompt = prompt.get("system_prompt", "")
    user_prompt = prompt.get("user_prompt", "")
    llm_prompt = {"system_prompt": system_prompt, "user_prompt": user_prompt}

    emit_event(
        event_sink,
        {
            "type": "llm_prompt",
            "node": "RESPONSE",
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
        },
    )

    _debug("run_response calling llm_report_tool")
    emit_event(event_sink, {"type": "tool_call", "tool": "llm_report_tool", "node": "RESPONSE"})

    try:
        output = llm_report_tool(
            system_prompt,
            user_prompt,
            model=model,
            node="RESPONSE",
            stream=stream,
            on_delta=(
                lambda chunk: emit_event(
                    event_sink,
                    {
                        "type": "response_delta",
                        "delta": chunk.get("content", ""),
                        "reasoning_delta": chunk.get("reasoning_content", ""),
                    },
                )
            )
            if event_sink
            else None,
        )
    except Exception as exc:
        _debug(f"run_response error: {exc}")
        output = {
            "type": "error",
            "content": f"[RESPONSE_ERROR] {exc}",
            "error": True,
        }

    emit_event(event_sink, {"type": "tool_result", "tool": "llm_report_tool", "node": "RESPONSE"})

    duration_ms = int((time.perf_counter() - started_ts) * 1000)
    _debug(f"run_response completed duration={duration_ms}ms")

    return output, duration_ms, llm_prompt


def run_nodes(
    profile: Dict[str, Any],
    nodes: List[str],
    inputs: Dict[str, Any],
    event_sink: Optional[EventSink] = None,
    stream: bool = False,
    skip_nodes: Optional[set[str]] = None,
) -> Dict[str, Any]:
    ordered = toposort(nodes, DEPS)
    outputs: Dict[str, Any] = {}
    skip_nodes = skip_nodes or set()
    for node in ordered:
        if node == "TIME_CONTEXT":
            continue
        if node in skip_nodes:
            cached = profile.get("node_cache", {}).get(node, {}).get("output")
            if cached is not None:
                outputs[node] = cached
            continue
        output = ensure_node(profile, node, inputs.get(node, {}), event_sink=event_sink, stream=stream)
        outputs[node] = output
    return outputs


def run_nodes_parallel(
    profile: Dict[str, Any],
    nodes: List[str],
    inputs: Dict[str, Any],
    event_sink: Optional[EventSink] = None,
    stream: bool = False,
    skip_nodes: Optional[set[str]] = None,
    precomputed_outputs: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    ordered = toposort(nodes, DEPS)
    deps = {node: set(DEPS.get(node, [])) for node in ordered}
    remaining = set(ordered)
    done: set[str] = set()
    futures = {}
    outputs: Dict[str, Any] = dict(precomputed_outputs or {})
    skip_nodes = skip_nodes or set()

    max_workers_env = os.environ.get("LLM_PARALLEL_WORKERS")
    if max_workers_env and max_workers_env.isdigit():
        max_workers = max(1, int(max_workers_env))
    else:
        max_workers = min(8, len(ordered) or 1)

    _debug(f"run_nodes_parallel nodes={ordered} max_workers={max_workers}")
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        while remaining or futures:
            ready = [n for n in remaining if deps.get(n, set()).issubset(done)]
            if not ready and not futures:
                break
            for node in ready:
                remaining.remove(node)
                if node == "TIME_CONTEXT":
                    done.add(node)
                    continue
                if node in skip_nodes:
                    if node not in outputs:
                        cached = profile.get("node_cache", {}).get(node, {}).get("output")
                        if cached is not None:
                            outputs[node] = cached
                    done.add(node)
                    continue
                _debug(f"submit node {node} deps={deps.get(node, set())}")
                futures[
                    executor.submit(
                        ensure_node,
                        profile,
                        node,
                        inputs.get(node, {}),
                        event_sink,
                        stream,
                    )
                ] = node
            if not futures:
                continue
            completed, _ = wait(futures.keys(), return_when=FIRST_COMPLETED)
            for fut in completed:
                node = futures.pop(fut)
                outputs[node] = fut.result()
                done.add(node)
                _debug(f"node future complete {node}")
    return outputs
