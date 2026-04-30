# Resources Model

## Purpose

统一定义 ScholarAI 核心资源、资源关系、状态机与生命周期事件，支撑 API 设计和异步任务治理。

## Scope

覆盖论文、会话、消息、知识片段、任务与索引等核心资源。

## Source of Truth

- API 契约：docs/specs/architecture/api-contract.md
- 系统总览：docs/specs/architecture/system-overview.md
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
- Note：用户笔记真源，Notes 2.0 以 `contentDoc` 与 `linkedEvidence[]` 为结构化字段
- EvidenceSourceView：按 `source_chunk_id` 回查证据原文与定位信息的只读资源视图
- EvidenceNote：由 claim+citation 落盘生成的用户可编辑笔记资源（归属 Note 主模型）
- ClaimVerificationReport：RAG 回答阶段的 claim 级验证结果资源（支持/弱支持/不支持）
- TruthfulnessReport：Phase I 首批统一 truthfulness substrate 资源，服务于 rag/chat/compare/review 共享 claim 校验与 repair
- GraphRetrievalResult：图增强检索候选与融合统计资源（compare/evolution/numeric 场景）
- ReviewDraft：KB 级正式综述草稿资源（outlineDoc + draftDoc 同源承载）
- ReviewRun：KB 级综述生成运行记录资源（steps/tool_events/artifacts/evidence/recovery）

资源关系：

- Paper 属于零个或多个 Collection。
- Paper 产生多个 Chunk。
- ChatSession 包含多个 ChatMessage。
- Task 作用于 Paper、Collection 或 IndexArtifact。
- UploadHistory 是 ImportJob、UploadSession、ProcessingTask 的状态投影视图，不应成为并行真源。
- EvidenceBundle 由 Chunk 聚合而成，可关联 table/figure/caption 与指标证据槽位。
- Note 资源允许通过 `content` 兼容旧数据，但结构化真源固定为 `contentDoc`；`linkedEvidence[]` 是沉淀后的 canonical evidence 数组。
- EvidenceSourceView 由 Chunk/索引产物投影生成，必须提供 `citation_jump_url` 作为统一跳转字段，并兼容回跳到 Read 页面定位参数（`paper_id`、`page_num`、`source_chunk_id`）。
- EvidenceNote 是 Note 的受控创建路径之一，必须绑定 `paper_id` 与 `source_chunk_id`，并把 EvidenceBlock 2.0 写入 `linkedEvidence[]`，不得创建并行笔记模型。
- ClaimVerificationReport 绑定单次 RAG 响应，引用 EvidenceBundle/Chunk 作为 claim 证据来源。
- TruthfulnessReport 可绑定单次 RAG/Compare/Review 段落响应，最小字段为 `totalClaims`、四档 support count、`unsupportedClaimRate`、`answerMode` 与 `results[]`。
- GraphRetrievalResult 绑定单次检索计划，作为 vector 检索的约束与重排辅助，不独立替代 Chunk。
- ReviewDraft 归属 KnowledgeBase，可选绑定 `sourcePaperIds[]` 子集；同一 draft 可被多次 retry/run 覆盖更新。
- ReviewRun 归属 KnowledgeBase 且可回链到 ReviewDraft；Run 是执行轨迹真源，禁止用 session 列表投影伪装。

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
- `context.paper_ids[]` 是 Compare -> Chat follow-up 的 canonical 多论文作用域输入；当其存在且 `mode=auto|rag` 时，后端必须把它转成真实 retrieval `paper_scope`，不能只作为前端展示上下文。

状态机：

- Paper：uploaded -> parsing -> parsed -> indexed -> archived | failed
- ImportJob：created -> queued -> running -> awaiting_user_action -> completed | failed | cancelled
- UploadSession：created -> uploading -> completed | aborted | failed
- `UploadSession.aborted` 为终态；前端允许将其投影为 `cancelled` 交互状态，但不得继续复用原 `uploadSessionId` 上传新分片。
- Task：queued -> running -> succeeded | failed | canceled
- ChatSession：active -> closed | archived
- IndexArtifact：building -> ready | failed -> rebuilding
- ImportBatch：created -> running -> completed | failed | cancelled | partial
- ReviewDraft：idle -> running -> completed | failed | partial
- ReviewRun：queued -> running -> completed | failed | cancelled

Paper 交互资源补充：

- PaperStar：用户与 Paper 的收藏关系资源，操作入口为 `/api/v1/papers/{paperId}/star`。
- PaperBatchOperation：批量操作结果资源，至少包含 `successItems` 与 `failedItems`。
- SearchResult：搜索结果资源，支持论文与知识片段的统一搜索，包括请求取消与前端缓存策略。
- ExternalPaper：外部论文发现的 canonical 只读投影视图，由统一搜索接口返回，不单独要求数据库真源。

关键生命周期事件：

- paper.uploaded
- paper.parsed
- paper.indexed
- task.started
- task.finished
- task.failed
- session.closed
- external_paper.discovered
- import_job.completed_metadata_only
- import_job.completed_fulltext_ready
- review_draft.created
- review_draft.run_started
- review_draft.completed
- review_draft.failed
- review_draft.retry_requested

