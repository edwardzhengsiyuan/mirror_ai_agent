# 八字 Agent 开发文档 / Development Guide

> 面向维护者/二次开发：包含架构、节点/工具接口、缓存与并发、配置、测试与排查。功能准确性不在此文档验证范围，重点是工程可运行性与可维护性。  
> EN: For maintainers and integrators. Covers architecture, nodes/tools, caching/concurrency, config, tests, and debugging. Accuracy of bazi interpretation is out of scope; this doc focuses on operability and maintainability.

## English Summary (TL;DR)
- **Concept separation**: Persistent **Nodes** (cached in profile) vs conversation-level **Tools** (PLANNER, TIME_CONTEXT) and **Response** (not cached).
- Single-turn flow: PAIPAN → PLANNER tool → parallel DAG → TIME_CONTEXT tool → Response generation.
- Planning only specifies years; dayun hints from PAIPAN help LLM understand time context.
- TIME_CONTEXT directly calls `find_yun_liu_nian_liuyue(year)` to fetch year data - no regex parsing.
- Prompts receive targeted year data (大运/流年/流月 details per year).
- Caching is per profile object; in-flight de-dup uses (profile object, node, inputs hash).
- **Conversation-level data**: PLANNER, TIME_CONTEXT, and Response are stored in conversation JSONL, not profile.node_cache.
- LLM calls default to stub if no API config; live tests are gated by env.
- **Web UI**: 3-column layout (sidebar/chat/info), streaming output, Markdown rendering, Chinese node names, conversation history.
- Agent rulebook lives in `CLAUDE.md`.
- Engine API reference lives in `bazi/README.md`.

---

## 1. 总览与目标
- 目标：按需规划、最小节点执行、可缓存复用、可观测、易测试。
- 非目标：不保证八字结论准确性；不做复杂评估体系；UI/对话管理留给上层。
- 入口：`app.py`（单轮 CLI）。核心编排：`agent/orchestrator.py` → 规划 → DAG 执行 → 时间定位 → 答案拼装。

## 2. 目录与模块
- `app.py`：CLI 入口，加载/保存用户档案。
- `web_server.py`：HTTP/SSE 服务与前端接口。
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

## 2.1 引擎说明（bazi）
- `bazi/` 当前为新引擎实现（原 `bazi_new`），对外导入路径保持不变。
- 结构化输出的枚举字段统一为命名空间码（`NAMESPACE:CODE`），展示层如需中文请用 `bazi.core.property.strip_ns` + 枚举映射。
- `BaziChartAnalyseFrame.find_yun_liu_nian_liuyue(target_year)` 可返回可读流年查询文本，包含完整的大运、流年、流月信息。
- `paipan_tool` 会从 `frame.res["yun"]` 直接提取 `dayun_list`（大运列表），用于规划提示词。
- API 参考文档：`bazi/README.md`。

## 3. 运行流程（`run_turn`）

### 概念区分
- **持久 Node**：存储在 `profile.node_cache`，用户维度缓存（PAIPAN, OVERALL, SHISHEN, GEJU, WUXING_PREFS, CAREER 等）
- **对话级 Tool**：存储在 `conversation/<session>.jsonl`，每次调用独立记录（PLANNER, TIME_CONTEXT）
- **对话级 Response**：存储在 `conversation/<session>.jsonl`，不再作为 node 缓存（原 FINAL）

### 执行流程
1) **PAIPAN 节点**（持久，缓存）：得到排盘文本、结构化 `paipan_output`、以及 `dayun_list`。
2) **PLANNER 工具**（对话级，不缓存）：`run_tool("PLANNER", {...})` 输出 `{"aspects":[...],"times":[...]}`；发送 `tool_invocation` 事件。
3) **持久节点 DAG**：组装 `COMMON_PREREQS + aspects`，使用 `run_nodes_parallel` 按拓扑并发执行；缓存命中时复用。
4) **TIME_CONTEXT 工具**（对话级，不缓存）：如需时间定位，`run_tool("TIME_CONTEXT", {...})` 获取年份数据；发送 `tool_invocation` 事件。
5) **Response 生成**（对话级，不缓存）：`run_response(profile, {...})` 综合所有节点输出与时间定位生成最终答复；发送 `response` 事件。
6) 返回结果：`{"plan", "outputs", "time_context", "response", "tool_invocations"}`。
7) 上层保存 profile（只保存持久节点缓存）。

