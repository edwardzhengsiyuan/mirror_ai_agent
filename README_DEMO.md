# BaZi Agent Demo API Deployment

This package exposes the existing BaZi agent as a customer-facing demo API with Swagger UI, Bearer token auth, Docker Compose deployment, and persistent local storage.

## What Is Included

- `GET /` - existing Web demo console
- `GET /docs` - Swagger UI for API testing
- `GET /openapi.json` - OpenAPI specification
- `GET /health` - health check
- `POST /v1/users` - create or update a demo user profile
- `GET /v1/users/{user_id}` - read a safe profile summary
- `POST /v1/ask` - synchronous Q&A
- `POST /v1/ask_stream` - Server-Sent Events streaming Q&A

The legacy `/api/*` endpoints remain available for the bundled Web console. Customer integrations should use `/v1/*`.

## Local Smoke Run

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe web_server.py
```

Open:

- Web console: `http://localhost:8000/`
- Swagger UI: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/health`

For real LLM calls, edit `.env` and set `LLM_MODE` empty or `auto`, plus provider keys.

Per-node model routing is managed in `config/llm_routes.json`:

- Default for unrouted nodes (`PLANNER`, `OVERALL`, `WUXING_PREFS`, `CAREER`, `RELATIONSHIP`, `HEALTH`, `GUIREN`, `LIUQIN`, `XINGGE`, `OTHER`, `RESPONSE`, `CEZI_RESPONSE`, `HEPAN_RESPONSE`) is `gptproto` + `gemini-3.1-pro-preview`.
- `SHISHEN`, `GEJU_ROUTER`, `GEJU_ANALYSIS`, `GEJU_LEVEL`, `NAJIA_RESPONSE` are pinned to `qwen` + `qwen3-max`.
- Exposed model choices currently come only from the route config: `gemini-3.1-pro-preview`, `gemini-3-flash-preview`, and `qwen3-max`.
- Requests can pass `node_model_overrides`, and profile settings can persist those overrides. Priority is node override, then route node default, then global `llm_model`, then route default.

Provider secrets stay in `.env`:

```env
GPTPROTO_API_BASE=https://gptproto.com/v1
GPTPROTO_API_KEY=...
QWEN_API_BASE=https://dashscope.aliyuncs.com/compatible-mode/v1
QWEN_API_KEY=...
```
The Qwen route uses DashScope's OpenAI-compatible endpoint by default: `https://dashscope.aliyuncs.com/compatible-mode/v1`.

## Remote Docker Deployment

### Pre-flight checklist

- Server with Docker Engine + Docker Compose v2 installed (`docker compose version` works).
- DNS A/AAAA record for the public domain pointing at the server's public IP (only if you want HTTPS).
- Inbound TCP `80` and `443` allowed in the host firewall and the cloud security group.
- Provider keys ready: `GPTPROTO_API_KEY` and `QWEN_API_KEY`.
- A long, random `DEMO_API_TOKEN` for `/v1/*` Bearer auth (rotate periodically).

### Deploy steps

```bash
cp .env.example .env
# edit .env: set DEMO_API_TOKEN to a strong token,
# fill GPTPROTO_API_KEY + QWEN_API_KEY, and set LLM_MODE empty (not "stub").
docker compose up -d --build
docker compose logs -f bazi-agent-api   # watch startup
```

The compose file ships two services: `bazi-agent-api` (Flask + waitress on internal port `8000`) and `bazi-agent-caddy` (Caddy fronting `:80`/`:443`). Storage is persisted via the host bind-mount `./storage:/app/storage`, so cache and conversation logs survive container restarts.

### HTTPS / custom domain

By default `Caddyfile` listens on plain `:80` for quick verification. Once DNS is ready, replace the `:80` block with your domain and Caddy will obtain Let's Encrypt certificates automatically:

```caddyfile
demo.example.com {
  encode gzip
  reverse_proxy bazi-agent-api:8000 {
    flush_interval -1
    transport http {
      read_timeout 10m
      write_timeout 10m
    }
  }
}
```

Reload Caddy after editing: `docker compose restart caddy`.

### Post-deploy verification

```bash
curl http://demo.example.com/health
# {"auth_configured":true,"service":"bazi-agent-api","status":"ok"}

curl -X POST http://demo.example.com/v1/users \
  -H "Authorization: Bearer $DEMO_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"user_id":"u_demo","birth":{"year":1990,"month":1,"day":1,"hour":8,"minute":0},"gender":"male"}'

curl -X POST http://demo.example.com/v1/ask \
  -H "Authorization: Bearer $DEMO_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"user_id":"u_demo","question":"今年事业怎么样？","session_id":"verify"}'
```

If any of those return non-200, inspect `docker compose logs bazi-agent-api` and `docker compose logs caddy`. The full smoke suite (BaZi stream + HePan + CeZi + Najia) is also runnable from the repo with `python scripts/smoke_e2e.py --port 80 --token $DEMO_API_TOKEN`.

### Operations notes

- `auth_configured: false` from `/health` means the container did not pick up `DEMO_API_TOKEN`; check `.env` and that `env_file: .env` is being loaded by compose.
- The waitress entrypoint is `waitress-serve --call web_server:create_app` (Python WSGI factory). To switch to gunicorn, swap the Dockerfile `CMD` to `gunicorn -w 2 -k gthread -t 600 -b 0.0.0.0:8000 'wsgi:app'` and add `gunicorn` to `requirements.txt`.
- LLM token usage and prompt traces live in `storage/users/<user>/conversations/*.jsonl` — sensitive, do not expose publicly.

## Authentication

All `/v1/*` endpoints require:

```http
Authorization: Bearer <DEMO_API_TOKEN>
```

The `/docs`, `/openapi.json`, `/health`, and existing Web UI are public by default. Do not place secrets in requests shown publicly.

## Example Request

```bash
curl -X POST http://localhost:8000/v1/ask \
  -H "Authorization: Bearer change-me-demo-token" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "u_demo",
    "birth": {"year": 1990, "month": 1, "day": 1, "hour": 8, "minute": 0, "second": 0},
    "gender": "male",
    "birth_time_unknown": false,
    "session_id": "demo_session",
    "question": "今年事业怎么样？",
    "history_n": 5
  }'
```

Response shape:

```json
{
  "request_id": "req_xxx",
  "session_id": "demo_session.jsonl",
  "user_id": "u_demo",
  "answer": "...",
  "plan": {"aspects": ["CAREER"], "time": {}, "times": []},
  "time_context": null,
  "error": false,
  "failed_nodes": [],
  "skipped_nodes": []
}
```

## Streaming Request

```bash
curl -N -X POST http://localhost:8000/v1/ask_stream \
  -H "Authorization: Bearer change-me-demo-token" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "u_demo",
    "question": "明年感情如何？",
    "session_id": "demo_session"
  }'
```

The stream emits public events only, such as `session`, `node_status`, `plan`, `tool_invocation`, `answer_delta`, `answer`, and `error`. Internal prompts and raw model traces are still stored in conversation JSONL for debugging, but are not returned through `/v1/ask_stream`.

## Storage

User profiles, node cache, and conversations are stored under:

```text
storage/users/<user_id>/
```

Docker Compose mounts `./storage:/app/storage`, so cache and conversation logs survive container restarts.

## Demo Positioning

This is a deployable ToB demo surface. It demonstrates chart calculation, planning, cache reuse, LLM integration, observability, and API integration. BaZi interpretation accuracy is not guaranteed by this demo layer.
