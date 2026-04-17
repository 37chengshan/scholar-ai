---
owner: ai-platform
status: done
depends_on:
  - PR10
last_verified_at: 2026-04-17
evidence_commits:
  - 89a9d9a
---

# PR11：Harness Observability 文件级实施方案

## 1. 目标

在当前 `scholar-ai` 主线基础上，为 **Chat / Search / KB Import / RAG Query** 四条主链路建立统一的可观测性底座，使系统具备：

- 可追踪：一次请求、一次会话、一次消息、一次导入任务可以串起来
- 可归因：知道慢在哪一步、错在哪一步、哪条链路出问题
- 可回放：后续 PR12 能基于统一 run id 和 phase 产出基线
- 可扩展：后续 Agent-Native UX、RAG 第二轮升级都能直接挂载

---

## 2. 当前基线（基于现有代码）

### 已有基础
- `apps/api/app/utils/logger.py`
  - 已使用 `structlog`
  - 已支持 `structlog.contextvars.merge_contextvars`
  - 已能自动合并 contextvars 到日志事件
- `apps/api/app/main.py`
  - 已有 `RequestLoggingMiddleware`
  - 是添加 request-scoped correlation id / tracing middleware 的最佳入口
- `apps/api/app/core/streaming.py`
  - 已有 RAG SSE streaming utilities
  - 当前仍是轻量事件模型（token / citations / error / done）
- `apps/api/app/services/chat_orchestrator.py`
  - 已具备 `message_id` 绑定、phase inference、SSEEventEnvelope、confirmation persistence
  - 是 Chat / Agent runtime observability 的主承接点
- `apps/web/src/app/hooks/useChatStream.ts`
  - 已有 phase、message_id 校验、buffer、toolTimeline、citations、confirmation
  - 是前端链路级 telemetry 与 UX 观测的最佳落点

### 当前缺口
- 没有统一的 `request_id / run_id / session_id / message_id / job_id`
- 后端 logs 还不是“主链路统一观测模型”
- 没有 trace spans（至少逻辑 span）
- 没有 phase-level duration / latency 统计
- 前端没有统一 telemetry sink
- KB import / Search / RAG / Chat 四条链路没有统一事件 schema
- 还没有给后续 PR12 的 benchmark 基线提供统一观测字段

---

## 3. 非目标（本 PR 不做）

- 不引入完整的 Grafana / Loki / Tempo 生产化平台
- 不做全量 OpenTelemetry vendor 集成
- 不做所有页面的 UI 埋点
- 不做 benchmark 脚本（那是 PR12）
- 不改业务语义，不做 agent-native 交互增强

---

## 4. 统一观测模型

## 4.1 统一上下文字段

后端日志 / 前端 telemetry / SSE envelope / benchmark 样本统一使用：

- `request_id`
- `run_id`
- `session_id`
- `message_id`
- `job_id`
- `paper_id`
- `kb_id`
- `query_id`（Search / RAG 可选）
- `user_id`
- `route`
- `phase`
- `event_type`
- `duration_ms`
- `status`

### 字段规则
- `request_id`：HTTP 请求级，来自 middleware
- `run_id`：一次完整业务执行链（Chat send、RAG query、Import run、Search action）
- `session_id`：聊天 / 会话上下文
- `message_id`：Chat assistant message 绑定
- `job_id`：导入任务、解析任务
- `phase`：analyzing / retrieving / reading / tool_calling / synthesizing / verifying / done / error / cancelled

---

## 4.2 事件命名规范

统一采用：

- `request_started`
- `request_completed`
- `request_failed`

- `run_started`
- `run_completed`
- `run_failed`

- `phase_started`
- `phase_completed`

- `tool_call_started`
- `tool_call_completed`
- `tool_call_failed`

- `stream_started`
- `stream_chunk_emitted`
- `stream_completed`
- `stream_failed`

- `import_job_started`
- `import_job_progress`
- `import_job_completed`
- `import_job_failed`

- `search_started`
- `search_completed`
- `search_failed`

- `rag_retrieve_started`
- `rag_retrieve_completed`
- `rag_answer_started`
- `rag_answer_completed`

---

## 5. 文件级实施方案

## 5.1 后端：日志与上下文主链

### A. 修改 `apps/api/app/utils/logger.py`
### 目标
把当前 `structlog` 基础配置升级为统一 observability logger。

### 具体改动
- 增加标准 processor：
  - request/run context merge
  - exception formatter
  - duration field helper
