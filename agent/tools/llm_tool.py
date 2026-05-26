"""LLM tool with real API call and stub fallback."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from typing import Any, Callable, Dict, Optional, Tuple

from ..events import EventSink, emit_event
from ..llm_config import resolve_llm_settings

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


def _do_llm_api_call(
    url: str,
    api_key: str,
    model_name: str,
    system_prompt: str,
    user_prompt: str,
    timeout_seconds: int,
    max_retries: int,
    stream: bool,
    on_delta: Optional[Callable[[Dict[str, str]], None]],
    event_sink: EventSink | None,
    node_label: str,
    authorization_scheme: str = "Bearer",
) -> Tuple[Optional[str], Optional[str], Optional[Exception]]:
    """Execute LLM API call with network error retry.

    Returns:
        Tuple of (content, reasoning_content, last_error)
        - On success: (content, reasoning_content, None)
        - On failure: (None, None, last_error)
    """
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
    auth_value = f"{authorization_scheme} {api_key}" if authorization_scheme else api_key
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": auth_value,
            "User-Agent": "bazi-agent/1.0",
        },
        method="POST",
    )

    last_err = None
    body = None
    for attempt in range(1, max_retries + 1):
        try:
            _debug(f"POST {url} attempt={attempt}/{max_retries} model={model_name} node={node_label}")
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
        return None, None, last_err

    try:
        parsed = json.loads(body)
    except json.JSONDecodeError as e:
        return None, None, e

    choice = (parsed.get("choices") or [{}])[0]
    message = choice.get("message", {})
    content = message.get("content", "")
    reasoning_content = message.get("reasoning") or message.get("reasoning_content") or ""

    return content, reasoning_content, None


def llm_report_tool(
    system_prompt: str,
    user_prompt: str,
    model: str | None = None,
    node: str | None = None,
    node_model_overrides: Dict[str, str] | None = None,
    sleep_ms: int | None = None,
    stream: bool = False,
    on_delta: Callable[[Dict[str, str]], None] | None = None,
    event_sink: EventSink | None = None,
    output_validator: Callable[[str], tuple[bool, str]] | None = None,
    validation_retries: int = 2,
) -> Dict[str, Any]:
    """LLM call with stub fallback for local testing.

    Args:
        system_prompt: System prompt for the LLM
        user_prompt: User prompt for the LLM
        model: Model name override (default: route config)
        node: Node label for logging/tracing
        sleep_ms: Optional delay before call
        stream: Enable streaming response
        on_delta: Callback for streaming chunks
        event_sink: Event sink for LLM tracing (llm_request/response/error events)
        output_validator: Optional function to validate output format.
            Takes content string, returns (is_valid, error_message).
            If validation fails, LLM is called again with the error feedback.
        validation_retries: Max retries for validation failures (default 2)

    Returns:
        Dict with content, structured, reasoning_content, error fields
    """
    if sleep_ms:
        time.sleep(sleep_ms / 1000.0)
    node_label = node or "UNKNOWN"
    call_started_ts = time.perf_counter()

    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    _load_env_file(os.path.join(repo_root, ".env"))

    route = resolve_llm_settings(node_label, requested_model=model, node_model_overrides=node_model_overrides)
    model_name = route.get("model") or model or _env("LLM_MODEL", "gemini-3.1-pro-preview")

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
    api_base = route.get("api_base") or _env_any(["LLM_API_BASE", "OPENAI_API_BASE"])
    api_key = route.get("api_key") or _env_any(["LLM_API_KEY", "OPENAI_API_KEY"])
    if mode == "stub" or not api_base or not api_key:
        _debug(
            f"stub response for {node_label} mode={mode} api_base={api_base} "
            f"api_key={'set' if api_key else 'missing'}"
        )
        emit_event(
            event_sink,
            {
                "type": "llm_request",
                "node": node_label,
                "model": model_name,
                "provider": route.get("provider"),
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
        f"prepared call node={node_label} provider={route.get('provider')} model={model_name} "
        f"mode={mode} api_base={api_base}"
    )

    base = api_base.rstrip("/")
    if base.endswith("/chat/completions"):
        url = base
    else:
        url = base + "/chat/completions"
    timeout_seconds = int(_env("LLM_TIMEOUT_SECONDS", "120"))
    max_retries = int(_env("LLM_MAX_RETRIES", "2"))

    # Main loop with validation retry
    current_user_prompt = user_prompt
    validation_attempt = 0
    last_content = ""
    last_reasoning_content = ""

    while validation_attempt <= validation_retries:
        content, reasoning_content, api_error = _do_llm_api_call(
            url=url,
            api_key=api_key,
            model_name=model_name,
            system_prompt=system_prompt,
            user_prompt=current_user_prompt,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
            stream=stream if validation_attempt == 0 else False,  # Only stream on first attempt
            on_delta=on_delta if validation_attempt == 0 else None,
            event_sink=event_sink,
            node_label=node_label,
            authorization_scheme=str(route.get("authorization_scheme") if route.get("authorization_scheme") is not None else "Bearer"),
        )

        if api_error is not None:
            return {
                "type": "report",
                "content": f"[LLM_ERROR:{node_label}] {api_error}",
                "structured": {"node": node_label, "summary": "LLM error"},
                "reasoning_content": "",
                "error": True,
            }

        last_content = content
        last_reasoning_content = reasoning_content

        # If no validator, return immediately
        if output_validator is None:
            break

        # Validate output
        is_valid, error_message = output_validator(content)
        if is_valid:
            _debug(f"validation passed for {node_label}")
            break

        validation_attempt += 1
        if validation_attempt > validation_retries:
            # Validation failed after all retries - return error
            _debug(f"validation failed after {validation_retries} retries for {node_label}: {error_message}")
            emit_event(
                event_sink,
                {
                    "type": "llm_error",
                    "node": node_label,
                    "model": model_name,
                    "attempt": validation_attempt,
                    "error": f"Output validation failed: {error_message}",
                    "error_type": "ValidationError",
                    "invalid_output": content[:500],  # Include truncated output for debugging
                },
            )
            return {
                "type": "report",
                "content": f"[LLM_VALIDATION_ERROR:{node_label}] {error_message}",
                "structured": {"node": node_label, "summary": "LLM validation error"},
                "reasoning_content": reasoning_content or "",
                "error": True,
            }

        # Build retry prompt with error feedback
        _debug(f"validation failed for {node_label} (attempt {validation_attempt}/{validation_retries}): {error_message}")
        emit_event(
            event_sink,
            {
                "type": "llm_validation_retry",
                "node": node_label,
                "attempt": validation_attempt,
                "error": error_message,
                "invalid_output_preview": content[:200],
            },
        )
        current_user_prompt = (
            f"{user_prompt}\n\n"
            f"---\n"
            f"## 重要：你上次的输出格式不正确，请修正\n\n"
            f"### 你的错误输出：\n```\n{content}\n```\n\n"
            f"### 错误原因：\n{error_message}\n\n"
            f"### 请严格按照要求的格式重新输出，不要包含任何额外的解释文字。"
        )

    duration_ms = int((time.perf_counter() - call_started_ts) * 1000)
    _debug(
        f"success node={node_label} model={model_name} "
        f"content_preview={last_content[:120].replace(chr(10), ' ')}"
    )

    # Emit llm_response event
    response_event: Dict[str, Any] = {
        "type": "llm_response",
        "node": node_label,
        "model": model_name,
        "content": last_content,
        "reasoning_content": last_reasoning_content,
        "duration_ms": duration_ms,
    }
    if _trace_raw_enabled():
        response_event["raw"] = {"content": last_content, "reasoning_content": last_reasoning_content}
    emit_event(event_sink, response_event)

    structured = {
        "node": node_label,
        "summary": f"Model={model_name}",
        "bullets": ["LLM response received."],
    }
    return {
        "type": "report",
        "content": last_content,
        "structured": structured,
        "reasoning_content": last_reasoning_content,
        "error": False,
    }
