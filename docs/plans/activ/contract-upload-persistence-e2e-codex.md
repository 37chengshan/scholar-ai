# 接口契约闭环 + 上传/导入/持久化闭环 + 关键 E2E（可直接丢给 GPT-5.3 Codex 执行）

## 目标

把当前仓库中 **chat 契约漂移、导入双轨、上传工作台缺口、持久化闭环不完整、关键 E2E 不成体系** 的问题一次性收口。

这份任务不是“补几个接口”，而是把以下四件事真正闭环：

1. chat / session / import / upload-session 共享契约冻结
2. 上传/导入统一为单一主链路
3. chat message / import job / upload session / upload history 持久化链路可恢复
4. 补齐关键 E2E 和契约测试，防止回归

## 已观察到的真实现状

1. `packages/types/src/chat/stream.ts`、`apps/web/src/services/sseService.ts`、`apps/web/src/features/chat/adapters/sseEventAdapter.ts`、`apps/api/app/models/chat.py` 之间仍有契约漂移：
   - 后端 envelope 使用 `event`
   - 前端 adapter 内部消费 `event_type`
   - shared types 里还残留 legacy 事件类型 `THOUGHT`、`THINKING_STATUS`、`STEP_PROGRESS`
2. `apps/web/src/services/sseService.ts` 仍向业务层发 legacy `SSEEvent` 结构，而不是只发 canonical envelope。
3. `apps/api/app/api/kb/kb_import.py` 的 `import-url`、`import-arxiv`、`batch-upload` 仍是 stub。
4. 本地 PDF 导入目前存在双轨：
   - 旧链路：`kbApi.uploadPdf()` → `apps/api/app/api/kb/kb_import.py` 直接创建 Paper + ProcessingTask + UploadHistory
   - 新链路：`importApi.create(local_file)` + `uploadSessionApi` → ImportJob-first
5. `apps/web/src/app/components/ImportDialog.tsx` 和 `apps/web/src/features/kb/components/KnowledgeWorkspaceShell.tsx` 都引用了 `@/features/uploads/components/UploadWorkspace`，但当前仓库里看不到这个文件路径，这是阻断项。
6. `apps/web/e2e/` 已有 PR19 相关流程脚本，但 package.json 的 `test:e2e` 没把这些场景纳入主回归入口。
7. `apps/api` 侧缺少成体系的 imports/chat integration tests 目录。

## 最终决策

### 决策 1：chat SSE 只保留一套 canonical 契约

采用以下准则：

- 后端真源：`apps/api/app/models/chat.py`
- 文档真源：`docs/architecture/api-contract.md`
- shared types：`packages/types/src/chat/*`
- frontend transport 边界：`apps/web/src/services/sseService.ts`
- frontend adapter：只做 canonical normalize，不再兼容 legacy 事件穿透到业务层

### 决策 2：本地 PDF 上传只保留 ImportJob-first 主链路

以后本地文件导入统一为：

- `POST /api/v1/knowledge-bases/{kbId}/imports` with `sourceType=local_file`
- `POST /api/v1/import-jobs/{jobId}/upload-sessions`
- `PUT /api/v1/upload-sessions/{sessionId}/parts/{partNumber}`
- `POST /api/v1/upload-sessions/{sessionId}/complete`
- 后端 worker 处理 import job

旧的 `kbApi.uploadPdf()` 直接建 Paper 的路径，不再作为主链路。

### 决策 3：外部来源导入也统一走 ImportJob-first

- `import-url`
- `import-arxiv`
- `semantic scholar`

都应该最终落到 `ImportJob`，而不是和旧 KB 上传路径并存。

---

## 执行顺序（按文件列出修改顺序）

## 阶段 0：先清阻断项

### 0.1 新增 `apps/web/src/features/uploads/components/UploadWorkspace.tsx`

#### 任务

补齐当前已经被多个页面引用、但实际缺失的上传工作台组件。

#### 必须提供

- `knowledgeBaseId` 入参
- 队列展示
- 本地 PDF 选择
- 每个文件先创建 `local_file` ImportJob
- 创建/恢复 upload session
- 分片上传
- 断点恢复
- complete session
- 轮询 import job 状态
- `onQueueComplete` 回调

#### 可拆分新增

- `apps/web/src/features/uploads/hooks/useUploadQueue.ts`
- `apps/web/src/features/uploads/hooks/useChunkedUpload.ts`
- `apps/web/src/features/uploads/components/UploadQueueList.tsx`
- `apps/web/src/features/uploads/components/UploadQueueRow.tsx`

#### 验收

- `ImportDialog.tsx` 和 `KnowledgeWorkspaceShell.tsx` 能实际渲染该组件
- 前端 type-check 不再因路径缺失失败