可被异步任务修改的资源：

- Paper（解析与索引状态）
- ImportJob（导入阶段、错误态、重试态）
- UploadSession（分片进度、缺片集合、完成态）
- Chunk（生成、重算、清理）
- Task（执行状态）
- IndexArtifact（构建状态）
- ImportBatch（聚合计数与整体状态）
- EvidenceBundle（重建、去重、字段回填）
- ReviewDraft（outline/draft 覆盖更新、quality/errorState 回写）
- ReviewRun（步骤状态、恢复动作、trace 元数据写入）

Phase B 外部发现/导入资源补充：

- `ExternalPaper` 是 SearchResult 的 external branch canonical shape，最小字段包括：
  - `external_id`
  - `source(arxiv|semantic_scholar)`
  - `title`
  - `authors[]`
  - `abstract`
  - `year`
  - `venue`
  - `doi`
  - `arxiv_id`
  - `s2_paper_id`
  - `url`
  - `pdf_url`
  - `open_access`
  - `citation_count`
  - `references_count`
  - `fields_of_study[]`
  - `availability(metadata_only|pdf_available|pdf_unavailable)`
  - `library_status(not_imported|importing|imported_metadata_only|imported_fulltext_ready)`
- `ExternalPaper` 与 `Paper` 不是并行真源关系：
  - `ExternalPaper` 是发现态投影
  - `Paper` 是入库后的持久资源
  - 两者通过 dedupe / import matching 关联
- Phase B 状态分层冻结如下，执行者不得混用：
  - `ImportJob.status`：任务级终态/运行态，继续使用 `created -> queued -> running -> awaiting_user_action -> completed | failed | cancelled`
  - `ImportJob.stage`：过程级进度，最小集合为 `queued | resolving | downloading | parsing | indexing | completed_metadata_only | completed_fulltext_ready | failed | cancelled`
  - `ExternalPaper.availability`：外部可得性，固定为 `metadata_only | pdf_available | pdf_unavailable`
  - `ExternalPaper.library_status`：文库消费态，固定为 `not_imported | importing | imported_metadata_only | imported_fulltext_ready`
- `imported_metadata_only` 表示 metadata 已入库但全文不可消费；不得被 Chat / Read 全文证据链路当作 `fulltext_ready`。
- `imported_fulltext_ready` 表示 PDF 获取、解析、chunk、embedding/index 已完成，可进入 KB / Read / Chat / Notes / Compare 主链。

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

ReviewDraft 最小字段契约（Phase 5）：

- `id`、`knowledge_base_id`、`title`
- `status`：`idle|running|completed|failed|partial`
- `source_paper_ids[]`
- `outline_doc`：`research_question`、`themes[]`、`sections[]`
- `outline_doc.sections[]`：`title`、`intent`、`supporting_paper_ids[]`、`seed_evidence[]`
- `draft_doc.sections[]`：`heading`、`paragraphs[]`、`omitted_reason`
- `draft_doc.sections[].paragraphs[]`：`paragraph_id`、`text`、`citations[]`、`evidence_blocks[]`、`citation_coverage_status(covered|insufficient)`
- `draft_doc.sections[].paragraphs[]` 可选补充 `claim_verification[]` 与 `truthfulness_summary{}`，且两者必须来自统一 truthfulness substrate。
- `quality`：`citation_coverage`、`unsupported_paragraph_rate`、`graph_assist_used`、`fallback_used`
- `trace_id`、`run_id`、`error_state`、`created_at`、`updated_at`

ReviewDraft 约束（Phase 5）：

- 正式段落必须携带 citation；无 citation 的正文段落禁止进入 `draft_doc`。
- 证据不足时以 section 级 `omitted_reason` 表达，不允许生成无证据正文占位段。
- `error_state` 最少覆盖：`insufficient_evidence|graph_unavailable|validation_failed|writer_failed|partial_draft`。

ReviewRun 最小字段契约（Phase 5）：

- `id`、`knowledge_base_id`、`review_draft_id`、`status`
- `steps[]`：每步至少包含 `step_name`、`status`、`started_at`、`ended_at`
- `steps[].metadata`：至少包含 `input_schema_name`、`output_schema_name`
- `tool_events[]`、`artifacts[]`、`evidence[]`、`recovery_actions[]`
- `trace_id`、`error_state`、`created_at`、`updated_at`

## Required Updates

- 新增资源类型：同步更新本文件与 docs/specs/architecture/api-contract.md。
- 资源状态迁移变化：同步更新 apps/api/app/models 与本文件。
- 新增异步任务：同步补充可修改资源列表。
- 资源契约边界变化：同步更新 docs/specs/governance/fallback-register.yaml 与相关 gate 脚本规则（如适用）。

## Verification

