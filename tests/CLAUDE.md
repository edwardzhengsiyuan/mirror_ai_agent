# Tests Documentation

Instructions for the coding agent and maintainers on how to run and extend tests.

---

## Quick Reference

```bash
# Minimum required (stub mode, fast)
.venv/bin/python -m pytest tests/test_planning_tool_normalization.py -v

# End-to-end stub test
.venv/bin/python tests/run_local_tester.py

# All stub tests
.venv/bin/python -m pytest tests/ -v

# Live LLM tests (requires API config)
LLM_LIVE_FULL=1 .venv/bin/pytest tests/test_llm_live.py -v
```

---

## Test Files Overview

### Core Unit Tests (Stub Mode)

| File | Purpose | Run Command |
|------|---------|-------------|
| `test_llm_tool_stub.py` | LLM stub placeholder output | `pytest tests/test_llm_tool_stub.py` |
| `test_planning_tool_normalization.py` | Planning tool field normalization | `pytest tests/test_planning_tool_normalization.py` |
| `test_planner_llm.py` | LLM-driven planner with mock | `pytest tests/test_planner_llm.py` |
| `test_cli_state.py` | UI state management events | `pytest tests/test_cli_state.py` |
| `test_prompt_history.py` | Conversation history loading | `pytest tests/test_prompt_history.py` |
| `test_cache_retry_on_error.py` | Auto-retry failed cache entries | `pytest tests/test_cache_retry_on_error.py` |
| `test_deps_unit.py` | DAG toposort and cycle detection | `pytest tests/test_deps_unit.py` |
| `test_planning_unit.py` | Planning functions (aspect/time detection) | `pytest tests/test_planning_unit.py` |
| `test_tools_unit.py` | Tool validation and normalization | `pytest tests/test_tools_unit.py` |
| `test_prompt_builder_unit.py` | Prompt building for all nodes | `pytest tests/test_prompt_builder_unit.py` |
| `test_edge_cases.py` | Edge cases and error handling | `pytest tests/test_edge_cases.py` |

### BaZi Engine Tests

| File | Purpose | Run Command |
|------|---------|-------------|
| `test_bazi_property.py` | Gan/Zhi enum, namespacing (ns/strip_ns) | `pytest tests/test_bazi_property.py` |
| `test_bazi_frame.py` | BaziChartAnalyseFrame basic operations | `pytest tests/test_bazi_frame.py` |

### Shared Fixtures

| File | Purpose |
|------|---------|
| `conftest.py` | Shared pytest fixtures (stub_env, sample_profile, mock_paipan, etc.) |

### Integration Tests (Stub Mode)

| File | Purpose | Run Command |
|------|---------|-------------|
| `test_parallel_execution.py` | Parallel DAG execution + caching | `pytest tests/test_parallel_execution.py` |
| `test_event_streaming_stub.py` | Full streaming event flow | `pytest tests/test_event_streaming_stub.py` |
| `test_inflight_dedup.py` | Concurrent request deduplication | `pytest tests/test_inflight_dedup.py` |
| `test_multi_time_context.py` | Multiple year queries | `pytest tests/test_multi_time_context.py` |
| `test_web_server.py` | Flask API endpoints | `pytest tests/test_web_server.py` |

### End-to-End Tests

| File | Purpose | Run Command |
|------|---------|-------------|
| `run_local_tester.py` | Multi-turn conversation replay (stub) | `python tests/run_local_tester.py` |
| `test_resume_cache_live_profiles.py` | Resume session with existing profiles | `pytest tests/test_resume_cache_live_profiles.py` |

### Live LLM Tests (Require API)

| File | Purpose | Run Command |
|------|---------|-------------|
| `test_llm_live.py` | Live LLM ping, single node, full pipeline | `pytest -m llm_live` |
| `run_live_suite.py` | Test matrix runner (scenarios) | `python tests/run_live_suite.py --scenario fast_nano` |

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_MODE` | `stub` if no API | `stub` for offline, omit for live |
| `LLM_API_BASE` | - | API endpoint URL (required for live) |
| `LLM_API_KEY` | - | API key (required for live) |
| `LLM_LIVE_FULL` | `0` | Set to `1` for full pipeline live test |
| `LLM_PLANNER_MODE` | `llm` | `rule` for keyword-based planning |
| `LLM_DEBUG` | `0` | Print debug logs |
| `LLM_TRACE_RAW` | `0` | Include raw API response in llm_response events |
| `TEST_RESUME_PROFILE` | - | Path to specific profile fixture |

---

## Test Categories

### By Speed

- **Fast (<1s)**: `test_llm_tool_stub.py`, `test_planning_tool_normalization.py`, `test_cli_state.py`, `test_prompt_history.py`, `test_cache_retry_on_error.py`, `test_deps_unit.py`, `test_planning_unit.py`, `test_tools_unit.py`, `test_prompt_builder_unit.py`, `test_bazi_property.py`, `test_bazi_frame.py`
- **Medium (1-5s)**: `test_parallel_execution.py`, `test_event_streaming_stub.py`, `test_inflight_dedup.py`, `test_multi_time_context.py`, `test_edge_cases.py`
- **Slow (5-30s)**: `run_local_tester.py`, `test_web_server.py`, `test_resume_cache_live_profiles.py`
- **Live (variable)**: `test_llm_live.py`, `run_live_suite.py`

### By pytest Markers

```bash
# Live LLM tests only
pytest -m llm_live

