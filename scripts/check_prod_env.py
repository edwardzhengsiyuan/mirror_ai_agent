"""Preflight validator for production deployment.

Run this before flipping a server to live mode. It loads the same .env
that web_server.py reads at boot and checks for the foot-guns we keep
catching by hand:

  - DEMO_API_TOKEN still set to the example/default value
  - LLM_MODE=stub (would return placeholder answers to paying users)
  - STRIPE_MODE=live but live keys missing or success URL still http://
  - WeChat Pay listed in STRIPE_PAYMENT_METHODS without dashboard activation hint
  - Sentry / observability not configured
  - Admin bypass on /v1/* still enabled (BILLING_ADMIN_BYPASS != 0)

Usage:
    python scripts/check_prod_env.py [--env .env] [--strict]

Exit codes:
    0 — no errors (warnings only)
    1 — at least one error (deploy will misbehave)
    2 — script could not be parsed (usage error)

With --strict, warnings escalate to errors. Useful in CI:
    python scripts/check_prod_env.py --env .env --strict
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Dict, List, Tuple


DEFAULT_TOKEN_MARKERS = {
    "change-me-demo-token",
    "smoke-admin-token-1234",
    "local-demo-token",
    "multiturn-token",
    "test-admin-token",
    "demo-token",
    "",
}


def _load_dotenv(path: str) -> Dict[str, str]:
    """Read a KEY=value .env file without touching os.environ.

    Mirrors web_server.load_env_file's parsing so what we check is what
    the server will actually see.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    out: Dict[str, str] = {}
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key:
                out[key] = value
    return out


def _merge_with_env(file_env: Dict[str, str]) -> Dict[str, str]:
    """File .env values lose to anything already set in the process env.

    Same precedence rule as web_server.load_env_file (only sets if absent).
    """
    merged: Dict[str, str] = {}
    for k, v in file_env.items():
        merged[k] = os.environ.get(k, v)
    for k, v in os.environ.items():
        merged.setdefault(k, v)
    return merged


# ---------------------------------------------------------------------------
# Individual checks. Each returns (severity, message) or None.
# severity is "error" or "warn".
# ---------------------------------------------------------------------------


CheckResult = Tuple[str, str]  # (severity, message)


def check_admin_token(env: Dict[str, str]) -> List[CheckResult]:
    token = (env.get("DEMO_API_TOKEN") or "").strip()
    issues: List[CheckResult] = []
    if not token:
        issues.append(("error", "DEMO_API_TOKEN is not set — admin endpoints are unreachable."))
        return issues
    if token in DEFAULT_TOKEN_MARKERS:
        issues.append((
            "error",
            f"DEMO_API_TOKEN looks like a placeholder ('{token}'). "
            "Generate a fresh one: python -c \"import secrets; print(secrets.token_urlsafe(32))\"",
        ))
    if len(token) < 24:
        issues.append((
            "warn",
            f"DEMO_API_TOKEN is short ({len(token)} chars). Aim for ≥32 random chars.",
        ))
    return issues


def check_llm_mode(env: Dict[str, str]) -> List[CheckResult]:
    mode = (env.get("LLM_MODE") or "").strip().lower()
    if mode == "stub":
        return [(
            "error",
            "LLM_MODE=stub will make every billed /v1/* request return "
            "placeholder text. Clear the variable for production.",
        )]
    return []


def check_llm_keys(env: Dict[str, str]) -> List[CheckResult]:
    issues: List[CheckResult] = []
    gptproto = (env.get("GPTPROTO_API_KEY") or "").strip()
    qwen = (env.get("QWEN_API_KEY") or "").strip()
    if not gptproto:
        issues.append((
            "error",
            "GPTPROTO_API_KEY is empty — all routes that fall through to "
            "the default provider will fail with auth errors.",
        ))
    if not qwen:
        issues.append((
            "warn",
            "QWEN_API_KEY is empty — SHISHEN/GEJU/NAJIA nodes will fail "
            "until you fill it (these routes are pinned to qwen3-max in "
            "config/llm_routes.json).",
        ))
    return issues


