# bazi_agent

一个面向八字问答的后端 Agent，提供排盘、按需规划、节点并发与缓存、LLM 调用（可 stub）、时间上下文解析，并配套本地/在线测试脚本。

## 功能概览
- 单轮入口 `app.py`：加载用户档案→规划→并发执行节点→拼装回答。
- 节点缓存与失败重跑：基于输入哈希缓存；缓存含错误会自动清除后重跑。
- Prompt 模板化：`agent/prompts/templates/` 按节点拆分，支持配置集切换（如 `lingyun_cat`）。
- 时间上下文：识别“今年/明年/具体年月”等，结合排盘结构定位大运/流年/流月。
- 测试矩阵：覆盖 stub、本地多轮回放、在线真实 LLM、错误注入。

## 目录速览
- `app.py`：CLI 入口。
- `agent/`：规划(`planning.py`)、依赖(`deps.py`)、执行与缓存(`execution.py`)、响应(`response.py`)、工具(`tools/`)、Prompt 组装(`nodes/prompt_builder.py`)、存储工具(`storage/`)。
- `agent/tools/`：`paipan_tool`（本地排盘）、`time_context_tool`（时间匹配）、`llm_tool`（LLM + stub + trace）。
- `agent/prompts/templates/`：各节点提示词模板。
- `bazi/`：八字计算引擎，`BaziChartAnalyseFrame` 输出结构化排盘与大运流年。
- `tests/`：并发、缓存重跑、stub/live、自定义回放等脚本。
- `storage/`：示例 profile/日志输出目录（测试运行时写入）。

## 快速开始
1) 安装依赖（建议虚拟环境）：
```bash
python -m pip install -r requirements.txt
```
2) 配置环境变量：在仓库根创建/编辑 `.env`，至少包含：
```
LLM_API_BASE=...   # 或 OPENAI_API_BASE
LLM_API_KEY=...    # 或 OPENAI_API_KEY
LLM_MODEL_REASONING=gpt-5
LLM_MODEL_FAST=gpt-5-nano
LLM_TIMEOUT_SECONDS=120
LLM_MAX_RETRIES=2
```
- 离线/占位输出：`LLM_MODE=stub`
- 追踪日志：`LLM_TRACE=1`（输出到 `storage/logs/llm_trace.jsonl`，可用 `LLM_TRACE_PATH` 覆盖）
3) 准备用户档案（示例）：
```json
{
  "user_id": "u_demo",
  "birth": {"year":1990,"month":1,"day":1,"hour":8,"minute":0,"second":0},
  "gender": "male",
  "birth_time_unknown": false,
  "prompt_config": "lingyun_cat",
  "node_cache": {}
}
```
保存为 `user_profile.json`，或放在自定义路径。
4) 运行单次问答：
```bash
python app.py --profile user_profile.json --question "今年事业怎么样"
```

## 运行与调试选项
- 并发：`LLM_PARALLEL_WORKERS` 控制线程池，默认最多 8。
- 强制报错：`LLM_FORCE_ERROR=OVERALL` 或 `ALL` 以演练失败链路。
- 缓存：命中相同输入哈希直接返回；带错误标记的缓存会自动重跑。

## 存储路径惯例
- 推荐通过 `agent/storage/paths.py` 生成：`storage/users/<user_id>/profile.json` 与 `storage/users/<user_id>/conversations/<session>.jsonl`。
- `save_profile`/`append_event` 自动建目录。

## 测试脚本
- LLM stub 自检：`python tests/test_llm_tool_stub.py`
- 并发+缓存：`python tests/test_parallel_execution.py`
- 缓存重跑（失败清除）：`python -m pytest tests/test_cache_retry_on_error.py`
- 本地多轮回放（默认 stub）：`python tests/run_local_tester.py`
- 在线 LLM：`python tests/test_llm_live.py`，或测试矩阵 `python tests/run_live_suite.py --scenario fast_nano|reasoning_gpt5|force_error_overall`

## 常见问题
- API key 缺失：设置 `.env` 中的 `LLM_API_BASE`/`LLM_API_KEY`，或使用 `LLM_MODE=stub`。
- 档案缺字段：`birth`（含时分秒）、`gender`、`prompt_config`、`node_cache` 必填；`birth_time_unknown` 为布尔值。
- 时间解析范围有限：仅支持“今年/明年/去年”及 `YYYY年`/`YYYY年MM月`，复杂表达需自行扩展。

## 前端/服务对接（示例）
- 本仓库未自带 HTTP 接口，可自行封装。典型调用路径：加载用户档案 → `run_turn(profile, question, now=None)` → 保存档案 → 返回 `result["response"]`。
- 新会话：为用户生成/加载 `storage/users/<user_id>/profile.json`，可选额外创建 `conversations/<session>.jsonl` 记录事件（使用 `agent/storage/conversation_store.append_event`）。
- 继续会话：重复加载同一 profile，传入新问题即可复用缓存；会话日志文件可以继续 append。
- Python 伪代码：
  ```python
  from agent.orchestrator import run_turn
  from agent.storage.profile_store import load_profile, save_profile
  profile = load_profile("storage/users/u_demo/profile.json")
  result = run_turn(profile, "今年事业怎么样")
  save_profile("storage/users/u_demo/profile.json", profile)
  print(result["response"])
  ```

## 深入阅读
- 设计、依赖、缓存、工具接口、测试矩阵等详见《Agent开发文档.md》。
