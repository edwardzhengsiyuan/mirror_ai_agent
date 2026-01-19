# Agent Rules / 代理规则

## Purpose / 目的
- EN: Mandatory rules and commands the coding agent must follow for this repo.
- 中文：编码代理必须遵守的规则与命令。

## Update Rules / 更新规则
- Any structural/code change must update `DEV.md` if it affects architecture, APIs, dependencies, or ops.
- Any change to these rules must update `AGENT_RULES.md`.
- Keep the top-level `README.md` minimal (entry point only).

## Test Policy / 测试策略
- Default full test run (includes live LLM): `LLM_LIVE_FULL=1 pytest` (requires API config).
- Live LLM requires `LLM_API_BASE`/`LLM_API_KEY` (or OpenAI equivalents) and `LLM_MODE` not set to `stub`.
- If tests are not run, the final response must say so explicitly.

## LLM Modes / LLM 模式
- Use `LLM_MODE=stub` for offline/dev runs.
- Use live mode only with valid API config and when needed.

## Documentation Policy / 文档策略
- Canonical dev doc: `DEV.md`.
- Canonical agent rules: `AGENT_RULES.md`.
- Engine API reference stays in `bazi/README.md`.

## Change Checklist / 变更清单
- Update docs (if impacted).
- Run tests per policy (or explicitly note skipped).
- Ensure links/paths still valid.
