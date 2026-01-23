# Post-Change Requirements

After completing any code changes, the agent MUST perform the following steps:

## 1. Update Documentation

Update the **relevant documentation** based on what changed:

| Change Type | Documentation File |
|-------------|-------------------|
| Execution flow, node DAG, planning logic, caching/concurrency, streaming events | `agent/CLAUDE.md` |
| Tool interfaces (paipan, time_context, llm) | `agent/tools/CLAUDE.md` |
| Prompt organization and templates | `agent/prompts/CLAUDE.md` |
| Storage API | `agent/storage/CLAUDE.md` |
| Storage directory structure | `storage/CLAUDE.md` |
| Engine API | `bazi/CLAUDE.md` |
| Web UI | `web/CLAUDE.md` |
| Configuration, environment variables, known limitations | `CLAUDE.md` |
| Testing | `tests/CLAUDE.md` |

## 2. Run Tests

- **Minimum required**: `.venv/bin/python -m pytest tests/test_planning_tool_normalization.py -v`
- **Recommended**: `.venv/bin/python tests/run_local_tester.py` (end-to-end stub test)
- **Full test** (if API available): `LLM_LIVE_FULL=1 .venv/bin/pytest`
- If tests fail, fix the issues before completing the task
- If tests are skipped, explicitly state why in the final response

## 3. Verify Changes

- Confirm no syntax errors: `.venv/bin/python -c "import agent.orchestrator"`
- Check storage paths are consistent with `storage/users/<user_id>/` structure
- Ensure no references to deprecated paths (e.g., `storage/profile_demo.json`, `storage/conversations/`)

## Change Checklist

Before marking a task as complete, verify:
- [ ] Code changes are syntactically correct (import test passes)
- [ ] Relevant documentation updated (see table above)
- [ ] Tests run successfully (at minimum: stub tests)
- [ ] No references to deprecated paths
- [ ] Links/paths in documentation are still valid
