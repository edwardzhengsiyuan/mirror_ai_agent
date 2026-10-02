# BaZi Agent

Backend agent for BaZi (八字, Four Pillars) Q&A: chart calculation (paipan), planning, caching, LLM integration, time context, and web API.

> Focus: Operability and maintainability. BaZi interpretation accuracy is out of scope.

---

## Overview

**Goals**
- On-demand planning with minimal node execution
- Cacheable and reusable computations
- Observable and testable architecture

**Non-goals**
- No guarantee of BaZi conclusion accuracy
- No complex evaluation systems
- UI/conversation management left to upper layers

**Entry Points**
- `app.py`: CLI entry point, loads/saves user profiles
- `web_server.py`: HTTP/SSE service and frontend interface

**Core Flow**
`agent/orchestrator.py` → Planning → DAG Execution → Time Context → Response Assembly

---

## Directory Structure

| Directory/File | Description |
|----------------|-------------|
| `app.py` | CLI entry point |
| `web_server.py` | HTTP/SSE service |
| `agent/` | Orchestration core (planning, deps, execution, nodes, response) |
| `agent/tools/` | Tool implementations (paipan, time_context, llm) |
| `agent/prompts/` | Prompt templates |
| `agent/storage/` | Profile/conversation storage |
| `agent/billing/` | Credit accounting (SQLite-backed users / api_keys / ledger) |
| `bazi/` | BaZi calculation engine |
| `web/` | Web UI frontend |
| `storage/` | User data and logs |
| `tests/` | Test suite |
| `config/pricing.json` | Per-endpoint price book (credits) |

---

## Quick Start

