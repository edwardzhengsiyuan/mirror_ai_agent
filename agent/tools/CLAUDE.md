# Tool Interfaces

API reference for agent tools: paipan, time_context, llm_report.

---

## paipan_tool(inputs)

Chart calculation tool that generates BaZi (八字) birth chart data.

**Input**

| Parameter | Type | Description |
|-----------|------|-------------|
| `birth` | object | `{year, month, day, hour, minute, second}` |
| `gender` | string | `"male"` or `"female"` |
| `birth_time_unknown` | bool | Whether birth time is missing |

**Implementation**
```
Solar.fromYmdHms(...).getLunar() → BaziChartAnalyseFrame(lunar, gender, without_time) → get_analysis_summary()
```

**Output**
```json
{
  "paipan_results": "text",
  "liupan_results": "text",
  "guji_results": "text",
  "paipan_output": {},
  "dayun_list": [...]
}
```

| Field | Description |
|-------|-------------|
| `paipan_results` | Main chart calculation text |
| `liupan_results` | Annual fortune/major luck cycle text |
| `guji_results` | Classical reference text |
| `paipan_output["yun"]` | Major luck cycle list with annual fortune `liunian`, monthly fortune `liuyue`; `startyun` is the start date/time |
| `dayun_list` | Extracted from `frame.res["yun"]`, format: `[{name, start_year, end_year, step, age_start}]`, used in planning prompts |

---

## time_context_tool(requests, birth, gender, birth_time_unknown=False)

Time context tool that retrieves major luck/annual/monthly fortune data for target years.

**Simplified interface**: Directly calls `find_yun_liu_nian_liuyue(year)` to get data for each target year, no intermediate index layer needed.

**Input**

| Parameter | Type | Description |
|-----------|------|-------------|
| `requests` | list | `[{year: int}]`, list of years to retrieve data for |
| `birth` | object | Birth info `{year, month, day, hour, minute, second}` |
| `gender` | string | `"male"` or `"female"` |
| `birth_time_unknown` | bool | Whether birth time is missing (default False) |

**Output**
```json
{
  "year_data": [
    {"year": 2026, "data": "Current dayun: 戊戌【正官正官】...Target liunian: 2026丙午...liuyue: ..."}
  ]
}
```

| Field | Description |
|-------|-------------|
| `year_data` | Each entry contains complete dayun/liunian/liuyue details for that year (from `find_yun_liu_nian_liuyue`) |

---

## llm_report_tool(system_prompt, user_prompt, model=None, node=None, sleep_ms=None, stream=False, on_delta=None, event_sink=None)

LLM call tool for generating reports.

**Parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `system_prompt` | str | System prompt for the LLM |
| `user_prompt` | str | User prompt for the LLM |
| `model` | str \| None | Model name override (default: route config) |
| `node` | str \| None | Node label for logging/tracing |
| `sleep_ms` | int \| None | Optional delay before call |
| `stream` | bool | Enable streaming response |
| `on_delta` | Callable | Callback for streaming chunks |
| `event_sink` | EventSink \| None | Event sink for LLM tracing (always-on) |

**Environment Loading**
Automatically reads `.env` from repo root (ignored if missing).

**Modes**
- `LLM_MODE=stub` or no API configured: returns placeholder output
- Otherwise calls `/chat/completions` HTTP POST

**Model Selection**
- Uses the passed `model` parameter directly
- Falls back to `LLM_MODEL` environment variable
- Falls back to the route default from `config/llm_routes.json` (`gemini-3-pro-preview` by default)
- Profile-level model stored in `profile.llm_model`, passed by orchestrator

**Retry and Timeout**
- Network error retry count: `LLM_MAX_RETRIES` (default 2)
- Timeout: `LLM_TIMEOUT_SECONDS` (default 120)

**Output Validation and Retry**
- `output_validator`: Optional callable `(content: str) -> (bool, str)` to validate output format
- `validation_retries`: Max retries for validation failures (default 2)
- When validation fails, the LLM is called again with error feedback appended to the prompt
- If validation still fails after all retries, returns error with `[LLM_VALIDATION_ERROR:...]`
- Emits `llm_validation_retry` event on each validation retry attempt

**Failure Injection**
`LLM_FORCE_ERROR=NODE1,NODE2|ALL` returns `{"error":True,"content":"[LLM_ERROR:...]"}`

**Always-On Tracing**
When `event_sink` is provided, the following events are emitted to the session's conversation JSONL:

| Event Type | When Emitted | Key Fields |
|------------|--------------|------------|
| `llm_request` | Before each API attempt | `node`, `model`, `attempt`, `url`, `timeout_seconds`, `system_prompt`, `user_prompt`, `stub` |
| `llm_response` | On successful response | `node`, `model`, `content`, `reasoning_content`, `duration_ms`, `raw?`, `stub` |
| `llm_error` | On API error (per attempt) | `node`, `model`, `attempt`, `error`, `error_type` |

Set `LLM_TRACE_RAW=1` to include raw API response in `llm_response` events.
