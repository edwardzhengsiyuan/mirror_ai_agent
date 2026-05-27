r"""Two-turn BaZi conversation smoke for the same session.

Runs question A then question B against ``/api/ask_stream`` with the same
``session_id`` and ``history_n>=5``, then inspects the conversation JSONL to
verify history is injected into turn 2 and that prompt sizes stay bounded.

Run against a server started by ``smoke_e2e.py``-style harness or directly via
``waitress-serve --call web_server:create_app``.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _post_stream(url: str, payload: Dict[str, Any], headers: Optional[Dict[str, str]] = None,
                 timeout: int = 600):
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    base_headers = {
        "Content-Type": "application/json; charset=utf-8",
        "Accept": "text/event-stream",
    }
    if headers:
        base_headers.update(headers)
    req = urllib.request.Request(url, data=body, headers=base_headers, method="POST")
    return urllib.request.urlopen(req, timeout=timeout)


def _post_json(url: str, payload: Dict[str, Any], token: str, timeout: int = 60):
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "Authorization": f"Bearer {token}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _conversation_path(user_id: str, session_id: str) -> str:
    if not session_id.endswith(".jsonl"):
        session_id = f"{session_id}.jsonl"
    return os.path.join(REPO_ROOT, "storage", "users", user_id, "conversations", session_id)


def _load_events(path: str) -> List[Dict[str, Any]]:
    if not os.path.exists(path):
        return []
    out: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def _ask_stream(base_url: str, user_id: str, session_id: str, question: str, history_n: int) -> Tuple[List[Dict[str, Any]], str]:
    payload = {
        "user_id": user_id,
        "session_id": session_id,
        "question": question,
        "history_n": history_n,
    }
    events: List[Dict[str, Any]] = []
    answer_chunks: List[str] = []
    with _post_stream(f"{base_url}/api/ask_stream", payload) as resp:
        for raw in resp:
            line = raw.decode("utf-8").strip()
            if not line.startswith("data:"):
                continue
            data = line[len("data:"):].strip()
            if not data:
                continue
            try:
                event = json.loads(data)
            except json.JSONDecodeError:
                continue
            events.append(event)
            if event.get("type") == "response_delta":
                answer_chunks.append(event.get("delta") or "")
    return events, "".join(answer_chunks)


def _prompts_per_turn(events: List[Dict[str, Any]], turn_idx: int, total_turns: int) -> Dict[str, Tuple[int, int]]:
    """Bucket llm_prompt events into turn N (0-indexed) by user_message boundary."""
    boundaries: List[int] = []
    for i, ev in enumerate(events):
        if ev.get("type") == "user_message":
            boundaries.append(i)
    if turn_idx >= len(boundaries):
        return {}
    start = boundaries[turn_idx]
    end = boundaries[turn_idx + 1] if turn_idx + 1 < len(boundaries) else len(events)
    out: Dict[str, Tuple[int, int]] = {}
    for ev in events[start:end]:
        if ev.get("type") != "llm_prompt":
            continue
        node = ev.get("node") or "?"
        sys_len = len(ev.get("system_prompt") or "")
        usr_len = len(ev.get("user_prompt") or "")
        out[node] = (sys_len, usr_len)
    return out


def _user_messages(events: List[Dict[str, Any]]) -> List[str]:
    return [str(ev.get("text") or "") for ev in events if ev.get("type") == "user_message"]


def _history_evidence_in_prompt(events: List[Dict[str, Any]], turn_idx: int, prior_q: str) -> bool:
    """Check whether prior turn's question text shows up in any prompt of turn turn_idx."""
    boundaries: List[int] = []
    for i, ev in enumerate(events):
        if ev.get("type") == "user_message":
            boundaries.append(i)
    if turn_idx >= len(boundaries):
        return False
    start = boundaries[turn_idx]
    end = boundaries[turn_idx + 1] if turn_idx + 1 < len(boundaries) else len(events)
    for ev in events[start:end]:
        if ev.get("type") != "llm_prompt":
            continue
        sys_p = ev.get("system_prompt") or ""
        usr_p = ev.get("user_prompt") or ""
        if prior_q and prior_q in (sys_p + usr_p):
            return True
    return False


