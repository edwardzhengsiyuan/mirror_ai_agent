# 远端部署操作手册（Volcengine / open.mymirrorai.com）

本文件给「本地改完代码 → 提交 → 推送 → 部署到火山引擎服务器」用。  
**在 Git Bash 里执行 bash 脚本**（PowerShell 也可以跑部分命令，但 deploy 脚本建议 Git Bash）。

---

## 0. 一次性准备

1. 复制并填写本地部署配置（不要提交）：

```bash
cp .deploy.env.example .deploy.env
```

2. `.deploy.env` 里至少要有：

| 变量 | 说明 |
|------|------|
| `DEPLOY_HOST` | 服务器公网 IP |
| `DEPLOY_USER` | 通常是 `root` |
| `DEPLOY_PORT` | 通常是 `22` |
| `DEPLOY_DOMAIN` | 例如 `open.mymirrorai.com` |
| `SSH_KEY_PATH` | 私钥路径，Windows 示例见下 |
| `APP_SECRET_KEY` | 会话 cookie 签名，部署脚本会校验 |
| `GPTPROTO_API_KEY` / `QWEN_API_KEY` | LLM 密钥 |
| `STRIPE_*` | 充值相关（live 模式见 `DEPLOYMENT.md`） |

3. Windows 私钥路径示例（Git Bash）：

```bash
SSH_KEY_PATH=/c/Users/11483/Documents/key/mirrorai-site2.pem
```

4. 服务器上 Caddy 只需**手动追加一次** snippet（见本文第 6 节）。之后日常 deploy 不用动 Caddy。

---

## 1. 常用本机命令（记不住就查这里）

### 查本机公网 IP（配安全组 SSH 白名单时用）

**Git Bash / macOS / Linux：**

```bash
curl -s https://ifconfig.me/ip
```

**PowerShell：**

```powershell
(Invoke-RestMethod https://ifconfig.me/ip).Trim()
```

### 测试 SSH 能否登录

**Git Bash：**

```bash
ssh -i /c/Users/11483/Documents/key/mirrorai-site2.pem root@你的服务器IP
```

**PowerShell：**

```powershell
ssh -i "C:\Users\11483\Documents\key\mirrorai-site2.pem" root@你的服务器IP
```

### 本地跑测试

```bash
.venv/Scripts/python.exe -m pytest
```

---

## 2. 提交并推送到 GitHub

```bash
cd /c/Users/11483/Documents/GitHub/mirror_ai_agent

git status
git add -A
# 不要提交 secrets 和本地 trace 报告：
git reset reports/

git commit -m "fix(agent): tighten BaZi node DAG inputs and SHISHEN routing"
git push origin master
```

说明：

- **不要** `git add .deploy.env`（已在 `.gitignore`）。
- `reports/` 是本地 LLM trace 审阅产物，一般不必进仓库。

---

## 3. 部署方式选择

| 方式 | 脚本 | 何时用 |
|------|------|--------|
| **源码部署（当前常用）** | `bash scripts/deploy_volcengine.sh` | 服务器上 `git pull` + `docker build` |
| **镜像部署** | `bash scripts/deploy_volcengine_image.sh` | 已在 CI 构建镜像并 push 到私有仓库，见 `DEPLOY_IMAGE_ONLY.md` |

`.deploy.env` 里若已配置非空 `IMAGE_REF`，用镜像脚本；否则用源码脚本。

---

## 4. 源码部署（推荐日常）

在 **Git Bash** 中：

```bash
cd /c/Users/11483/Documents/GitHub/mirror_ai_agent
bash scripts/deploy_volcengine.sh
```

脚本会自动：

1. 读取 `.deploy.env` 做 preflight（`scripts/check_prod_env.py`）
2. SSH 到服务器 `git pull` + `docker compose build/up`
3. 写入服务器 `/opt/mirror_ai_agent/.env`
4. 本机检查 `127.0.0.1:8000/health` 等
5. 若 `DEPLOY_VERIFY_PUBLIC=1`，再测公网 HTTPS

首次部署或改 Caddy 后，把 `DEPLOY_VERIFY_PUBLIC=1` 打开做一次公网验收。

---

## 5. 镜像部署（可选）

前提：GitHub Actions 已 push 镜像，且 `.deploy.env` 有：

```env
IMAGE_REF=你的registry/namespace/mirror-ai-agent:latest
REGISTRY_HOST=...
REGISTRY_USERNAME=...
REGISTRY_PASSWORD=...
```

```bash
bash scripts/deploy_volcengine_image.sh
```

细节见 `DEPLOY_IMAGE_ONLY.md`。

---

## 6. Caddy（仅首次或改路由时）

1. 本地生成 snippet 预览（deploy 脚本也会写到服务器 `deploy/generated-api-caddy-snippet.Caddyfile`）：

```bash
sed "s|\${DEPLOY_DOMAIN}|open.mymirrorai.com|g" deploy/Caddyfile.existing-proxy-api-snippet.template
```

2. SSH 上服务器，编辑主站 Caddyfile，**只追加一次**上述 snippet，不要重复粘贴。

3. 校验并重载：

```bash
sudo caddy validate --config /etc/caddy/Caddyfile
sudo systemctl reload caddy
```

4. 等 30–60 秒证书签发后，再测 HTTPS。

---

## 7. 部署后验收

### 公网页面（浏览器）

- https://open.mymirrorai.com/
- https://open.mymirrorai.com/login
- https://open.mymirrorai.com/dashboard
- https://open.mymirrorai.com/docs
- https://open.mymirrorai.com/health

### 应返回 404 的内部路径

- `/app.html`
- `/admin.html`
- `/openapi.json`
- `/_swagger`

### 命令行快速测

**Git Bash：**

```bash
curl -sS -o /dev/null -w "%{http_code}\n" https://open.mymirrorai.com/health
curl -sS -o /dev/null -w "%{http_code}\n" https://open.mymirrorai.com/app.html
```

**PowerShell：**

```powershell
(Invoke-WebRequest https://open.mymirrorai.com/health -UseBasicParsing).StatusCode
(Invoke-WebRequest https://open.mymirrorai.com/app.html -UseBasicParsing).StatusCode
```

完整手工流程见 `PORTAL_REMOTE_TEST.md`。

---

## 8. 常见问题

| 现象 | 处理 |
|------|------|
| `scp: stat local "22"` | 用 Git Bash 跑 deploy 脚本（已修复 scp 端口参数） |
| SSH `Bad permissions` | Windows 上对 `.pem` 收紧 ACL，仅当前用户可读 |
| deploy 成功但公网 502 | 服务器上 `docker ps`，看 `mirror_ai_agent` 容器是否 healthy |
| LLM 401 | 检查服务器 `.env` 里 `GPTPROTO_API_KEY` 是否有对应 model 权限 |
| Stripe 仍是 test warning | `.deploy.env` 设 `STRIPE_MODE=live` 并填 live webhook secret |

---

## 9. 安全提醒

- SSH：密钥登录 + 禁用密码 + 安全组仅允许你的公网 IP 访问 22
- 服务器 `.env`：`chmod 600 .env`
- 不要把 `.deploy.env`、API key、Stripe secret 提交到 Git