- 统一输出字段：
  - `event`
  - `request_id`
  - `run_id`
  - `session_id`
  - `message_id`
  - `job_id`
  - `phase`
  - `duration_ms`
- 新增 logger helper：
  - `bind_request_context(...)`
  - `bind_run_context(...)`
  - `clear_observability_context()`

### 交付
- logger 不只是“能打日志”，而是“能承载统一上下文”

---

### B. 新增 `apps/api/app/core/observability/context.py`
### 目标
集中管理 correlation ids 与 contextvars。

### 新增内容
- contextvars 定义：
  - request_id_var
  - run_id_var
  - session_id_var
  - message_id_var
  - job_id_var
  - paper_id_var
  - kb_id_var
  - user_id_var
  - route_var
- helper：
  - `set_request_context(...)`
  - `set_run_context(...)`
  - `bind_optional_context(...)`
  - `clear_context()`
  - `current_context_dict()`

---

### C. 新增 `apps/api/app/core/observability/events.py`
### 目标
统一事件构造，不让每个模块自己拼 event payload。

### 新增内容
- `build_event(...)`
- `build_phase_event(...)`
- `build_tool_event(...)`
- `build_error_event(...)`
- `build_metric_payload(...)`

### 说明
这个文件只负责结构化 payload，不负责写日志。

---

### D. 新增 `apps/api/app/core/observability/decorators.py`
### 目标
把 phase / tool / pipeline 观测最小侵入化。

### 新增内容
- `@observe_phase("retrieving")`
- `@observe_tool("rag_search")`
- `@observe_pipeline("rag_query")`

### 作用
自动打：
- started
- completed
- failed
- duration_ms

---

### E. 新增 `apps/api/app/middleware/observability.py`
### 目标
在 FastAPI 请求入口生成 `request_id` 并绑定 route / user / method / path。

### 具体逻辑
- 在每个请求开始时：
  - 生成 `request_id`
  - 记录 `request_started`
- 在请求结束时：
  - 记录 `request_completed`
  - 写 `status_code` 和 `duration_ms`
- 在异常时：
  - 记录 `request_failed`

### 依赖
- `context.py`
- `logger.py`

---

### F. 修改 `apps/api/app/main.py`
### 目标
把 observability middleware 接到应用主入口。

### 具体改动
- 在 `RequestLoggingMiddleware` 附近注册 `ObservabilityMiddleware`
- 保证 middleware 顺序：
  1. observability（生成 request_id）
  2. request logging
  3. CORS
  4. error handler

### 备注
若当前 `RequestLoggingMiddleware` 已经写入部分日志，需要协调避免重复。

---

## 5.2 后端：Chat / Agent 主链

### G. 修改 `apps/api/app/services/chat_orchestrator.py`
### 目标
把当前 phase inference / SSE event orchestration 升级成可观测主链。

### 具体改动
1. 在 `execute_with_streaming(...)` 开始时生成 `run_id`
2. 绑定：
   - `run_id`
   - `session_id`
   - `message_id`
   - `user_id`
3. 在关键节点打事件：
   - `run_started`
   - `phase_started / phase_completed`
   - `tool_call_started / completed / failed`
   - `stream_started / completed`
   - `confirmation_required`
   - `run_completed / run_failed`
4. 为 phase 切换记录 `phase_entered_at`，计算 phase duration
5. 在 `_close_message_binding()` 时输出最终 summary：
   - final_phase
   - total_duration_ms
   - tool_count
   - reasoning_chars
   - content_chars

### 特别说明
这个文件是 PR11 的核心收益点，优先级最高。

---

### H. 修改 `apps/api/app/core/agent_runner.py`
### 目标
补齐 tool execution 和 agent loop 级事件。

### 具体改动
- 每个 tool call 执行前：
  - `tool_call_started`
- 成功：
  - `tool_call_completed`
- 失败：
  - `tool_call_failed`
- agent loop 每轮：
  - `agent_iteration_started`
  - `agent_iteration_completed`

### 备注
如果当前 `AgentRunner` 文件名或位置有变动，以实际仓库为准；若已拆分到别的模块，也按同样原则打点。

---

## 5.3 后端：RAG / Search / Import 主链

### I. 修改 `apps/api/app/api/rag.py`
### 目标
为 blocking / stream / agentic 三种 query 入口加 run-level observability。