## 4. 节点与依赖（DAG）

### 持久节点（缓存在 profile.node_cache）
- 常量 `PERSISTENT_NODES = ["PAIPAN","OVERALL","SHISHEN","GEJU","WUXING_PREFS","CAREER","RELATIONSHIP","HEALTH","GUIREN","LIUQIN","XINGGE","OTHER"]`
- 常量 `COMMON_PREREQS = ["PAIPAN","OVERALL","SHISHEN","GEJU","WUXING_PREFS"]`
- `DEPS`：
  - `PAIPAN`: []（排盘工具）
  - `OVERALL`: [PAIPAN]（总体分析）
  - `SHISHEN`: [PAIPAN]
  - `GEJU`: [PAIPAN, OVERALL]
  - `WUXING_PREFS`: [PAIPAN, OVERALL, SHISHEN, GEJU]
- 领域节点 `CAREER/RELATIONSHIP/HEALTH/GUIREN/LIUQIN/XINGGE/OTHER`: 依赖 `COMMON_PREREQS`
- 拓扑排序：`deps.toposort(nodes)` 确保依赖在前。

### 对话级工具（不缓存，存储在 conversation JSONL）
- `CONVERSATION_TOOLS = ["PLANNER", "TIME_CONTEXT"]`
- `PLANNER`：问题规划，返回 aspects 和 times
- `TIME_CONTEXT`：时间定位，返回 year_data

### Response（不缓存，存储在 conversation JSONL）
- 原 `FINAL` 节点已重命名为 Response
- 不再出现在 DEPS 中
- 使用 `run_response()` 函数执行

## 5. 规划逻辑（`planning.py`）
- 规划默认走 LLM：`LLM_PLANNER_MODE=llm`（默认），通过 LLM 输出 `planning_tool` 的 JSON 调用结果，且 prompt 中包含大运范围提示。
- 规则回退：`LLM_MODE=stub` 或 `LLM_PLANNER_MODE=rule` 时使用关键词/正则规则。
- 方面分类（规则）：`ASPECT_KEYWORDS` 关键词匹配；未命中则 `["OTHER"]`。
- 时间识别（规则）：会扫描多个时间表达并生成 `times` 列表（仅支持年份）。
  - 相对年：`今年/明年/去年` → `{need_tool: true, ref_text: "今年", year: now.year+offset}`
  - 绝对年：`YYYY年` 或 `YYYY年MM月` → 仅提取 year
- 规划合并：即使 LLM 只返回单条时间，也会用正则补全问题中遗漏的多年份。
- 规范化：若 LLM 提供了年份但 `need_tool=false`，会自动强制为 `true`，确保时间工具执行。
- **大运字段（已简化）**：`dayun` 字段为可选/已弃用。LLM 规划只需指定年份（year），系统会通过 `find_yun_liu_nian_liuyue(year)` 自动获取该年对应的大运信息。
- **时间范围展开**：LLM 规划器应将"未来两年"等范围表达展开为多个具体年份的 `times` 条目。
- 规划提示词位置：`agent/planning.py` 的 `_build_planner_prompt()`。
- LLM 输出 schema（简化版，仅需指定年份）：
  ```json
  {"tool":"planning_tool","args":{"aspects":["CAREER"],"times":[{"year":2025}]}}
  ```
  - `times` 支持多条时间；`time` 字段为兼容保留，等于 `times[0]`。
  - 规范化后的 time 结构：`{need_tool: bool, ref_text: string|null, year: int|null}`。
  - **注意**：`granularity` 和 `month` 字段已移除，系统仅支持年级别查询。

