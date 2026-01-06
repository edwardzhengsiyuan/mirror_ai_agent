# 八字 Agent 开发文档

> 面向维护者/二次开发：包含架构、节点/工具接口、缓存与并发、配置、测试与排查。功能准确性不在此文档验证范围，重点是工程可运行性与可维护性。

---

## 1. 总览与目标
- 目标：按需规划、最小节点执行、可缓存复用、可观测、易测试。
- 非目标：不保证八字结论准确性；不做复杂评估体系；UI/对话管理留给上层。
- 入口：`app.py`（单轮 CLI）。核心编排：`agent/orchestrator.py` → 规划 → DAG 执行 → 时间定位 → 答案拼装。

## 2. 目录与模块
- `app.py`：CLI 入口，加载/保存用户档案。
- `agent/planning.py`：方面分类与时间粒度识别（关键词+正则）。
- `agent/deps.py`：节点依赖常量与拓扑排序。
- `agent/execution.py`：缓存、并发、in-flight 去重、节点调度。
- `agent/nodes/prompt_builder.py`：从缓存取材料、加载模板、拼装 system/user prompt。
- `agent/response.py`：最终回答拼装。
- `agent/tools/`：`paipan_tool`（排盘）、`time_context_tool`（大运/流年/流月定位）、`llm_tool`（LLM+stub+trace）。
- `agent/storage/`：profile/conversation 读写、路径助手。
- `agent/prompts/templates/`：各节点的提示词模板（`lingyun_cat` 配置集）。
- `bazi/`：八字计算引擎，`BaziChartAnalyseFrame` 产出结构化排盘与大运流年。
- `tests/`：stub、自测、本地回放、并发、缓存重跑、在线 LLM。

## 3. 运行流程（`run_turn`）
1) `plan(question, now)`：输出 `{"aspects":[...],"time":{need_tool,granularity,ref_text,...}}`。未命中方面则归入 `OTHER`。
2) 组装节点集：`COMMON_PREREQS + aspects + PAIPAN`，使用 `run_nodes_parallel` 按拓扑并发执行；TIME_CONTEXT 不在 DAG 内。
3) 如需时间定位：调用 `ensure_node(..., "TIME_CONTEXT", {paipan_output, ref_text, now})`。
4) `compose_response`：按方面顺序拼接报告内容，附加时间定位信息（如有）。
5) 返回结果并由上层保存 profile（CLI 中由 `save_profile` 完成）。

## 4. 节点与依赖（DAG）
- 常量 `COMMON_PREREQS = ["PAIPAN","OVERALL","SHISHEN","GEJU","WUXING_PREFS"]`。
- `DEPS`：
  - `PAIPAN`: []（工具节点）
  - `OVERALL`: [PAIPAN]（总体分析）
  - `SHISHEN`: [PAIPAN]
  - `GEJU`: [PAIPAN, OVERALL]
  - `WUXING_PREFS`: [PAIPAN, OVERALL, SHISHEN, GEJU]
  - 领域节点 `CAREER/RELATIONSHIP/HEALTH/GUIREN/LIUQIN/XINGGE/OTHER`: 依赖 `COMMON_PREREQS`
- `TIME_CONTEXT`：不在 DAG，按需单独调用。
- 拓扑排序：`deps.toposort(nodes)` 确保依赖在前。

## 5. 规划逻辑（`planning.py`）
- 方面分类：`ASPECT_KEYWORDS` 基于关键词匹配；命中多个则多方面；都未命中则 `["OTHER"]`。
- 时间识别：
  - 相对年：`今年/明年/去年` → `need_tool=True, granularity="year", year=now.year+offset`
  - 绝对年月：`YYYY年MM月` → `granularity="month"`；绝对年：`YYYY年` → `granularity="year"`
  - 其他：`need_tool=False`
- 限制：不解析大运干支/范围描述；无 LLM fallback；需要扩展时可在此文件增加规则或引入模型。

