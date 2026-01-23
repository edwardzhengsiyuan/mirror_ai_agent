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

## llm_report_tool(system_prompt, user_prompt, model=None, node=None, sleep_ms=None)

LLM call tool for generating reports.

**Environment Loading**
Automatically reads `.env` from repo root (ignored if missing).

**Modes**
- `LLM_MODE=stub` or no API configured: returns placeholder output
- Otherwise calls `/chat/completions` HTTP POST

**Model Selection**
- `model="reasoning"` → `LLM_MODEL_REASONING`
- Otherwise uses `LLM_MODEL_FAST` (default gpt-5-nano)

**Retry and Timeout**
- Retry count: `LLM_MAX_RETRIES` (default 2)
- Timeout: `LLM_TIMEOUT_SECONDS` (default 120)

**Failure Injection**
`LLM_FORCE_ERROR=NODE1,NODE2|ALL` returns `{"error":True,"content":"[LLM_ERROR:...]"}`

**Trace**
`LLM_TRACE=1` logs request/response/forced_error to `storage/logs/llm_trace.jsonl` (`LLM_TRACE_PATH` can override)
