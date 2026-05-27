"""Local end-to-end Stripe smoke test.

This script does the API-side dance for you and prints the Stripe
Checkout URL you should open in a browser. It does NOT automate the
browser — Stripe's Checkout flow includes interactive 3DS / WeChat QR
challenges that need a human.

Prerequisites:
    1. Server is running locally (e.g. waitress on :8000) with:
       STRIPE_MODE=test
       STRIPE_SECRET_KEY_TEST=sk_test_...
       STRIPE_PUBLISHABLE_KEY_TEST=pk_test_...
       STRIPE_WEBHOOK_SECRET_TEST=whsec_... (from `stripe listen`)
       DEMO_API_TOKEN=...
    2. In another terminal, ``stripe listen --forward-to
       http://localhost:8000/webhooks/stripe`` is running and the
       printed `whsec_...` matches the env var above.

Usage:
    python scripts/smoke_stripe.py --port 8000 --pack pack_30
    python scripts/smoke_stripe.py --port 8000 --custom-yuan 50

The script will:
    1. Hit /v1/register to open a fresh test user (returns the api_key).
    2. Hit /v1/checkout/create with the chosen pack/amount.
    3. Print the Checkout URL (open in browser; pay with test card
       4242 4242 4242 4242 / future date / any CVC).
    4. Poll /v1/balance every 2 seconds for up to 5 minutes,
       waiting for the webhook to land. When balance > 0, print
       success and the new balance.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.request
from typing import Any, Dict, Optional, Tuple


def _post(url: str, payload: Dict[str, Any], token: Optional[str] = None) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {"Content-Type": "application/json; charset=utf-8"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode("utf-8")), None
    except urllib.error.HTTPError as e:
        return None, f"HTTP {e.code}: {e.read().decode('utf-8', errors='replace')[:300]}"
    except Exception as e:  # noqa: BLE001
        return None, str(e)


def _get(url: str, token: Optional[str] = None) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8")), None
    except urllib.error.HTTPError as e:
        return None, f"HTTP {e.code}: {e.read().decode('utf-8', errors='replace')[:200]}"
    except Exception as e:  # noqa: BLE001
        return None, str(e)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--host", default="127.0.0.1")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--pack", help="pack_id from /v1/topup_packs (e.g. pack_10, pack_30)")
    g.add_argument("--custom-yuan", type=int, help="Custom amount in 元 (1-9999)")
    ap.add_argument("--poll-seconds", type=int, default=300)
    args = ap.parse_args(argv)

    base = f"http://{args.host}:{args.port}"

    # 1. Health.
    health, err = _get(f"{base}/health")
    if err or not health:
        print(f"[FATAL] /health unreachable: {err}", file=sys.stderr)
        return 2
    print(f"[health] {health}")

    # 2. Inspect pack catalog.
    packs, err = _get(f"{base}/v1/topup_packs")
    if err or not packs:
        print(f"[FATAL] /v1/topup_packs failed: {err}", file=sys.stderr)
        return 2
    if not packs.get("stripe_configured"):
        print("[FATAL] server reports stripe_configured=false. Set STRIPE_SECRET_KEY_TEST.", file=sys.stderr)
        return 2
    print(f"[packs] mode={packs['stripe_mode']} count={len(packs['packs'])}")

    # 3. Open a fresh user.
    user, err = _post(f"{base}/v1/register", {"display_name": "Stripe smoke"})
    if err or not user or not user.get("api_key"):
        print(f"[FATAL] /v1/register failed: {err or user}", file=sys.stderr)
        return 2
    user_id = user["user"]["user_id"]
    api_key = user["api_key"]
    starting_balance = user["user"]["balance_credits"]
    print(f"[register] user_id={user_id} balance={starting_balance} api_key={api_key[:10]}...")

    # 4. Create the checkout session.
    payload: Dict[str, Any] = {}
    if args.pack:
        payload["pack_id"] = args.pack
    else:
        payload["custom_yuan"] = args.custom_yuan
    session, err = _post(f"{base}/v1/checkout/create", payload, token=api_key)
    if err or not session:
        print(f"[FATAL] /v1/checkout/create failed: {err or session}", file=sys.stderr)
        return 2
    print()
    print(f"[checkout] amount=¥{session['amount_fen']/100:.2f} → {session['credits']} credits")
    print(f"[checkout] session_id={session['session_id']}")
    print()
    print("=" * 70)
    print("OPEN THIS URL IN A BROWSER TO PAY:")
    print(session["checkout_url"])
    print("=" * 70)
    print()
    print("Test card:  4242 4242 4242 4242")
    print("Expiry:     any future date")
    print("CVC:        any 3 digits")
    print("ZIP:        any value")
    print()
    print("(Or scan WeChat QR if you enabled wechat_pay in test mode.)")
    print()

    # 5. Poll balance until webhook lands.
    print(f"[poll] watching /v1/balance for up to {args.poll_seconds}s...")
    deadline = time.time() + args.poll_seconds
    last_balance = starting_balance
    while time.time() < deadline:
        bal, err = _get(f"{base}/v1/balance", token=api_key)
        if bal and bal["balance_credits"] != last_balance:
            print(f"[poll] balance: {last_balance} → {bal['balance_credits']}")
            last_balance = bal["balance_credits"]
            if bal["balance_credits"] >= starting_balance + session["credits"]:
                print()
                print("[PASS] webhook fired and balance reflects topup ✓")
                # Show the ledger row Stripe created.
                usage, _ = _get(f"{base}/v1/usage?limit=5", token=api_key)
                if usage:
                    for row in usage["rows"]:
                        if row["kind"] == "topup":
                            meta = json.loads(row.get("meta_json") or "{}")
                            print(f"[ledger] +{row['amount_credits']} credits via {meta.get('source')} session={meta.get('session_id')}")
                            break
                return 0
        time.sleep(2)
    print(f"[FAIL] balance never updated (still {last_balance}). Did you complete payment? Is `stripe listen` running?", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