```bash
# Create virtual environment
python3 -m venv .venv
.venv/bin/pip install --require-hashes -r requirements.lock

# Run CLI (stub mode)
LLM_MODE=stub .venv/bin/python app.py --profile storage/users/u_demo/profile.json --question "How is my career this year?"

# Run Web service
.venv/bin/python web_server.py
```

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_API_BASE` / `OPENAI_API_BASE` | - | API endpoint URL |
| `LLM_API_KEY` / `OPENAI_API_KEY` | - | API key |
| `LLM_MODE` | - | `stub` for placeholder output |
| `LLM_MODEL` | gemini-3.1-pro-preview | Default model name (user-selectable via UI or env var) |
| `PORT` | 8000 | HTTP listen port for `web_server.py` |
| `HOST` | 0.0.0.0 | HTTP listen host |
| `LLM_TIMEOUT_SECONDS` | 120 | Timeout in seconds |
| `LLM_MAX_RETRIES` | 2 | Retry count |
| `LLM_PARALLEL_WORKERS` | min(8, nodes) | Concurrent thread count |
| `LLM_DEBUG` | - | Print debug logs |
| `LLM_TRACE_RAW` | false | Include raw API response in llm_response events |
| `LLM_FORCE_ERROR` | - | Force node errors (NODE1,NODE2\|ALL) |
| `LLM_BYPASS_CACHE` | false | Skip all cache lookups and re-run nodes |
| `BILLING_DB_PATH` | `<storage>/billing.db` | SQLite path for billing state |
| `BILLING_INFLIGHT_LIMIT` | 2 | Max concurrent billable requests per user |
| `BILLING_RATE_LIMIT_PER_MIN` | 10 | Max requests per minute per API key |
| `AUTH_LOGIN_PER_MIN` | 20 | Login attempts per minute, separately limited by source IP and normalized email |
| `AUTH_REGISTER_PER_MIN` | 10 | Registrations per minute per source IP, shared by both signup routes |
| `APP_TRUSTED_PROXY_HOPS` | 0 | Trusted reverse-proxy hop count for client IP/protocol; set only when the origin is reachable exclusively through that proxy chain |
| `APP_SECRET_KEY` | required outside stub mode | Stable random secret (at least 32 characters in production); signs sessions and derives portal-key encryption unless a dedicated key ring is configured |
| `BILLING_KEY_ENCRYPTION_KEYS` | derived from `APP_SECRET_KEY` | Optional comma-separated Fernet keys, newest first; keep outside the database and preserve for backup recovery |

**Available Models** (canonical list lives in `config/llm_routes.json`):
- `gemini-3.1-pro-preview` (default, gptproto provider)
- `gemini-3-flash-preview` (gptproto provider)
- `qwen3-max` (qwen provider, used by GEJU and NAJIA node overrides)

`agent/models.py` is a backwards-compatibility shim — the live source of truth is `agent/llm_config.py` reading `config/llm_routes.json`. Per-node routing/overrides are configured under `nodes` in the same JSON file.

**Note**: `LLM_MODEL_REASONING` and `LLM_MODEL_FAST` are deprecated. Use `LLM_MODEL` (global default) or the per-profile `llm_model` / `node_model_overrides` fields instead. Node-level overrides win over the global default.

**Cache behavior**: Cache lookup is model-agnostic by default. LLM node keys include the rendered prompts (templates and consumed upstream content), input context, and chart identity. A model-only change can reuse matching outputs; template/upstream/chart changes invalidate them. Older LLM entries miss once after this change. Use `LLM_BYPASS_CACHE=1` or `profile.bypass_cache=true` to force re-run all nodes.

**HTTP concurrency and streaming**: Requests modifying the same profile share an OS file lease and conflicts return `409 profile_busy`. SSE sends heartbeats every 15 seconds and bounds each client's queue to 256 events / 2 MiB. Disconnect or overflow stops delivery; the worker finishes persistence and billing in the background. Pending charges left by process termination require explicit reconciliation with `scripts/reconcile_billing.py`; see `agent/billing/AGENTS.md`.

**Note**: LLM tracing is always-on and integrated with per-session conversation storage. All LLM calls emit `llm_request`, `llm_response`, and `llm_error` events to the session's conversation JSONL file.

### Windows Docker execution

- Before local Docker work, use the existing audited `../autoworker/scripts/docker-preflight.ps1` when available; its default mode is read-only. Read that project's `docs/DOCKER_EXECUTION_TROUBLESHOOTING.md` before diagnosing startup failures on this machine.
- Never start Docker Desktop using `Start-Process`, `docker desktop start`, or a newly created `Shell.Application.ShellExecute`. The Codex MSIX command context has reproduced AF_UNIX endpoint access failures through these paths.
- When startup is needed, use the audited preflight's explicit `-StartDesktop`: it obtains the existing Explorer desktop through `FindWindowSW(...SWC_DESKTOP...)` and calls that desktop's `Document.Application.ShellExecute`. Existing Desktop/backend processes must not be started again; if the desktop interface is unavailable, stop and report it.
- Do not delete or rename endpoints, reset Docker data, alter ACLs/isolation, or create scheduled-task workarounds. Distinguish permission failures from an unavailable daemon, and verify engine readiness independently of process startup.

### Python Environment

- Use the in-repo virtual environment: `.venv/`
- Create: `python3 -m venv .venv`
- Install: `.venv/bin/pip install --require-hashes -r requirements.lock`
- `requirements.txt` declares direct dependencies; regenerate `requirements.lock` with `pip-compile --generate-hashes --no-emit-index-url --output-file requirements.lock requirements.txt` and run dependency audits before updates.
- Run tests: `.venv/bin/pytest`
- **Do not rely on system global Python** (may be restricted by PEP 668)

---

## Integration Guide

### Python Usage

```python
from agent.orchestrator import run_turn
from agent.storage.profile_store import edit_profile
from agent.storage.conversation_store import append_event, load_recent_rounds
from agent.storage.paths import session_paths
import datetime as dt

user_id = "u_demo"
profile_path, convo_path = session_paths(user_id, session_id="sess_1")

question = "How is my career this year?"
now = dt.datetime.now()
with edit_profile(profile_path) as profile:
    history_rounds = load_recent_rounds(convo_path, 5)
    append_event(convo_path, {"ts": now.isoformat(), "type": "user_message", "text": question})
    result = run_turn(profile, question, now=now, history_rounds=history_rounds)
    # Successful context exit saves atomically; exceptions preserve the previous file.
