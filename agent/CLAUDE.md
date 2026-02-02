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
- Constant `PERSISTENT_NODES = ["PAIPAN","OVERALL","SHISHEN","GEJU_ROUTER","GEJU_ANALYSIS","GEJU_LEVEL","WUXING_PREFS","CAREER","RELATIONSHIP","HEALTH","GUIREN","LIUQIN","XINGGE","OTHER"]`
- Constant `COMMON_PREREQS = ["PAIPAN","OVERALL","SHISHEN","GEJU_ROUTER","GEJU_ANALYSIS","GEJU_LEVEL","WUXING_PREFS"]`
- `DEPS`:
  - `PAIPAN`: [] (chart calculation tool)
  - `OVERALL`: [PAIPAN] (overall analysis)
  - `SHISHEN`: [PAIPAN]
  - `GEJU_ROUTER`: [PAIPAN, OVERALL] (格局识别 - pattern classification)
  - `GEJU_ANALYSIS`: [PAIPAN, OVERALL, GEJU_ROUTER] (格局分析 - detailed analysis based on router output)
  - `GEJU_LEVEL`: [PAIPAN, OVERALL, GEJU_ROUTER, GEJU_ANALYSIS] (格局层次 - level evaluation)
  - `WUXING_PREFS`: [PAIPAN, OVERALL, SHISHEN, GEJU_LEVEL]
- Domain nodes `CAREER/RELATIONSHIP/HEALTH/GUIREN/LIUQIN/XINGGE/OTHER`: depend on `COMMON_PREREQS`
- Topological sort: `deps.toposort(nodes)` ensures dependencies come first.

### GEJU Multi-Stage Workflow

The GEJU (格局) analysis has been split into 3 sequential nodes:

```
GEJU_ROUTER → GEJU_ANALYSIS → GEJU_LEVEL
     ↓              ↓              ↓
  格局分类      格局详细分析     格局层次评估
```

1. **GEJU_ROUTER**: Classifies the chart pattern (正格/特殊格局/杂格/无格) and outputs JSON with `category` and `patterns` array.
2. **GEJU_ANALYSIS**: Dynamically selects prompt based on router output (e.g., `正官格` uses `# 正格_正官格.md`).
3. **GEJU_LEVEL**: Evaluates pattern quality using "有情/有力" (harmony/strength) principles.

Prompt files are located in `agent/prompts/geju/`. Router output is parsed to select the appropriate analysis prompt.

**GEJU_ROUTER Output Validation**: The router output is validated to ensure correct JSON format with required fields (`category`, `patterns`). If validation fails, the LLM is retried with error feedback (up to 2 retries). See `NODE_VALIDATORS` in `prompt_builder.py`.

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

- Planning defaults to LLM: `LLM_PLANNER_MODE=llm` (default), LLM outputs `planning_tool` JSON call result, prompt includes dayun range hint and conversation history.
- Rule fallback: `LLM_MODE=stub` or `LLM_PLANNER_MODE=rule` uses keyword/regex rules.
- **History context**: PLANNER receives `history_rounds` from orchestrator and includes truncated conversation history in the prompt for better context understanding.
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

- **Cache key**: `_cache_key_inputs` JSON-serializes inputs (excluding `model` field) + sha256 for model-agnostic cache lookup.
- **Full input hash**: `_hash_inputs` JSON-serializes all inputs + sha256 for debugging/reference.
- Failure detection: `_is_failure_output` checks `output.error` or `content` starting with `[LLM_ERROR:` → treated as failure, cache cleared and re-run; tool exceptions wrapped as `[NODE_ERROR:...]` output with `error=true`.
- Cache structure: `profile["node_cache"][node] = {"created_at","cache_key","inputs_hash","output","meta":{started_at,ended_at,duration_ms}}`.
- **Failed outputs NOT cached**: When a node fails, its output is NOT stored in cache. This ensures automatic retry on the next request without requiring manual cache eviction.
- In-flight deduplication: During concurrency, same node in same profile instance + same cache_key executes only once, other threads wait for event completion then reuse result.
- Concurrency: `run_nodes_parallel` uses thread pool (default `min(8,len(nodes))`, controllable via `LLM_PARALLEL_WORKERS`). Ready nodes (dependencies completed) batch-submitted; TIME_CONTEXT skipped.
- **Workflow stops on failure**: When a node fails, all dependent nodes are automatically skipped (marked with `error=true, skipped=true`). This prevents wasted computation and avoids generating responses with incomplete data.
- Single node execution:
  - PAIPAN → `paipan_tool`
  - TIME_CONTEXT → `time_context_tool`
  - Others → build prompt → `llm_report_tool`