def check_stripe(env: Dict[str, str]) -> List[CheckResult]:
    issues: List[CheckResult] = []
    mode = (env.get("STRIPE_MODE") or "").strip().lower() or "test"

    secret_test = (env.get("STRIPE_SECRET_KEY_TEST") or "").strip()
    secret_live = (env.get("STRIPE_SECRET_KEY_LIVE") or "").strip()
    whsec_test = (env.get("STRIPE_WEBHOOK_SECRET_TEST") or "").strip()
    whsec_live = (env.get("STRIPE_WEBHOOK_SECRET_LIVE") or "").strip()
    success = (env.get("STRIPE_SUCCESS_URL") or "").strip()
    cancel = (env.get("STRIPE_CANCEL_URL") or "").strip()

    if mode == "live":
        if not secret_live:
            issues.append(("error", "STRIPE_MODE=live but STRIPE_SECRET_KEY_LIVE is empty."))
        elif not (secret_live.startswith("sk_live_") or secret_live.startswith("rk_live_")):
            issues.append((
                "error",
                "STRIPE_SECRET_KEY_LIVE should start with sk_live_ or rk_live_ "
                "(restricted keys are rk_live_) — wrong mode?",
            ))
        if not whsec_live:
            issues.append((
                "error",
                "STRIPE_MODE=live but STRIPE_WEBHOOK_SECRET_LIVE is empty. "
                "Register https://YOUR_HOST/webhooks/stripe in dashboard.stripe.com → Developers → Webhooks.",
            ))
        elif not whsec_live.startswith("whsec_"):
            issues.append(("error", "STRIPE_WEBHOOK_SECRET_LIVE does not start with whsec_ — wrong value?"))
        if success and success.startswith("http://"):
            issues.append((
                "error",
                f"STRIPE_SUCCESS_URL uses http:// in live mode ({success}). "
                "Stripe Checkout requires https for live redirects.",
            ))
        if cancel and cancel.startswith("http://"):
            issues.append((
                "error",
                f"STRIPE_CANCEL_URL uses http:// in live mode ({cancel}). "
                "Use https.",
            ))
        if secret_test and not secret_live:
            issues.append((
                "warn",
                "STRIPE_SECRET_KEY_TEST is set but live key is missing; "
                "live mode will silently fail Session.create.",
            ))
    elif mode == "test":
        if not secret_test:
            issues.append((
                "warn",
                "STRIPE_MODE=test but STRIPE_SECRET_KEY_TEST is empty — "
                "Stripe checkout will fail with a 503.",
            ))
        elif not secret_test.startswith("sk_test_"):
            issues.append(("warn", "STRIPE_SECRET_KEY_TEST does not start with sk_test_ — wrong mode?"))
        if secret_test and not whsec_test:
            issues.append((
                "warn",
                "STRIPE_WEBHOOK_SECRET_TEST is empty — webhooks will be rejected. "
                "Run `stripe listen --forward-to http://localhost:8000/webhooks/stripe` to get one.",
            ))
    else:
        issues.append(("error", f"STRIPE_MODE='{mode}' is invalid; expected 'test' or 'live'."))

    methods_raw = (env.get("STRIPE_PAYMENT_METHODS") or "card").strip().lower()
    methods = {m.strip() for m in methods_raw.split(",") if m.strip()}
    if "wechat_pay" in methods:
        if mode == "live":
            issues.append((
                "warn",
                "STRIPE_PAYMENT_METHODS includes wechat_pay in live mode. "
                "Confirm WeChat Pay is approved at "
                "https://dashboard.stripe.com/settings/payment_methods before deploying, "
                "or Session.create will return 400.",
            ))
    return issues


def check_admin_bypass(env: Dict[str, str]) -> List[CheckResult]:
    raw = (env.get("BILLING_ADMIN_BYPASS") or "1").strip().lower()
    mode = (env.get("STRIPE_MODE") or "").strip().lower()
    if raw not in ("0", "false", "no", "off") and mode == "live":
        return [(
            "warn",
            "BILLING_ADMIN_BYPASS is enabled in live mode. A leaked "
            "DEMO_API_TOKEN can be used to burn free LLM credits on /v1/*. "
            "Set BILLING_ADMIN_BYPASS=0 after migrating smoke scripts to "
            "use a real user API key.",
        )]
    return []


def check_observability(env: Dict[str, str]) -> List[CheckResult]:
    if not (env.get("SENTRY_DSN") or "").strip():
        return [(
            "warn",
            "SENTRY_DSN is empty. Uncaught exceptions will only appear in "
            "container logs (rotating, max ~250MB). Consider a Sentry "
            "free-tier project for production.",
        )]
    return []


CHECKS = (
    check_admin_token,
    check_llm_mode,
    check_llm_keys,
    check_stripe,
    check_admin_bypass,
    check_observability,
)


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------


def run_checks(env: Dict[str, str]) -> Tuple[List[CheckResult], List[CheckResult]]:
    errors: List[CheckResult] = []
    warnings: List[CheckResult] = []
    for fn in CHECKS:
        for severity, msg in fn(env):
            if severity == "error":
                errors.append((severity, msg))
            else:
                warnings.append((severity, msg))
    return errors, warnings


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--env", default=".env", help="Path to .env file (default: .env)")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as errors (useful in CI).",
    )
    args = parser.parse_args(argv)

    try:
        file_env = _load_dotenv(args.env)
    except FileNotFoundError:
        print(f"[check_prod_env] .env not found at {args.env}", file=sys.stderr)
        return 2
    env = _merge_with_env(file_env)

    errors, warnings = run_checks(env)

    if not errors and not warnings:
        print("[check_prod_env] all checks passed - safe to deploy.")
        return 0

    if warnings:
        print(f"\n[check_prod_env] {len(warnings)} warning(s):")
        for _, msg in warnings:
            print(f"  WARN  {msg}")

    if errors:
        print(f"\n[check_prod_env] {len(errors)} error(s):")
        for _, msg in errors:
            print(f"  FAIL  {msg}")

    if errors or (args.strict and warnings):
        print("\n[check_prod_env] preflight FAILED. Fix the above before deploying.", file=sys.stderr)
        return 1
    print("\n[check_prod_env] warnings only - acceptable to deploy.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
