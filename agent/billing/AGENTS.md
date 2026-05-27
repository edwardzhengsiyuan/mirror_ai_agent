# Billing Module

Credit accounting for `/v1/*` endpoints: per-user balances, API keys, ledger,
in-flight limits, and rate limiting.

> Source of truth for prices: `config/pricing.json`.
> Source of truth for state: `storage/billing.db` (SQLite, WAL mode).

---

## Files

| File | Purpose |
|------|---------|
| `store.py` | Low-level SQLite CRUD. Owns the schema (`users` / `api_keys` / `ledger` / `inflight` / `rate_events`). |
| `service.py` | High-level operations: `authenticate`, `charge`, `settle`, `refund`, `topup`, `issue_api_key`, `revoke_api_key`, `get_balance`, `list_usage`, `update_charge_meta`. Idempotent on `request_id`. |
| `pricing.py` | Loads `config/pricing.json`. `Pricing.cost(endpoint, variant_params)` returns credits. |
| `middleware.py` | Flask helpers: `BillingHelpers.authenticate_request`, `try_charge`, `settle`, `refund`, `with_billing` decorator. |
| `errors.py` | Exception hierarchy. |
| `stripe_gateway.py` | Stripe SDK façade: `StripeGateway.from_env()`, `build_checkout_session()`, `verify_webhook()`, `parse_checkout_completed()`, `resolve_amount(pack_id|custom_yuan)`. Loads pack catalog from `config/stripe_packs.json`. |

`BillingService` is composed in `web_server.create_app` and held inside the
`BillingHelpers` instance. Each endpoint calls `_begin_billed_request(...)`
(in `web_server.py`) and uses the returned closures to charge / settle / refund.

---

## Schema (5 tables)

- `users(user_id PK, balance_credits, status active|disabled, daily_credits_limit, ...)`
- `api_keys(api_key_hash PK, user_id FK, label, created_at, last_seen_at, revoked)` — keys stored as `sha256(plaintext)`; plaintext is shown only once.
- `ledger(id PK, user_id, request_id UNIQUE, endpoint, kind charge|refund|topup, amount_credits, balance_after, status pending|settled|refunded, meta_json, ts)`
- `inflight(request_id PK, user_id, endpoint, started_at)` — cleared on settle / refund.
- `rate_events(id PK, scope, ts_epoch)` — rolling 60s window keyed by `key:<api_key_hash>`.

All write paths use `BEGIN IMMEDIATE` to take the writer lock up front.

---

## Charging flow (sync endpoint)

