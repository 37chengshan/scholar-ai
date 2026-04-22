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
- ImportBatch：批量导入会话
- EvidenceBundle：面向学术检索的证据包聚合资源（跨 text/table/figure/caption）
- ClaimVerificationReport：RAG 回答阶段的 claim 级验证结果资源（支持/弱支持/不支持）
- GraphRetrievalResult：图增强检索候选与融合统计资源（compare/evolution/numeric 场景）

资源关系：

- Paper 属于零个或多个 Collection。
- Paper 产生多个 Chunk。
- ChatSession 包含多个 ChatMessage。
- Task 作用于 Paper、Collection 或 IndexArtifact。
- UploadHistory 是 ImportJob、UploadSession、ProcessingTask 的状态投影视图，不应成为并行真源。
- EvidenceBundle 由 Chunk 聚合而成，可关联 table/figure/caption 与指标证据槽位。
- ClaimVerificationReport 绑定单次 RAG 响应，引用 EvidenceBundle/Chunk 作为 claim 证据来源。
- GraphRetrievalResult 绑定单次检索计划，作为 vector 检索的约束与重排辅助，不独立替代 Chunk。

ChatSession/ChatMessage 读取契约约束：

- `GET /api/v1/sessions/{session_id}/messages` 必须返回：
	- `total`：会话消息全量总数
	- `limit` / `offset`：分页窗口
	- `order`：消息时间序（`asc` 或 `desc`）
	- `pagination.has_more` / `pagination.returned` / `pagination.next_offset`
- 禁止把 `total` 语义降级为“当前页长度”。
- Chat SSE 除 heartbeat 外必须携带 `message_id`，并且与历史消息回读中的 `ChatMessage.id` 可追踪关联。
- Chat SSE 事件集合冻结为：`session_start`、`routing_decision`、`phase`、`reasoning`、`message`、`tool_call`、`tool_result`、`citation`、`confirmation_required`、`cancel`、`done`、`heartbeat`、`error`。
- `tool_result` 产生的工具执行结果必须作为 `ChatMessage(role=tool)` 持久化到同一 `ChatSession`，不得只存在于瞬时 SSE 流中。

认证与会话资源约束：

- RefreshToken、认证黑名单与登录限流均依赖 Redis 可用性，不允许在 Redis 故障时静默降级为本地内存状态。
- `POST /api/v1/auth/register`、`POST /api/v1/auth/login`、`POST /api/v1/auth/forgot-password` 在限流依赖异常时必须返回 `503`，而不是继续放行。
- TokenUsageLog 作为审计型资源，允许记录 Chat 会话与推理链路的模型调用成本，但不得替代会话消息真源。

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
- `UploadSession.aborted` 为终态；前端允许将其投影为 `cancelled` 交互状态，但不得继续复用原 `uploadSessionId` 上传新分片。
- Task：queued -> running -> succeeded | failed | canceled
- ChatSession：active -> closed | archived
- IndexArtifact：building -> ready | failed -> rebuilding
- ImportBatch：created -> running -> completed | failed | cancelled | partial

Paper 交互资源补充：

- PaperStar：用户与 Paper 的收藏关系资源，操作入口为 `/api/v1/papers/{paperId}/star`。
- PaperBatchOperation：批量操作结果资源，至少包含 `successItems` 与 `failedItems`。
- SearchResult：搜索结果资源，支持论文与知识片段的统一搜索，包括请求取消与前端缓存策略。

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
- ImportBatch（聚合计数与整体状态）
- EvidenceBundle（重建、去重、字段回填）

EvidenceBundle 最小字段契约：

- `paper_role`：`method|result|limitation|ablation|conclusion`
- `table_ref`、`figure_ref`、`caption_text`
- `metric_sentence`、`metric_name`、`score_value`、`metric_direction`
- `dataset`、`baseline`、`method`
- `evidence_bundle_id`、`evidence_types[]`

ClaimVerificationReport 最小字段契约：

- `totalClaims`、`supportedClaimCount`、`weaklySupportedClaimCount`、`unsupportedClaimCount`
- `unsupportedClaimRate`
- `results[]`：每条 claim 包含 `claim_id`、`text`、`claim_type`、`support_level`、`support_score`、`evidence_ids[]`
- 回答决策字段：`abstained`、`abstainReason`、`answerMode(full|partial|abstain)`

GraphRetrievalResult 最小字段契约：

- `graphRetrievalUsed`、`graphCandidateCount`、`graphVectorMergedEvidence`
- 可选追踪字段：`graph_narrowed_paper_ids[]`（用于检索约束下推可观测性）

## Required Updates

- 新增资源类型：同步更新本文件与 docs/architecture/api-contract.md。
- 资源状态迁移变化：同步更新 apps/api/app/models 与本文件。
- 新增异步任务：同步补充可修改资源列表。
- 资源契约边界变化：同步更新 docs/governance/fallback-register.yaml 与相关 gate 脚本规则（如适用）。

## Verification

- 抽样检查 API 响应中的资源状态是否在状态机集合内。
- 抽样检查任务完成后资源状态迁移是否可追踪。
- 抽样检查同一资源无重复命名或平行模型定义。
- 运行 `cd apps/api && .venv/bin/python -m pytest -q tests/integration/test_imports_chat_contract.py --maxfail=1`，验证 stream->messages 回读链路契约稳定。

## Open Questions

- IndexArtifact 是否需要拆分为向量索引与图索引两类资源。
- ChatSession 的归档策略是否需要时间窗口自动化。
