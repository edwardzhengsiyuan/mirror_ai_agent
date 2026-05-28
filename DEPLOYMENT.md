# Production Deployment Runbook

One-page checklist for taking BaZi Agent from local test mode to a public
HTTPS server taking real payments. Pair this with the long-form notes in
`README_DEMO.md`; this file is the dense checklist.

For the `api.mymirrorai.com` Volcengine deployment that exposes only API
docs/API/self-service billing pages and hides the BaZi frontend/admin UI, see
`DEPLOY_VOLCENGINE.md`.

> The Docker image, Caddy reverse proxy, Stripe integration, billing
> SQLite store, and admin/user APIs are already built. Everything below
> is configuration, secrets, DNS, and policy — no code changes required.

---

## 0. Prerequisites

- A server (2 vCPU / 2 GB RAM minimum) with Docker Engine + Docker Compose v2 installed.
- A domain you control (Stripe live mode requires HTTPS).
- A Stripe account that has completed activation (KYC, business info, bank).
- LLM provider accounts with billing on:
  - GPTProto (default routes) — `sk-...` for `GPTPROTO_API_KEY`.
  - Aliyun DashScope (for SHISHEN / GEJU / NAJIA nodes) — `sk-...` for `QWEN_API_KEY`.

---

## 1. Pre-flight (do this BEFORE `docker compose up`)

### 1.1 Buy a domain and point DNS

Add an A (and optionally AAAA) record:

```
demo.example.com.   3600 IN A   <SERVER_PUBLIC_IP>
```

Wait until `dig +short demo.example.com` resolves to the right IP. ACME
challenges will fail otherwise and Caddy will busy-loop.

### 1.2 Edit `Caddyfile` for HTTPS

Open `Caddyfile`:

1. Set `email ops@example.com` at the top to a real address — Let's Encrypt
   sends renewal-failure warnings here.
2. Comment out the `:80 { ... }` block.
3. Uncomment the `demo.example.com { ... }` block and replace the hostname.

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

### 1.3 Edit `.env` — secrets and live mode

Starting from `.env.example`:

```bash
cp .env.example .env
```

Fill in (replace placeholders, do not commit):

```env
# Admin / billing
DEMO_API_TOKEN=<output of `python -c "import secrets; print(secrets.token_urlsafe(32))"`>
BILLING_ADMIN_BYPASS=0      # IMPORTANT: leaked admin tokens can't burn LLM credits

# LLM (real keys with quota; LLM_MODE empty so we are NOT in stub)
LLM_MODE=
GPTPROTO_API_KEY=sk-...
QWEN_API_KEY=sk-...

# Stripe (live)
STRIPE_MODE=live
STRIPE_SECRET_KEY_LIVE=sk_live_...
STRIPE_PUBLISHABLE_KEY_LIVE=pk_live_...
STRIPE_WEBHOOK_SECRET_LIVE=whsec_...      # filled after step 1.5

STRIPE_SUCCESS_URL=https://demo.example.com/billing.html?status=success&session_id={CHECKOUT_SESSION_ID}
STRIPE_CANCEL_URL=https://demo.example.com/billing.html?status=cancelled

# Card only by default. Switch to `card,wechat_pay` ONLY after Stripe has
# approved WeChat Pay on your account — otherwise Session.create returns 400.
STRIPE_PAYMENT_METHODS=card

# Optional but recommended
SENTRY_DSN=https://...@sentry.io/<project>
```

### 1.4 Validate with the preflight script

```bash
.venv/bin/python scripts/check_prod_env.py --env .env
```

Fix anything reported as `FAIL` before proceeding. Warnings are
acceptable but should each have a deliberate rationale.

For CI / hardening, run with `--strict` to treat warnings as errors:

```bash
.venv/bin/python scripts/check_prod_env.py --env .env --strict
```

### 1.5 Register the Stripe webhook in the dashboard

`stripe listen` is a local-dev tool. Production uses a dashboard-registered
webhook endpoint:

1. https://dashboard.stripe.com → Developers → Webhooks → **Add endpoint**.
2. URL: `https://demo.example.com/webhooks/stripe`.
3. Subscribe to these two events only:
   - `checkout.session.completed`
   - `checkout.session.async_payment_succeeded`
4. Copy the resulting `whsec_...` into `STRIPE_WEBHOOK_SECRET_LIVE` in `.env`.

### 1.6 Stripe activation prerequisites (one-time)

Stripe will not let you accept live payments until your account has:

- Business info, tax info, bank account.
- A **public Terms of Service URL** — point to `https://demo.example.com/terms.html`.
- A **public Privacy Policy URL** — point to `https://demo.example.com/privacy.html`.
- A **public support email** — edit it into `web/terms.html` and `web/privacy.html` before deploy.

The placeholder pages at `/terms.html` and `/privacy.html` ship with the
repo. **Customize the placeholders to reflect your real entity** (legal
counsel review recommended).

### 1.7 (Mainland China only) ICP filing

If your host is in mainland China, your domain needs an ICP filing
(`备案`) before opening :80/:443 publicly — operators take down unfiled
sites within ~30 days. The cloud vendor's console (Aliyun / Tencent
Cloud) walks you through it; lead time is 5–20 business days.

### 1.8 Server hardening (one-time)