## 6. 执行、缓存与并发（`execution.py`）
- 输入哈希：`_hash_inputs` 对 inputs JSON 序列化 + sha256，用于缓存命中判断。
- 失败识别：`_is_failure_output` 检查 `output.error` 或 `content` 以 `[LLM_ERROR:` 开头 → 视为失败并清缓存重跑；工具异常会包装为 `[NODE_ERROR:...]` 输出并标记 `error=true`。
- 缓存结构：`profile["node_cache"][node] = {"created_at","inputs_hash","output","meta":{started_at,ended_at,duration_ms}}`。
- In-flight 去重：并发时同一节点在同一 profile 实例 + 同一 inputs hash 下只执行一次，其他线程等待事件完成后复用结果。
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
- 输出：`{"paipan_results":文本,"liupan_results":文本,"guji_results":文本,"paipan_output":frame.res,"dayun_list":[...]}`。
- `paipan_output["yun"]`：大运列表，含流年 `liunian`、流月 `liuyue`；`startyun` 为起运年月日时。
- `dayun_list`：直接从 `frame.res["yun"]` 提取，格式为 `[{name,start_year,end_year,step,age_start}]`，用于规划提示词中的大运范围提示。

### 7.2 `time_context_tool(requests, birth, gender, birth_time_unknown=False)`
- **简化后的接口**：直接调用 `find_yun_liu_nian_liuyue(year)` 获取每个目标年份的数据，无需中间索引层。
- 输入：
  - `requests`：`[{year: int}]`，需要获取数据的年份列表。
  - `birth`：出生信息 `{year, month, day, hour, minute, second}`。
  - `gender`：`"male"` 或 `"female"`。
  - `birth_time_unknown`：是否缺少出生时间（bool）。
- 输出：`{"year_data": [{year: int, data: str}, ...]}`。
  - `year_data` 每条包含该年的完整大运/流年/流月详情（来自 `find_yun_liu_nian_liuyue`）。
  - 示例：`{"year_data": [{"year": 2026, "data": "所在大运：戊戌【正官正官】...目标流年：2026丙午...流月：..."}]}`。

### 7.3 `llm_report_tool(system_prompt, user_prompt, model=None, node=None, sleep_ms=None)`
- 环境加载：自动读取仓库根 `.env`（缺失则忽略）。
- 模式：`LLM_MODE=stub` 或未配置 API 时返回占位输出；否则调用 `/chat/completions` HTTP POST。
- 模型选择：`model="reasoning"` → `LLM_MODEL_REASONING`，否则用 `LLM_MODEL_FAST`（默认 gpt-5-nano）。
- 重试：`LLM_MAX_RETRIES` 次（默认 2）；超时 `LLM_TIMEOUT_SECONDS`（默认 120）。
- 失败注入：`LLM_FORCE_ERROR=NODE1,NODE2|ALL` 返回 `{"error":True,"content":"[LLM_ERROR:...]"}`。
- Trace：`LLM_TRACE=1` 记录 request/response/forced_error 到 `storage/logs/llm_trace.jsonl`（`LLM_TRACE_PATH` 可覆盖）。

## 8. Prompt 组织（`nodes/prompt_builder.py`）
- 模板目录：`agent/prompts/templates/`；固定模板：`OVERALL→init_analysis.md`、`SHISHEN→shishen.md`、`GEJU→geju.md`、`WUXING_PREFS→inter.md`、`RESPONSE_PROMPT→final_answer.md`。
- 配置集：`PROMPT_CONFIGS["lingyun_cat"]` 映射各领域节点到对应 `*_lym.md`；`prompt_config` 可在 profile 中切换。
- 上下文注入：从缓存读取 `PAIPAN` 文本（paipan/guji）、`OVERALL`/`SHISHEN`/`GEJU`/`WUXING_PREFS` 的 `output.content` 拼入 user prompt。
- **Response prompt**：使用 `build_response_prompt()` 函数构建，`time_context` 作为参数传入（而非从缓存读取）；会额外拼接各领域节点报告、用户问题与最近对话轮次（`history_rounds`）。
- **year_data 注入**：`TIME_CONTEXT` 返回的 `year_data` 包含每个目标年份的大运/流年/流月详情（来自 `find_yun_liu_nian_liuyue`），会被注入到 Response prompt 中。
- 容错：上游缺失时会插入空字符串，不会抛错；需要更强提示可在此文件增加显式缺失提示。

