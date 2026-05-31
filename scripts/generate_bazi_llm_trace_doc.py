"""Run one live BaZi case and export LLM node inputs/outputs to Markdown.

This is an audit helper, not part of the serving path. It runs a fresh profile
with cache bypass enabled, records the built-in llm_request/llm_response events,
then writes a reviewer-friendly Markdown report under reports/.

Usage:
    .venv/Scripts/python.exe scripts/generate_bazi_llm_trace_doc.py

Optional:
    --question "..."
    --out reports/my_report.md
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agent.orchestrator import run_turn
from agent.storage.conversation_store import (
    append_event,
    load_llm_traces,
    log_event_to_conversation,
)
from agent.storage.paths import session_paths
from agent.storage.profile_store import save_profile


DEFAULT_QUESTION = (
    "请完整评估这个命盘在2026年的情况，重点覆盖：整体格局、十神特点、"
    "格局层次、五行喜忌、事业财运、感情、健康、贵人、六亲、性格与年度建议。"
    "请每个方面都给出可复核的依据。"
)


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def _fenced_markdown(text: Any) -> str:
    if text is None:
        text = ""
    if not isinstance(text, str):
        text = json.dumps(text, ensure_ascii=False, indent=2)
    # Four backticks allow ordinary ``` fences inside model prompts/outputs.
    return f"````markdown\n{text}\n````"


def _fenced_json(value: Any) -> str:
    return "```json\n" + json.dumps(value, ensure_ascii=False, indent=2) + "\n```"


def _pair_traces(traces: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    calls: List[Dict[str, Any]] = []
    pending: Dict[str, Dict[str, Any]] = {}
    for ev in traces:
        ev_type = ev.get("type")
        node = str(ev.get("node") or "UNKNOWN")
        attempt = ev.get("attempt") or 1
        key = f"{node}#{attempt}#{len(calls)}"
        if ev_type == "llm_request":
            pending[node] = {"request": ev, "response": None, "error": None}
            calls.append(pending[node])
        elif ev_type == "llm_response":
            target = pending.get(node)
            if target is None or target.get("response") is not None:
                target = {"request": None, "response": None, "error": None}
                calls.append(target)
            target["response"] = ev
        elif ev_type == "llm_error":
            target = pending.get(node)
            if target is None or target.get("error") is not None:
                target = {"request": None, "response": None, "error": None}
                calls.append(target)
            target["error"] = ev
    return calls


def _summarize_call(call: Dict[str, Any], index: int) -> Dict[str, Any]:
    req = call.get("request") or {}
    resp = call.get("response") or {}
    err = call.get("error") or {}
    return {
        "index": index,
        "node": req.get("node") or resp.get("node") or err.get("node"),
        "model": req.get("model") or resp.get("model") or err.get("model"),
        "attempt": req.get("attempt") or err.get("attempt") or 1,
        "duration_ms": resp.get("duration_ms"),
        "status": "error" if err else "ok" if resp else "missing_response",
    }


def _write_report(
    out_path: Path,
    *,
    user_id: str,
    profile: Dict[str, Any],
    question: str,
    now: dt.datetime,
    duration_sec: float,
    result: Dict[str, Any],
    convo_path: str,
    calls: List[Dict[str, Any]],
) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    summaries = [_summarize_call(call, i + 1) for i, call in enumerate(calls)]
    lines: List[str] = []
    lines.append("# BaZi LLM 节点输入/输出审阅记录")
    lines.append("")
    lines.append("## 1. Case Metadata")
    lines.append("")
    lines.append(f"- Generated at: `{dt.datetime.now(dt.UTC).isoformat()}`")
    lines.append(f"- User ID: `{user_id}`")
    lines.append(f"- Conversation trace: `{convo_path}`")
    lines.append(f"- Runtime: `{duration_sec:.1f}s`")
    lines.append(f"- Fixed now: `{now.isoformat()}`")
    lines.append(f"- Error flag: `{result.get('error')}`")
    lines.append("")
    lines.append("### Profile")
    lines.append("")
    lines.append(_fenced_json({
        "birth": profile.get("birth"),
        "gender": profile.get("gender"),
        "birth_time_unknown": profile.get("birth_time_unknown"),
        "prompt_config": profile.get("prompt_config"),
        "bypass_cache": profile.get("bypass_cache"),
    }))
    lines.append("")
    lines.append("### User Question")
    lines.append("")
    lines.append(_fenced_markdown(question))
    lines.append("")
    lines.append("## 2. Plan / Final Response")
    lines.append("")
    lines.append("### Plan")
    lines.append("")
    lines.append(_fenced_json(result.get("plan")))
    lines.append("")
    lines.append("### Final Response")
    lines.append("")
    lines.append(_fenced_markdown(result.get("response", "")))
    lines.append("")
    if result.get("failed_nodes") or result.get("skipped_nodes"):
        lines.append("### Failed / Skipped Nodes")
        lines.append("")
        lines.append(_fenced_json({
            "failed_nodes": result.get("failed_nodes"),
            "skipped_nodes": result.get("skipped_nodes"),
        }))
        lines.append("")
    lines.append("## 3. LLM Call Summary")
    lines.append("")
    lines.append("| # | Node | Model | Attempt | Duration ms | Status |")
    lines.append("|---:|---|---|---:|---:|---|")
    for s in summaries:
        lines.append(
            f"| {s['index']} | `{s['node']}` | `{s['model']}` | "
            f"{s['attempt']} | {s['duration_ms'] if s['duration_ms'] is not None else ''} | `{s['status']}` |"
        )
    lines.append("")
    lines.append("## 4. Per-node Inputs / Outputs")
    lines.append("")
    lines.append(
        "说明：所有发给 LLM 的 system/user prompt 以及 LLM 输出都放在 fenced code block 中，"
        "避免其中 Markdown 被本报告渲染后影响审阅。"
    )
    lines.append("")
    for i, call in enumerate(calls, start=1):
        req = call.get("request") or {}
        resp = call.get("response") or {}
        err = call.get("error") or {}
        node = req.get("node") or resp.get("node") or err.get("node") or "UNKNOWN"
        lines.append(f"### {i}. `{node}`")
        lines.append("")
        lines.append(f"- Model: `{req.get('model') or resp.get('model') or err.get('model')}`")
        lines.append(f"- Attempt: `{req.get('attempt') or err.get('attempt') or 1}`")
        lines.append(f"- URL: `{req.get('url')}`")
        lines.append(f"- Timeout seconds: `{req.get('timeout_seconds')}`")
        if resp:
            lines.append(f"- Duration ms: `{resp.get('duration_ms')}`")
        if err:
            lines.append(f"- Error type: `{err.get('error_type')}`")
        lines.append("")
        lines.append("#### System Prompt")
        lines.append("")
        lines.append(_fenced_markdown(req.get("system_prompt", "")))
        lines.append("")
        lines.append("#### User Prompt")
        lines.append("")
        lines.append(_fenced_markdown(req.get("user_prompt", "")))
        lines.append("")
        if resp:
            lines.append("#### LLM Output")
            lines.append("")
            lines.append(_fenced_markdown(resp.get("content", "")))
            lines.append("")
            reasoning = resp.get("reasoning_content")
            if reasoning:
                lines.append("#### Reasoning Content")
                lines.append("")
                lines.append(_fenced_markdown(reasoning))
                lines.append("")
        if err:
            lines.append("#### LLM Error")
            lines.append("")
            lines.append(_fenced_markdown(err.get("error", "")))
            lines.append("")
    out_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--question", default=DEFAULT_QUESTION)
    parser.add_argument("--out", default="")
    args = parser.parse_args()

    _load_env_file(ROOT / ".env")
    # Make sure this is a live run and not a cached/stub run.
    os.environ.pop("LLM_MODE", None) if os.environ.get("LLM_MODE") == "stub" else None
    os.environ["LLM_BYPASS_CACHE"] = "1"

    now = dt.datetime(2026, 5, 31, 14, 0, 0)
    user_id = f"u_trace_bazi_{dt.datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
    session_id = "bazi_llm_trace"
    profile_path, convo_path = session_paths(user_id, session_id=session_id)
    profile: Dict[str, Any] = {
        "user_id": user_id,
        "birth": {
            "year": 1990,
            "month": 5,
            "day": 12,
            "hour": 10,
            "minute": 0,
            "second": 0,
        },
        "gender": "male",
        "birth_time_unknown": False,
        "prompt_config": "lingyun_cat",
        "node_cache": {},
        "bypass_cache": True,
    }

    append_event(convo_path, {"ts": now.isoformat(), "type": "user_message", "text": args.question})

    started = time.perf_counter()

    def sink(event: Dict[str, Any]) -> None:
        log_event_to_conversation(convo_path, event, ts=now.isoformat())

    result = run_turn(
        profile,
        args.question,
        now=now,
        event_sink=sink,
        stream=False,
        history_rounds=[],
    )
    duration_sec = time.perf_counter() - started
    append_event(convo_path, {"ts": now.isoformat(), "type": "plan", "plan": result.get("plan")})
    append_event(convo_path, {"ts": now.isoformat(), "type": "response", "text": result.get("response", "")})
    save_profile(profile_path, profile)

    traces = load_llm_traces(convo_path)
    calls = _pair_traces(traces)
    default_name = f"bazi_llm_trace_{dt.datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    out_path = Path(args.out) if args.out else ROOT / "reports" / default_name
    _write_report(
        out_path,
        user_id=user_id,
        profile=profile,
        question=args.question,
        now=now,
        duration_sec=duration_sec,
        result=result,
        convo_path=convo_path,
        calls=calls,
    )

    print(json.dumps({
        "report": str(out_path),
        "conversation": convo_path,
        "user_id": user_id,
        "duration_sec": round(duration_sec, 1),
        "llm_calls": len(calls),
        "nodes": [(_summarize_call(c, i + 1)["node"]) for i, c in enumerate(calls)],
        "error": result.get("error"),
        "failed_nodes": result.get("failed_nodes"),
        "skipped_nodes": result.get("skipped_nodes"),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
