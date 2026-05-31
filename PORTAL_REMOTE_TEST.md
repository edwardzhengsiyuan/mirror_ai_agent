# Mirror AI Developer Portal 远端测试手册

目标：在正式切换到“私有镜像部署”前，先确认当前公网版本完整可用。

公网地址：

```text
https://open.mymirrorai.com
```

测试范围：

- 注册
- 登录
- Dashboard 查看余额 / API key
- 重置 API key
- API 请求
- Billing / 充值页面
- 登出
- 隐藏路径检查

> 当前注意：如果 `.deploy.env` 里 `STRIPE_WEBHOOK_SECRET_TEST` 还是空的，Stripe 付款成功后的 webhook 入账不会生效。也就是说，充值页面和创建 checkout 可能可用，但“付款后自动加 credits”要等 Stripe webhook 配好后再测。

---

## 1. 打开首页

浏览器访问：

```text
https://open.mymirrorai.com
```

预期：

- 页面标题/品牌显示 `Mirror AI`
- 有 `注册账号`、`查看文档`、`登录` 等入口
- 不应该看到旧 BaZi 前端或 admin UI

---

## 2. 注册账号

打开：

```text
https://open.mymirrorai.com/register
```

填写：

```text
邮箱：你的测试邮箱，例如 test+001@example.com
密码：至少 8 位
公司 / 项目名：可选
```

点击“创建账号”。

预期：

- 成功后跳到：

```text
https://open.mymirrorai.com/dashboard?welcome=1
```

- Dashboard 顶部显示账号邮箱
- 显示余额 `0 credits`
- 显示完整 API key
- 看到欢迎提示：账号创建成功

记录这把 API key，后续 API 测试会用。

---

## 3. 登录账号

先点右上角“登出”，或打开：

```text
https://open.mymirrorai.com/login
```

输入刚才注册的邮箱和密码。

预期：

- 登录成功后跳到 Dashboard
- `/v1/me` cookie session 正常
- 仍能看到当前 API key

---

## 4. Dashboard 测试

打开：

```text
https://open.mymirrorai.com/dashboard
```

检查：

- `账户余额` 显示 credits
- `API Key` 区域显示完整 key
- “复制”按钮能复制 key
- “最近调用”表格能加载

### 重置 API key

点击：

```text
重置 Key
```

确认弹窗。

预期：

- 新 key 生成
- 页面显示新 key
- 旧 key 立刻失效
- 新 key 可用于 API 请求

---

## 5. 文档页面测试

打开：

```text
https://open.mymirrorai.com/docs
```

预期：

- 显示 `API 文档`
- 有 Quickstart
- 有 6 组 endpoint：
  - Account
  - BaZi 八字
  - HePan 合盘
  - CeZi 测字
  - NaJia 纳甲
  - ZWDS 紫微斗数
  - Billing
- curl / Python / Node.js 三种示例可以切换

如果已登录，文档里的 `YOUR_API_KEY` 会自动替换成你的真实 key。

---

## 6. API 请求测试

下面命令建议在 Git Bash 里跑。

先设置变量，把 `YOUR_API_KEY` 换成 Dashboard 里的真实 key：

```bash
API_KEY="YOUR_API_KEY"
BASE_URL="https://open.mymirrorai.com"
```

### 6.1 查询余额

```bash
curl -s "$BASE_URL/v1/balance" \
  -H "Authorization: Bearer $API_KEY"
```

预期：

```json
{
  "user_id": "u_xxxxxxxx",
  "balance_credits": 0,
  "daily_credits_limit": null
}
```

### 6.2 查询使用记录

```bash
curl -s "$BASE_URL/v1/usage?limit=20" \
  -H "Authorization: Bearer $API_KEY"
```

预期：

```json
{
  "user_id": "u_xxxxxxxx",
  "rows": []
}
```

如果已有调用/充值记录，`rows` 会有数据。

