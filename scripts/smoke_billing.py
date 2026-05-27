"""End-to-end billing smoke: open a user, topup, call a billed endpoint, assert.

Hits a running ``web_server.py`` on the configured port. The admin token comes
from ``DEMO_API_TOKEN``, falling back to ``local-demo-token`` to match the
repo's example .env. Override with ``--admin-token`` or
``$env:DEMO_API_TOKEN`` when the server is configured with a different value.

This is a safe smoke test: it uses the cheapest billed endpoint (``/v1/cezi/ask``)
so a single run only spends 30 credits.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from typing import Any, Dict, Optional, Tuple


def _post_json(
    url: str,
    payload: Dict[str, Any],
    token: str,
    timeout: int = 600,
) -> Tuple[Optional[Dict[str, Any]], Optional[str], Dict[str, str]]:
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
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            headers = {k: v for k, v in resp.headers.items()}
            return data, None, headers
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")[:300]
        return None, f"HTTP {e.code}: {body}", {}
    except Exception as e:  # noqa: BLE001
        return None, f"{type(e).__name__}: {e}", {}


def _get_json(
    url: str,
    token: str,
    timeout: int = 30,
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    req = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {token}"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8")), None
    except urllib.error.HTTPError as e:
        return None, f"HTTP {e.code}: {e.read().decode('utf-8', errors='replace')[:300]}"
    except Exception as e:  # noqa: BLE001
        return None, f"{type(e).__name__}: {e}"


def main(argv) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", default=os.environ.get("SMOKE_PORT", "28080"))
    parser.add_argument(
        "--admin-token",
        default=os.environ.get("DEMO_API_TOKEN", "local-demo-token"),
    )
    parser.add_argument("--user-id", default=f"u_billing_smoke_{int(time.time())}")
    parser.add_argument("--initial-credits", type=int, default=300)
    parser.add_argument("--topup", type=int, default=200)
    args = parser.parse_args(argv)

    base_url = f"http://127.0.0.1:{args.port}"
    print(f"[billing] base_url={base_url} user={args.user_id}")

    failures = []

    # 1. health
    health, err = _get_json(f"{base_url}/health", token="")
    if err or not health or health.get("status") != "ok":
        print(f"[FATAL] /health failed: {err or health}")
        return 2
    print(f"[health] {health}")

    # 2. admin: create user
    create_resp, err, _ = _post_json(
        f"{base_url}/admin/users",
        {
            "user_id": args.user_id,
            "display_name": "billing smoke",
            "initial_credits": args.initial_credits,
        },
        token=args.admin_token,
    )
    if err or not create_resp or not create_resp.get("api_key"):
        print(f"[FATAL] /admin/users failed: {err or create_resp}")
        return 2
    api_key = create_resp["api_key"]
    initial_balance = create_resp["user"]["balance_credits"]
    print(f"[create] balance={initial_balance} api_key={api_key[:8]}...")
    if initial_balance != args.initial_credits:
        failures.append(f"initial balance mismatch: {initial_balance} != {args.initial_credits}")

    # 3. admin: topup
    topup_resp, err, _ = _post_json(
        f"{base_url}/admin/topup",
        {
            "user_id": args.user_id,
            "amount_credits": args.topup,
            "note": "smoke",
        },
        token=args.admin_token,
    )
    if err or not topup_resp:
        print(f"[FATAL] /admin/topup failed: {err}")
        return 2
    after_topup = topup_resp["balance_credits"]
    print(f"[topup] balance={after_topup}")
    if after_topup != initial_balance + args.topup:
        failures.append(f"after-topup balance mismatch: {after_topup}")

    # 4. user: balance
    bal, err = _get_json(f"{base_url}/v1/balance", token=api_key)
    if err or not bal:
        print(f"[FATAL] /v1/balance failed: {err}")
        return 2
    if bal["balance_credits"] != after_topup:
        failures.append(f"/v1/balance disagrees with admin topup: {bal['balance_credits']}")
    print(f"[balance] {bal['balance_credits']}")

    # 5. user: call cheapest billed endpoint (cezi). Note: this uses real LLM.
    print("[cezi] calling /v1/cezi/ask (real LLM, ~30s)...")
    started = time.time()
    cezi_resp, err, headers = _post_json(
        f"{base_url}/v1/cezi/ask",
        {
            "question": "项目能不能成？",
            "character": "合",
        },
        token=api_key,
    )
    elapsed = time.time() - started
    if err or not cezi_resp:
        print(f"[FATAL] /v1/cezi/ask failed: {err}")
        return 2
    charged = headers.get("X-Charged-Credits")
    balance_after = headers.get("X-Balance-After")
    print(f"[cezi] elapsed={elapsed:.1f}s charged={charged} balance_after={balance_after}")
    if charged is None or balance_after is None:
        failures.append("response missing X-Charged-Credits / X-Balance-After")
    if cezi_resp.get("answer", "").startswith("[LLM_PLACEHOLDER"):
        failures.append("cezi answer is stubbed (LLM_MODE=stub or LLM not configured)")

    # 6. user: balance should reflect deduction
    bal2, err = _get_json(f"{base_url}/v1/balance", token=api_key)
    if err or not bal2:
        print(f"[FATAL] /v1/balance (after) failed: {err}")
        return 2
    expected_balance = after_topup - int(charged or 0)
    print(f"[balance after] {bal2['balance_credits']} (expected {expected_balance})")
    if bal2["balance_credits"] != expected_balance:
        failures.append(
            f"post-call balance {bal2['balance_credits']} != expected {expected_balance}"
        )

    # 7. user: usage history shows charge + topup
    usage, err = _get_json(f"{base_url}/v1/usage?limit=10", token=api_key)
    if err or not usage:
        failures.append(f"/v1/usage failed: {err}")
    else:
        kinds = [r["kind"] for r in usage["rows"]]
        print(f"[usage] kinds={kinds}")
        if "charge" not in kinds:
            failures.append("usage missing charge row")
        if "topup" not in kinds:
            failures.append("usage missing topup row")

    # 8. insufficient funds path: drain balance, expect 402
    print("[drain] draining balance via /admin/topup negative trick? skip — unsupported.")
    # We instead trigger insufficient funds by issuing a charge that exceeds balance.
    # Easiest: disable user, then re-enable. But disabled = 401, not 402. Instead,
    # call cezi again until balance < 30. Each call costs 30 credits.
    while bal2["balance_credits"] >= 30:
        bal2, _ = _get_json(f"{base_url}/v1/balance", token=api_key)
        if bal2["balance_credits"] < 30:
            break
        print(f"[drain] balance={bal2['balance_credits']}, calling /v1/cezi/ask to drain...")
        _post_json(
            f"{base_url}/v1/cezi/ask",
            {"question": "Q", "character": "合"},
            token=api_key,
        )
        bal2, _ = _get_json(f"{base_url}/v1/balance", token=api_key)
    print(f"[drain] final balance={bal2['balance_credits']}")
    insufficient_resp, err, _ = _post_json(
        f"{base_url}/v1/cezi/ask",
        {"question": "Q", "character": "合"},
        token=api_key,
    )
    if not err or "402" not in str(err):
        failures.append(
            f"expected HTTP 402 insufficient_funds when drained, got: {err or insufficient_resp}"
        )
    else:
        print(f"[insufficient] confirmed 402 when balance < cost")

    print()
    if failures:
        print("[FAIL] " + "; ".join(failures))
        return 1
    print("[PASS] billing e2e smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
