# Volcengine API-Only Deployment

This guide deploys the project to a Volcengine Ubuntu/Debian server under:

```text
https://api.mymirrorai.com
```

It intentionally exposes only the API/docs/self-service billing surface and
keeps the BaZi web interaction frontend private.

## What Will Be Public

Public:

- `/docs`
- `/openapi.json`
- `/health`
- `/v1/*`
- `/register.html`
- `/billing.html`
- `/terms.html`
- `/privacy.html`
- `/webhooks/stripe`

Hidden behind Caddy `404`:

- `/`
- `/index.html`
- `/admin.html`
- `/admin/*`
- `/api/*` legacy web-console endpoints
- other frontend assets not needed by the allowed pages

The Flask app still contains those routes; Caddy blocks them before traffic
reaches Flask.

## Architecture

```text
Internet
  -> api.mymirrorai.com DNS A record
  -> Volcengine security group 80/443
  -> existing host-level Caddy (HTTPS + route allowlist)
  -> bazi-agent-api container on 127.0.0.1:8000 (Flask/Waitress)
  -> ./storage/billing.db (SQLite bind mount)
```

## Database Deployment

No external database is required for the first server.

Billing data uses SQLite at:

```text
/opt/mirror_ai_agent/storage/billing.db
```

That directory is mounted into the Docker container by `docker-compose.yml`:

```yaml
volumes:
  - ./storage:/app/storage
```

The deploy script creates `/opt/mirror_ai_agent/storage` and never deletes it
when updating the code. Do not run `docker compose down -v` on production
unless you have a backup.

After launch, schedule the existing backup script:

```bash
chmod +x /opt/mirror_ai_agent/scripts/backup_billing.sh
crontab -e
```

Add:

```cron
17 3 * * * BILLING_DB=/opt/mirror_ai_agent/storage/billing.db BACKUP_DIR=/var/backups/bazi-billing /opt/mirror_ai_agent/scripts/backup_billing.sh >> /var/log/bazi-backup.log 2>&1
```

For real durability, also configure COS/S3/rclone in `scripts/backup_billing.sh`
so backups leave the server.

## Existing Website Server Facts

The current `mymirrorai.com` website server already has host-level Caddy
running as a systemd service:

```text
/usr/bin/caddy run --environ --config /etc/caddy/Caddyfile
```

It owns public ports `80` and `443` and serves:

```caddyfile
mymirrorai.com, www.mymirrorai.com {
        root * /var/www/html
        file_server
}
```

The static website deploy swaps `/var/www/html` as a symlink to release
directories such as `/var/www/html.<git-sha>`.

Because of this, this API deploy must not start another Caddy container and
must not overwrite `/etc/caddy/Caddyfile`. The API container is published only
on `127.0.0.1:8000`; the existing host-level Caddy will reverse proxy
`api.mymirrorai.com` to that local port.

## One-Time Volcengine Setup

In the Volcengine console:

1. Create or use an Ubuntu/Debian ECS instance.
2. Security group inbound rules:
   - TCP `22` from your IP (or `0.0.0.0/0` temporarily)
   - TCP `80` from `0.0.0.0/0`
   - TCP `443` from `0.0.0.0/0`
3. Confirm you can SSH:
   ```bash
   ssh root@YOUR_SERVER_IP
   ```

## DNS Setup

In your DNS provider for `mymirrorai.com`, add:

```text
Type: A
Host: api
Value: YOUR_SERVER_PUBLIC_IP
TTL: default
```

Verify locally:

```bash
nslookup api.mymirrorai.com
```

Do not deploy HTTPS until this resolves correctly, otherwise Caddy cannot get
the Let's Encrypt certificate.

## Local Deploy Configuration

From the repo root on your local machine:

```bash
cp .deploy.env.example .deploy.env
```

Edit `.deploy.env`:

```env
DEPLOY_HOST=YOUR_SERVER_PUBLIC_IP
DEPLOY_USER=root
DEPLOY_PORT=22
DEPLOY_DOMAIN=api.mymirrorai.com
DEPLOY_REPO=https://github.com/edwardzhengsiyuan/mirror_ai_agent.git
DEPLOY_BRANCH=master
DEPLOY_PATH=/opt/mirror_ai_agent
DEPLOY_VERIFY_PUBLIC=0

DEMO_API_TOKEN=<generate with python -c "import secrets; print(secrets.token_urlsafe(32))">
BILLING_ADMIN_BYPASS=0

LLM_MODE=
GPTPROTO_API_KEY=...
QWEN_API_KEY=...

STRIPE_MODE=test
STRIPE_SECRET_KEY_TEST=sk_test_...
STRIPE_PUBLISHABLE_KEY_TEST=pk_test_...
STRIPE_WEBHOOK_SECRET_TEST=whsec_...

STRIPE_PAYMENT_METHODS=card
```

Notes:

- `.deploy.env` is gitignored and must never be committed.
- Start with `STRIPE_MODE=test` if live activation is not ready.
- For live mode, set `STRIPE_MODE=live` and fill `STRIPE_*_LIVE`.
- Keep `STRIPE_PAYMENT_METHODS=card` until Stripe has approved WeChat Pay.

