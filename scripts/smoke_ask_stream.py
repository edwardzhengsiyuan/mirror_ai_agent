"""Smoke test: hit /api/ask_stream and report planner aspects + prompt sizes.

Used to verify after the codex fixes that:
1. The planner returns CAREER (not OTHER) for "今年创业情况怎么样？".
2. RESPONSE prompt size is bounded and not stuffed with stale aspects.

Reads the conversation JSONL after the SSE stream finishes to inspect
``llm_prompt`` events emitted by every node.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.request


def post_json(url: str, payload: dict) -> "urllib.request.addinfourl":
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "Accept": "text/event-stream",
        },
        method="POST",
    )
    return urllib.request.urlopen(req, timeout=600)


def stream(url: str, payload: dict) -> tuple[str | None, list[dict]]:
    events: list[dict] = []
    session_id: str | None = None
    answer_chunks: list[str] = []
    plan: dict | None = None
    with post_json(url, payload) as resp:
        for raw in resp:
            line = raw.decode("utf-8").strip()
            if not line.startswith("data:"):
                continue
            payload_str = line[len("data:"):].strip()
            if not payload_str:
                continue
            try:
                event = json.loads(payload_str)
            except json.JSONDecodeError:
                continue
            events.append(event)
            etype = event.get("type")
            if etype == "session":
                session_id = event.get("session_id")
            elif etype == "plan":
                plan = event.get("plan")
            elif etype == "answer_delta":
                answer_chunks.append(event.get("delta") or "")
            elif etype == "answer":
                if event.get("answer"):
                    answer_chunks.append("\n[final]\n" + event["answer"])
            elif etype == "error":
                answer_chunks.append("\n[ERROR] " + str(event.get("message")))
    print("---- plan ----")
    print(json.dumps(plan, ensure_ascii=False, indent=2))
    print("---- answer (truncated) ----")
    text = "".join(answer_chunks)
    print(text[:600] + ("..." if len(text) > 600 else ""))
    return session_id, events


def report_prompts(convo_path: str) -> None:
    if not os.path.exists(convo_path):
        print(f"[warn] no conversation file at {convo_path}")
        return
    print("\n---- llm_prompt sizes per node (latest) ----")
    by_node: dict[str, dict] = {}
    with open(convo_path, "r", encoding="utf-8") as f:
        for line in f:
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if event.get("type") != "llm_prompt":
                continue
            node = event.get("node") or "?"
            by_node[node] = {
                "system_len": len(event.get("system_prompt") or ""),
                "user_len": len(event.get("user_prompt") or ""),
            }
    for node, sizes in by_node.items():
        total = sizes["system_len"] + sizes["user_len"]
        print(f"  {node:<14} system={sizes['system_len']:>6}  user={sizes['user_len']:>6}  total={total:>6}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", default=os.environ.get("SMOKE_PORT", "28080"))
    parser.add_argument("--user-id", default="auto_manual_199711190400_male")
    parser.add_argument("--question", default="今年创业情况怎么样？")
    parser.add_argument(
        "--conversation-root",
        default=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "storage", "users"),
    )
    args = parser.parse_args()

    base_url = f"http://127.0.0.1:{args.port}"
    print(f"[smoke] base_url={base_url} user={args.user_id} q={args.question!r}")

    payload = {
        "user_id": args.user_id,
        "question": args.question,
        "history_n": 0,
    }
    started = time.time()
    session_id, events = stream(f"{base_url}/api/ask_stream", payload)
    elapsed = time.time() - started
    print(f"\nstreamed {len(events)} events in {elapsed:.2f}s session={session_id}")

    if session_id:
        convo_path = os.path.join(args.conversation_root, args.user_id, "conversations", session_id)
        report_prompts(convo_path)

    plan_events = [e for e in events if e.get("type") == "plan"]
    if plan_events:
        plan = plan_events[-1].get("plan") or {}
        aspects = plan.get("aspects") or []
        print(f"\nfinal aspects: {aspects}")
        if "CAREER" in aspects and "OTHER" not in aspects:
            print("[PASS] planner picked CAREER without falling back to OTHER")
        elif "OTHER" in aspects:
            print("[WARN] planner returned OTHER (fallback path)")
        else:
            print("[INFO] aspects:", aspects)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
