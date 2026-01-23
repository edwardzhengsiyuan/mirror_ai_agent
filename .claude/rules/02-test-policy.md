# Test Policy

## Running Tests

- Default full test run (includes live LLM): `LLM_LIVE_FULL=1 pytest` (requires API config)
- Live LLM requires `LLM_API_BASE`/`LLM_API_KEY` (or OpenAI equivalents) and `LLM_MODE` not set to `stub`
- If tests are not run, the final response must say so explicitly
- **Always use `.venv/bin/python`** for running tests (not system Python)

## LLM Modes

- Use `LLM_MODE=stub` for offline/dev runs
- Use live mode only with valid API config and when needed

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
