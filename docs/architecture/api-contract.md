# API Contract

## Purpose

统一 ScholarAI API 的路由、响应、错误、分页、鉴权、命名与 SSE 约定，避免接口形态漂移。

## Scope

适用于新的 HTTP/SSE 接口，以及对现有接口的重构与兼容迁移。

## Source of Truth

- 仓库级契约：docs/architecture/api-contract.md
- 后端实现细节：apps/api/docs/API_CONTRACT.md
- 资源生命周期：docs/domain/resources.md
- 跨端共享契约：packages/types
- 跨端 typed client：packages/sdk

## Rules

路由前缀规范：

- 统一使用 /api/v1 作为版本前缀。
- 同一资源只允许一套路由命名，不允许并存平行命名。

成功响应格式：

```json
{
  "success": true,
  "data": {},
  "meta": null
}
```

列表响应格式：

```json
{
  "success": true,
  "data": {
    "items": []
  },
  "meta": {
    "limit": 20,
    "offset": 0,
    "total": 100
  }
}
```

分页资源样板（papers）：

```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "paper-uuid",
        "title": "Attention Is All You Need",
        "authors": ["Ashish Vaswani"],
        "status": "completed",
        "arxivId": "1706.03762",
        "createdAt": "2026-04-16T08:00:00Z",
        "updatedAt": "2026-04-16T08:05:00Z"
      }
    ]
  },
  "meta": {
    "limit": 20,
    "offset": 0,
    "total": 1
  }
}
```

错误响应格式（RFC 7807）：

```json
{
  "type": "https://scholarai/errors/validation",
  "title": "Validation Error",
  "status": 400,
  "detail": "Field title is required",
  "instance": "/api/v1/papers"
}
```

分页规范：

- 请求参数：limit、offset
- 响应字段：meta.limit、meta.offset、meta.total
- 兼容期可接受 page+limit 输入，但后端内部统一归一化到 limit+offset。

鉴权规范：

- 受保护路由必须显式声明鉴权依赖。
- 未认证返回 401，已认证但无权限返回 403。
- 不在响应中泄露密钥、令牌或内部鉴权策略细节。

认证限流规范：

- `POST /api/v1/auth/register`、`POST /api/v1/auth/login`、`POST /api/v1/auth/forgot-password` 必须应用按客户端 IP 的速率限制。
- 速率限制由后端配置项控制，至少包含 `RATE_LIMIT_ENABLED` 与 `RATE_LIMIT_DEFAULT_PER_HOUR`；具体阈值可在路由层按端点覆盖。
- 当限流服务可用时，超限请求返回 429 Too Many Requests。
- 当 Redis 不可用或限流校验发生运行时错误时，认证端点必须 fail-closed，返回 503 Service Unavailable，不得降级为本地内存桶或静默放行。
- 认证黑名单与会话校验同样依赖 Redis 可用性；Redis 不可用时，认证相关路径不得假定请求可继续成功。

字段命名规则：

- 后端内部（ORM/DTO/schema）：snake_case
- 前端模型（props/store/view-model）：camelCase
- 命名风格转换只在 API 边界进行一次。

SSE 事件规范：

- 事件类型（冻结集合）：session_start、routing_decision、phase、reasoning、message、tool_call、tool_result、citation、confirmation_required、cancel、done、heartbeat、error
- 标准 envelope 字段固定为：`event`、`data`、`message_id`。
- 每个事件必须包含可解析 JSON 载荷。
- 长连接必须有 heartbeat 或等价保活策略。
- done 为唯一完成事件，不得与错误事件混用。
- Chat 流式接口仅接受 canonical 事件类型，不再支持 legacy alias 映射。
- 除 heartbeat 外，所有业务事件必须携带 `message_id`。

Import Pipeline 契约补充：