### 6.3 测字接口（最便宜，适合 smoke）

> 注意：如果当前账户余额是 0，这个接口会返回 `402 insufficient_funds`，这是正常的。除非你先充值或后台加 credits。

```bash
curl -s "$BASE_URL/v1/cezi/ask" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "这个项目合作能不能成？",
    "character": "合"
  }'
```

余额为 0 时预期：

```json
{
  "error": {
    "code": "insufficient_funds",
    "message": "..."
  }
}
```

如果账户有 credits，预期返回：

```json
{
  "request_id": "...",
  "user_id": "u_xxxxxxxx",
  "method": "cezi",
  "answer": "...",
  "character": "合"
}
```

响应 header 会带：

```text
X-Charged-Credits
X-Balance-After
X-Request-Id
```

---

## 7. 充值页面测试

打开：

```text
https://open.mymirrorai.com/billing
```

检查：

- 显示当前余额
- 显示支付方式/Stripe 状态
- 显示套餐或自定义金额输入

### 当前 Stripe webhook 未配置时

如果服务器 `.env` 里 `STRIPE_WEBHOOK_SECRET_TEST` 为空：

- 创建 checkout 可能可以成功
- 但 Stripe 支付完成后，服务器 webhook 会拒绝或无法验签
- credits 不会自动入账

因此现阶段只建议测试：

- 页面可打开
- 套餐能加载
- 如果 Stripe key 已配置，点击充值能跳 Stripe Checkout

不要把“付款后余额没变”当成 portal bug，先配置 webhook。

---

## 8. 登出测试

点击右上角：

```text
登出
```

预期：

- 跳转到 `/login`
- 再访问 `/dashboard` 会跳回登录页
- `/v1/me` 返回 401

可用命令验证：

```bash
curl -i "$BASE_URL/v1/me"
```

未带 cookie 时预期：

```text
HTTP/...
401
```

---

## 9. 隐藏路径检查

这些路径必须是 404：

```bash
curl -I https://open.mymirrorai.com/app.html
curl -I https://open.mymirrorai.com/admin.html
curl -I https://open.mymirrorai.com/openapi.json
curl -I https://open.mymirrorai.com/_swagger
curl -I https://open.mymirrorai.com/admin/users
```

预期：

```text
HTTP/1.1 404 Not Found
```

这些路径必须是 200：

```bash
curl -I https://open.mymirrorai.com/
curl -I https://open.mymirrorai.com/login
curl -I https://open.mymirrorai.com/register
curl -I https://open.mymirrorai.com/dashboard
curl -I https://open.mymirrorai.com/billing
curl -I https://open.mymirrorai.com/docs
```

预期：

```text
HTTP/1.1 200 OK
```

---

## 10. 一键端到端 smoke

本地 Git Bash：

```bash
cd /c/Users/11483/Documents/GitHub/mirror_ai_agent
BASE_URL=https://open.mymirrorai.com .venv/Scripts/python.exe scripts/smoke_portal.py
```

成功预期：

```text
All smoke checks passed.
```

这个 smoke 覆盖：

- 注册
- 登录 cookie
- `/v1/me`
- Bearer API key
- 查询余额
- 重置 key
- 旧 key 失效
- 新 key 可用
- 修改密码
- 登出

---

## 通过标准

正式切镜像部署前，建议至少确认：

- [ ] `/`、`/login`、`/register`、`/dashboard`、`/billing`、`/docs` 都能打开
- [ ] 注册能成功
- [ ] 登录能成功
- [ ] Dashboard 能显示完整 API key
- [ ] 复制 key 后 `/v1/balance` 能返回 200
- [ ] 重置 key 后旧 key 返回 401，新 key 返回 200
- [ ] `/app.html`、`/admin.html`、`/openapi.json`、`/_swagger`、`/admin/users` 都是 404
- [ ] `scripts/smoke_portal.py` 公网模式通过

Stripe webhook 可放到下一步单独测试。