## 6. 执行、缓存与并发（`execution.py`）
- 输入哈希：`_hash_inputs` 对 inputs JSON 序列化 + sha256，用于缓存命中判断。
- 失败识别：`_is_failure_output` 检查 `output.error` 或 `content` 以 `[LLM_ERROR:` 开头 → 视为失败并清缓存重跑。
- 缓存结构：`profile["node_cache"][node] = {"created_at","inputs_hash","output","meta":{started_at,ended_at,duration_ms}}`。
- In-flight 去重：并发时同一节点只执行一次，其他线程等待事件完成后复用结果。
- 并发：`run_nodes_parallel` 使用线程池（默认 `min(8,len(nodes))`，可由 `LLM_PARALLEL_WORKERS` 控制）。就绪节点（依赖已完成）批量提交；TIME_CONTEXT 被跳过。
- 单节点执行：
  - PAIPAN → `paipan_tool`
  - TIME_CONTEXT → `time_context_tool`
  - 其他 → build prompt → `llm_report_tool`
- 重试：LLM 工具层受 `LLM_MAX_RETRIES` 控制（默认 2 次尝试）；执行层无额外重试封装。
- 日志：`LLM_DEBUG` 打印节点开始/结束/缓存命中/等待；`meta.duration_ms` 记录耗时。

## 7. 工具接口
### 7.1 `paipan_tool(inputs)`
- 输入：`birth`（year/month/day/hour/minute/second）、`gender` ("male"/"female")、`birth_time_unknown`（bool）。
- 实现：`Solar.fromYmdHms(...).getLunar()` → `BaziChartAnalyseFrame(lunar, gender, without_time=birth_time_unknown)` → `get_analysis_summary()`。
- 输出：`{"paipan_results":文本,"liupan_results":文本,"guji_results":文本,"paipan_output":frame.res}`。
- `paipan_output["yun"]`：大运列表，含流年 `liunian`、流月 `liuyue`，用于时间工具；`startyun` 为起运年月日时。

### 7.2 `time_context_tool(paipan_output, ref_text, now_iso=None)`
- 仅在有排盘输出且命中规则时返回结构化时间：`{granularity,matched,dayun:{name,start_year,end_year},year:{year,ganzhi},month,source,confidence,raw_match}`。
- 支持相对年（今年/明年/去年）、绝对年、绝对年月；匹配失败返回 `None`。

### 7.3 `llm_report_tool(system_prompt, user_prompt, model=None, node=None, sleep_ms=None)`
- 环境加载：自动读取仓库根 `.env`（缺失则忽略）。
- 模式：`LLM_MODE=stub` 或未配置 API 时返回占位输出；否则调用 `/chat/completions` HTTP POST。
- 模型选择：`model="reasoning"` → `LLM_MODEL_REASONING`，否则用 `LLM_MODEL_FAST`（默认 gpt-5-nano）。
- 重试：`LLM_MAX_RETRIES` 次（默认 2）；超时 `LLM_TIMEOUT_SECONDS`（默认 120）。
- 失败注入：`LLM_FORCE_ERROR=NODE1,NODE2|ALL` 返回 `{"error":True,"content":"[LLM_ERROR:...]"}。`
- Trace：`LLM_TRACE=1` 记录 request/response/forced_error 到 `storage/logs/llm_trace.jsonl`（`LLM_TRACE_PATH` 可覆盖）。

## 8. Prompt 组织（`nodes/prompt_builder.py`）
- 模板目录：`agent/prompts/templates/`；固定模板：`OVERALL→init_analysis.md`、`SHISHEN→shishen.md`、`GEJU→geju.md`、`WUXING_PREFS→inter.md`。
- 配置集：`PROMPT_CONFIGS["lingyun_cat"]` 映射各领域节点到对应 `*_lym.md`；`prompt_config` 可在 profile 中切换。
- 上下文注入：从缓存读取 `PAIPAN` 文本（paipan/liupan/guji）、`OVERALL`/`SHISHEN`/`GEJU`/`WUXING_PREFS` 的 `output.content` 拼入 user prompt；`SYSTEM_PROMPT` 为固定英文句子。
- 容错：上游缺失时会插入空字符串，不会抛错；需要更强提示可在此文件增加显式缺失提示。

## 9. 存储与路径
- Profile 路径助手：`agent/storage/paths.py` → `storage/users/<user_id>/profile.json`；会话日志 `storage/users/<user_id>/conversations/<session>.jsonl`。
- Profile 结构（示例）：
  ```json
  {\n    "user_id": "u_demo",\n    "birth": {"year":1990,"month":1,"day":1,"hour":8,"minute":0,"second":0},\n    "gender": "male",\n    "birth_time_unknown": false,\n    "prompt_config": "lingyun_cat",\n    "node_cache": {}\n  }\n  ```