## 9. 存储与路径
- Profile 路径助手：`agent/storage/paths.py` → `storage/users/<user_id>/profile.json`；会话日志 `storage/users/<user_id>/conversations/<session>.jsonl`。
- Profile 结构（示例）：
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
- 缓存项：见 §6。`save_profile`/`append_event` 自动建目录。
- 会话日志：`conversation_store.append_event(path, event_dict)` 逐行 JSONL。
- **新增事件类型**：
  - `tool_invocation`：对话级工具调用记录（PLANNER, TIME_CONTEXT），包含 input/output/duration_ms/llm_prompt
  - `response`：Response 生成记录，包含 text/input_summary/llm_prompt/duration_ms
- **Legacy 事件**：`plan`、`time_context` 仍会记录；`assistant_final` 已废弃（新对话不再写入）
- 便捷读取：
  - `conversation_store.load_recent_rounds(path, max_rounds=5)` 返回最近 N 轮 `{"user","assistant"}` 对话对（使用 response 格式）
  - `conversation_store.load_tool_invocations(path, tool=None)` 返回工具调用列表
  - `conversation_store.load_responses(path)` 返回 Response 事件列表

## 10. 配置与环境变量
- `LLM_API_BASE`/`OPENAI_API_BASE`，`LLM_API_KEY`/`OPENAI_API_KEY`：真实调用所需。
- `LLM_MODE`：`stub` 时走占位输出（不访问网络）。
- `LLM_MODEL_REASONING`（默认 gpt-5），`LLM_MODEL_FAST`（默认 gpt-5-nano）。
- `LLM_TIMEOUT_SECONDS`（默认 120），`LLM_MAX_RETRIES`（默认 2）。
- `LLM_PARALLEL_WORKERS`：并发线程池大小（默认 min(8,节点数)）。
- `LLM_DEBUG`：打印调试日志；`LLM_TRACE`/`LLM_TRACE_PATH`：请求/响应追踪输出路径。
- `LLM_FORCE_ERROR`：强制特定节点或 `ALL` 走错误形态，用于演练失败链路。

## 10.1 Python 环境 / Python Environment
- 推荐使用仓库内的虚拟环境目录：`.venv/`。
- 创建与安装：
  - `python3 -m venv .venv`
  - `.venv/bin/pip install -r requirements.txt`
- 运行 pytest：
  - `.venv/bin/pytest`
- 说明：不要依赖系统全局 Python（可能受 PEP 668 限制）。
## 11. 测试与调试脚本
- 依赖：pytest 已包含在 `requirements.txt`。
- Stub 自检：`python tests/test_llm_tool_stub.py`（无需 API）。
- 并发与缓存：`python tests/test_parallel_execution.py`（依赖 stub）。
- 缓存失败重跑：`python -m pytest tests/test_cache_retry_on_error.py`。
- 多时间点解析：`python -m pytest tests/test_multi_time_context.py`。
- 本地多轮回放：`python tests/run_local_tester.py`，生成/更新 `storage/users/u_demo/profile.json` 与 `storage/users/u_demo/conversations/demo.jsonl`。
- 在线 LLM（pytest）：`pytest -m llm_live`（需配置 API KEY）；全流程需 `LLM_LIVE_FULL=1`。
- 在线 LLM 默认超时：测试会设置 `LLM_TIMEOUT_SECONDS=400`。
- 在线 LLM（脚本）：`python tests/test_llm_live.py`；测试矩阵 `python tests/run_live_suite.py --scenario fast_nano|reasoning_gpt5|force_error_overall`。
- 全流程在线验收：`LLM_LIVE_FULL=1` 会额外校验事件流与会话日志。

