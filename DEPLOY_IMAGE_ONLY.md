# Image-only Deployment

This guide migrates production from "server git pull + docker build" to
"GitHub Actions builds image + server docker pull".

Why do this:

- The server no longer keeps a full git checkout, tests, docs, or repository
  history.
- Deploys become faster and more repeatable.
- The private registry becomes the only source of production artifacts.

Important limitation:

- This is **not** perfect source-code protection. Python source still exists
  inside the Docker image because the app needs it to run. A root-level server
  compromise can still extract the running image. This deployment mainly reduces
  the amount of extra source/history/secrets exposed on the server.

---

## What You Need To Prepare

Recommended registry: **Volcengine Container Registry** (same cloud/region as
the server, better pull reliability than Docker Hub/GHCR from mainland China).

You need:

1. A private registry host, for example:

   ```text
   registry-cn-beijing.volces.com
   ```

2. A namespace/project, for example:

   ```text
   mirror
   ```

3. An image repository, for example:

   ```text
   mirror-ai-agent
   ```

4. A registry username and password/token that can push/pull this repository.

5. The final image reference:

   ```text
   registry-cn-beijing.volces.com/mirror/mirror-ai-agent:latest
   ```

---

## GitHub Secrets

In GitHub repo settings:

`Settings -> Secrets and variables -> Actions -> New repository secret`

Add:

| Secret | Example |
| --- | --- |
| `REGISTRY_HOST` | `registry-cn-beijing.volces.com` |
| `REGISTRY_NAMESPACE` | `mirror` |
| `REGISTRY_USERNAME` | registry username |
| `REGISTRY_PASSWORD` | registry password / token |

The workflow `.github/workflows/build-image.yml` pushes:

- `<registry>/<namespace>/mirror-ai-agent:<short-sha>`
- `<registry>/<namespace>/mirror-ai-agent:latest`

Trigger it either by pushing to `master` or manually via GitHub Actions.

---

## Local `.deploy.env`

Keep the normal deploy variables you already use, and add:

```env
IMAGE_REF=registry-cn-beijing.volces.com/mirror/mirror-ai-agent:latest
REGISTRY_HOST=registry-cn-beijing.volces.com
REGISTRY_USERNAME=your-registry-username
REGISTRY_PASSWORD=your-registry-password-or-token

# First image-only deploy: keep this 0.
# After it works: set 1 once to remove leftover server source checkout.
DEPLOY_IMAGE_PRUNE_SOURCE=0
```

Also keep:

```env
SSH_KEY_PATH=/c/Users/11483/Documents/key/mirrorai-site2.pem
DEPLOY_VERIFY_PUBLIC=1
```

Never commit `.deploy.env`.

---

## First Image-only Deploy

From Git Bash:

```bash
cd /c/Users/11483/Documents/GitHub/mirror_ai_agent
bash scripts/deploy_volcengine_image.sh
```

The script will:

1. SSH to the server.
2. Optionally `docker login` to the private registry.
3. Upload only:
   - `.env`
   - `docker-compose.image-only.yml`
   - generated Caddy snippet
4. `docker compose pull`.
5. Run production preflight inside the pulled image.
6. Start `bazi-agent-api` from the image.
7. Verify local health and optional public routes.

At this point the old git checkout may still exist on the server, but it is no
longer needed by the running container.

---

## Prune Server Source Checkout

After the first image-only deploy succeeds and public smoke tests pass, set:

```env
DEPLOY_IMAGE_PRUNE_SOURCE=1
```

Then rerun:

```bash
bash scripts/deploy_volcengine_image.sh
```

The script removes everything directly under `DEPLOY_PATH` except:

- `.env`
- `storage/`
- `deploy/`
- `docker-compose.image-only.yml`

Expected server layout:

```text
/opt/mirror_ai_agent/
  .env
  docker-compose.image-only.yml
  deploy/generated-api-caddy-snippet.Caddyfile
  storage/
```

---

## Server-side Verification

On the server:

```bash
cd /opt/mirror_ai_agent
docker compose -f docker-compose.image-only.yml ps
curl -fsS http://127.0.0.1:8000/health && echo
ls -la /opt/mirror_ai_agent
```

From local Git Bash:

```bash
curl -I https://open.mymirrorai.com/
curl -I https://open.mymirrorai.com/docs
curl -I https://open.mymirrorai.com/app.html      # should be 404
curl -I https://open.mymirrorai.com/openapi.json  # should be 404

BASE_URL=https://open.mymirrorai.com .venv/Scripts/python.exe scripts/smoke_portal.py
```

---

## Rollback

If an image-only deploy fails before pruning source:

```bash
ssh -i /c/Users/11483/Documents/key/mirrorai-site2.pem root@150.5.154.101
cd /opt/mirror_ai_agent
docker compose -f docker-compose.api-only.yml up -d --build
```

If source has already been pruned, rollback by deploying a previous image tag:

```env
IMAGE_REF=registry-cn-beijing.volces.com/mirror/mirror-ai-agent:<old-short-sha>
```

Then rerun:

```bash
bash scripts/deploy_volcengine_image.sh
```