---

## 阶段 1：冻结共享契约

### 1.1 修改 `docs/architecture/api-contract.md`

#### 任务

把以下内容写清并与实现保持一致：

- chat stream request body
- chat SSE envelope 形状
- allowed event set
- `message_id` 约束
- upload-session request/response
- import job list/get/create/retry/cancel/dedupe
- upload history 响应字段

#### 明确冻结

- chat envelope 字段名统一为：
  - `event`
  - `data`
  - `message_id`
- canonical event set 统一为：
  - `session_start`
  - `routing_decision`
  - `phase`
  - `reasoning`
  - `message`
  - `tool_call`
  - `tool_result`
  - `citation`
  - `confirmation_required`
  - `cancel`
  - `done`
  - `heartbeat`
  - `error`

不要再让 `thought`、`thinking_status`、`step_progress` 留在共享真源里。

---

### 1.2 修改 `packages/types/src/chat/stream.ts`

#### 任务

- 删除 legacy 事件类型：`THINKING_STATUS`、`STEP_PROGRESS`、`THOUGHT`
- `StreamEventEnvelope` 只保留 canonical 结构：`event/data/message_id`
- `DoneEventData`、`ErrorEventData`、`ToolResultEventData` 与后端对齐
- 如需要兼容旧字段，只能放在 adapter 层，不得留在 shared contract

---

### 1.3 修改 `packages/types/src/chat/dto.ts`

#### 任务

- 确认 `ChatMode`、`ChatScope` 与文档一致
- `ChatScope.type` 维持 `paper | knowledge_base | general`
- 补齐 `SessionMessagesResponse` 的消费契约，如果后端还有 legacy envelope，明确 adapter 去处理，不要继续让页面兜底

---

### 1.4 修改 `packages/types/src/kb/import.ts`

#### 任务

把下列 DTO 明确冻结：

- `ImportJobDto`
- `UploadHistoryRecordDto`
- `UploadSessionStateDto`
- `CreateUploadSessionResponseDto`

#### 要求

- 字段语义和命名只允许一份真源
- 前端页面层不再自己二次猜测 `nextAction` 结构

---

### 1.5 修改 `packages/sdk/src/chat/stream.ts`
### 1.6 修改 `packages/sdk/src/kb/import.ts`

#### 任务

- SDK 只承接冻结后的 shared contract
- 不要在 SDK 里继续做模糊兼容
- `buildChatStreamBody()` 与文档保持一致
- import SDK 的 list/get/create/retry/cancel 接口与 `packages/types` 对齐

---

## 阶段 2：收口 chat transport 和 adapter

### 2.1 修改 `apps/web/src/services/sseService.ts`

#### 任务

把它改成 **单一 canonical transport 边界**。

#### 必做

- `onMessage` 只向上层发 canonical envelope，不再发 legacy `SSEEvent`
- cancel/done/error 行为统一
- `event:` 行仍是 authoritative type
- wrapped payload / flat payload 的兼容只保留在 transport 边界

#### 建议改法

把对外 handler 改成：

- `onEnvelope(envelope)`
- `onDone(doneData)`
- `onError(error)`

不要继续让业务层同时接 legacy 和 envelope 两套结构。

---

### 2.2 修改 `apps/web/src/features/chat/adapters/sseEventAdapter.ts`

#### 任务

- 输入改为 canonical envelope：`event/data/message_id`
- adapter 内部如需给 `useChatStream` 转为 `event_type`，只能在这里做一次映射
- 支持 `cancel`
- 拒绝 legacy 事件类型进入业务层

---

### 2.3 修改 `apps/web/src/services/chatApi.ts`

#### 任务

- `streamMessage()` 只消费 canonical transport
- 删除“既能吃 legacy SSEEvent 又能吃 envelope”的模糊逻辑
- `streamMessage()` 请求体严格使用 shared sdk builder

---

### 2.4 修改 `apps/web/src/services/sessionResponse.ts`

#### 任务

- 保留 response adapter，但把兼容边界固定在 service 层
- 页面层不再消费两种 session messages 结构

---

## 阶段 3：后端 chat/message persistence 闭环

### 3.1 修改 `apps/api/app/models/chat.py`

#### 任务

- 明确 `SSEEventEnvelope` 为 canonical 对外模型
- event set 与文档一致
- 删除 shared contract 已移除的 legacy 真源定义，或降为明确 deprecated 注释，不再导出给前端真源

---

### 3.2 修改 `apps/api/app/services/chat_orchestrator.py`

#### 任务

- 统一事件发射口径
- 保证除 heartbeat 外，所有事件都携带 `message_id`
- `done` 前确保 assistant message 持久化完成
- confirmation resume 流程继续沿用相同 `message_id`
- cancel / error / done 都写入可恢复的终态