### 引擎回归检查（快速）
- 构建 `BaziChartAnalyseFrame` 并调用 `get_analysis_summary()`，确认无异常。
- 调用 `find_yun_liu_nian_liuyue(YYYY)`，确认返回非空文本。
- 运行 `python app.py --profile user_profile.json --question "今年事业怎么样"`，确认输出包含 `【流年大运排盘】`。
- 检查 `time_index["liunian_list"][0]["ganzhi"]` 为中文（非 `GAN:*`）。
- 断点恢复示例：`python -m pytest tests/test_resume_cache_live_profiles.py`（使用 `storage/users/*/profile.json` 作为夹具）。

## 12. 已知限制与改进建议
- 规划简单：仅关键词+正则；上下文记忆仅注入最近 N 轮（默认 5，可配置）。可引入更复杂的对话状态管理。
- 时间解析：LLM 规划器可处理时间范围表达（如"未来两年"），会展开为多个年份条目；规则模式仅支持相对年/绝对年月。
- LLM 重试：仅工具层按 `LLM_MAX_RETRIES`，若需统一 3 次重试或熔断需在执行层封装。
- Prompt 容错：缺失上游内容只会插入空字符串，如需显式"不确定"提示需修改 `prompt_builder`。
- 安全：仓库含示例 `.env`，请在生产环境替换密钥；避免将真实密钥提交版本库。

## 13. 排查指南
- 运行无响应/报错 `[LLM_ERROR:*]`：检查 `.env` 的 BASE/KEY；或开启 `LLM_MODE=stub`；查看 `storage/logs/llm_trace.jsonl`。
- 排盘失败：确认 profile 中 `birth` 字段完整（含时分秒）且 `gender`、`birth_time_unknown` 合法；`lunar-python` 需能处理的日期范围内。
- 缓存不命中/重复执行：检查是否修改了输入（导致 `inputs_hash` 变化）；`LLM_FORCE_ERROR` 会使缓存被视为失败并重算。
- 并发阻塞：确认 `LLM_PARALLEL_WORKERS` 是否过小；in-flight 去重会导致同节点等待同一个执行完成。
- 时间定位为空：`ref_text` 未命中规则或排盘无对应年份；可打印 `plan["times"]`（或 `plan["time"]`）及 `time_context_tool` 返回值排查。

## 14. 流式事件与节点输出
- 接口：`run_turn(profile, question, now=None, event_sink=..., stream=True)`。
- 可选参数：`history_rounds=[{"user":"...","assistant":"..."}]` 用于 Response prompt 注入最近对话。
- 事件回调：`event_sink(event: dict)`，会在节点开始/结束、工具调用、流式输出时被调用。
- 关键事件类型：
  - **`tool_invocation`**：（新）对话级工具调用完成，包含 `{tool, invocation_id, input, output, duration_ms, llm_prompt}`。
  - **`response`**：（新）Response 生成完成，包含 `{text, input_summary, llm_prompt, duration_ms}`。
  - `plan`：规划结果（向后兼容，同时有 `tool_invocation` 事件）。
  - `node_start` / `node_end`：持久节点开始/结束；`node_end.output` 为最终输出；缓存命中会带 `cached=true`。
  - `node_delta`：流式输出片段（`delta`/`reasoning_delta`）。
  - `response_delta`：（新）Response 流式输出片段。
  - `tool_call` / `tool_result`：低级工具调用与完成（paipan_tool/llm_report_tool/time_context_tool）。
  - `llm_prompt`：每次 LLM 调用的 system/user prompt（便于前端审计与调试）。
  - `time_context`：时间定位结果（legacy 事件）。
  - `assistant_final`：**已废弃**，新对话使用 `response` 事件。
- 工具节点流式：PAIPAN 在计算完成后以分片形式回放输出，保证前端统一接收流式事件。
- 线程安全：执行引擎可能并发调用事件回调，建议在回调中使用线程安全队列或锁。

### UI 展示建议
- **持久节点**：显示在独立的节点面板，展示状态（idle/running/done/cache/error）和输出内容。
- **对话级工具**（PLANNER, TIME_CONTEXT）：在用户消息下方以内联方式展示，可点击展开查看输入输出详情。
- **Response**：在对话面板显示最终回答，可点击展开查看输入摘要和完整 prompt。

## 15. Web UI / 前端界面

