# Agent Rules / 代理规则

## Purpose / 目的
- EN: Mandatory rules and commands the coding agent must follow for this repo.
- 中文：编码代理必须遵守的规则与命令。

---

## Mandatory Post-Change Steps / 变更后必做步骤

**After completing any code changes, the agent MUST:**

### 1. Update Documentation / 更新文档
- **Always update `DEV.md`** when changes affect:
  - Architecture or execution flow (§3 运行流程)
  - Node dependencies or DAG (§4 节点与依赖)
  - Planning logic or time handling (§5 规划逻辑)
  - Tool interfaces or parameters (§7 工具接口)
  - Prompt organization (§8 Prompt 组织)
  - Storage paths or structure (§9 存储与路径)
  - Configuration options (§10 配置)
  - Test commands or paths (§11 测试)
  - Known limitations (§12 已知限制)
- Update the **English Summary (TL;DR)** section if major behavior changes
- Update **CLAUDE.md** if rules or policies change

### 2. Run Tests / 运行测试
- **Minimum required**: `.venv/bin/python -m pytest tests/test_planning_tool_normalization.py tests/test_time_context_regex.py -v`
- **Recommended**: `.venv/bin/python tests/run_local_tester.py` (end-to-end stub test)
- **Full test** (if API available): `LLM_LIVE_FULL=1 .venv/bin/pytest`
- If tests fail, fix the issues before completing the task
- If tests are skipped, explicitly state why in the final response

### 3. Verify Changes / 验证变更
- Confirm no syntax errors: `.venv/bin/python -c "import agent.orchestrator"`
- Check storage paths are consistent with `storage/users/<user_id>/` structure
- Ensure no references to deprecated paths (e.g., `storage/profile_demo.json`, `storage/conversations/`)

---

## Update Rules / 更新规则
- Any structural/code change must update `DEV.md` if it affects architecture, APIs, dependencies, or ops.
- Any change to these rules must update `CLAUDE.md`.
- Keep the top-level `README.md` minimal (entry point only).

## Test Policy / 测试策略
- Default full test run (includes live LLM): `LLM_LIVE_FULL=1 pytest` (requires API config).
- Live LLM requires `LLM_API_BASE`/`LLM_API_KEY` (or OpenAI equivalents) and `LLM_MODE` not set to `stub`.
- If tests are not run, the final response must say so explicitly.
- **Always use `.venv/bin/python`** for running tests (not system Python).

## LLM Modes / LLM 模式
- Use `LLM_MODE=stub` for offline/dev runs.
- Use live mode only with valid API config and when needed.

## Documentation Policy / 文档策略
- Canonical dev doc: `DEV.md`.
- Canonical agent rules: `CLAUDE.md`.
- Engine API reference stays in `bazi/README.md`.
- **Documentation updates are NOT optional** - they are part of completing a task.

## Storage Structure / 存储结构
- All user data must be stored in `storage/users/<user_id>/`
- Profile: `storage/users/<user_id>/profile.json`
- Conversations: `storage/users/<user_id>/conversations/<session>.jsonl`
- Logs: `storage/logs/` (LLM trace, etc.)
- **Do not create files at `storage/` root level** (legacy structure)

## Change Checklist / 变更清单
Before marking a task as complete, verify:
- [ ] Code changes are syntactically correct (import test passes)
- [ ] `DEV.md` updated if architecture/APIs/behavior changed
- [ ] Tests run successfully (at minimum: stub tests)
- [ ] No references to deprecated paths
- [ ] Links/paths in documentation are still valid
