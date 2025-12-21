"""Execution layer for nodes with caching."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from typing import Any, Dict, List

from .deps import DEPS, toposort
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


def ensure_node(profile: Dict[str, Any], node: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
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
    if node == "PAIPAN":
        output = paipan_tool(inputs)
    elif node == "TIME_CONTEXT":
        output = time_context_tool(
            inputs.get("paipan_output", {}),
            inputs.get("ref_text", ""),
            inputs.get("now"),
        )
    else:
        prompt_config = inputs.get("prompt_config", "lingyun_cat")
        prompt = build_prompt(node, cache, prompt_config=prompt_config)
        system_prompt = prompt.get("system_prompt", "")
        user_prompt = prompt.get("user_prompt", "")
        sleep_ms = inputs.get("sleep_ms")
        output = llm_report_tool(
            system_prompt,
            user_prompt,
            model=inputs.get("model"),
            node=node,
            sleep_ms=sleep_ms,
        )

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
    return output


def run_nodes(profile: Dict[str, Any], nodes: List[str], inputs: Dict[str, Any]) -> Dict[str, Any]:
    ordered = toposort(nodes, DEPS)
    outputs: Dict[str, Any] = {}
    for node in ordered:
        if node == "TIME_CONTEXT":
            continue
        output = ensure_node(profile, node, inputs.get(node, {}))
        outputs[node] = output
    return outputs


def run_nodes_parallel(profile: Dict[str, Any], nodes: List[str], inputs: Dict[str, Any]) -> Dict[str, Any]:
    ordered = toposort(nodes, DEPS)
    deps = {node: set(DEPS.get(node, [])) for node in ordered}
    remaining = set(ordered)
    done: set[str] = set()
    futures = {}
    outputs: Dict[str, Any] = {}

    max_workers_env = os.environ.get("LLM_PARALLEL_WORKERS")
    if max_workers_env and max_workers_env.isdigit():
        max_workers = max(1, int(max_workers_env))
    else:
        max_workers = min(8, len(ordered) or 1)

    _debug(f"run_nodes_parallel nodes={ordered} max_workers={max_workers}")
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        while remaining or futures:
            ready = [n for n in remaining if deps.get(n, set()).issubset(done)]
            for node in ready:
                remaining.remove(node)
                if node == "TIME_CONTEXT":
                    done.add(node)
                    continue
                _debug(f"submit node {node} deps={deps.get(node, set())}")
                futures[executor.submit(ensure_node, profile, node, inputs.get(node, {}))] = node
            if not futures:
                break
            completed, _ = wait(futures.keys(), return_when=FIRST_COMPLETED)
            for fut in completed:
                node = futures.pop(fut)
                outputs[node] = fut.result()
                done.add(node)
                _debug(f"node future complete {node}")
    return outputs