- 创建导入任务：`POST /api/v1/knowledge-bases/{kb_id}/imports`
- 单文件上传：`PUT /api/v1/import-jobs/{job_id}/file`
- 批量创建导入任务：`POST /api/v1/knowledge-bases/{kb_id}/imports/batch`
- 批量本地文件上传：`POST /api/v1/import-batches/{batch_id}/files`
- dedupe 决策：`POST /api/v1/import-jobs/{job_id}/dedupe-decision`

批量本地文件上传响应要求：

- `data.accepted[]` 返回已入队条目
- `data.rejected[]` 返回拒绝条目与 `reason`
- 允许部分成功，不允许静默丢弃

Chat 流协议真源：

- app/models/chat.py 为 Chat SSE 事件 DTO 与 envelope 真源。
- app/services/chat_orchestrator.py 负责 message_id 绑定与事件编排。
- app/api/chat.py 负责 stream 接口对外契约。

Chat stream 请求体契约（冻结）：

- 路径：`POST /api/v1/chat/stream`
- 请求体：

```json
{
  "session_id": "session-uuid",
  "message": "请总结这篇论文的贡献",
  "mode": "auto",
  "scope": {
    "type": "paper",
    "paper_id": "paper-uuid"
  },
  "context": {
    "auto_confirm": false
  }
}
```

- 字段语义：
  - `mode`：`auto | rag | agent`，默认 `auto`。
  - `scope.type`：`paper | knowledge_base | general`。
  - `scope.paper_id` 仅在 `scope.type=paper` 时有效。
  - `scope.knowledge_base_id` 仅在 `scope.type=knowledge_base` 时有效。
  - `context`：可选扩展上下文，保持向后兼容。

Session messages 契约（冻结）：

- 路径：`GET /api/v1/sessions/{session_id}/messages`
- 查询参数：`limit`、`offset`、`order(asc|desc)`
- 响应体：

```json
{
  "success": true,
  "data": {
    "session_id": "session-uuid",
    "messages": [],
    "total": 120,
    "limit": 50,
    "offset": 0,
    "order": "desc",
    "pagination": {
      "has_more": true,
      "returned": 50,
      "next_offset": 50
    }
  }
}
```

- 分页语义：
  - `total` 是该会话消息全量总数，不是当前页长度。
  - `returned` 是本次返回条数。
  - `next_offset` 基于 `offset + returned` 计算。
  - Agent 运行期间产生的 `tool_result` 必须持久化为会话历史中的 `tool` 角色消息，保证 SSE 回放与历史回读一致。

Agent Run 协议补充（PR37）：

- `RunPhase` 冻结枚举：`idle`、`planning`、`executing`、`waiting_for_user`、`verifying`、`completed`、`failed`、`cancelled`。
- `StepType` 冻结枚举：`analyze`、`retrieve`、`read`、`tool_call`、`synthesize`、`verify`、`confirm`。
- `StepStatus` 冻结枚举：`pending`、`running`、`completed`、`failed`、`skipped`、`waiting`。
- `ToolEvent.event_type` 冻结枚举：`call`、`result`、`error`。
- `confirmation_required` 是 Run 一级字段；当值为 `true` 时，必须同步返回 `confirmation` 结构。
- `final_summary` 允许携带 `answerEvidenceConsistency` 与 `lowConfidenceReasons[]`，用于结果可信度呈现。
- `run_complete` 是 Run 协议的终态收口事件；成功必须返回 `status=completed`，失败/异常必须返回 `status=failed`，取消必须返回 `status=cancelled`。
- `recovery_available` 只能作为终态补充动作提示，不能替代 `run_complete`。

Run 恢复与控制接口（PR37）：

- `POST /api/v1/chat/cancel`
  - 请求：`session_id`（必填），`run_id`（可选）
  - 成功响应：`{ "status": "cancelled", "session_id": "...", "run_id": "..." }`
  - 语义：取消当前会话活跃运行，并主动断开该会话 SSE 连接。

RAG 检索与规划字段补充（Phase 1 + 2）：

