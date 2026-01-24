"""LLM tool with real API call and stub fallback."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from typing import Any, Callable, Dict, Optional

from ..events import EventSink, emit_event

_TRACE_NAMES = ("1", "true", "yes")


def _load_env_file(path: str) -> None:
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip("\"").strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


def _env(name: str, default: Optional[str] = None) -> Optional[str]:
    return os.environ.get(name, default)


def _env_any(names: list[str], default: Optional[str] = None) -> Optional[str]:
    for name in names:
        value = os.environ.get(name)
        if value:
            return value
    return default


def _stub_response(node_label: str) -> Dict[str, Any]:
    content = (
        f"[LLM_PLACEHOLDER:{node_label}] "
        "This is a stubbed report for local testing."
    )
    structured = {
        "node": node_label,
        "summary": f"Placeholder summary for {node_label}.",
        "bullets": [
            "This is a deterministic dummy output.",
            "Replace llm_report_tool with a real LLM call later.",
        ],
    }
    return {
        "type": "report",
        "content": content,
        "structured": structured,
        "reasoning_content": None,
        "stub": True,
        "error": False,
    }


def _debug(msg: str) -> None:
    if os.environ.get("LLM_DEBUG", "").lower() not in _TRACE_NAMES:
        return
    ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    print(f"[DEBUG llm_tool] {ts} {msg}", flush=True)


def _trace_raw_enabled() -> bool:
    """Check if raw API response should be included in trace events."""
    return os.environ.get("LLM_TRACE_RAW", "").lower() in _TRACE_NAMES


def _emit_stub_stream(content: str, on_delta: Callable[[Dict[str, str]], None]) -> None:
    chunk_size = 120
    for idx in range(0, len(content), chunk_size):
        on_delta({"content": content[idx : idx + chunk_size], "reasoning_content": ""})


def _stream_sse_response(
    resp: Any, on_delta: Optional[Callable[[Dict[str, str]], None]]
) -> tuple[str, str]:
    content_parts: list[str] = []
    reasoning_parts: list[str] = []
    for raw_line in resp:
        line = raw_line.decode("utf-8").strip()
        if not line or not line.startswith("data:"):
            continue
        data = line[len("data:") :].strip()
        if data == "[DONE]":
            break
        try:
            payload = json.loads(data)
        except json.JSONDecodeError:
            continue
        choice = (payload.get("choices") or [{}])[0]
        delta = choice.get("delta") or {}
        content_delta = delta.get("content") or ""
        reasoning_delta = delta.get("reasoning") or delta.get("reasoning_content") or ""
        if content_delta:
            content_parts.append(content_delta)
        if reasoning_delta:
            reasoning_parts.append(reasoning_delta)
        if on_delta and (content_delta or reasoning_delta):
            on_delta({"content": content_delta, "reasoning_content": reasoning_delta})
    return "".join(content_parts), "".join(reasoning_parts)


def llm_report_tool(
    system_prompt: str,
    user_prompt: str,
    model: str | None = None,
    node: str | None = None,
    sleep_ms: int | None = None,
    stream: bool = False,
    on_delta: Callable[[Dict[str, str]], None] | None = None,
    event_sink: EventSink | None = None,
) -> Dict[str, Any]:
    """LLM call with stub fallback for local testing.

    Args:
        system_prompt: System prompt for the LLM
        user_prompt: User prompt for the LLM
        model: Model name override (default: LLM_MODEL or DEFAULT_MODEL)
        node: Node label for logging/tracing
        sleep_ms: Optional delay before call
        stream: Enable streaming response
        on_delta: Callback for streaming chunks
        event_sink: Event sink for LLM tracing (llm_request/response/error events)

    Returns:
        Dict with content, structured, reasoning_content, error fields
    """
    if sleep_ms:
        time.sleep(sleep_ms / 1000.0)
    node_label = node or "UNKNOWN"
    call_started_ts = time.perf_counter()

    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    _load_env_file(os.path.join(repo_root, ".env"))

    from ..models import DEFAULT_MODEL
    model_name = model or _env("LLM_MODEL", DEFAULT_MODEL)

    force_error = _env("LLM_FORCE_ERROR", "")
    force_error_set = {n.strip().upper() for n in force_error.split(",") if n.strip()}
    if "ALL" in force_error_set or node_label.upper() in force_error_set:
        err_msg = f"[LLM_ERROR:{node_label}] forced error via LLM_FORCE_ERROR"
        emit_event(
            event_sink,
            {
                "type": "llm_error",
                "node": node_label,
                "model": model_name,
                "attempt": 1,
                "error": err_msg,
                "error_type": "ForcedError",
            },
        )
        return {
            "type": "report",
            "content": err_msg,
            "structured": {"node": node_label, "summary": "LLM forced error"},
            "reasoning_content": "",
            "error": True,
        }

    mode = _env("LLM_MODE", "auto")
    api_base = _env_any(["LLM_API_BASE", "OPENAI_API_BASE"])
    api_key = _env_any(["LLM_API_KEY", "OPENAI_API_KEY"])
    if mode == "stub" or not api_base or not api_key:
        _debug(
            f"stub response for {node_label} mode={mode} api_base={api_base} "
            f"api_key={'set' if api_key else 'missing'}"
        )
        # Emit llm_request event for stub mode
        emit_event(
            event_sink,
            {
                "type": "llm_request",
                "node": node_label,
                "model": model_name,
                "attempt": 1,
                "url": None,
                "timeout_seconds": None,
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
                "stub": True,
            },
        )
        resp = _stub_response(node_label)
        if stream and on_delta:
            _emit_stub_stream(resp.get("content", ""), on_delta)
        duration_ms = int((time.perf_counter() - call_started_ts) * 1000)
        # Emit llm_response event for stub mode
        emit_event(
            event_sink,
            {
                "type": "llm_response",
                "node": node_label,
                "model": model_name,
                "content": resp.get("content", ""),
                "reasoning_content": resp.get("reasoning_content"),
                "duration_ms": duration_ms,
                "stub": True,
            },
        )
        return resp

    _debug(
        f"prepared call node={node_label} model={model_name} "
        f"mode={mode} api_base={api_base}"
    )

    base = api_base.rstrip("/")
    if base.endswith("/chat/completions"):
        url = base
    else:
        url = base + "/chat/completions"
    timeout_seconds = int(_env("LLM_TIMEOUT_SECONDS", "120"))
    max_retries = int(_env("LLM_MAX_RETRIES", "2"))
    payload = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }
    if stream:
        payload["stream"] = True
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    last_err = None
    for attempt in range(1, max_retries + 1):
        try:
            _debug(f"POST {url} attempt={attempt}/{max_retries} model={model_name} node={node_label}")
            # Emit llm_request event before API call
            emit_event(
                event_sink,
                {
                    "type": "llm_request",
                    "node": node_label,
                    "model": model_name,
                    "attempt": attempt,
                    "url": url,
                    "timeout_seconds": timeout_seconds,
                    "system_prompt": system_prompt,
                    "user_prompt": user_prompt,
                },
            )
            with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
                if stream:
                    content, reasoning_content = _stream_sse_response(resp, on_delta)
                    body = json.dumps(
                        {
                            "choices": [
                                {
                                    "message": {
                                        "content": content,
                                        "reasoning": reasoning_content,
                                    }
                                }
                            ]
                        }
                    )
                else:
                    body = resp.read().decode("utf-8")
            last_err = None
            break
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
            last_err = e
            _debug(f"error attempt={attempt} node={node_label} err={e}")
            # Emit llm_error event for this attempt
            emit_event(
                event_sink,
                {
                    "type": "llm_error",
                    "node": node_label,
                    "model": model_name,
                    "attempt": attempt,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )
            time.sleep(min(2 * attempt, 5))
            continue
    if last_err is not None:
        return {
            "type": "report",
            "content": f"[LLM_ERROR:{node_label}] {last_err}",
            "structured": {"node": node_label, "summary": "LLM error"},
            "reasoning_content": "",
            "error": True,
        }

    try:
        parsed = json.loads(body)
    except json.JSONDecodeError:
        return {
            "type": "report",
            "content": f"[LLM_ERROR:{node_label}] invalid JSON",
            "structured": {"node": node_label, "summary": "LLM error"},
            "reasoning_content": None,
            "error": True,
        }

    choice = (parsed.get("choices") or [{}])[0]
    message = choice.get("message", {})
    content = message.get("content", "")
    reasoning_content = message.get("reasoning") or message.get("reasoning_content")
    if reasoning_content is None:
        reasoning_content = ""
    duration_ms = int((time.perf_counter() - call_started_ts) * 1000)
    _debug(
        f"success node={node_label} model={model_name} "
        f"content_preview={content[:120].replace(chr(10), ' ')}"
    )
    # Emit llm_response event
    response_event: Dict[str, Any] = {
        "type": "llm_response",
        "node": node_label,
        "model": model_name,
        "content": content,
        "reasoning_content": reasoning_content,
        "duration_ms": duration_ms,
    }
    if _trace_raw_enabled():
        response_event["raw"] = parsed
    emit_event(event_sink, response_event)

    structured = {
        "node": node_label,
        "summary": f"Model={model_name}",
        "bullets": ["LLM response received."],
    }
    return {
        "type": "report",
        "content": content,
        "structured": structured,
        "reasoning_content": reasoning_content,
        "error": False,
    }