- Retry: LLM tool layer controlled by `LLM_MAX_RETRIES` (default 2 attempts); execution layer has no additional retry wrapper.
- Logging: `LLM_DEBUG` prints node start/end/cache hit/wait; `meta.duration_ms` records duration.

### Model-Agnostic Cache Behavior

Cache lookup is **model-agnostic** by default. The `cache_key` is computed excluding the `model` field, so switching LLM models will still use cached outputs if the `prompt_config` remains the same.

| Node | Inputs | Cache Key | Behavior on Model Switch |
|------|--------|-----------|-------------------------|
| PAIPAN | `{birth, gender, birth_time_unknown}` | Same (no model) | **Cache hit** |
| LLM nodes (OVERALL, SHISHEN, etc.) | `{prompt_config, model}` | Excludes model | **Cache hit** (reuses previous model's output) |

**Rationale**: In most cases, users want fast responses and don't need to regenerate all analysis when switching models. The cache persists previous outputs regardless of which model generated them.

**Backward compatibility**: Old cache entries with only `inputs_hash` (no `cache_key`) will still work. The system falls back to checking `inputs_hash` if `cache_key` is not present, and cache entries are upgraded to the new format when overwritten.

### Bypass Cache Setting

To force re-running all nodes and ignore cached outputs, use either:

1. **Environment variable**: `LLM_BYPASS_CACHE=1`
2. **Profile field**: `profile.bypass_cache = true` (settable via UI toggle)

When bypass is enabled:
- All cache lookups are skipped
- Nodes always execute fresh
- Results are still saved to cache (for next time when bypass is off)
- `LLM_DEBUG` logs will show "bypass_cache enabled, skipping cache lookup for {node}"

### Error Handling in `run_turn`
- After DAG execution, orchestrator checks for failed nodes (nodes with `error=true` but not `skipped`)
- If any critical node failed, returns early with clean error response instead of generating response with bad data
- Return structure includes: `error=true`, `failed_nodes=["NODE1", ...]`, `skipped_nodes=["NODE2", ...]`
- Error response is user-friendly Chinese: `"无法完成分析，以下节点执行失败：...。请稍后重试。"`

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
| `node_start` / `node_end` | Persistent node start/end; `node_end.output` is final output; cache hit has `cached=true`; error has `error=true` |
| `node_failed` | Node execution failed, contains `{node, error}` - emitted when a node completes with error |
| `node_skipped` | Node skipped due to failed prerequisite, contains `{node, reason}` |
| `workflow_error` | Critical failure in DAG, contains `{failed_nodes, skipped_nodes, message}` - response generation aborted |
| `node_delta` | Streaming output fragment (`delta`/`reasoning_delta`) |
| `response_delta` | Response streaming output fragment |
| `tool_call` / `tool_result` | Low-level tool call and completion (paipan_tool/llm_report_tool/time_context_tool) |
| `llm_prompt` | Each LLM call's system/user prompt (for frontend audit and debugging) |
| `llm_request` | Always-on tracing: emitted before each LLM API call, contains `{node, model, attempt, url, timeout_seconds, system_prompt, user_prompt, stub}` |
| `llm_response` | Always-on tracing: emitted on successful LLM response, contains `{node, model, content, reasoning_content, duration_ms, raw?, stub}` |
| `llm_error` | Always-on tracing: emitted on LLM API error, contains `{node, model, attempt, error, error_type}` |
| `llm_validation_retry` | Emitted when output validation fails and retry is attempted, contains `{node, attempt, error, invalid_output_preview}` |
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
