from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Tuple

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agent.orchestrator import run_turn
from agent.execution import ensure_node
from agent.storage.profile_store import load_profile


def _load_profile_copy(path: Path):
    data = load_profile(str(path))
    # deep copy to avoid mutating fixture in memory across tests
    return json.loads(json.dumps(data))


def _pick_fixture(prefer_substr: str | None = None) -> Tuple[dict, Path]:
    """Pick a profile fixture from storage/users (or TEST_RESUME_PROFILE env)."""
    env_path = os.environ.get("TEST_RESUME_PROFILE")
    if env_path:
        p = Path(env_path)
        if p.exists():
            return _load_profile_copy(p), p
    candidates = sorted((ROOT / "storage" / "users").glob("*/profile.json"))
    if not candidates:
        raise FileNotFoundError("no profile fixtures found under storage/users")
    if prefer_substr:
        for c in candidates:
            if prefer_substr in str(c):
                return _load_profile_copy(c), c
    return _load_profile_copy(candidates[0]), candidates[0]


def _pick_fixture_with_nodes(required_nodes: list[str]) -> Tuple[dict, Path]:
    candidates = sorted((ROOT / "storage" / "users").glob("*/profile.json"))
    for c in candidates:
        data = _load_profile_copy(c)
        cache = data.get("node_cache", {})
        if all(node in cache for node in required_nodes):
            return data, c
    pytest.skip(f"no profile fixture with nodes: {required_nodes}")


def test_resume_uses_cached_nodes_and_skips_rerun(monkeypatch) -> None:
    # Use an existing live profile fixture (already contains PAIPAN/OVERALL/etc.)
    profile, path = _pick_fixture_with_nodes(["PAIPAN", "OVERALL", "RELATIONSHIP"])
    # Force stub mode to avoid network
    monkeypatch.setenv("LLM_MODE", "stub")

    # Seed a failing node in cache to verify auto-retry clears it
    profile["node_cache"]["RELATIONSHIP"]["output"]["content"] = "[LLM_ERROR:RELATIONSHIP] simulated"
    profile["node_cache"]["RELATIONSHIP"]["output"]["error"] = True

    # On resume, asking another question should reuse existing good nodes and rerun failed ones
    question = "补充看看感情和健康"
    result = run_turn(profile, question)

    cache = profile["node_cache"]
    # Cached good nodes should remain (no deletion)
    assert "PAIPAN" in cache and cache["PAIPAN"]["output"]
    assert "OVERALL" in cache and cache["OVERALL"]["output"]
    # Failed node should have been rerun in stub mode, now no error flag
    rel_output = cache["RELATIONSHIP"]["output"]
    assert rel_output.get("error") is False
    assert not rel_output.get("content", "").startswith("[LLM_ERROR")
    assert cache["HEALTH"]["output"]["content"]


def test_resume_without_prompting_reruns_only_missing(monkeypatch) -> None:
    profile, path = _pick_fixture_with_nodes(["PAIPAN", "OVERALL"])
    monkeypatch.setenv("LLM_MODE", "stub")

    # Drop one node to simulate missing cache
    cache = profile["node_cache"]
    cache.pop("CAREER", None)

    question = "只问事业"
    result = run_turn(profile, question)

    # Missing node should be filled
    assert "CAREER" in cache
    # Already-present reasoning nodes should not be error-marked
    assert "reasoning_content" in cache["OVERALL"]["output"]


if __name__ == "__main__":
    import pytest

    os.environ.setdefault("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")
    raise SystemExit(pytest.main([__file__]))