## Run Deployment

From local Git Bash / WSL / macOS / Linux shell:

```bash
bash scripts/deploy_volcengine.sh
```

The script will:

1. SSH to the server.
2. Install `git`, `curl`, `docker.io`, `docker-compose-plugin`, `sqlite3`,
   and `python3` if missing.
3. Clone or update `/opt/mirror_ai_agent`.
4. Write `/opt/mirror_ai_agent/.env` from your local `.deploy.env`.
5. Render `deploy/Caddyfile.existing-proxy-api-snippet.template` into
   `/opt/mirror_ai_agent/deploy/generated-api-caddy-snippet.Caddyfile`.
6. Run `python3 scripts/check_prod_env.py --env .env` on the server.
7. Run `docker compose -f docker-compose.api-only.yml up -d --build`.
8. Verify:
   - `http://127.0.0.1:8000/health` from inside the server
   - `http://127.0.0.1:8000/docs` from inside the server
   - `http://127.0.0.1:8000/openapi.json` from inside the server

The script deliberately does **not** edit `/etc/caddy/Caddyfile` or reload
Caddy. That keeps the existing public website safe.

If you want warnings to block deployment too, add this to `.deploy.env`:

```env
DEPLOY_STRICT_PREFLIGHT=1
```

## Add api.mymirrorai.com to Existing Caddy

After the API container is healthy locally, append the generated snippet to the
host Caddyfile.

On the server:

```bash
cd /opt/mirror_ai_agent
sed -n '1,220p' deploy/generated-api-caddy-snippet.Caddyfile
```

Review it, then make a timestamped backup and append:

```bash
cp /etc/caddy/Caddyfile /etc/caddy/Caddyfile.bak.$(date +%Y%m%d%H%M%S)
cat deploy/generated-api-caddy-snippet.Caddyfile >> /etc/caddy/Caddyfile
caddy validate --config /etc/caddy/Caddyfile
systemctl reload caddy
```

Then set this in local `.deploy.env`:

```env
DEPLOY_VERIFY_PUBLIC=1
```

Rerun:

```bash
bash scripts/deploy_volcengine.sh
```

The second run verifies public HTTPS routes and the hidden-page 404 behavior.

## Stripe Dashboard Setup

Webhook URL:

```text
https://api.mymirrorai.com/webhooks/stripe
```

Subscribe to:

- `checkout.session.completed`
- `checkout.session.async_payment_succeeded`

Success/cancel URLs are generated by the deploy script as:

```text
https://api.mymirrorai.com/billing.html?status=success&session_id={CHECKOUT_SESSION_ID}
https://api.mymirrorai.com/billing.html?status=cancelled
```

Terms and privacy URLs for Stripe activation:

```text
https://api.mymirrorai.com/terms.html
https://api.mymirrorai.com/privacy.html
```

Customize `web/terms.html` and `web/privacy.html` before live activation.

## Verification Commands

After deployment:

```bash
curl -i https://api.mymirrorai.com/health
curl -i https://api.mymirrorai.com/docs
curl -i https://api.mymirrorai.com/openapi.json
curl -i https://api.mymirrorai.com/register.html
curl -i https://api.mymirrorai.com/billing.html

# These should be 404.
curl -i https://api.mymirrorai.com/
curl -i https://api.mymirrorai.com/index.html
curl -i https://api.mymirrorai.com/admin.html
curl -i https://api.mymirrorai.com/admin/users
curl -i https://api.mymirrorai.com/api/ask
```

Run Stripe checkout smoke:

```bash
python scripts/smoke_stripe.py --base-url https://api.mymirrorai.com --pack pack_10
```

In test mode, use Stripe test card / WeChat sandbox. In live mode, this is a
real charge; refund it in the Stripe Dashboard after verification.

## Updating Code Later

Push changes to:

```text
https://github.com/edwardzhengsiyuan/mirror_ai_agent.git
```

Then rerun:

```bash
bash scripts/deploy_volcengine.sh
```

The script does a `git pull --ff-only`, rewrites `.env`, refreshes the generated
Caddy snippet under `deploy/`, and rebuilds/restarts only the API Docker
container. It does not touch `/etc/caddy/Caddyfile`. The SQLite database under
`storage/` is preserved.

## If Deployment Fails

Check server logs:

```bash
ssh root@YOUR_SERVER_IP
cd /opt/mirror_ai_agent
docker compose ps
docker compose logs -f bazi-agent-api
docker compose -f docker-compose.api-only.yml logs -f bazi-agent-api
journalctl -u caddy -n 100 --no-pager
```

Common causes:

- DNS `api.mymirrorai.com` does not point to the server.
- Volcengine security group does not allow 80/443.
- The generated Caddy snippet was not appended/reloaded yet.
- Another process already uses `127.0.0.1:8000`.
- `.deploy.env` has `LLM_MODE=stub`.
- `STRIPE_MODE=live` but live keys/webhook secret are missing.
- `STRIPE_PAYMENT_METHODS=card,wechat_pay` before Stripe live WeChat Pay approval.