### 15.1 布局架构
Web UI 采用三列布局（类似 ChatGPT/Claude 风格）：
```
┌─────────────┬─────────────────────┬──────────────┐
│  左侧边栏    │      中间对话区      │   右侧面板    │
│  (260px)    │       (flex)        │   (340px)    │
├─────────────┼─────────────────────┼──────────────┤
│ 对话历史列表 │     聊天消息        │  用户档案     │
│             │     Tool Cards      │  节点输出     │
│             │     输入框          │  事件日志     │
├─────────────┤                     │              │
│ 用户信息     │                     │              │
│ 设置按钮     │                     │              │
└─────────────┴─────────────────────┴──────────────┘
```

### 15.2 核心功能
- **流式响应显示**：监听 `response_delta` 事件实时渲染 LLM 输出
- **Tool Call 即时显示**：`tool_call` 事件触发时立即创建占位卡片，`tool_invocation` 完成后更新
- **Markdown 渲染**：使用 marked.js 渲染 assistant 消息（标题、列表、代码块、引用）
- **中文节点名称**：`NODE_NAMES_ZH` 映射（如 PAIPAN→排盘, CAREER→事业）
- **对话历史侧边栏**：通过 `/api/session_metadata` 获取会话列表及首条消息预览
- **响应式设计**：移动端（<1024px）自动隐藏侧边栏

### 15.3 后端 API
| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/session_metadata` | GET | 返回会话列表及首条消息预览 |
| `/api/sessions` | GET/POST | 会话列表/创建新会话 |
| `/api/users` | GET/POST | 用户列表/创建用户 |
| `/api/profile` | GET | 获取用户档案 |
| `/api/history` | GET | 获取会话历史消息 |
| `/api/ask_stream` | POST | 流式问答（SSE） |

### 15.4 文件
- `web/index.html`：前端 HTML/CSS/JS（单文件）
- `web_server.py`：Flask 后端

## 16. 前端/服务对接指南
- 当前不内置 HTTP 层，建议自行封装薄的 API 服务，调用链：加载 profile → `run_turn(profile, question, now=None)` → 保存 profile → 返回 `result`。
- Profile 位置：推荐 `storage/users/<user_id>/profile.json`（可用 `agent/storage/paths.py` 生成）；会话日志可选写入 `storage/users/<user_id>/conversations/<session>.jsonl`（使用 `conversation_store.append_event`）。
- 新会话：
  - 创建/初始化 profile（含 birth/gender/prompt_config/node_cache）。
  - 生成新的 session id，用 JSONL 记录 `user_message/plan/response` 事件（可选）。
  - 调用 run_turn，得到 `result={"plan","outputs","time_context","response"}`。
- 继续会话：重复加载同一 profile，传入新问题即可复用缓存；日志文件可在同一 session 继续 append。
- Python 示例（可作为 HTTP handler 内部逻辑）：
  ```python
  from agent.orchestrator import run_turn
  from agent.storage.profile_store import load_profile, save_profile
  from agent.storage.conversation_store import append_event, load_recent_rounds
  from agent.storage.paths import session_paths
  import datetime as dt

  user_id = "u_demo"
  profile_path, convo_path = session_paths(user_id, session_id="sess_1")
  profile = load_profile(profile_path)

  question = "今年事业怎么样"
  now = dt.datetime.now()
  history_rounds = load_recent_rounds(convo_path, 5)
  append_event(convo_path, {"ts": now.isoformat(), "type": "user_message", "text": question})
  result = run_turn(profile, question, now=now, history_rounds=history_rounds)
  append_event(convo_path, {"ts": now.isoformat(), "type": "plan", "plan": result["plan"]})
  # Note: response event is logged automatically via event_sink
  save_profile(profile_path, profile)
  ```
- 如需 HTTP JSON 形态，可封装接口：`POST /ask`，请求 `{user_id, question, session_id?}`，响应 `{plan, time_context, response, cache_keys?}`；内部逻辑与上述相同。
- 流式接口 `POST /api/ask_stream` 会额外推送 `llm_prompt` 事件，便于前端查看每次 LLM 的输入。