- `/api/v1/rag/query` 与检索评测链路允许返回以下 planner 字段：
  - `query_family`：`fact|compare|evolution|critique|limitation|numeric|figure|table`
  - `planner_query_count`：planner 生成检索变体数量
  - `decontextualized_query`：去语境化后的查询
  - `second_pass_used`：是否触发 second-pass rewrite
  - `second_pass_gain`：second-pass 带来的新增命中增益
- 检索结果 `results[]` 支持 evidence bundle 字段：
  - `paper_role`、`table_ref`、`figure_ref`、`metric_sentence`
  - `dataset`、`baseline`、`method`
  - `score_value`、`metric_name`、`metric_direction`
  - `caption_text`、`evidence_bundle_id`、`evidence_types`
- 向后兼容：新增字段均为可选，不得破坏既有客户端对基础字段的读取。

RAG 回答验证与图检索字段补充（Phase 3 + 4）：

- `POST /api/v1/rag/query` 的 `RAGQueryResponse` 在保留既有字段基础上新增可选字段：
  - `claimVerification`：claim 级验证报告，至少包含 `totalClaims`、`supportedClaimCount`、`weaklySupportedClaimCount`、`unsupportedClaimCount`、`unsupportedClaimRate`、`results[]`。
  - `supportedClaimCount`、`unsupportedClaimCount`：回答级 claim 支持统计。
  - `abstained`、`abstainReason`、`answerMode`：回答三态决策，`answerMode` 取值冻结为 `full|partial|abstain`。
  - `graphRetrievalUsed`、`graphCandidateCount`、`graphVectorMergedEvidence`：图检索参与与融合证据统计。
- `sources[]` 仍为主证据数组；新增验证/图字段均不得替代已有 `sources[]` 读取路径。
- cache 语义不变：命中缓存时以上字段应与首次计算结果保持同构。
- 向后兼容：客户端未消费新增字段时，旧渲染链路必须可继续工作。

RAG Iteration 3 契约补充（Citation-Aware Iterative Retrieval + Outline-Guided Synthesis）：

- `POST /api/v1/rag/query` 在 `RAGQueryResponse` 中新增可选字段：
  - `retrievalEvaluator`：first-pass retrieval 评估结果，至少包含 `is_weak`、`weak_reasons[]`、`metrics{}`。
  - `iterativeRetrievalTriggered`：是否触发二次检索编排。
  - `retrievalTrace`：iterative orchestration trace，至少包含 `mode`、`iterative_triggered`、`rounds[]`。
  - `citationAwareMetadata`：citation-aware 扩展统计，至少包含 `citation_expansion_applied` 与 relation 计数。
  - `scientificSynthesisMetrics`：科学综合质量指标，至少包含 `citation_faithfulness`、`unsupported_claim_rate`、`cross_paper_synthesis_quality`、`partial_abstain_quality`。
- `metadata.answerMode` 仍维持 `full|partial|abstain` 冻结取值，不允许新增第四态。
- `retrievalTrace` 与 `citationAwareMetadata` 在 cache 命中响应中必须保持结构同构。
- `POST /api/v1/chat/retry`
  - 请求：`session_id`（必填），可选 `mode` 与 `scope`
  - 语义：重放该会话最后一条 `user` 消息，并复用 `chat/stream` 流式返回。
  - 错误：无可重放用户消息时返回 `404`。

Run timeline 前端契约补充（PR37）：

- timeline item `type` 扩展为：`phase | tool | step | confirmation | done | error | recovery`。
- timeline item 可携带 `status` 字段，前端用于执行态展示与恢复动作分流。
Paper 资源契约补充：

- `GET /api/v1/papers`：返回 `data.items[]` 与 `meta.limit/offset/total`。
- `GET /api/v1/papers/{paperId}`：返回单资源结构，字段命名遵循边界转换规则。
- `POST /api/v1/papers/{paperId}/star`：只允许返回统一 envelope，不允许裸布尔返回。
- `POST /api/v1/papers/batch-delete`：批量删除必须返回可追踪结果（成功列表与失败列表）。
- `paper.reading_notes`：只表示系统生成阅读摘要，不得作为用户可编辑 Note 实体的并行真源。
- `paper.notes_version`、`paper.is_notes_ready`、`paper.notes_failed`：`POST /api/v1/notes/generate`、`POST /api/v1/notes/regenerate` 与 notes worker 必须使用一致的更新语义。

