# Agent Core Documentation

For maintainers: Covers execution flow, node DAG, planning logic, caching/concurrency, debugging, and streaming events.

---

## 1. Execution Flow (`run_turn`)

### Concept Distinction
- **Persistent Node**: Stored in `profile.node_cache`, user-level cache (PAIPAN, OVERALL, SHISHEN, GEJU, WUXING_PREFS, CAREER, etc.)
- **Conversation-level Tool**: Stored in `conversation/<session>.jsonl`, each call recorded independently (PLANNER, TIME_CONTEXT)
- **Conversation-level Response**: Stored in `conversation/<session>.jsonl`, no longer cached as node (formerly FINAL)

### Execution Steps
1) **PAIPAN node** (persistent, cached): Produces chart text, structured `paipan_output`, and `dayun_list`.
2) **PLANNER tool** (conversation-level, not cached): `run_tool("PLANNER", {...})` outputs `{"aspects":[...],"times":[...]}`; emits `tool_invocation` event.
3) **Persistent node DAG**: Assembles `COMMON_PREREQS + aspects`, uses `run_nodes_parallel` for topological concurrent execution; cache hits are reused.
4) **TIME_CONTEXT tool** (conversation-level, not cached): If time context needed, `run_tool("TIME_CONTEXT", {...})` gets year data; emits `tool_invocation` event.
5) **Response generation** (conversation-level, not cached): `run_response(profile, {...})` combines all node outputs with time context to generate final answer; emits `response` event.
6) Returns result: `{"plan", "outputs", "time_context", "response", "tool_invocations"}`.
7) Upper layer saves profile (only saves persistent node cache).

---

## 2. Nodes and Dependencies (DAG)

### Persistent Nodes (cached in profile.node_cache)
- Constant `PERSISTENT_NODES = ["PAIPAN","OVERALL","SHISHEN","GEJU","WUXING_PREFS","CAREER","RELATIONSHIP","HEALTH","GUIREN","LIUQIN","XINGGE","OTHER"]`
- Constant `COMMON_PREREQS = ["PAIPAN","OVERALL","SHISHEN","GEJU","WUXING_PREFS"]`
- `DEPS`:
  - `PAIPAN`: [] (chart calculation tool)
  - `OVERALL`: [PAIPAN] (overall analysis)
  - `SHISHEN`: [PAIPAN]
  - `GEJU`: [PAIPAN, OVERALL]
  - `WUXING_PREFS`: [PAIPAN, OVERALL, SHISHEN, GEJU]
- Domain nodes `CAREER/RELATIONSHIP/HEALTH/GUIREN/LIUQIN/XINGGE/OTHER`: depend on `COMMON_PREREQS`
- Topological sort: `deps.toposort(nodes)` ensures dependencies come first.

### Conversation-level Tools (not cached, stored in conversation JSONL)
- `CONVERSATION_TOOLS = ["PLANNER", "TIME_CONTEXT"]`
- `PLANNER`: Question planning, returns aspects and times
- `TIME_CONTEXT`: Time context, returns year_data

### Response (not cached, stored in conversation JSONL)
- Former `FINAL` node renamed to Response
- No longer appears in DEPS
- Uses `run_response()` function to execute

---

## 3. Planning Logic (`planning.py`)

- Planning defaults to LLM: `LLM_PLANNER_MODE=llm` (default), LLM outputs `planning_tool` JSON call result, prompt includes dayun range hint.
- Rule fallback: `LLM_MODE=stub` or `LLM_PLANNER_MODE=rule` uses keyword/regex rules.
- Aspect classification (rules): `ASPECT_KEYWORDS` keyword matching; no match defaults to `["OTHER"]`.
- Time recognition (rules): Scans multiple time expressions and generates `times` list (year-level only).
  - Relative year: `今年/明年/去年` (this year/next year/last year) → `{need_tool: true, ref_text: "今年", year: now.year+offset}`
  - Absolute year: `YYYY年` or `YYYY年MM月` → extracts year only
- Planning merge: Even if LLM returns single time entry, regex supplements missing years from question.
- Normalization: If LLM provides year but `need_tool=false`, automatically forced to `true` to ensure time tool execution.
- **Dayun field (simplified)**: `dayun` field is optional/deprecated. LLM planning only needs to specify year, system auto-retrieves dayun info via `find_yun_liu_nian_liuyue(year)`.
- **Time range expansion**: LLM planner should expand range expressions like "next two years" into multiple year `times` entries.
- Planning prompt location: `_build_planner_prompt()` in `agent/planning.py`.

### LLM Output Schema (simplified, year only needed)
```json
{"tool":"planning_tool","args":{"aspects":["CAREER"],"times":[{"year":2025}]}}
```
- `times` supports multiple entries; `time` field is kept for compatibility, equals `times[0]`.
- Normalized time structure: `{need_tool: bool, ref_text: string|null, year: int|null}`.
- **Note**: `granularity` and `month` fields removed, system only supports year-level queries.

