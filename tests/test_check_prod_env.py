"""Unit tests for scripts/check_prod_env.py.

Each test feeds a synthetic env dict to ``run_checks`` and asserts which
severity bucket the expected message lands in. End-to-end behaviour (the
argparse + .env-file path) is covered by one integration-style test that
writes a tempfile and invokes ``main``.
"""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple

import pytest


# The script lives outside the ``agent`` / ``tests`` import paths, so load it
# directly by file path rather than dragging it into a package.
_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check_prod_env.py"
_spec = importlib.util.spec_from_file_location("check_prod_env", _SCRIPT)
assert _spec and _spec.loader, "scripts/check_prod_env.py not found"
check_prod_env = importlib.util.module_from_spec(_spec)
sys.modules["check_prod_env"] = check_prod_env
_spec.loader.exec_module(check_prod_env)  # type: ignore[union-attr]


def _ok_env(**overrides) -> Dict[str, str]:
    """An env dict with no errors and no warnings (best-case baseline)."""
    env = {
        "DEMO_API_TOKEN": "qXc8GkP9aZ4tYwH3sFvJ2nB7mLc6E5RpTuVxKjNbMwQ",
        "LLM_MODE": "",
        "GPTPROTO_API_KEY": "sk-real-gptproto-key-here",
        "QWEN_API_KEY": "sk-real-qwen-key-here",
        "STRIPE_MODE": "live",
        "STRIPE_SECRET_KEY_LIVE": "sk_live_fakeXYZ",
        "STRIPE_WEBHOOK_SECRET_LIVE": "whsec_fakeXYZ",
        "STRIPE_SUCCESS_URL": "https://example.com/billing.html?status=success&session_id={CHECKOUT_SESSION_ID}",
        "STRIPE_CANCEL_URL": "https://example.com/billing.html?status=cancelled",
        "STRIPE_PAYMENT_METHODS": "card",
        "BILLING_ADMIN_BYPASS": "0",
        "SENTRY_DSN": "https://abc@sentry.io/123",
    }
    env.update(overrides)
    return env


def _msgs(results: List[Tuple[str, str]]) -> str:
    return "\n".join(m for _, m in results)


def test_clean_env_passes() -> None:
    errors, warnings = check_prod_env.run_checks(_ok_env())
    assert errors == [], _msgs(errors)
    assert warnings == [], _msgs(warnings)


def test_default_admin_token_is_error() -> None:
    env = _ok_env(DEMO_API_TOKEN="change-me-demo-token")
    errors, _ = check_prod_env.run_checks(env)
    joined = _msgs(errors)
    assert "DEMO_API_TOKEN" in joined
    assert "placeholder" in joined


def test_missing_admin_token_is_error() -> None:
    env = _ok_env(DEMO_API_TOKEN="")
    errors, _ = check_prod_env.run_checks(env)
    assert any("DEMO_API_TOKEN is not set" in m for _, m in errors)


def test_short_admin_token_is_warning_not_error() -> None:
    env = _ok_env(DEMO_API_TOKEN="abc123")
    errors, warnings = check_prod_env.run_checks(env)
    # Custom token strings short of 24 chars should warn but not block.
    assert errors == [], _msgs(errors)
    assert any("short" in m for _, m in warnings)


def test_llm_stub_mode_is_error() -> None:
    env = _ok_env(LLM_MODE="stub")
    errors, _ = check_prod_env.run_checks(env)
    assert any("LLM_MODE=stub" in m for _, m in errors)


def test_missing_gptproto_key_is_error() -> None:
    env = _ok_env(GPTPROTO_API_KEY="")
    errors, _ = check_prod_env.run_checks(env)
    assert any("GPTPROTO_API_KEY" in m for _, m in errors)


def test_missing_qwen_key_is_warn() -> None:
    env = _ok_env(QWEN_API_KEY="")
    errors, warnings = check_prod_env.run_checks(env)
    assert errors == [], _msgs(errors)
    assert any("QWEN_API_KEY" in m for _, m in warnings)


def test_live_mode_without_live_secret_is_error() -> None:
    env = _ok_env(STRIPE_SECRET_KEY_LIVE="")
    errors, _ = check_prod_env.run_checks(env)
    assert any("STRIPE_SECRET_KEY_LIVE is empty" in m for _, m in errors)


def test_live_mode_with_test_key_is_error() -> None:
    env = _ok_env(STRIPE_SECRET_KEY_LIVE="sk_test_wrong")
    errors, _ = check_prod_env.run_checks(env)
    assert any("does not start with sk_live_" in m for _, m in errors)