Notes 资源契约补充：

- `POST /api/v1/notes`：创建用户可编辑笔记；请求体字段为 `title`、`content`、`tags`、`paperIds`，响应为统一 `success + data` envelope，且服务端必须剥离系统 `__ai_note__` tag。
- `GET /api/v1/notes` 与 `GET /api/v1/notes/paper/{paperId}`：返回的 `Note` 资源仅表示用户可编辑笔记。
- `GET /api/v1/notes/{id}`、`PUT /api/v1/notes/{id}`、`DELETE /api/v1/notes/{id}`：历史 `__ai_note__` 记录必须视为不存在，不得通过 by-id CRUD 暴露系统摘要实体。
- `GET /api/v1/notes`：列表响应必须返回 `data.notes[]`、`data.total`、`data.limit`、`data.offset`；`paperId` 与 `tag` 过滤仅作用于用户可编辑笔记。
- `PUT /api/v1/notes/{id}`：仅允许更新用户笔记的 `title`、`content`、`tags`、`paperIds`，响应为统一 `success + data` envelope。
- `DELETE /api/v1/notes/{id}`：仅允许删除用户笔记，对历史 `__ai_note__` 返回 not found 语义。
- `POST /api/v1/notes/generate` 与 `POST /api/v1/notes/regenerate`：只允许写入 `paper.reading_notes`、`paper.notes_version`、`paper.is_notes_ready`、`paper.notes_failed`，不得创建或回写 `Note` 实体；响应统一为 `GeneratedNotesResponse` envelope。
- `GET /api/v1/notes/{paperId}/export`：导出的是 `paper.reading_notes` 的 Markdown 视图，不得隐式创建用户 `Note`。
- Notes 页面允许展示由 `paper.reading_notes` 派生的系统摘要，但该展示不得反向创建或更新 `Note` 资源。
- Read 页面自动创建/加载的 `reading note` 仅绑定用户笔记，不得复用系统摘要记录。

Search API 契约补充：

- `GET /api/v1/search/unified`：统一搜索接口
  - 查询参数：`query`、`limit`、`offset`、`year_from`（可选）、`year_to`（可选）
  - 响应格式：返回 `data.results[]` 与 `meta.limit/offset/total`
  - 客户端实现：支持 AbortSignal 用于请求取消（frontend request cancellation）
  - 前端额外功能：支持会话搜索（session-side filtering）与结果缓存（react-query keepPreviousData）

- `POST /api/v1/search/multimodal`：库内多模态检索接口
  - 请求体：`query`、`paper_ids[]`、`top_k`、`use_reranker`、`content_types[]`、`enable_clustering`
  - 响应格式：统一 `success + data` envelope
  - `data.results[]` 检索条目允许返回：`backend`、`source_id`、`section_path`、`content_subtype`、`anchor_text`、`vector_score`、`sparse_score`、`hybrid_score`、`reranker_score`、`retrieval_trace_id`
  - `data.vectorBackend` 表示本次检索实际使用的后端，允许值仅为 `milvus | qdrant`；默认主线仍为 `milvus`
  - `data.trace` 为可选调试字段，仅在显式开启检索追踪时返回，至少包含 `trace_id`、`planner_queries[]`、`metadata_filters`、`weights` 与结果级分数快照

Plan C 契约治理约束：

- 契约表面改动（apps/api/app/api, apps/api/app/models, apps/web/src/services, packages/types, packages/sdk）必须同步更新本文件与 `docs/domain/resources.md`。
- 任何 fallback 契约兼容必须在 `docs/governance/fallback-register.yaml` 登记到期时间与删除计划。
- UploadHistory 是 ImportJob/UploadSession/ProcessingTask 的投影视图，不作为并行真源。

