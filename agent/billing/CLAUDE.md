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
| `service.py` | High-level operations: `authenticate`, `charge`, `settle`, `refund`, `topup`, `issue_api_key`, `revoke_api_key`, `get_balance`, `list_usage`. Idempotent on `request_id`. |
| `pricing.py` | Loads `config/pricing.json`. `Pricing.cost(endpoint, variant_params)` returns credits. |
| `middleware.py` | Flask helpers: `BillingHelpers.authenticate_request`, `try_charge`, `settle`, `refund`, `with_billing` decorator. |
| `errors.py` | Exception hierarchy. |

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
3. **Charge** — `service.charge(user_id, endpoint, cost, request_id)` deducts credits atomically and inserts a `pending` ledger row + an `inflight` slot. Raises `InsufficientFundsError` (→ 402), `InflightLimitError` (→ 429), `DuplicateRequestError` (→ 409).
4. **Run the work**.
5. **Settle on success** (`service.settle(request_id)`) or **refund on failure** (`service.refund(request_id, reason)`). Both clear the inflight slot and are idempotent.

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
  "default_credits": 50,
  "endpoints":  {"/v1/cezi/ask": 30, "/v1/zwds/ask": 80, ...},
  "variants":   {"/v1/zwds/ask?include_star_gong=true": 150, ...}
}
```

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

## Tests

- `tests/test_billing.py` — 27 unit tests on `BillingStore` / `BillingService` / `Pricing` (auth, charge/settle/refund, idempotency, inflight, rate limit, concurrent-charge stress).
- `tests/test_endpoint_billing.py` — 17 Flask `test_client` tests covering all `/v1/*` and `/admin/*` paths, admin bypass, validation refunds, orchestrator-exception refunds, SSE billing events, and `user_id_mismatch`.
- `scripts/smoke_billing.py` — production smoke test that hits a running server end-to-end.