---

## 4. Execution, Caching, and Concurrency (`execution.py`)

- Input hash: `_hash_inputs` JSON-serializes inputs + sha256 for cache hit checking.
- Failure detection: `_is_failure_output` checks `output.error` or `content` starting with `[LLM_ERROR:` → treated as failure, cache cleared and re-run; tool exceptions wrapped as `[NODE_ERROR:...]` output with `error=true`.
- Cache structure: `profile["node_cache"][node] = {"created_at","inputs_hash","output","meta":{started_at,ended_at,duration_ms}}`.
- In-flight deduplication: During concurrency, same node in same profile instance + same inputs hash executes only once, other threads wait for event completion then reuse result.
- Concurrency: `run_nodes_parallel` uses thread pool (default `min(8,len(nodes))`, controllable via `LLM_PARALLEL_WORKERS`). Ready nodes (dependencies completed) batch-submitted; TIME_CONTEXT skipped.
- Single node execution:
  - PAIPAN → `paipan_tool`
  - TIME_CONTEXT → `time_context_tool`
  - Others → build prompt → `llm_report_tool`
- Retry: LLM tool layer controlled by `LLM_MAX_RETRIES` (default 2 attempts); execution layer has no additional retry wrapper.
- Logging: `LLM_DEBUG` prints node start/end/cache hit/wait; `meta.duration_ms` records duration.

---

## 5. Debugging Guide

- **No response/`[LLM_ERROR:*]` error**: Check `.env` BASE/KEY; or enable `LLM_MODE=stub`; check conversation JSONL for `llm_request`/`llm_response`/`llm_error` events.
- **LLM tracing**: All LLM calls are automatically traced to the session's conversation JSONL file. Use `load_llm_traces(convo_path)` to retrieve all trace events. Enable `LLM_TRACE_RAW=1` to include raw API responses.
- **Chart calculation failed**: Verify profile `birth` field is complete (includes hour:minute:second), `gender` and `birth_time_unknown` are valid; date must be within `lunar-python` supported range.
- **Cache miss/repeated execution**: Check if inputs were modified (causing `inputs_hash` change); `LLM_FORCE_ERROR` causes cache to be treated as failure and recalculated.
- **Concurrency blocking**: Verify `LLM_PARALLEL_WORKERS` is not too small; in-flight deduplication causes same node to wait for same execution to complete.
- **Empty time context**: `ref_text` didn't match rules or chart lacks corresponding year; print `plan["times"]` (or `plan["time"]`) and `time_context_tool` return value to debug.

---

## 6. Streaming Events and Node Output

### Interface
- `run_turn(profile, question, now=None, event_sink=..., stream=True)`
- Optional parameter: `history_rounds=[{"user":"...","assistant":"..."}]` for injecting recent conversation into Response prompt.

### Event Callback
`event_sink(event: dict)` called on node start/end, tool invocation, streaming output.

### Key Event Types
| Event Type | Description |
|------------|-------------|
| `tool_invocation` | Conversation-level tool call completed, contains `{tool, invocation_id, input, output, duration_ms, llm_prompt}` |
| `response` | Response generation completed, contains `{text, input_summary, llm_prompt, duration_ms}` |
| `plan` | Planning result (backward compatible, also has `tool_invocation` event) |
| `node_start` / `node_end` | Persistent node start/end; `node_end.output` is final output; cache hit has `cached=true` |
| `node_delta` | Streaming output fragment (`delta`/`reasoning_delta`) |
| `response_delta` | Response streaming output fragment |
| `tool_call` / `tool_result` | Low-level tool call and completion (paipan_tool/llm_report_tool/time_context_tool) |
| `llm_prompt` | Each LLM call's system/user prompt (for frontend audit and debugging) |
| `llm_request` | Always-on tracing: emitted before each LLM API call, contains `{node, model, attempt, url, timeout_seconds, system_prompt, user_prompt, stub}` |
| `llm_response` | Always-on tracing: emitted on successful LLM response, contains `{node, model, content, reasoning_content, duration_ms, raw?, stub}` |
| `llm_error` | Always-on tracing: emitted on LLM API error, contains `{node, model, attempt, error, error_type}` |
| `time_context` | Time context result (legacy event) |
| `assistant_final` | **Deprecated**, new conversations use `response` event |

### Tool Node Streaming
PAIPAN replays output in fragments after calculation completes, ensuring frontend receives uniform streaming events.

### Thread Safety
Execution engine may concurrently invoke event callback; recommend using thread-safe queue or lock in callback.

### UI Display Recommendations
- **Persistent nodes**: Display in separate node panel, show status (idle/running/done/cache/error) and output content.
- **Conversation-level tools** (PLANNER, TIME_CONTEXT): Display inline below user message, expandable for input/output details.
- **Response**: Display final answer in chat panel, expandable for input summary and full prompt.