前端主链路补充：

- Chat 页面主执行入口固定为 `apps/web/src/features/chat/workspace/ChatWorkspaceV2.tsx`。
- 兼容容器可以保留，但不得再引入第二条生产级 Chat runtime 主链路。

## Required Updates

- 新增接口：同步校验是否符合本契约。
- 改动响应格式：同步更新本文件与调用方。
- 改动 SSE 事件：同步更新 docs/architecture/system-overview.md。

上传会话（PR19）接口补充：

- `POST /api/v1/import-jobs/{jobId}/upload-sessions`
  - 用途：创建或恢复本地 PDF 的分片上传会话，支持秒传命中。
  - 请求：`filename`、`sizeBytes`、`chunkSize`、`sha256`、`mimeType`
  - 响应：`instantImport` 或 `session`（含 `uploadSessionId`、`missingParts`、`progress`）
- `GET /api/v1/upload-sessions/{sessionId}`
  - 用途：拉取会话状态与缺失分片列表，用于断点恢复。
  - 约束：当 `status=aborted` 时，该会话视为终态，不允许继续作为 resumable session 恢复上传。
- `PUT /api/v1/upload-sessions/{sessionId}/parts/{partNumber}`
  - 用途：上传单个分片（`application/octet-stream`）。
- `POST /api/v1/upload-sessions/{sessionId}/complete`
  - 用途：合并分片、写入文件元数据并触发 ImportJob 入队。
- `POST /api/v1/upload-sessions/{sessionId}/abort`
  - 用途：终止会话，阻止后续分片写入。

ImportJob `nextAction` 补充：

- 本地文件场景从 `upload_file` 切换为 `create_upload_session`。
- `createSessionUrl` 指向 `/api/v1/import-jobs/{id}/upload-sessions`。

导入任务流式事件契约补充：

- `GET /api/v1/imports/import-jobs/{jobId}/stream` 事件集合固定为：
  - `status_update`
  - `stage_change`
  - `progress`
  - `completed`
  - `error`
- `status_update.data` 必须包含：
  - `status`
  - `stage`
  - `progress`
  - `nextAction`（可空）
  - `error`（可空，结构为 `{ code, message }`）

导入兜底上传契约补充：

- `PUT /api/v1/import-jobs/{jobId}/file` 定位为 fallback/small-file-only，不作为本地主路径。
- 该接口成功响应 `data.pathMode` 固定为 `fallback_small_file_only`，用于前后端链路标识。

ImportJob `nextAction` 场景补充：

- 本地上传主路径：
  - `type = create_upload_session`
  - `createSessionUrl = /api/v1/import-jobs/{id}/upload-sessions`
- DOI/URL 无可下载 PDF 场景：
  - `type = upload_local_pdf`
  - `createSessionUrl = /api/v1/import-jobs/{id}/upload-sessions`
  - 可携带 `triedSources[]` 与 `sourceErrors{}` 作为可观测上下文。

RAG 查询响应契约补充：

- `POST /api/v1/rag/query` 响应增加：
  - `answerEvidenceConsistency`（`0..1`）
  - `lowConfidenceReasons[]`
- `lowConfidenceReasons` 枚举冻结为：
  - `retrieval_weak`
  - `evidence_insufficient`
  - `evidence_conflict`

## Verification

- 抽样检查新接口响应是否包含 success/data/meta。
- 抽样检查错误路径是否为 RFC 7807。
- 抽样检查分页接口参数与 meta 字段是否一致。
- 抽样检查受保护接口的 401/403 行为。
- 运行 `cd apps/api && .venv/bin/python -m pytest -q tests/integration/test_imports_chat_contract.py --maxfail=1`，冻结导入批次与 Chat 主链路契约。

## Open Questions

- 是否需要统一错误 type 枚举并下沉到共享 SDK。
- 是否将分页从 offset 模式逐步升级到 cursor 模式。
