# Storage API

API reference for profile and conversation storage.

---

## Profile Path Helper

`agent/storage/paths.py` → `storage/users/<user_id>/profile.json`

Session logs: `storage/users/<user_id>/conversations/<session>.jsonl`

## Profile Structure

```json
{
  "user_id": "u_demo",
  "birth": {"year":1990,"month":1,"day":1,"hour":8,"minute":0,"second":0},
  "gender": "male",
  "birth_time_unknown": false,
  "prompt_config": "lingyun_cat",
  "node_cache": {}
}
```

## Cache Entry Structure

```json
{
  "created_at": "ISO timestamp",
  "inputs_hash": "sha256 hash",
  "output": {"content": "...", "error": false},
  "meta": {
    "started_at": "ISO timestamp",
    "ended_at": "ISO timestamp",
    "duration_ms": 1234
  }
}
```

See `agent/CLAUDE.md` §4 for execution caching details.

## Session Logs

`conversation_store.append_event(path, event_dict)` writes line-by-line JSONL.

### Event Types

| Type | Description |
|------|-------------|
| `user_message` | User question/input |
| `tool_invocation` | Conversation-level tool call record (PLANNER, TIME_CONTEXT), includes input/output/duration_ms/llm_prompt |
| `response` | Response generation record, includes text/input_summary/llm_prompt/duration_ms |
| `llm_prompt` | LLM call prompts (system/user) per node |
| `llm_request` | Always-on LLM tracing: request before API call, includes node/model/attempt/url/timeout_seconds/system_prompt/user_prompt/stub |
| `llm_response` | Always-on LLM tracing: response after API call, includes node/model/content/reasoning_content/duration_ms/raw?/stub |
| `llm_error` | Always-on LLM tracing: API error per attempt, includes node/model/attempt/error/error_type |
| `plan` | Legacy: planning result |
| `time_context` | Legacy: time context result |
| `assistant_final` | **Deprecated** (no longer written in new conversations) |

## Convenience Read Functions

| Function | Description |
|----------|-------------|
| `conversation_store.load_recent_rounds(path, max_rounds=5)` | Returns recent N `{"user","assistant"}` conversation pairs |
| `conversation_store.load_tool_invocations(path, tool=None)` | Returns tool invocation list |
| `conversation_store.load_responses(path)` | Returns Response event list |
| `conversation_store.load_llm_traces(path, node=None)` | Returns LLM trace events (llm_request/llm_response/llm_error), optionally filtered by node |

## Modules

- `profile_store.py`: `load_profile()`, `save_profile()`
- `conversation_store.py`: `append_event()`, `load_recent_rounds()`, `load_tool_invocations()`, `load_responses()`, `load_llm_traces()`
- `paths.py`: `session_paths()`, `profile_path()`, `conversation_path()`
