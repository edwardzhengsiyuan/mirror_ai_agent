# BaZi Agent Demo API Deployment

This package exposes the existing BaZi agent as a customer-facing demo API with Swagger UI, Bearer token auth, Docker Compose deployment, and persistent local storage.

## What Is Included

- `GET /` - existing Web demo console
- `GET /billing.html` - user self-service portal (balance / usage / API keys)
- `GET /admin.html` - admin console (open users / topup / ledger; needs `DEMO_API_TOKEN`)
- `GET /docs` - Swagger UI for API testing
- `GET /openapi.json` - OpenAPI specification
- `GET /health` - health check
- `POST /v1/users` (admin) - create or update a profile (birth chart info)
- `GET /v1/users/{user_id}` (admin) - read a safe profile summary
- `POST /v1/ask`, `POST /v1/ask_stream` - BaZi Q&A (billed)
- `POST /v1/hepan/ask`, `POST /v1/cezi/ask`, `POST /v1/najia/ask`, `POST /v1/zwds/ask` - other divination systems (billed)
- `GET /v1/balance`, `GET /v1/usage` - user billing self-service
- `POST /v1/api_keys`, `GET /v1/api_keys`, `DELETE /v1/api_keys/{prefix}` - user API key management
- `POST /admin/users`, `GET /admin/users`, `POST /admin/users/{id}/status` - admin user management
- `POST /admin/topup`, `GET /admin/ledger`, `GET /admin/pricing` - admin billing management

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

## Authentication & Billing

The server now runs **two parallel auth schemes** for `/v1/*` endpoints:

| Scheme | Token | Use case | Charged? |
|--------|-------|----------|----------|
| **User API key** | `Bearer <api_key>` issued via `/admin/users` or `/v1/api_keys` | Customer-facing requests | Yes — credits deducted per call |
| **Admin token** | `Bearer <DEMO_API_TOKEN>` | Internal smoke tests, the `/admin/*` endpoints, the bundled Web UI | No — admin requests bypass billing |

`/docs`, `/openapi.json`, `/health`, and the existing Web UI remain public.

### Pricing (defaults in `config/pricing.json`)

1 元 = 100 credits. Override per deploy by editing the JSON file (and restarting).

| Endpoint | Cost (credits) | Notes |
|----------|---------------:|-------|
| `/v1/cezi/ask`  | 30 | cheapest |
| `/v1/najia/ask` | 50 | + 30 with `paraphrase=true` |
| `/v1/zwds/ask`  | 80 | + 70 with `include_star_gong=true` |
| `/v1/hepan/ask` | 100 | requires two BaZi computations |
| `/v1/ask`, `/v1/ask_stream` | 200 | full BaZi DAG |

Default for any unconfigured endpoint: 50 credits.

### Concurrency & rate limits

- Per user: **≤ 2** in-flight billable requests (overrides via `BILLING_INFLIGHT_LIMIT`).
- Per API key: **≤ 10** requests / minute (overrides via `BILLING_RATE_LIMIT_PER_MIN`).

### Admin cheatsheet

```bash
# 1. Create a user with starting credits and get a one-time API key
curl -X POST http://localhost:8000/admin/users \
  -H "Authorization: Bearer $DEMO_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"user_id":"u_alice","display_name":"Alice","initial_credits":1000}'
# response: {"user": {...}, "api_key": "<save-this-now>"}

# Optional: cap the daily spend (resets at UTC midnight). Add this on
# create or via PATCH-equivalent UPDATE on the users table. The check
# fires inside charge() and returns 402 with code=daily_limit_exceeded.
#   {"user_id":"u_capped","initial_credits":10000,"daily_credits_limit":300}

# 2. Top up (idempotent on request_id — safe for payment webhooks)
curl -X POST http://localhost:8000/admin/topup \
  -H "Authorization: Bearer $DEMO_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"user_id":"u_alice","amount_credits":500,"note":"promo"}'

# 3. List users / ledger / pricing
curl -H "Authorization: Bearer $DEMO_API_TOKEN" http://localhost:8000/admin/users
curl -H "Authorization: Bearer $DEMO_API_TOKEN" "http://localhost:8000/admin/ledger?user_id=u_alice&limit=20"
curl -H "Authorization: Bearer $DEMO_API_TOKEN" http://localhost:8000/admin/pricing

# 4. Disable / re-enable a user (e.g. fraud, abuse)
curl -X POST http://localhost:8000/admin/users/u_alice/status \
  -H "Authorization: Bearer $DEMO_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"status":"disabled"}'
```

**Web UIs**: open `/admin.html` for a one-page admin console (paste `DEMO_API_TOKEN` once, then create/topup/inspect via buttons), or use the PowerShell helpers:

```powershell
. .\scripts\admin.ps1
Set-BillingAdmin -BaseUrl "https://demo.example.com" -Token $env:DEMO_API_TOKEN
New-BillingUser -UserId u_alice -InitialCredits 1000 -DisplayName "Alice"
Invoke-Topup -UserId u_alice -Amount 500 -Note "promo"
Get-BillingLedger -UserId u_alice -Limit 20
Get-BillingPricing
```

### User cheatsheet

```bash
# Check balance + recent usage
curl -H "Authorization: Bearer $API_KEY" http://localhost:8000/v1/balance
curl -H "Authorization: Bearer $API_KEY" "http://localhost:8000/v1/usage?limit=20"

# Issue a second API key (e.g. for a phone app) and revoke it later
curl -X POST -H "Authorization: Bearer $API_KEY" -H "Content-Type: application/json" \
  -d '{"label":"phone-app"}' http://localhost:8000/v1/api_keys
# Response includes the new "api_key" field — store it now (won't be shown again).

curl -H "Authorization: Bearer $API_KEY" http://localhost:8000/v1/api_keys
curl -X DELETE -H "Authorization: Bearer $API_KEY" \
  http://localhost:8000/v1/api_keys/<first-12-hex-of-the-key>
```

A self-service web page is bundled at `/billing.html` — it stores the API key in `localStorage` and shows balance, usage and active keys.

### Response headers (billed requests only)

Every billed request returns:

- `X-Charged-Credits: <int>` — how many credits this call cost.
- `X-Balance-After: <int>` — the user's remaining balance after settlement.
- `X-Request-Id: <uuid>` — pass back as `X-Request-Id` on retries to make the call idempotent.

### SSE billing events

`/v1/ask_stream` emits two extra events (in addition to `session`, `plan`, `response_delta`, etc.):

```json
{"type":"billing","stage":"charged","amount_credits":200,"balance_after":800,...}
{"type":"billing","stage":"settled","amount_credits":200,"balance_after":800,...}
```

If the worker fails mid-stream, the final billing event has `stage:"refunded"` and the balance is restored.

### Token / latency tracking

Every successful charge stores LLM usage stats in the ledger row's `meta_json`:

```json
{
  "llm_usage": {"prompt_tokens": 1234, "completion_tokens": 567,
                "total_tokens": 1801, "node_count": 5},
  "duration_ms": 12340,
  "variant_params": ["paraphrase=True"]
}
```

These show up in `GET /v1/usage` and `GET /admin/ledger` responses. They're recorded on a best-effort basis: stub mode and providers that don't return a `usage` block (some streaming responses) will leave `node_count: 0`.

### Storage

Billing data lives in `storage/billing.db` (SQLite, WAL mode). Override with the `BILLING_DB_PATH` env var. The repo's Docker bind-mount (`./storage:/app/storage`) already persists this across container restarts.

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