1. **Authenticate** — `BillingHelpers.authenticate_request(allow_admin_bypass=True)` resolves the bearer token to either `{user_id, key_hash, ...}` or `{is_admin: True}`. Admin requests skip steps 2–5 entirely.
2. **Validate the payload** — return early on 4xx without touching credits.
3. **Charge** — `service.charge(user_id, endpoint, cost, request_id)` deducts credits atomically and inserts a `pending` ledger row + an `inflight` slot. Raises `InsufficientFundsError` (→ 402, code `insufficient_funds`), `DailyLimitExceededError` (→ 402, code `daily_limit_exceeded`, computed from today's UTC charges − refunds vs. `users.daily_credits_limit`), `InflightLimitError` (→ 429), `DuplicateRequestError` (→ 409).
4. **Run the work** through a sink wrapped by `ctx["wrap_sink"]`, which observes `llm_usage` events from `llm_tool` and aggregates `prompt_tokens` / `completion_tokens` / `node_count`.
5. **Settle on success** (`service.settle(request_id)`) or **refund on failure** (`service.refund(request_id, reason)`). The wrapper persists the aggregated token counts and `duration_ms` into the charge row's `meta_json` via `update_charge_meta` immediately before settle/refund. Both calls clear the inflight slot and are idempotent.

For SSE (`/v1/ask_stream`), step 3 happens before launching the worker so failed-charge errors return as plain HTTP 402; steps 4–5 execute inside the worker's `finally`, and a `billing` SSE event is emitted on settle/refund.

---

## Idempotency

`charge`, `settle`, `refund`, and `topup` are all idempotent on `request_id`:

- Re-sending the same `request_id` to `charge` raises `DuplicateRequestError` (→ HTTP 409) without double-charging.
- Re-calling `settle` / `refund` after the first call is a no-op.
- `topup` with the same `request_id` returns the original receipt (HTTP 200 with `duplicate: true`).

Clients can safely retry network-flapping calls by reusing `X-Request-Id`.

---

## Pricing

```json
{
  "default_credits": 100,
  "endpoints":  {"/v1/cezi/ask": 100, "/v1/najia/ask": 200, "/v1/hepan/ask": 300, "/v1/zwds/ask": 400, "/v1/ask": 500, "/v1/ask_stream": 500},
  "variants":   {"/v1/zwds/ask?include_star_gong=true": 700, "/v1/najia/ask?paraphrase=true": 400}
}
```

1 元 = 100 credits = 100 fen (CNY's smallest unit). This invariant lets
us trust Stripe's `amount_total` (returned in fen) as the credit count
when topping up via the webhook.

Variant lookup precedence: `variants[exact_key] > endpoints[endpoint] > default_credits`.
Variant keys are built deterministically (`sorted(name=lowercased_value)`)
so booleans `True`, the string `"true"`, and the string `"True"` all match.

---

## Authentication scheme

| Mode | Source | Use case |
|------|--------|----------|
| User key | `Authorization: Bearer <api_key>` (43-char URL-safe token) | Customer requests; charged. |
| Admin token | `Authorization: Bearer <DEMO_API_TOKEN>` | Smoke tests, the bundled Web UI, all `/admin/*` endpoints; never charged. |

The web layer adds a defensive **`user_id` mismatch check** on business
endpoints: when authenticated as a real user, any `user_id` field in the
body must equal the auth-bound user_id. Admin requests can pass any user_id
(legacy behavior).

---

## Stripe payments

`stripe_gateway.StripeGateway` is constructed once in
`web_server.create_app` from environment variables (`STRIPE_MODE`,
`STRIPE_SECRET_KEY_TEST/_LIVE`, `STRIPE_WEBHOOK_SECRET_TEST/_LIVE`,
`STRIPE_SUCCESS_URL`, `STRIPE_CANCEL_URL`,
`STRIPE_PAYMENT_METHODS`). The Stripe SDK is imported lazily inside the
two methods that need it (`build_checkout_session`, `verify_webhook`) so
the rest of the codebase still loads when `stripe` isn't installed.

`STRIPE_PAYMENT_METHODS` is a comma-separated list (default
`card,wechat_pay`). Methods listed here must also be turned on per
account in the Stripe dashboard — listing `wechat_pay` when the account
has not enabled it makes Session.create return 4xx. The list is
echoed by `/v1/topup_packs` so the frontend can render the right hint.

Three HTTP endpoints wire it up:

| Endpoint | Auth | Purpose |
|----------|------|---------|
| `POST /v1/register` | none | Public self-signup. Auto-generates `user_id = u_<8hex>`, returns one-time API key. Initial credits taken from `REGISTER_INITIAL_CREDITS` env (default 0). |
| `GET /v1/topup_packs` | none | Public catalog: list packs from `config/stripe_packs.json` plus `stripe_configured` flag. |
| `POST /v1/checkout/create` | user API key | Builds a Stripe Checkout Session (card + WeChat Pay), returns `{checkout_url, session_id}`. Admin tokens are rejected (no real `user_id` to bind to). |
| `POST /webhooks/stripe` | Stripe-Signature header | Verifies signature, parses `checkout.session.completed` **and** `checkout.session.async_payment_succeeded`, calls `service.topup(user_id, credits, request_id="stripe:<session_id>")`. Idempotent — duplicate sessions return `duplicate=true` with no extra credit. |

`stripe_gateway.resolve_amount(pack_id|custom_yuan)` enforces the
range `[min_custom_yuan, max_custom_yuan]` from `stripe_packs.json` and
returns `{amount_fen, credits, currency, label, pack_id}`.

The gateway JSON-serializes the verified Stripe event (via
`to_dict_recursive` → `to_dict` → `json.dumps` fallback) so callers
never depend on the SDK's runtime types.

---

## Tests

- `tests/test_billing.py` — unit tests on `BillingStore` / `BillingService` / `Pricing` (auth, charge/settle/refund, idempotency, inflight, rate limit, daily-limit, concurrent-charge stress, `update_charge_meta` merge).
- `tests/test_endpoint_billing.py` — Flask `test_client` tests covering all `/v1/*` and `/admin/*` paths, admin bypass, validation refunds, orchestrator-exception refunds, SSE billing events, daily-limit 402, `user_id_mismatch`, and the `llm_usage` → ledger meta plumbing.
- `tests/test_stripe_gateway.py` — `StripeGateway` unit tests with mocked SDK (pack lookup, custom amounts, checkout kwargs, real-HMAC webhook signature verification, payload parsing).
- `tests/test_endpoint_stripe.py` — endpoint tests for `/v1/register`, `/v1/topup_packs`, `/v1/checkout/create`, `/webhooks/stripe` (idempotent topup, bad signature, unconfigured server, unknown user).
- `scripts/smoke_billing.py` — production smoke test that hits a running server end-to-end (supports `--allow-stub` for stub-mode validation).
- `scripts/smoke_sse_billing.py` — smoke for the SSE billing event wire format.
- `scripts/smoke_stripe.py` — drives a full Checkout flow end-to-end against a running server + `stripe listen`. Prints the URL to open and polls `/v1/balance` until the webhook lands.