### 具体改动
- `rag_query(...)`
  - 绑定 `run_id`
  - 记录 cache hit / miss
  - 记录 retrieve duration
  - 记录 answer synthesize duration
  - 记录 source_count / confidence
- `rag_query_stream(...)`
  - 记录 streaming path
  - 记录 cached stream 与 live stream 的差异
- `agentic_search(...)`
  - 记录 rounds_executed
  - sub_questions 数量
  - convergence 状态

---

### J. 修改 `apps/api/app/core/streaming.py`
### 目标
把当前轻量 SSE streaming 提升为可观测流式通道。

### 具体改动
- 为 `stream_tokens(...)`
  - 统计 chunk_count
  - total_chars
  - stream_duration_ms
- 为 `stream_rag_response(...)`
  - 生成 `run_id`
  - 记录 retrieve / prompt build / llm stream / citations emit
- 异常路径统一输出 `stream_failed`

### 说明
这个文件后续也会服务 PR12 的 stream benchmark。

---

### K. 修改 Search API 主链文件
### 预期文件（按当前仓库主线）
- `apps/api/app/api/search.py`
- 若 Search 已收口到别的 service，则对应 service 一并改

### 目标
记录：
- query text hash
- result_count
- latency
- filter usage
- pagination info

### 不确定说明
若当前 search 真实编排逻辑在 service 层而非 route 层，优先改 service，route 只补 request-level bind。

---

### L. 修改 Import 主链文件
### 预期文件（按当前仓库主线）
- `apps/api/app/api/imports.py`
- `apps/api/app/services/import_*`
- 解析/任务执行文件（按当前仓库实际命名）

### 目标
记录：
- `job_id`
- `kb_id`
- source type
- parse / embed / index 阶段
- progress events
- final status
- error category

### 不确定说明
若 import pipeline 被拆到 worker / task 模块，请把日志和 run_id 下沉到任务执行层。

---

## 5.4 前端：Telemetry 与 UI phase 观测

### M. 新增 `apps/web/src/lib/observability/telemetry.ts`
### 目标
统一前端 telemetry sink。

### 新增内容
- `trackUIEvent(...)`
- `trackStreamEvent(...)`
- `trackImportEvent(...)`
- `trackSearchEvent(...)`

### 初期策略
先写到 console / debug logger + 可选 POST 到 `/api/v1/system/observability`（若后端同步提供）
本 PR 允许先只做本地标准化 sink，不强制上报。

---

### N. 修改 `apps/web/src/app/hooks/useChatStream.ts`
### 目标
把现有 stream state machine 接到 telemetry。

### 具体改动
记录：
- stream started
- message chunk received
- reasoning chunk received
- phase changed
- tool call appeared
- confirmation required
- stream completed / error / cancelled

### 同步字段
- `session_id`
- `message_id`
- `phase`
- `stream_status`
- `tool_count`
- `citation_count`

---

### O. 修改 Chat workspace 相关 hook / store
### 预期文件
- `apps/web/src/features/chat/hooks/*`
- `apps/web/src/features/chat/state/*`
- `apps/web/src/services/sseService.ts`

### 目标
在不污染 UI 的前提下：
- 给 SSE connect / disconnect / reconnect 打点
- 记录 stale event / message_id mismatch
- 记录 retry / stop / confirmation action

---

### P. 修改 Search workspace 相关 hook
### 预期文件
- `apps/web/src/features/search/hooks/*`
- `apps/web/src/features/search/components/*`（仅必要处）

### 目标
记录：
- search submitted
- filter changed
- pagination changed
- import flow started / cancelled / completed

---

### Q. 修改 KB workspace 相关 hook
### 预期文件
- `apps/web/src/features/kb/hooks/useImportJobsPolling.ts`
- `apps/web/src/features/kb/hooks/useImportWorkflow.ts`
- 其它 workspace hook

### 目标
记录：
- polling started / stopped
- import refresh triggered
- import completion detected
- silent refresh
- cancel / retry

---

## 5.5 测试与文档

### R. 新增后端测试
建议新增：
- `apps/api/tests/unit/test_observability_context.py`
- `apps/api/tests/unit/test_observability_decorators.py`
- `apps/api/tests/unit/test_chat_orchestrator_observability.py`
- `apps/api/tests/unit/test_streaming_observability.py`

### 覆盖点
- request/run context 能正确注入
- decorator 自动输出 started/completed/failed
- chat orchestrator 正确打 phase/tool/run 事件
- streaming 正确输出 stream summary