def test_live_mode_with_http_success_url_is_error() -> None:
    env = _ok_env(STRIPE_SUCCESS_URL="http://example.com/billing.html?status=success")
    errors, _ = check_prod_env.run_checks(env)
    assert any("http://" in m and "SUCCESS_URL" in m for _, m in errors)


def test_live_mode_missing_webhook_secret_is_error() -> None:
    env = _ok_env(STRIPE_WEBHOOK_SECRET_LIVE="")
    errors, _ = check_prod_env.run_checks(env)
    assert any("STRIPE_WEBHOOK_SECRET_LIVE" in m for _, m in errors)


def test_admin_bypass_on_live_is_warning() -> None:
    env = _ok_env(BILLING_ADMIN_BYPASS="1")
    errors, warnings = check_prod_env.run_checks(env)
    assert errors == [], _msgs(errors)
    assert any("BILLING_ADMIN_BYPASS" in m for _, m in warnings)


def test_admin_bypass_off_in_test_mode_is_fine() -> None:
    env = _ok_env(STRIPE_MODE="test", BILLING_ADMIN_BYPASS="1",
                  STRIPE_SECRET_KEY_TEST="sk_test_x", STRIPE_WEBHOOK_SECRET_TEST="whsec_x",
                  STRIPE_SECRET_KEY_LIVE="", STRIPE_WEBHOOK_SECRET_LIVE="")
    errors, warnings = check_prod_env.run_checks(env)
    # Test mode + admin bypass + http URLs etc are all fine; only Sentry warn if any.
    assert errors == [], _msgs(errors)
    # We tolerate any leftover sentry warning, but not the admin bypass one.
    assert not any("BILLING_ADMIN_BYPASS" in m for _, m in warnings)


def test_wechat_pay_in_live_mode_is_warning() -> None:
    env = _ok_env(STRIPE_PAYMENT_METHODS="card,wechat_pay")
    errors, warnings = check_prod_env.run_checks(env)
    assert errors == [], _msgs(errors)
    assert any("wechat_pay" in m for _, m in warnings)


def test_invalid_stripe_mode_is_error() -> None:
    env = _ok_env(STRIPE_MODE="sandbox")
    errors, _ = check_prod_env.run_checks(env)
    assert any("STRIPE_MODE='sandbox'" in m for _, m in errors)


def test_no_sentry_is_warning_only() -> None:
    env = _ok_env(SENTRY_DSN="")
    errors, warnings = check_prod_env.run_checks(env)
    assert errors == [], _msgs(errors)
    assert any("SENTRY_DSN" in m for _, m in warnings)


# ---------------------------------------------------------------------------
# main() end-to-end: writes a real .env file and invokes the script entry.
# ---------------------------------------------------------------------------


def _write_env_file(tmp_path, env: Dict[str, str]) -> str:
    path = tmp_path / ".env"
    path.write_text("\n".join(f"{k}={v}" for k, v in env.items()), encoding="utf-8")
    return str(path)


@pytest.fixture(autouse=True)
def _clean_process_env(monkeypatch):
    """Ensure the host's real env vars don't pollute these tests."""
    for k in list(os.environ.keys()):
        if (
            k.startswith("STRIPE_")
            or k.startswith("BILLING_")
            or k.startswith("LLM_")
            or k.startswith("DEMO_")
            or k in {"SENTRY_DSN", "GPTPROTO_API_KEY", "QWEN_API_KEY"}
        ):
            monkeypatch.delenv(k, raising=False)


def test_main_exits_0_on_clean_env(tmp_path, capsys) -> None:
    path = _write_env_file(tmp_path, _ok_env())
    rc = check_prod_env.main(["--env", path])
    assert rc == 0
    out = capsys.readouterr().out
    assert "safe to deploy" in out


def test_main_exits_1_on_error(tmp_path, capsys) -> None:
    env = _ok_env(LLM_MODE="stub")
    path = _write_env_file(tmp_path, env)
    rc = check_prod_env.main(["--env", path])
    assert rc == 1
    err = capsys.readouterr()
    assert "preflight FAILED" in err.err


def test_main_strict_promotes_warning_to_failure(tmp_path, capsys) -> None:
    env = _ok_env(SENTRY_DSN="")  # warn-only
    path = _write_env_file(tmp_path, env)
    assert check_prod_env.main(["--env", path]) == 0
    assert check_prod_env.main(["--env", path, "--strict"]) == 1


def test_main_missing_env_file_returns_2(tmp_path, capsys) -> None:
    rc = check_prod_env.main(["--env", str(tmp_path / "does_not_exist.env")])
    assert rc == 2
