# Resources Model

## Purpose

统一定义 ScholarAI 核心资源、资源关系、状态机与生命周期事件，支撑 API 设计和异步任务治理。

## Scope

覆盖论文、会话、消息、知识片段、任务与索引等核心资源。

## Source of Truth

- API 契约：docs/architecture/api-contract.md
- 系统总览：docs/architecture/system-overview.md
- 后端模型：apps/api/app/models
- 后端服务：apps/api/app/services

## Rules

核心资源清单：

- Paper：论文与元数据
- ImportJob：导入任务与状态机
- UploadSession：分片上传会话与断点恢复状态
- Collection：文献集合与组织单元
- Chunk：文本切片与向量化单元
- ChatSession：会话上下文
- ChatMessage：会话消息
- Task：异步任务
- IndexArtifact：索引或检索产物
- ImportJob：统一导入任务（上传/解析/去重/入库）
- ImportBatch：批量导入会话

资源关系：

- Paper 属于零个或多个 Collection。
- Paper 产生多个 Chunk。
- ChatSession 包含多个 ChatMessage。
- Task 作用于 Paper、Collection 或 IndexArtifact。

ChatSession/ChatMessage 读取契约约束：

- `GET /api/v1/sessions/{session_id}/messages` 必须返回：
	- `total`：会话消息全量总数
	- `limit` / `offset`：分页窗口
	- `order`：消息时间序（`asc` 或 `desc`）
	- `pagination.has_more` / `pagination.returned` / `pagination.next_offset`
- 禁止把 `total` 语义降级为“当前页长度”。

Chat 查询作用域资源约束：

- Chat stream 请求允许 `scope`：
	- `paper`（绑定单论文）
	- `knowledge_base`（绑定知识库）
	- `general`（全局无绑定）
- `mode` 固定枚举：`auto | rag | agent`。

状态机：

- Paper：uploaded -> parsing -> parsed -> indexed -> archived | failed
- ImportJob：created -> queued -> running -> awaiting_user_action -> completed | failed | cancelled
- UploadSession：created -> uploading -> completed | aborted | failed
- Task：queued -> running -> succeeded | failed | canceled
- ChatSession：active -> closed | archived
- IndexArtifact：building -> ready | failed -> rebuilding
- ImportJob：created -> queued -> running -> awaiting_user_action -> completed | failed | cancelled
- ImportBatch：created -> running -> completed | failed | cancelled | partial

Paper 交互资源补充：

- PaperStar：用户与 Paper 的收藏关系资源，操作入口为 `/api/v1/papers/{paperId}/star`。
- PaperBatchOperation：批量操作结果资源，至少包含 `successItems` 与 `failedItems`。

关键生命周期事件：

- paper.uploaded
- paper.parsed
- paper.indexed
- task.started
- task.finished
- task.failed
- session.closed

可被异步任务修改的资源：

- Paper（解析与索引状态）
- ImportJob（导入阶段、错误态、重试态）
- UploadSession（分片进度、缺片集合、完成态）
- Chunk（生成、重算、清理）
- Task（执行状态）
- IndexArtifact（构建状态）
- ImportJob（阶段推进与终态）
- ImportBatch（聚合计数与整体状态）

## Required Updates

- 新增资源类型：同步更新本文件与 docs/architecture/api-contract.md。
- 资源状态迁移变化：同步更新 apps/api/app/models 与本文件。
- 新增异步任务：同步补充可修改资源列表。
- 资源契约边界变化：同步更新 docs/governance/fallback-register.yaml 与相关 gate 脚本规则（如适用）。

## Verification

- 抽样检查 API 响应中的资源状态是否在状态机集合内。
- 抽样检查任务完成后资源状态迁移是否可追踪。
- 抽样检查同一资源无重复命名或平行模型定义。

## Open Questions

- IndexArtifact 是否需要拆分为向量索引与图索引两类资源。
- ChatSession 的归档策略是否需要时间窗口自动化。