---

### 3.3 修改 `apps/api/app/services/message_service.py`
### 3.4 修改 `apps/api/app/api/chat.py`

#### 任务

- 保证 `POST /api/v1/chat/stream` 结束后，`GET /api/v1/sessions/{id}/messages` 能读到最终 assistant message
- 处理以下场景：
  - 正常完成
  - cancel
  - error
  - confirmation pause/resume
- 不允许只在流里出现内容、数据库里没有最终消息

#### 验收

- stream done 后刷新页面，消息仍在
- cancel/error 有明确终态，不是“前端看到过，刷新就没了”

---

## 阶段 4：上传 / 导入主链路统一

### 4.1 修改 `apps/web/src/services/kbApi.ts`

#### 任务

- 将 `uploadPdf()` 标记为 legacy wrapper 或直接改为走 ImportJob-first
- `importFromUrl()` / `importFromArxiv()` 不再调用 stub 式旧接口
- 所有知识库导入入口统一走 `importApi`

#### 推荐做法

- 对外页面只保留 `importApi`
- `kbApi.uploadPdf()` 可短期保留，但内部必须调用：
  - create local_file job
  - create/resume upload session
  - upload/complete

---

### 4.2 修改 `apps/web/src/services/importApi.ts`
### 4.3 修改 `apps/web/src/services/uploadSessionApi.ts`

#### 任务

- 对接冻结后的 shared contract
- 统一本地文件导入与外部来源导入的返回 shape
- `getStreamUrl()` 若当前没真正接入，不要伪暴露；要么落地，要么移除未使用接口

---

### 4.4 修改 `apps/web/src/app/components/ImportDialog.tsx`
### 4.5 修改 `apps/web/src/features/kb/components/KnowledgeWorkspaceShell.tsx`

#### 任务

- 本地 PDF 只走 `UploadWorkspace`
- 外部来源只走 `importApi.create()`
- 导入完成后触发：
  - refresh import jobs
  - refresh papers
  - refresh kb summary
- 不要再从对话框里直接走 `kbApi.uploadPdf()` 旧链路

---

### 4.6 修改 `apps/api/app/api/kb/kb_import.py`

#### 任务

清理这个文件里的旧直传路径和 stub：

- `upload`：
  - 若短期保留，改成 wrapper 到 ImportJob-first
  - 或直接声明 deprecated，只保留兼容壳
- `import-url`、`import-arxiv`：不要再返回 “to be implemented”
- `batch-upload`：不要继续 stub

#### 推荐

- 让 `kb_import.py` 只保留兼容入口，真正逻辑下沉到 `imports/*`
- 所有新页面走 `imports/*` 正式接口

---

### 4.7 修改 `apps/api/app/api/imports/jobs.py`
### 4.8 修改 `apps/api/app/api/imports/sources.py`
### 4.9 修改 `apps/api/app/api/imports/upload_sessions.py`
### 4.10 修改 `apps/api/app/services/import_job_service.py`
### 4.11 修改 `apps/api/app/services/upload_session_service.py`

#### 任务

把 ImportJob-first 链路做实：

- 本地文件：create job → upload session → complete → worker queue
- 外部来源：resolve → create job → worker queue
- 秒传：sha256 命中后 job 正确复用 paper
- 重试：failed job 可 retry
- 取消：job/session 可 cancel/abort
- `next_action` 稳定、可恢复

#### 验收

- 刷新页面后 import job 状态可恢复
- 断点上传可恢复 missing parts
- 秒传命中后不会重复创建 paper

---

## 阶段 5：upload history 与 import job 的关系做实

### 5.1 修改 `apps/api/app/api/kb/kb_import.py`
### 5.2 如需要新增/修改 `apps/api/app/models/upload_history.py` 相关写入点

#### 任务

明确 upload history 的来源，不允许旧链路、新链路各写一套语义不同的数据。

#### 建议原则

- upload history 是“用户看到的导入历史视图”
- 真实执行真源是 ImportJob / UploadSession / ProcessingTask
- upload history 可作为投影视图，但状态必须来自统一主链路

#### 验收

- 刷新知识库详情页后，上传历史仍能反映真实状态
- completed / failed / processing 不再依赖页面内存态

---

## 阶段 6：关键测试补齐

## 6.1 前端单测 / 集成测试

### 修改 `apps/web/src/services/chatApi.test.ts`

补测试：

- body 包含 `mode/scope/context`
- `paperId` / `kbId` 作用域映射正确

### 修改 `apps/web/src/features/chat/adapters/sseEventAdapter.test.ts`

补测试：