- 缓存项：见 §6。`save_profile`/`append_event` 自动建目录。
- 会话日志：`conversation_store.append_event(path, event_dict)` 逐行 JSONL；测试脚本用它记录 `user_message/plan/outputs/time_context/assistant_final`。

## 10. 配置与环境变量
- `LLM_API_BASE`/`OPENAI_API_BASE`，`LLM_API_KEY`/`OPENAI_API_KEY`：真实调用所需。
- `LLM_MODE`：`stub` 时走占位输出（不访问网络）。
- `LLM_MODEL_REASONING`（默认 gpt-5），`LLM_MODEL_FAST`（默认 gpt-5-nano）。
- `LLM_TIMEOUT_SECONDS`（默认 120），`LLM_MAX_RETRIES`（默认 2）。
- `LLM_PARALLEL_WORKERS`：并发线程池大小（默认 min(8,节点数)）。
- `LLM_DEBUG`：打印调试日志；`LLM_TRACE`/`LLM_TRACE_PATH`：请求/响应追踪输出路径。
- `LLM_FORCE_ERROR`：强制特定节点或 `ALL` 走错误形态，用于演练失败链路。

## 11. 测试与调试脚本
- Stub 自检：`python tests/test_llm_tool_stub.py`（无需 API）。
- 并发与缓存：`python tests/test_parallel_execution.py`（依赖 stub）。
- 缓存失败重跑：`python -m pytest tests/test_cache_retry_on_error.py`。
- 本地多轮回放：`python tests/run_local_tester.py`，生成/更新 `storage/profile_demo.json` 与 `storage/conversations/demo.jsonl`。
- 在线 LLM：`python tests/test_llm_live.py`；测试矩阵 `python tests/run_live_suite.py --scenario fast_nano|reasoning_gpt5|force_error_overall`（`LLM_LIVE_FULL=1` 才跑全流程）。
- 断点恢复示例：`python -m pytest tests/test_resume_cache_live_profiles.py`（使用 `storage/users/*/profile.json` 作为夹具）。

## 12. 已知限制与改进建议
- 规划简单：仅关键词+正则；不解析大运干支/时间范围；无多轮上下文记忆。可引入 LLM 分类或规则扩展。
- 时间解析覆盖有限：相对年/绝对年月，未覆盖“未来两年”“第 X 步大运”等复杂表达。
- LLM 重试：仅工具层按 `LLM_MAX_RETRIES`，若需统一 3 次重试或熔断需在执行层封装。
- Prompt 容错：缺失上游内容只会插入空字符串，如需显式“不确定”提示需修改 `prompt_builder`。
- 安全：仓库含示例 `.env`，请在生产环境替换密钥；避免将真实密钥提交版本库。

## 13. 排查指南
- 运行无响应/报错 `[LLM_ERROR:*]`：检查 `.env` 的 BASE/KEY；或开启 `LLM_MODE=stub`；查看 `storage/logs/llm_trace.jsonl`。
- 排盘失败：确认 profile 中 `birth` 字段完整（含时分秒）且 `gender`、`birth_time_unknown` 合法；`lunar-python` 需能处理的日期范围内。
- 缓存不命中/重复执行：检查是否修改了输入（导致 `inputs_hash` 变化）；`LLM_FORCE_ERROR` 会使缓存被视为失败并重算。
- 并发阻塞：确认 `LLM_PARALLEL_WORKERS` 是否过小；in-flight 去重会导致同节点等待同一个执行完成。
- 时间定位为空：`ref_text` 未命中规则或排盘无对应年份；可打印 `plan["time"]` 及 `time_context_tool` 返回值排查。

## 14. 流式事件与节点输出
- 接口：`run_turn(profile, question, now=None, event_sink=..., stream=True)`。
- 事件回调：`event_sink(event: dict)`，会在节点开始/结束、工具调用、流式输出时被调用。
- 关键事件类型：
  - `plan`：规划结果（包含 `aspects` 与 `time`）。
  - `node_start` / `node_end`：节点开始/结束；`node_end.output` 为最终输出；缓存命中会带 `cached=true`。
  - `node_delta`：流式输出片段（`delta`/`reasoning_delta`）。
  - `tool_call` / `tool_result`：工具调用与完成（PAIPAN/TIME_CONTEXT/LLM）。
  - `time_context`：时间定位结果（可能为 `None`）。
