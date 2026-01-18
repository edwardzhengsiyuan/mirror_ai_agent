"""Execution layer for nodes with caching."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from typing import Any, Dict, List, Optional

from .deps import DEPS, toposort
from .events import EventSink, emit_event, emit_text_chunks
from .nodes.prompt_builder import build_prompt
from .tools.llm_tool import llm_report_tool
from .tools.paipan_tool import paipan_tool
from .tools.time_context_tool import time_context_tool

_LOCK = threading.Lock()
_IN_FLIGHT: Dict[str, threading.Event] = {}


def _debug(msg: str) -> None:
    if os.environ.get("LLM_DEBUG", "").lower() not in ("1", "true", "yes"):
        return
    ts = dt.datetime.utcnow().isoformat() + "Z"
    print(f"[DEBUG execution] {ts} {msg}", flush=True)


def _hash_inputs(inputs: Dict[str, Any]) -> str:
    payload = json.dumps(inputs, ensure_ascii=True, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _is_failure_output(output: Any) -> bool:
    if not isinstance(output, dict):
        return False
    if output.get("error"):
        return True
    content = output.get("content", "")
    return isinstance(content, str) and content.startswith("[LLM_ERROR:")


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
        if node in _IN_FLIGHT:
            event = _IN_FLIGHT[node]
            _debug(f"waiting on inflight node {node}")
        else:
            event = threading.Event()
            _IN_FLIGHT[node] = event
            _debug(f"start node {node} hash={inputs_hash[:8]}")
            event = None
    if event is not None:
        event.wait()
        with _LOCK:
            _debug(f"join inflight node {node} hash={inputs_hash[:8]}")
            return cache[node]["output"]

    started_at = dt.datetime.utcnow().isoformat() + "Z"
    started_ts = time.perf_counter()
    emit_event(
        event_sink,
        {
            "type": "node_start",
            "node": node,
            "inputs_hash": inputs_hash,
        },
    )
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
            inputs.get("dayun_list", []),
            inputs.get("liunian_list", []),
            inputs.get("ref_text", ""),
            inputs.get("now"),
            target_year=inputs.get("target_year"),
            target_month=inputs.get("target_month"),
            target_dayun=inputs.get("target_dayun"),
            liuyue_by_year=inputs.get("liuyue_by_year"),
            requests=inputs.get("requests"),
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

    ended_at = dt.datetime.utcnow().isoformat() + "Z"
    duration_ms = int((time.perf_counter() - started_ts) * 1000)
    entry = {
        "created_at": dt.datetime.utcnow().isoformat() + "Z",
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
        inflight = _IN_FLIGHT.pop(node, None)
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