- canonical envelope 正常进入业务层
- legacy thought 事件被拒绝
- cancel 事件被识别

### 新增 `apps/web/src/features/uploads/*` 测试

补测试：

- create session / resume session
- upload missing parts only
- complete session after all parts uploaded
- 秒传命中分支

### 修改 `apps/web/src/features/kb/hooks/useImportJobsPolling.test.tsx`

补测试：

- running job 时轮询
- 页面隐藏时按策略暂停
- completed 后停止高频轮询

---

## 6.2 后端集成测试

### 新增目录

- `apps/api/tests/integration/test_chat_stream_contract.py`
- `apps/api/tests/integration/test_chat_persistence.py`
- `apps/api/tests/integration/test_import_job_flow.py`
- `apps/api/tests/integration/test_upload_session_flow.py`

### 必测链路

#### chat stream contract

- `/api/v1/chat/stream` 请求体校验
- SSE 事件集合只出现 canonical event
- 除 heartbeat 外全部带 `message_id`

#### chat persistence

- stream done 后 session messages 可读到 assistant message
- cancel/error 后有终态
- confirmation resume 后 assistant message 不丢失

#### import job flow

- create local_file job
- create upload session
- upload parts
- complete session
- job 进入 queued/running/completed

#### upload session flow

- resume existing session
- missing parts 正确返回
- complete 时校验 sha256
- abort 后不可继续写入

---

## 6.3 E2E：把关键链路纳入主回归入口

### 新增 / 整理

- `apps/web/e2e/chat-critical.spec.ts`
- `apps/web/e2e/import-upload-critical.spec.ts`
- `apps/web/e2e/kb-import-history-critical.spec.ts`
- `apps/web/e2e/chat-resume-critical.spec.ts`

### 关键场景

#### 场景 A：知识库本地 PDF 导入

- 进入 KB 详情页
- 打开上传工作台
- 选择 1~3 个本地 PDF
- 成功创建 import jobs
- 上传完成后 import jobs 进入 completed
- papers 列表出现新论文
- upload history 可见
- 刷新页面后状态仍在

#### 场景 B：外部来源导入

- 输入 arXiv / URL / DOI
- resolve 成功
- create import job
- 轮询到 completed
- papers 列表可见

#### 场景 C：chat 主链路

- 新建 session
- 发送消息
- 看到 streaming
- done 后消息持久化
- 刷新后消息仍在

#### 场景 D：chat cancel

- 发送消息
- 中途 stop
- UI 进入 cancelled/terminal
- 刷新后没有 ghost streaming 状态

#### 场景 E：KB scoped chat

- 从知识库详情页进入 chat
- `kbId` scope 生效
- 返回结果正常
- session messages 保留

---

### 修改 `apps/web/package.json`

#### 任务

把关键 E2E 纳入主命令，而不是只躺在仓库里：

- `test:e2e`
- `test:e2e:ci`

都要包含新的关键场景 spec。

---

## 建议 commit 切片

### Commit 1
- add missing UploadWorkspace and upload hooks

### Commit 2
- freeze docs and shared contracts for chat/import/upload-session

### Commit 3
- unify frontend SSE transport and adapter to canonical envelope

### Commit 4
- harden backend chat stream and message persistence

### Commit 5
- unify local/external import onto ImportJob-first flow

### Commit 6
- make upload history and import status refresh-safe

### Commit 7
- add frontend tests and backend integration tests

### Commit 8
- wire critical E2E into package scripts

---

## 完成定义

满足以下条件才算完成：

- `UploadWorkspace` 真正存在并可运行
- chat SSE 只有一套 canonical shared contract
- 本地 PDF 不再依赖旧 `kbApi.uploadPdf()` 直传主链路
- `import-url` / `import-arxiv` 不再是 stub
- chat done 后 assistant message 刷新仍存在
- upload session 支持 resume / complete / abort / sha256 校验
- upload history 刷新后仍能反映真实状态
- 关键 E2E 被纳入默认回归命令

---

## 给 Codex 的执行约束

1. 先做阶段 0 和阶段 1，再动业务实现。
2. 任何契约变更都必须同步修改：
   - `docs/architecture/api-contract.md`
   - `packages/types`
   - `packages/sdk`
   - 对应 frontend/backend adapter
3. 旧本地上传链路可以保留兼容壳，但新页面入口必须全部切到 ImportJob-first。
4. 不要继续扩散 legacy SSEEvent 到页面层。
5. 后端若缺测试目录，直接创建，不要因为“仓库里还没有”就跳过。
6. 每个 commit 完成后至少跑：
   - web type-check
   - web vitest 相关用例
   - api pytest 相关用例
   - playwright 关键链路
