# Web UI

Web interface documentation for the BaZi agent.

---

## Layout Architecture

Three-column layout (ChatGPT/Claude style):

```
┌─────────────┬─────────────────────┬──────────────┐
│  Left Sidebar│      Chat Area      │  Right Panel │
│   (260px)   │       (flex)        │   (340px)    │
├─────────────┼─────────────────────┼──────────────┤
│ Session List │    Chat Messages    │ User Profile │
│             │    Tool Cards       │ Node Outputs │
│             │    Input Box        │ Event Log    │
├─────────────┤                     │              │
│ User Info   │                     │              │
│ Settings    │                     │              │
└─────────────┴─────────────────────┴──────────────┘
```

## Core Features

| Feature | Description |
|---------|-------------|
| Model selector | Dropdown in chat header to select LLM model, persists to user profile |
| Bypass cache toggle | Checkbox in settings modal to skip cache and re-run all nodes |
| Streaming response display | Listens to `response_delta` events for real-time LLM output rendering |
| Instant tool call display | `tool_call` event triggers placeholder card creation, updates on `tool_invocation` completion |
| Markdown rendering | Uses marked.js to render assistant messages (headings, lists, code blocks, quotes) |
| Chinese node names | `NODE_NAMES_ZH` mapping (e.g., PAIPAN→排盘, CAREER→事业) |
| Session history sidebar | Fetches session list and first message preview via `/api/session_metadata` |
| Responsive design | Mobile (<1024px) automatically hides sidebars |

## Backend API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/models` | GET | Returns available models and default model |
| `/api/session_metadata` | GET | Returns session list with first message preview |
| `/api/sessions` | GET/POST | List sessions / Create new session |
| `/api/users` | GET/POST | List users / Create user (accepts `llm_model`) |
| `/api/profile` | GET | Get user profile |
| `/api/profile` | PUT | Update user profile (supports `llm_model`, `prompt_config`, `bypass_cache`) |
| `/api/history` | GET | Get session message history |
| `/api/ask_stream` | POST | Streaming Q&A (SSE) |

### Model API

**GET /api/models**
```json
{
  "models": ["gemini-3.1-pro-preview", "gemini-3-flash-preview", "qwen3-max"],
  "default": "gemini-3.1-pro-preview",
  "configurable_nodes": ["SHISHEN", "GEJU_ROUTER", "RESPONSE", "..."]
}
```

**PUT /api/profile**
```json
// Request - update model
{"user_id": "u_demo", "llm_model": "gemini-3.1-pro-preview", "node_model_overrides": {"SHISHEN": "qwen3-max"}}

// Request - enable bypass cache
{"user_id": "u_demo", "bypass_cache": true}

// Response
{"success": true, "profile": {...}}
```

## Files

| File | Description |
|------|-------------|
| `web/index.html` | Frontend HTML/CSS/JS (single file) |
| `web_server.py` | Flask backend |