- Disable password SSH: `PasswordAuthentication no` in `/etc/ssh/sshd_config`.
- Move SSH off port 22 (optional but recommended).
- `ufw` (or `firewalld`): allow only 22 (or your chosen SSH port), 80, 443.
- Install `fail2ban` to throttle SSH brute force.
- Set up unattended security upgrades (`unattended-upgrades` on Debian/Ubuntu).
- If RAM ≤ 2 GB, configure a 2 GB swap file (LLM concurrency can spike).

---

## 2. First boot

```bash
docker compose up -d --build
docker compose logs -f bazi-agent-api   # watch startup; Ctrl+C when steady
```

Verify, replacing the hostname:

```bash
curl https://demo.example.com/health
# {"auth_configured": true, "service": "bazi-agent-api", "status": "ok"}

curl https://demo.example.com/v1/topup_packs
# {"stripe_configured": true, "mode": "live", "payment_methods": ["card"], ...}
```

Both calls must succeed. If `auth_configured` is false, the container
didn't read `DEMO_API_TOKEN`. If `stripe_configured` is false, the
Stripe secret didn't load — `docker compose exec bazi-agent-api env | grep STRIPE`
and re-check `.env`.

---

## 3. End-to-end payment smoke test

Run the smoke driver (it creates a real Stripe Checkout session — in
live mode that means a real card charge):

```bash
.venv/bin/python scripts/smoke_stripe.py --base-url https://demo.example.com --pack pack_10
```

It will print a Checkout URL. Pay ¥10 with a real card (test will be
refunded later from the dashboard). Within ~10 seconds you should see:

```
[poll] balance: 0 -> 1000
[PASS] webhook fired and balance reflects topup
```

If the balance doesn't move, check:

1. `docker compose logs bazi-agent-api | grep webhook` — was the event received?
2. Stripe Dashboard → Developers → Webhooks → your endpoint → "Recent
   deliveries" — did it return 200? If 400, your `STRIPE_WEBHOOK_SECRET_LIVE`
   is wrong. If 5xx, see API logs.

---

## 4. Operational setup

### 4.1 Schedule billing DB backups

The SQLite ledger at `storage/billing.db` is your only authoritative
record of user balances. Lose it and you lose everyone's money. Install
the snapshot cron:

```bash
chmod +x /opt/bazi/scripts/backup_billing.sh
crontab -e
# add the suggested line from the top of the script, then uncomment and
# customize one of the `aws s3 cp` / `coscli cp` / `rclone copy` lines
# inside the script to ship snapshots to off-host storage.
```

### 4.2 External health monitoring

UptimeRobot / BetterStack / Pingdom — any of them, 1-minute interval
GET on `https://demo.example.com/health`, alert via email/Webhook when
non-200 for two consecutive checks.

### 4.3 Error tracking

If you filled `SENTRY_DSN` in `.env`, `web_server.create_app` already
initialised the SDK. Verify by forcing an error in a test environment
and confirming it shows up in your Sentry project. The traces sample
rate defaults to 5%; raise via `SENTRY_TRACES_SAMPLE_RATE=0.1` if you
want more flame graphs.

### 4.4 Log rotation

`docker-compose.yml` caps each container at ~250 MB of logs (5 files
× 50 MB) via the `json-file` driver. Nothing else to do.

### 4.5 Stripe webhook replay drill

Twice a year, simulate a webhook failure: stop the API container, send
a test payment, restart the container, then in Stripe Dashboard →
Webhooks → "Failed events" tab, click **Resend**. Confirm the balance
catches up. This is your only chance to verify your retry runbook
before a real outage.

---

## 5. Things to do later (don't block initial launch)

| Item | When |
|------|------|
| Edge rate limit for `/v1/register` via Caddy `rate_limit` plugin (rebuild with `xcaddy`) | When you see registration abuse |
| Edge IP allowlist on `/admin/*` (uncomment block in `Caddyfile`) | If admin console will be used remotely |
| Switch waitress to gunicorn (see `README_DEMO.md` Operations notes) | When SSE concurrency > 8 simultaneous streams |
| Capacity benchmark via concurrent `scripts/smoke_e2e.py` runs | Before announcing to users |
| Data retention sweep (delete `storage/users/<id>/conversations/*.jsonl` older than 90 days) | After 90 days of operation |

---

## 6. Token / secret rotation

When (not if) you need to rotate:

- **`DEMO_API_TOKEN`**: generate new, replace in `.env`, `docker compose
  restart bazi-agent-api`. Update any admin scripts using the old value.
  Old token stops working immediately.
- **Stripe secret key**: dashboard → API keys → roll. Update
  `STRIPE_SECRET_KEY_LIVE`, restart. No data migration.
- **Stripe webhook secret**: dashboard → Webhooks → your endpoint →
  "Click to reveal" → roll. Update `STRIPE_WEBHOOK_SECRET_LIVE`, restart.
  Webhook deliveries during the few-second restart window will retry and
  succeed automatically (Stripe retries for 3 days).

---

## 7. Tear-down (for staging environments)

```bash
docker compose down -v          # drops caddy volumes (cert cache)
rm -rf storage                  # WARNING: deletes ALL billing data
```

Production: never run `down -v` without an off-host backup pulled first.