---

### S. 新增前端测试
建议新增：
- `apps/web/src/app/hooks/useChatStream.observability.test.ts`
- `apps/web/src/features/kb/hooks/useImportJobsPolling.observability.test.ts`
- `apps/web/src/features/search/hooks/useSearchImportFlow.observability.test.ts`

### 覆盖点
- phase 切换 telemetry
- stream complete / error / cancel telemetry
- import polling telemetry
- search import cancel telemetry

---

### T. 文档修改
- `docs/architecture/observability.md`（新增）
- `docs/development/testing-strategy.md`
- `docs/architecture/api-contract.md`（如新增 observability event/reporting endpoint）
- `architecture.md`

---

## 6. 实施步骤（按依赖顺序）

## Phase 1：上下文与基础日志
1. 改 `logger.py`
2. 新增 `context.py`
3. 新增 `events.py`
4. 新增 `decorators.py`
5. 新增 `middleware/observability.py`
6. 在 `main.py` 注册 middleware

### 依赖关系
- `middleware` 依赖 `context` + `logger`
- `decorators` 依赖 `logger` + `events` + `context`

---

## Phase 2：Chat / Streaming 主链
1. 改 `chat_orchestrator.py`
2. 改 `agent_runner.py`
3. 改 `streaming.py`

### 依赖关系
- 必须在 Phase 1 之后
- `chat_orchestrator.py` 是最高优先级
- `streaming.py` 与 PR12 基线直接相关

---

## Phase 3：RAG / Search / Import 主链
1. 改 `api/rag.py`
2. 改 Search 主链
3. 改 Import 主链

### 依赖关系
- 依赖 Phase 1
- 最好在 Phase 2 后做，统一 run_id 设计

---

## Phase 4：前端 telemetry
1. 新增 `telemetry.ts`
2. 改 `useChatStream.ts`
3. 改 chat/search/kb workspace hooks
4. 改 `sseService.ts`

### 依赖关系
- 可与 Phase 3 并行
- 但需与后端字段命名统一

---

## Phase 5：测试 + 文档 + 收尾
1. 新增/更新测试
2. 文档更新
3. 在 PR 模板 / 验证命令中加入 observability 检查（可选）

---

## 7. 交付清单

### 必交付
- 统一 observability context（request/run/session/message/job）
- 后端 middleware + logger + decorators
- Chat / Streaming / RAG / Search / Import 四条链路结构化日志
- 前端 telemetry sink
- 关键 hooks observability 接口
- 单元测试
- 架构文档

### 完成标准
- 一次 chat stream 能通过 `request_id + run_id + session_id + message_id` 串起来
- 一次 rag query 能看到 retrieve/answer/citations 的耗时和状态
- 一次 import job 能看到关键阶段与最终状态
- search 关键动作可追踪
- 前后端事件命名与字段口径统一

---

## 8. 验收命令

### 后端
```bash
cd apps/api && pytest -q tests/unit/test_observability_context.py
cd apps/api && pytest -q tests/unit/test_observability_decorators.py
cd apps/api && pytest -q tests/unit/test_chat_orchestrator_observability.py
cd apps/api && pytest -q tests/unit/test_streaming_observability.py
cd apps/api && pytest -q tests/unit/test_services.py --maxfail=1
cd apps/api && pytest -q tests/test_unified_search.py --maxfail=1
```

### 前端
```bash
cd apps/web && npm run type-check
cd apps/web && npm run test:run -- src/app/hooks/useChatStream.observability.test.ts
cd apps/web && npm run test:run -- src/features/kb/hooks/useImportJobsPolling.observability.test.ts
cd apps/web && npm run test:run -- src/features/search/hooks/useSearchImportFlow.observability.test.ts
```

### 仓库级
```bash
bash scripts/check-governance.sh
bash scripts/verify-all-phases.sh
```

---

## 9. 风险与控制

### 风险 1：日志过量
控制：
- chunk 级别日志只打 debug 或 sampling
- done summary 打 info

### 风险 2：重复日志
控制：
- middleware/request logging 与 observability logging 要去重职责

### 风险 3：前后端字段口径不一致
控制：
- 先固定字段词典，再落代码

### 风险 4：把 observability 逻辑散进 UI
控制：
- 前端统一从 `telemetry.ts` 出口

---

## 10. PR 建议标题

`feat(observability): add harness observability for chat/search/rag/import pipelines`