- 抽样检查 API 响应中的资源状态是否在状态机集合内。
- 抽样检查任务完成后资源状态迁移是否可追踪。
- 抽样检查同一资源无重复命名或平行模型定义。
- 运行 `cd apps/api && .venv/bin/python -m pytest -q tests/integration/test_imports_chat_contract.py --maxfail=1`，验证 stream->messages 回读链路契约稳定。

## Phase 6 评测资源（文件系统模型）

以下资源均以文件系统产物形式存储于 `apps/api/artifacts/benchmarks/phase6/`，**无 DB 表**，通过 `eval_service.py` 读取。

### BenchmarkDataset（冻结语料库）
- 文件：`phase6/corpus.json`
- 字段：`dataset_version`、`total_queries`、`total_papers`、`query_families[]`、`queries[]`
- 状态：**冻结**（只读，不可变更）
- 每个 query 含：`query_id`、`family`、`question`、`expected_paper_ids`、`expected_sections`、`must_abstain`、`expected_citation_targets`
- v2.0 pass 最低要求：`paper_count >= 50`、`query_count >= 128`，且 8 个 families `{single_fact, method, experiment_result, table, figure_caption, multi_paper_compare, kb_global, no_answer}` 同时存在于 `query_families[]` 与 `queries[]`

### BenchmarkRun（运行产物目录）
- 路径：`phase6/runs/{run_id}/`
- 子文件：`meta.json`、`retrieval.json`、`answer_quality.json`、`citation_jump.json`、`dashboard_summary.json`、`diff_from_baseline.json`
- `meta.json` 字段：`run_id`、`mode (offline|online)`、`reranker (on|off)`、`dataset_version`、`total_queries`、`overall_verdict`、`created_at`
- `dashboard_summary.json` 是归一化指标快照，gate 重新计算以实际 thresholds 为准
- 不可变：写入后不得修改（append-only artifact model）
- v2.0 close-out 至少要求：
  - 1 个 offline baseline run
  - 1 个 offline candidate run
  - candidate run 的 `diff_from_baseline.json`
  - 每个 run 均完整包含 `meta.json`、`dashboard_summary.json`、`retrieval.json`、`answer_quality.json`、`citation_jump.json`

### DiffReport（对比报告）
- 存储：嵌入 `runs/{run_id}/diff_from_baseline.json`
- 字段：`base_run_id`、`candidate_run_id`、`deltas{}`、`summary{improved, regressed, unchanged}`
- 动态计算：也可通过 `GET /api/v1/evals/diff` 实时计算，不依赖存储文件

### GateVerdict（门禁裁决）
- 不独立存储；嵌入 `dashboard_summary.json` 与 `meta.json` 的 `overall_verdict` 字段
- 硬性阈值见 `eval_service.py::PHASE6_THRESHOLDS`
- 门禁脚本：`scripts/evals/phase6_gate.py`（exit 0=PASS / exit 1=FAIL）
- v2.0 close-out 额外规则：
  - `fallback_used_count <= 5`
  - `cost_per_answer` 必须存在
  - diff 在 `retrieval_hit_rate`、`answer_supported_rate`、`groundedness`、`citation_jump_valid_rate`、`abstain_precision`、`recall_at_5` 上不得回退

## Phase D 真实验证资源（文件系统模型）

以下资源均以文件系统产物形式存储于 `artifacts/validation-results/phase_d/`，**无 DB 表**，通过 `scripts/evals/v3_0_real_world_validation_report.py` 读取并汇总到正式报告。

### RealWorldValidationPayload（真实验证载荷）
- 文件：`phase_d/real_world_validation.json`
- 字段：`schema_version`、`generated_at`、`notes[]`、`sample_registry[]`、`runs[]`
- `sample_registry[]` 最小字段：`sample_id`、`title`、`sample_type`、`source_type`、`discipline`、`document_complexity`、`language_mix`、`expected_risk`
- `runs[]` 最小字段：`run_id`、`sample_ids[]`、`workflow_steps[]`、`success_state`、`failure_points[]`、`recovery_actions[]`、`evidence_reviews[]`、`honesty_checks{}`、`user_visible_confusions[]`
- 状态：append-only；真实 run 一旦记录，不允许删除，只允许追加或补充分析字段

### RealWorldValidationSummary（真实验证汇总）
- 文件：`phase_d/real_world_validation.summary.json`
- 字段：`sample_summary`、`run_summary`、`workflow_summary`、`failure_summary`、`evidence_summary`、`honesty_summary`、`recommendation`
- 语义：由脚本生成的归一化统计快照，不作为手工编辑真源

### RealWorldValidationReport（正式 close-out 报告）
- 文件：`docs/plans/v3_0/reports/validation/v3_0_real_world_validation.md`
- 内容至少包含：样本组成、workflow 覆盖、失败分桶、evidence 质量、honesty 检查、release 建议
- 状态：report-only；结论必须由 `real_world_validation.json` 与 `real_world_validation.summary.json` 推导，不允许手工写出与载荷不一致的结论

## Open Questions

- IndexArtifact 是否需要拆分为向量索引与图索引两类资源。
- ChatSession 的归档策略是否需要时间窗口自动化。