# Skip live tests
pytest -m "not llm_live"
```

---

## Writing New Tests

### Conventions

1. **File naming**: `test_<feature>.py` for pytest, `run_<name>.py` for standalone scripts
2. **Use stub mode by default**: Set `LLM_MODE=stub` in test setup
3. **Mock external tools**: Use `monkeypatch` for `paipan_tool`, `time_context_tool`
4. **Use pytest fixtures**: Prefer `tmp_path` for temporary files
5. **Always use `.venv/bin/python`**: Never use system Python

### Template for Stub Test

```python
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, ROOT)


def test_my_feature(monkeypatch) -> None:
    monkeypatch.setenv("LLM_MODE", "stub")

    # Mock external dependencies if needed
    from agent import execution

    def fake_paipan(inputs):
        return {
            "paipan_results": "",
            "liupan_results": "",
            "guji_results": "",
            "paipan_output": {},
            "dayun_list": [],
        }

    monkeypatch.setattr(execution, "paipan_tool", fake_paipan)

    # Test implementation
    from agent.orchestrator import run_turn

    profile = {
        "user_id": "u_test",
        "birth": {"year": 1990, "month": 1, "day": 1, "hour": 8, "minute": 0, "second": 0},
        "gender": "male",
        "birth_time_unknown": False,
        "prompt_config": "lingyun_cat",
        "node_cache": {},
    }

    result = run_turn(profile, "Test question")
    assert result["response"]
```

### Template for Live Test

```python
import pytest

@pytest.mark.llm_live
def test_my_live_feature() -> None:
    # This test requires API configuration
    api_base = os.environ.get("LLM_API_BASE")
    if not api_base:
        pytest.skip("LLM_API_BASE not configured")

    # Live test implementation
    ...
```

---

## Known Gaps

The following areas lack test coverage:

1. **Edge cases** (partially addressed in `test_edge_cases.py`):
   - Empty/whitespace-only questions
   - Very long questions
   - Boundary date values (month/hour ranges)
   - Special characters and emoji in questions
   - Malformed data raises exceptions (documented as known limitation)

2. **Error paths**:
   - Network timeouts during LLM calls
   - Rate limiting responses
   - Invalid profile.json structure (partial: missing node_cache tested)

3. **Unit tests** (mostly addressed):
   - `agent/deps.py` circular dependency detection (`test_deps_unit.py`)
   - `agent/planning.py` rule-based keyword parsing (`test_planning_unit.py`)
   - `agent/nodes/prompt_builder.py` build functions (`test_prompt_builder_unit.py`)
   - `bazi/` Gan/Zhi enums and namespacing (`test_bazi_property.py`)
   - `bazi/` BaziChartAnalyseFrame (`test_bazi_frame.py`)
   - Template fallback edge cases

4. **Performance**:
   - No benchmarks beyond parallel execution timing
   - No memory usage tests

5. **Concurrency**:
   - Race conditions in profile save/load
   - Concurrent session writes to same JSONL

---

## Troubleshooting

### Tests fail with import errors

```bash
# Ensure virtual environment is active
source .venv/bin/activate

# Or use explicit path
.venv/bin/python -m pytest tests/
```

### Live tests skip unexpectedly

Check environment variables:
```bash
echo $LLM_API_BASE
echo $LLM_API_KEY
echo $LLM_MODE  # Should NOT be "stub" for live tests
```

### Parallel tests fail with timing assertions

The timing thresholds assume reasonable system performance:
- 3 parallel nodes with 300ms sleep should complete in <1.2s
- Cache hits should complete in <0.3s

If your system is slower, adjust `sleep_ms` in test inputs or increase thresholds.

### Profile fixture not found

For `test_resume_cache_live_profiles.py`:
```bash
# Create a fixture first
python tests/run_local_tester.py

# Or specify a custom profile
TEST_RESUME_PROFILE=/path/to/profile.json pytest tests/test_resume_cache_live_profiles.py
```

---

## CI Integration

### Recommended CI stages

```yaml
# Stage 1: Fast unit tests
- name: Unit Tests
  run: .venv/bin/python -m pytest tests/test_*stub*.py tests/test_planning*.py tests/test_cli*.py tests/test_prompt*.py tests/test_cache*.py tests/test_deps*.py tests/test_tools*.py tests/test_bazi*.py -v

# Stage 2: Integration tests
- name: Integration Tests
  run: .venv/bin/python -m pytest tests/test_parallel*.py tests/test_event*.py tests/test_inflight*.py tests/test_multi*.py tests/test_web*.py tests/test_edge*.py -v

# Stage 3: End-to-end (stub)
- name: E2E Stub Test
  run: .venv/bin/python tests/run_local_tester.py

# Stage 4: Live tests (optional, requires secrets)
- name: Live LLM Tests
  if: ${{ secrets.LLM_API_KEY }}
  env:
    LLM_API_BASE: ${{ secrets.LLM_API_BASE }}
    LLM_API_KEY: ${{ secrets.LLM_API_KEY }}
    LLM_LIVE_FULL: "1"
  run: .venv/bin/python -m pytest tests/test_llm_live.py -v
```

---

## Updating This Document

When adding new tests:
1. Add entry to the appropriate table in "Test Files Overview"
2. Update "Known Gaps" if the new test addresses a gap
3. Add any new environment variables to the table
4. Update CI recommendations if needed