```

`edit_profile` shares the HTTP lease and protects the whole read/compute/save operation. Raw `load_profile` / `save_profile` remain low-level primitives and must not be combined into an unprotected concurrent editor. The lock format changed to `<canonical-profile-path>.lock`; stop old service instances before upgrading.

### Storage maintenance and acceptance

- Portal API keys use authenticated encryption at rest; authentication still uses SHA-256 key hashes. Run `scripts/secure_billing_keys.py --help` for offline legacy migration, consistent backup, WAL cleanup and key rotation. Old backups remain sensitive.
- Preview conversation retention with `.venv/bin/python scripts/prune_conversations.py --storage storage --days 90`. `--apply` removes eligible logs; active profile leases and external symlinks are excluded. No automatic deletion is scheduled.
- Reproduce TLS, secure-cookie, signed-webhook replay and SSE billing acceptance using `docker-compose.audit.yml` and `scripts/smoke_local_https.py`. This stack is local-only with synthetic keys and tmpfs data, never a production deployment.
- `scripts/check_live_service.py --base https://YOUR_HOST` only probes public health and anonymous access boundaries. It cannot certify deployed revision, paid model execution or real payment completion.

### HTTP API

For HTTP JSON interface, wrap: `POST /ask`
- Request: `{user_id, question, session_id?}`
- Response: `{plan, time_context, response, cache_keys?}`

Streaming interface `POST /api/ask_stream` also pushes `llm_prompt`, `llm_request`, `llm_response`, and `llm_error` events for full LLM tracing.

---

## Known Limitations

- **Simple planning**: Keywords + regex only; context memory injects only recent N rounds (default 5, configurable)
- **Time parsing**: LLM planner can handle time range expressions (e.g., "next two years"), expanding to multiple year entries; rule mode only supports relative/absolute year
- **LLM retry**: Only at tool layer per `LLM_MAX_RETRIES`; unified 3-retry or circuit breaker requires execution layer wrapper
- **Prompt fallback**: Missing upstream content inserts empty string
- **Security**: Repo contains example `.env`; replace keys in production

---

## BaZi Domain Glossary

Chinese terms preserved in code and documentation:

| Chinese (Pinyin) | English | Description |
|------------------|---------|-------------|
| 八字 (bazi) | Four Pillars | Birth chart based on year, month, day, hour |
| 排盘 (paipan) | Chart Calculation | Computing the full birth chart |
| 十神 (shishen) | Ten Gods | Relationship types between stems |
| 大运 (dayun) | Major Luck Cycle | 10-year fortune periods |
| 流年 (liunian) | Annual Fortune | Year-by-year fortune |
| 流月 (liuyue) | Monthly Fortune | Month-by-month fortune |
| 五行 (wuxing) | Five Elements | Wood, Fire, Earth, Metal, Water |
| 五行喜忌 (wuxing xiji) | Five Element Preferences | Favorable/unfavorable elements |
| 格局 (geju) | Chart Pattern | Overall chart structure type |
| 天干 (tiangan) | Heavenly Stems | 10 cyclical characters |
| 地支 (dizhi) | Earthly Branches | 12 cyclical characters |
| 神煞 (shensha) | Spirit Influences | Special star/spirit indicators |
| 贵人 (guiren) | Noble Helper | Beneficial influence indicator |
| 六亲 (liuqin) | Six Relations | Family relationship indicators |
| 性格 (xingge) | Personality | Character analysis |
| 纳音 (nayin) | Elemental Sound | 60 Jiazi cycle elements |
| 地势 (dishi) | Life Phase | 12 stages of element strength |

---

## Documentation Index

| Documentation | Description |
|---------------|-------------|
| `AGENTS.md` | Project entry (this file) |
| `agent/AGENTS.md` | Orchestration core (flow, DAG, caching, debugging, events) |
| `agent/tools/AGENTS.md` | Tool interface API |
| `agent/prompts/AGENTS.md` | Prompt template management |
| `agent/storage/AGENTS.md` | Storage API |
| `bazi/AGENTS.md` | Engine API reference |
| `web/AGENTS.md` | Web UI documentation |
| `storage/AGENTS.md` | Storage directory structure |
| `tests/AGENTS.md` | Test documentation |
