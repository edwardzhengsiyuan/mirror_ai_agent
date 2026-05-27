r"""End-to-end smoke test runner for the demo APIs.

Hits the four user-facing turns (BaZi stream, HePan, CeZi, Najia) against a
running ``web_server.py`` on a configurable port, prints structured pass/fail
output, and inspects each session's conversation JSONL for prompt sizes and
LLM errors.

Usage (PowerShell):

    $env:PORT = "28080"
    .\.venv\Scripts\python.exe web_server.py            # in another terminal
    .\.venv\Scripts\python.exe scripts\smoke_e2e.py --suite all

The auth bearer token comes from the ``DEMO_API_TOKEN`` env var, falling back
to ``change-me-demo-token`` to match the repo's example .env. Override with
``--token`` or ``$env:DEMO_API_TOKEN`` when the server is configured with a
different value.
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
DEFAULT_USER = "auto_manual_199711190400_male"


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

def _post(url: str, payload: Dict[str, Any], headers: Optional[Dict[str, str]] = None,
          timeout: int = 600, expect_stream: bool = False):
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    base_headers = {
        "Content-Type": "application/json; charset=utf-8",
        "Accept": "text/event-stream" if expect_stream else "application/json",
    }
    if headers:
        base_headers.update(headers)
    req = urllib.request.Request(url, data=body, headers=base_headers, method="POST")
    return urllib.request.urlopen(req, timeout=timeout)


def _get(url: str, headers: Optional[Dict[str, str]] = None, timeout: int = 30):
    req = urllib.request.Request(url, headers=headers or {}, method="GET")
    return urllib.request.urlopen(req, timeout=timeout)


# ---------------------------------------------------------------------------
# Conversation JSONL inspection
# ---------------------------------------------------------------------------

def _conversation_path(user_id: str, session_id: str) -> str:
    return os.path.join(REPO_ROOT, "storage", "users", user_id, "conversations", session_id)


def _load_events(convo_path: str) -> List[Dict[str, Any]]:
    if not os.path.exists(convo_path):
        return []
    out: List[Dict[str, Any]] = []
    with open(convo_path, "r", encoding="utf-8") as f:
        for line in f:
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def _summarize_prompts(events: List[Dict[str, Any]]) -> Dict[str, Tuple[int, int]]:
    by_node: Dict[str, Tuple[int, int]] = {}
    for ev in events:
        if ev.get("type") != "llm_prompt":
            continue
        node = ev.get("node") or "?"
        sys_len = len(ev.get("system_prompt") or "")
        usr_len = len(ev.get("user_prompt") or "")
        by_node[node] = (sys_len, usr_len)
    return by_node


def _llm_errors(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [ev for ev in events if ev.get("type") == "llm_error"]


def _node_failures(events: List[Dict[str, Any]]) -> List[str]:
    failed: List[str] = []
    for ev in events:
        if ev.get("type") == "node_end" and (ev.get("output") or {}).get("error"):
            failed.append(str(ev.get("node")))
        if ev.get("type") == "node_failed":
            failed.append(str(ev.get("node")))
    return failed


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------

class Outcome:
    def __init__(self, name: str) -> None:
        self.name = name
        self.passed = False
        self.notes: List[str] = []
        self.session_id: Optional[str] = None
        self.duration_s: float = 0.0
        self.prompt_sizes: Dict[str, Tuple[int, int]] = {}
        self.error: Optional[str] = None
        self.answer_preview: str = ""

    def add(self, msg: str) -> None:
        self.notes.append(msg)

    def render(self) -> str:
        status = "PASS" if self.passed else "FAIL"
        head = f"[{status}] {self.name}  ({self.duration_s:.1f}s)"
        lines = [head]
        if self.session_id:
            lines.append(f"  session: {self.session_id}")
        if self.prompt_sizes:
            lines.append("  prompt sizes (sys/user/total):")
            for node, (s, u) in self.prompt_sizes.items():
                lines.append(f"    {node:<16} {s:>6} / {u:>6} / {s+u:>6}")
        if self.answer_preview:
            preview = self.answer_preview.replace("\n", " ")
            if len(preview) > 200:
                preview = preview[:200] + "..."
            lines.append(f"  answer preview: {preview}")
        for note in self.notes:
            lines.append(f"  - {note}")
        if self.error:
            lines.append(f"  ERROR: {self.error}")
        return "\n".join(lines)


def run_bazi_stream(base_url: str, *, user_id: str, question: str,
                    expected_aspect: Optional[str] = None) -> Outcome:
    out = Outcome(f"BaZi stream / {expected_aspect or 'free-form'} / {question[:24]}")
    payload = {"user_id": user_id, "question": question, "history_n": 0}
    started = time.time()
    answer_chunks: List[str] = []
    plan: Optional[Dict[str, Any]] = None
    try:
        with _post(f"{base_url}/api/ask_stream", payload, expect_stream=True) as resp:
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
                etype = event.get("type")
                if etype == "session":
                    out.session_id = event.get("session_id")
                elif etype == "plan":
                    plan = event.get("plan")
                elif etype == "node_delta":
                    pass  # node deltas ignored
                elif etype == "response_delta":
                    answer_chunks.append(event.get("delta") or "")
                elif etype == "node_end" and (event.get("output") or {}).get("error"):
                    out.add(f"node_end error: {event.get('node')}")
                elif etype == "server_error":
                    out.add(f"server_error: {event.get('error')}")
    except urllib.error.HTTPError as e:
        out.error = f"HTTP {e.code}: {e.read().decode('utf-8', errors='replace')[:300]}"
        out.duration_s = time.time() - started
        return out
    except Exception as e:  # noqa: BLE001
        out.error = f"{type(e).__name__}: {e}"
        out.duration_s = time.time() - started
        return out

    out.duration_s = time.time() - started
    answer_text = "".join(answer_chunks)
    out.answer_preview = answer_text[:300]

    events: List[Dict[str, Any]] = []
    if out.session_id:
        events = _load_events(_conversation_path(user_id, out.session_id))
        out.prompt_sizes = _summarize_prompts(events)

    failures = _node_failures(events)
    if failures:
        out.add(f"failed nodes: {failures}")

    if plan is None:
        out.add("no plan event received")
        return out
    aspects = plan.get("aspects") or []
    out.add(f"plan aspects={aspects}")
    if expected_aspect and expected_aspect not in aspects:
        out.add(f"EXPECTED aspect '{expected_aspect}' not in plan")
        return out

    response_events = [ev for ev in events if ev.get("type") == "response"]
    if not response_events:
        out.add("no response event recorded")
        return out
    last_resp_text = response_events[-1].get("text") or ""
    if not last_resp_text:
        out.add("response.text empty")
        return out
    if not answer_text and not last_resp_text:
        out.add("answer text empty")
        return out

    if not failures:
        out.passed = True
    return out


def _post_json(base_url: str, path: str, payload: Dict[str, Any], token: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    try:
        with _post(f"{base_url}{path}", payload, headers={"Authorization": f"Bearer {token}"}, timeout=600) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data, None
    except urllib.error.HTTPError as e:
        return None, f"HTTP {e.code}: {e.read().decode('utf-8', errors='replace')[:300]}"
    except Exception as e:  # noqa: BLE001
        return None, f"{type(e).__name__}: {e}"


def run_hepan(base_url: str, token: str) -> Outcome:
    out = Outcome("HePan / 长期发展兼容度")
    payload = {
        "user_id": "u_hepan_smoke",
        "question": "我们适合长期发展吗？",
        "person_a": {
            "name": "甲",
            "gender": "male",
            "birth": {"year": 1990, "month": 5, "day": 12, "hour": 8, "minute": 0, "second": 0},
            "birth_time_unknown": False,
        },
        "person_b": {
            "name": "乙",
            "gender": "female",
            "birth": {"year": 1992, "month": 9, "day": 3, "hour": 14, "minute": 0, "second": 0},
            "birth_time_unknown": False,
        },
    }
    started = time.time()
    data, err = _post_json(base_url, "/v1/hepan/ask", payload, token)
    out.duration_s = time.time() - started
    if err:
        out.error = err
        return out
    assert data is not None
    out.session_id = data.get("session_id")
    answer = data.get("answer") or ""
    out.answer_preview = answer[:300]
    compatibility = data.get("compatibility") or {}
    out.add(f"compatibility keys: {sorted(compatibility.keys()) if isinstance(compatibility, dict) else type(compatibility).__name__}")
    if not answer:
        out.add("answer empty")
        return out

    if out.session_id:
        events = _load_events(_conversation_path(payload["user_id"], out.session_id))
        out.prompt_sizes = _summarize_prompts(events)
        errors = _llm_errors(events)
        if errors:
            out.add(f"llm_error count: {len(errors)} (last: {errors[-1].get('error')})")
            return out
    out.passed = True
    return out


def run_cezi(base_url: str, token: str) -> Outcome:
    out = Outcome("CeZi / 字: 合, 项目合作")
    payload = {
        "user_id": "u_cezi_smoke",
        "question": "这个项目合作能不能成？",
        "character": "合",
    }
    started = time.time()
    data, err = _post_json(base_url, "/v1/cezi/ask", payload, token)
    out.duration_s = time.time() - started
    if err:
        out.error = err
        return out
    assert data is not None
    out.session_id = data.get("session_id")
    answer = data.get("answer") or ""
    out.answer_preview = answer[:300]
    if not answer:
        out.add("answer empty")
        return out

    if out.session_id:
        events = _load_events(_conversation_path(payload["user_id"], out.session_id))
        out.prompt_sizes = _summarize_prompts(events)
        errors = _llm_errors(events)
        if errors:
            out.add(f"llm_error count: {len(errors)} (last: {errors[-1].get('error')})")
            return out
    out.passed = True
    return out


def run_zwds(base_url: str, token: str) -> Outcome:
    out = Outcome("Zwds / 紫微斗数: 事业感情")
    payload = {
        "user_id": "u_zwds_smoke",
        "question": "今年我的事业和感情运势如何？",
        "birth": {"year": 1990, "month": 5, "day": 12, "hour": 8, "minute": 0, "second": 0},
        "gender": "male",
        "target_years": [2026],
    }
    started = time.time()
    data, err = _post_json(base_url, "/v1/zwds/ask", payload, token)
    out.duration_s = time.time() - started
    if err:
        out.error = err
        return out
    assert data is not None
    out.session_id = data.get("session_id")
    answer = data.get("answer") or ""
    out.answer_preview = answer[:300]
    chart = data.get("chart") or {}
    if isinstance(chart, dict):
        out.add(f"chart target_years={chart.get('target_years')} benming_chars={len(chart.get('benming_info') or '')}")
    if not answer:
        out.add("answer empty")
        return out

    if out.session_id:
        events = _load_events(_conversation_path(payload["user_id"], out.session_id))
        out.prompt_sizes = _summarize_prompts(events)
        errors = _llm_errors(events)
        if errors:
            out.add(f"llm_error count: {len(errors)} (last: {errors[-1].get('error')})")
            return out
    out.passed = True
    return out


def run_najia(base_url: str, token: str) -> Outcome:
    out = Outcome("Najia / 六爻: 项目推进")
    payload = {
        "user_id": "u_najia_smoke",
        "question": "这个项目三个月内能不能推进成功？",
        "yao_values": [0, 1, 2, 3, 4, 5],
    }
    started = time.time()
    data, err = _post_json(base_url, "/v1/najia/ask", payload, token)
    out.duration_s = time.time() - started
    if err:
        out.error = err
        return out
    assert data is not None
    out.session_id = data.get("session_id")
    answer = data.get("answer") or ""
    out.answer_preview = answer[:300]
    gua = data.get("gua") or {}
    if isinstance(gua, dict):
        bengua = gua.get("bengua") or {}
        biangua = gua.get("biangua") or {}
        out.add(f"bengua={bengua.get('fullname') or bengua.get('name')} biangua={biangua.get('fullname') or biangua.get('name')}")
    if not answer:
        out.add("answer empty")
        return out

    if out.session_id:
        events = _load_events(_conversation_path(payload["user_id"], out.session_id))
        out.prompt_sizes = _summarize_prompts(events)
        errors = _llm_errors(events)
        if errors:
            out.add(f"llm_error count: {len(errors)} (last: {errors[-1].get('error')})")
            return out
    out.passed = True
    return out


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", default=os.environ.get("SMOKE_PORT", "28080"))
    parser.add_argument("--user-id", default=DEFAULT_USER, help="BaZi demo user id")
    parser.add_argument("--token", default=os.environ.get("DEMO_API_TOKEN", "change-me-demo-token"))
    parser.add_argument(
        "--suite",
        default="all",
        choices=["all", "bazi", "hepan", "cezi", "najia", "zwds"],
        help="Which sub-suite to run",
    )
    args = parser.parse_args(argv)

    base_url = f"http://127.0.0.1:{args.port}"
    print(f"[e2e] base_url={base_url} suite={args.suite}")

    # Quick health check
    try:
        with _get(f"{base_url}/health", timeout=5) as resp:
            health = json.loads(resp.read().decode("utf-8"))
            print(f"[health] {health}")
    except Exception as e:  # noqa: BLE001
        print(f"[FATAL] /health failed: {e}")
        return 2

    outcomes: List[Outcome] = []
    if args.suite in ("all", "bazi"):
        outcomes.append(run_bazi_stream(
            base_url,
            user_id=args.user_id,
            question="今年创业情况怎么样？",
            expected_aspect="CAREER",
        ))

    if args.suite in ("all", "hepan"):
        outcomes.append(run_hepan(base_url, args.token))

    if args.suite in ("all", "cezi"):
        outcomes.append(run_cezi(base_url, args.token))

    if args.suite in ("all", "najia"):
        outcomes.append(run_najia(base_url, args.token))

    if args.suite in ("all", "zwds"):
        outcomes.append(run_zwds(base_url, args.token))

    print("\n================ E2E RESULTS ================\n")
    for o in outcomes:
        print(o.render())
        print()

    failed = [o for o in outcomes if not o.passed]
    print(f"summary: {len(outcomes) - len(failed)}/{len(outcomes)} passed")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