def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", default=os.environ.get("SMOKE_PORT", "28182"))
    parser.add_argument("--token", default=os.environ.get("DEMO_API_TOKEN", "multiturn-token"))
    parser.add_argument("--user-id", default=f"u_multiturn_{int(time.time())}")
    args = parser.parse_args(argv)

    base_url = f"http://127.0.0.1:{args.port}"
    print(f"[multi-turn] base_url={base_url} user={args.user_id}")

    profile_payload = {
        "user_id": args.user_id,
        "birth": {"year": 1992, "month": 6, "day": 15, "hour": 14, "minute": 0, "second": 0},
        "gender": "female",
        "birth_time_unknown": False,
    }
    try:
        prof = _post_json(f"{base_url}/v1/users", profile_payload, args.token)
        prof_inner = (prof or {}).get("profile") or {}
        print(f"[setup] /v1/users -> user_id={prof_inner.get('user_id')} bypass_cache={prof_inner.get('bypass_cache')}")
    except urllib.error.HTTPError as e:
        print(f"[FATAL] /v1/users failed: HTTP {e.code}: {e.read().decode('utf-8', errors='replace')[:300]}")
        return 2

    session_id = f"mt_session_{int(time.time())}"
    q1 = "今年事业怎么样？"
    q2 = "那感情运势呢？"

    started = time.time()
    print(f"\n[turn 1] q={q1!r}")
    _, a1 = _ask_stream(base_url, args.user_id, session_id, q1, history_n=5)
    print(f"  answer1 preview: {(a1[:120] or '<empty>')!r}")
    print(f"  elapsed: {time.time() - started:.1f}s")

    started = time.time()
    print(f"\n[turn 2] q={q2!r}")
    _, a2 = _ask_stream(base_url, args.user_id, session_id, q2, history_n=5)
    print(f"  answer2 preview: {(a2[:120] or '<empty>')!r}")
    print(f"  elapsed: {time.time() - started:.1f}s")

    convo = _conversation_path(args.user_id, session_id)
    events = _load_events(convo)
    print(f"\n[convo] {convo}")
    print(f"[convo] {len(events)} events, user_messages={_user_messages(events)}")

    t1 = _prompts_per_turn(events, 0, 2)
    t2 = _prompts_per_turn(events, 1, 2)
    print("\n--- turn 1 prompt sizes (sys / user / total) ---")
    for node, (s, u) in sorted(t1.items()):
        print(f"  {node:<18} {s:>6} / {u:>6} / {s+u:>6}")
    print("--- turn 2 prompt sizes (sys / user / total) ---")
    for node, (s, u) in sorted(t2.items()):
        print(f"  {node:<18} {s:>6} / {u:>6} / {s+u:>6}")

    # Sanity checks
    failures: List[str] = []
    if not a1:
        failures.append("turn 1 returned empty answer")
    if not a2:
        failures.append("turn 2 returned empty answer")
    if not t2:
        failures.append("no llm_prompt events recorded for turn 2")

    history_in_t2 = _history_evidence_in_prompt(events, 1, q1)
    print(f"\n[history check] turn 2 prompt contains turn 1 question text? {history_in_t2}")
    if not history_in_t2:
        failures.append("turn 2 prompt does not include prior question text")

    # Bound check: turn 2 RESPONSE prompt should not balloon vs turn 1 (history_rounds injection should add roughly the prior round, not duplicate the entire chart).
    if "RESPONSE" in t1 and "RESPONSE" in t2:
        t1_total = sum(t1["RESPONSE"])
        t2_total = sum(t2["RESPONSE"])
        ratio = t2_total / max(1, t1_total)
        print(f"[bound check] RESPONSE total turn1={t1_total} turn2={t2_total} ratio={ratio:.2f}")
        if ratio > 2.0:
            failures.append(f"turn 2 RESPONSE prompt grew {ratio:.2f}x vs turn 1 (>2x)")
        if t2_total > 60_000:
            failures.append(f"turn 2 RESPONSE prompt exceeds 60k chars: {t2_total}")

    if failures:
        print("\n[FAIL] " + "; ".join(failures))
        return 1

    print("\n[PASS] multi-turn conversation E2E")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
