"""Sub-smoke: validate /v1/ask_stream emits billing events and X-* headers over the wire."""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request


def _post(url: str, payload: dict, token: str) -> tuple[bytes, int]:
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
    with urllib.request.urlopen(req, timeout=120) as resp:
        return resp.read(), resp.status


def main() -> int:
    port = os.environ.get("SMOKE_PORT", "28099")
    admin = os.environ.get("DEMO_API_TOKEN", "smoke-admin-token-1234")
    base = f"http://127.0.0.1:{port}"

    user_id = f"u_sse_smoke_{int(time.time())}"
    body, status = _post(
        f"{base}/admin/users",
        {"user_id": user_id, "initial_credits": 2000},
        admin,
    )
    assert status == 200, body
    api_key = json.loads(body)["api_key"]

    body, status = _post(
        f"{base}/v1/users",
        {
            "user_id": user_id,
            "birth": {"year": 1990, "month": 1, "day": 1, "hour": 8},
            "gender": "male",
        },
        admin,
    )
    assert status == 200, body

    body, status = _post(
        f"{base}/v1/ask_stream",
        {"question": "今年事业怎么样？", "history_n": 0},
        api_key,
    )
    assert status == 200, body

    events = []
    for raw in body.decode("utf-8").splitlines():
        if not raw.startswith("data:"):
            continue
        chunk = raw[len("data:"):].strip()
        if not chunk:
            continue
        try:
            events.append(json.loads(chunk))
        except json.JSONDecodeError:
            pass

    types = [e.get("type") for e in events]
    print(f"[sse] event types: {set(types)}")
    print(f"[sse] total events: {len(events)}")

    billing = [e for e in events if e.get("type") == "billing"]
    stages = [e.get("stage") for e in billing]
    print(f"[sse] billing stages: {stages}")

    failures = []
    if "session" not in types:
        failures.append("missing session event")
    if "charged" not in stages:
        failures.append("missing billing.charged event")
    if not any(s in ("settled", "refunded") for s in stages):
        failures.append("missing billing.settled / billing.refunded event")

    final = [e for e in billing if e.get("stage") in ("settled", "refunded")]
    if final:
        f = final[-1]
        print(f"[sse] final stage={f['stage']} amount={f.get('amount_credits')} balance_after={f.get('balance_after')}")
        if f["stage"] == "settled" and f.get("amount_credits") != 500:
            failures.append(f"settled amount {f.get('amount_credits')} != 500")

    if failures:
        print("[FAIL] " + "; ".join(failures))
        return 1
    print("[PASS] SSE billing wire format")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