- 工具节点流式：PAIPAN/TIME_CONTEXT 在计算完成后以分片形式回放输出，保证前端统一接收流式事件。
- 线程安全：执行引擎可能并发调用事件回调，建议在回调中使用线程安全队列或锁。

## 15. 前端/服务对接指南
- 当前不内置 HTTP 层，建议自行封装薄的 API 服务，调用链：加载 profile → `run_turn(profile, question, now=None)` → 保存 profile → 返回 `result`。
- Profile 位置：推荐 `storage/users/<user_id>/profile.json`（可用 `agent/storage/paths.py` 生成）；会话日志可选写入 `storage/users/<user_id>/conversations/<session>.jsonl`（使用 `conversation_store.append_event`）。
- 新会话：
  - 创建/初始化 profile（含 birth/gender/prompt_config/node_cache）。
  - 生成新的 session id，用 JSONL 记录 `user_message/plan/assistant_final` 事件（可选）。
  - 调用 run_turn，得到 `result={"plan","outputs","time_context","response"}`。
- 继续会话：重复加载同一 profile，传入新问题即可复用缓存；日志文件可在同一 session 继续 append。
- Python 示例（可作为 HTTP handler 内部逻辑）：
  ```python
  from agent.orchestrator import run_turn
  from agent.storage.profile_store import load_profile, save_profile
  from agent.storage.conversation_store import append_event
  from agent.storage.paths import session_paths
  import datetime as dt

  user_id = "u_demo"
  profile_path, convo_path = session_paths(user_id, session_id="sess_1")
  profile = load_profile(profile_path)

  question = "今年事业怎么样"
  now = dt.datetime.now()
  append_event(convo_path, {"ts": now.isoformat(), "type": "user_message", "text": question})
  result = run_turn(profile, question, now=now)
  append_event(convo_path, {"ts": now.isoformat(), "type": "plan", "plan": result["plan"]})
  append_event(convo_path, {"ts": now.isoformat(), "type": "assistant_final", "text": result["response"]})
  save_profile(profile_path, profile)
  ```
- 如需 HTTP JSON 形态，可封装接口：`POST /ask`，请求 `{user_id, question, session_id?}`，响应 `{plan, time_context, response, cache_keys?}`；内部逻辑与上述相同。

## 16. CLI 聊天前端
- 启动：`python cli_chatbot.py`。
- 功能：选择/创建用户、选择会话、流式显示节点输出与工具调用，节点可展开/折叠。
- 操作：`Tab` 切换视图，`↑/↓` 选择节点，`Space` 展开/折叠，`Enter` 发送，`q` 退出。

## 17. Web 前端
- 后端服务：`python web_server.py`，默认监听 `0.0.0.0:8000`。
- 前端入口：`http://localhost:8000/`（静态页面 `web/index.html`）。
- 交互能力：
  - 创建用户与会话、加载历史消息。
  - 通过 SSE 订阅 `ask_stream` 的事件流，流式更新节点输出与工具调用日志。
  - 节点输出以 `<details>` 展开/折叠，流式输出自动刷新。
- API 约定（JSON）：
  - `GET /api/users` → `{users: []}`
  - `POST /api/users` → `{user_id, birth, gender, birth_time_unknown, prompt_config}` 创建用户
  - `GET /api/profile?user_id=...` → profile JSON
  - `GET /api/sessions?user_id=...` → `{sessions: []}`
  - `POST /api/sessions` → `{user_id, session_id?}` 创建会话
  - `GET /api/history?user_id=...&session_id=...` → `{messages:[{role,text}]}` 
  - `POST /api/ask` → 非流式 `{plan, time_context, response}`
  - `POST /api/ask_stream` → `text/event-stream`，逐条返回事件 JSON（含 `session`、`plan`、`node_*`、`tool_*`、`assistant_final`）

---

更新维护：本文件为开发者手册，README 只保留给使用者的快速指南。修改核心流程或依赖时请同步更新两份文档。
