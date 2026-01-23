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
| `bazi/` | BaZi calculation engine |
| `web/` | Web UI frontend |
| `storage/` | User data and logs |
| `tests/` | Test suite |

---

## Quick Start

```bash
# Create virtual environment
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

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
| `LLM_MODEL_REASONING` | gpt-5 | Reasoning model |
| `LLM_MODEL_FAST` | gpt-5-nano | Fast model |
| `LLM_TIMEOUT_SECONDS` | 120 | Timeout in seconds |
| `LLM_MAX_RETRIES` | 2 | Retry count |
| `LLM_PARALLEL_WORKERS` | min(8, nodes) | Concurrent thread count |
| `LLM_DEBUG` | - | Print debug logs |
| `LLM_TRACE_RAW` | false | Include raw API response in llm_response events |
| `LLM_FORCE_ERROR` | - | Force node errors (NODE1,NODE2\|ALL) |

**Note**: LLM tracing is always-on and integrated with per-session conversation storage. All LLM calls emit `llm_request`, `llm_response`, and `llm_error` events to the session's conversation JSONL file.

### Python Environment

- Use the in-repo virtual environment: `.venv/`
- Create: `python3 -m venv .venv`
- Install: `.venv/bin/pip install -r requirements.txt`
- Run tests: `.venv/bin/pytest`
- **Do not rely on system global Python** (may be restricted by PEP 668)

---

## Integration Guide

### Python Usage

```python
from agent.orchestrator import run_turn
from agent.storage.profile_store import load_profile, save_profile
from agent.storage.conversation_store import append_event, load_recent_rounds
from agent.storage.paths import session_paths
import datetime as dt

user_id = "u_demo"
profile_path, convo_path = session_paths(user_id, session_id="sess_1")
profile = load_profile(profile_path)

question = "How is my career this year?"
now = dt.datetime.now()
history_rounds = load_recent_rounds(convo_path, 5)
append_event(convo_path, {"ts": now.isoformat(), "type": "user_message", "text": question})

result = run_turn(profile, question, now=now, history_rounds=history_rounds)
# result = {"plan", "outputs", "time_context", "response", "tool_invocations"}

save_profile(profile_path, profile)
```

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
| `CLAUDE.md` | Project entry (this file) |
| `agent/CLAUDE.md` | Orchestration core (flow, DAG, caching, debugging, events) |
| `agent/tools/CLAUDE.md` | Tool interface API |
| `agent/prompts/CLAUDE.md` | Prompt template management |
| `agent/storage/CLAUDE.md` | Storage API |
| `bazi/CLAUDE.md` | Engine API reference |
| `web/CLAUDE.md` | Web UI documentation |
| `storage/CLAUDE.md` | Storage directory structure |
| `tests/CLAUDE.md` | Test documentation |
