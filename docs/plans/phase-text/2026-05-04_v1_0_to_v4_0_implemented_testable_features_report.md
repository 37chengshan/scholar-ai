# ScholarAI v1.0-v4.0 已实现且可测试功能报告

> 日期：2026-05-04  
> 范围：`v1.0` -> `v4.0`  
> 性质：事实盘点，不替代 release verdict  
> 结论口径：只统计“仓库已实现且当前仍可测试/可验证”的功能

## 1. 方法与真源

本报告同时依赖三类证据：

1. 版本文档与 closeout：
   - `docs/plans/v1_0/reports/v1_0_release_candidate_report.md`
   - `docs/plans/v2_0/reports/2026-04-28_v2_0_closeout_pass_framework.md`
   - `docs/plans/v3_0/active/overview/06_v3_0_overview_plan.md`
   - `docs/plans/v3_0/reports/general/2026-04-29_v3_0_strict_closeout_report.md`
   - `docs/plans/v3_0/reports/release/v3_6_release_gate_report.md`
   - `docs/plans/v4_0/reports/2026-05-02_v4_0_phase_0_closeout_report.md`
   - `docs/plans/v4_0/reports/2026-05-02_v4_0_phase_1_closeout_report.md`
   - `docs/plans/v4_0/reports/2026-05-04_v4_0_phase_2_closeout_report.md`
2. 当前真实代码入口：
   - 前端：`apps/web/src/app/routes.tsx`、`apps/web/src/app/pages/*`、`apps/web/src/features/*`
   - 后端：`apps/api/app/main.py`、`apps/api/app/api/*`
3. 当前测试与验证证据：
   - `apps/web/src/**/*.test.tsx|test.ts`
   - `apps/api/tests/unit/*`
   - `apps/api/tests/integration/*`
   - `apps/api/tests/e2e/*`
   - v4.0 Phase 2 browser walkthrough closeout

统计规则：

1. 文档说有但代码入口缺失，不计入“已实现”。
2. 代码入口存在但没有自动化测试时，仍可计入“已实现”，但必须标记为“代码事实 / 证据较弱”。
3. 测试通过和 closeout 证据只代表“当前可验证”，不自动等于“release-pass”。

## 2. 总结

截至 2026-05-04，ScholarAI 当前仓库中已经形成、且可测试/可验证的主能力面包括：

1. 账号认证与会话管理
2. Dashboard 与 workflow continuity
3. 本地库检索、外部论文发现与统一搜索
4. 上传、导入、解析、知识库入库、导入状态流
5. Read 页面、source 高亮、阅读进度与 paper chunks/summary
6. Chat / RAG / evidence / citations / SSE streaming
7. Notes 的 CRUD、生成、证据保存、导出
8. 多论文 Compare 与演化对比
9. KB Review draft / runs / claims repair
10. Entities / Graph / PageRank
11. Analytics / eval artifact 读取与展示
12. Health / system / governance gates
13. Projects / annotations / user settings 等支持域

当前版本化真相：

1. `v1.0`：RC 视角收口 Evidence UI、trace/cost/error_state、release gate。
2. `v2.0`：完成前端/后端/治理三大重构，形成 Upload/Import -> Parse/Index -> KB -> RAG 的基础主链。
3. `v3.0`：把系统推进到 External Search、Claim/Citation、Online-first RAG、Truth+Route、Benchmark/Release Gate、Frontend Reliability 的多主线阶段。
4. `v4.0`：当前已验证到 Phase 0-2，补齐 workflow continuity 与 beta hardening，主链模型已收口到线上模型。

## 3. 跨版本能力演进

| version | 当前可确认的能力沉淀 | 当前状态 |
|---|---|---|
| `v1.0` | Evidence-first 前端链路、trace/cost/error_state、release gate 报告链 | 仍在当前仓库可见且可测试 |
| `v2.0` | 前后端架构收口、SSE 适配层、KB Detail 解耦、运行档位/健康探针/RAG 契约统一、治理门禁上线、Upload/Import/RAG 主链骨架 | 已被后续版本继承 |
| `v3.0` | External Search + Import、Claim/Citation、Online-first RAG、Truthfulness/Route、Benchmark/Analytics、Frontend Reliability | 大量能力仍是当前主链组成部分 |
| `v4.0` | Workflow continuity、Dashboard command center continuity、beta assets、fresh-state walkthrough、online provider mainline、demo-ready closeout | 当前版本真源 |

## 4. 当前已实现且可测试功能清单

## 4.1 认证、账号与会话

已实现功能：

1. Landing / Login / Register / Forgot Password / Reset Password 页面。
2. Cookie-based auth、`/me`、refresh、logout。
3. Chat sessions 的创建、列表、读取、重命名、删除与按用户隔离。

代码证据：

1. 前端路由：`apps/web/src/app/routes.tsx`
2. 页面：`apps/web/src/app/pages/Landing.tsx`、`Login.tsx`、`Register.tsx`、`ForgotPassword.tsx`、`ResetPassword.tsx`
3. 后端接口：`apps/api/app/api/auth.py`、`apps/api/app/api/session.py`

测试证据：

1. `apps/api/tests/integration/test_api.py`
2. `apps/api/tests/unit/test_auth.py`
3. `apps/api/tests/unit/test_auth_dependency.py`
4. `apps/web/src/features/chat/chatHandoff.session-isolation.test.ts`

版本归属：

1. 基础认证能力在早期版本已存在。
2. durable handoff + session isolation 在 `v4.0-1` / `v4.0-2` 明显加强。

## 4.2 Dashboard 与 workflow continuity

已实现功能：

1. Dashboard 作为 command center。
2. durable handoff：Search / Review / Compare / Read 等入口可把上下文带入 Chat。
3. `WorkflowHydration` 把 handoff 映射成 waiting workflow、pending actions、artifacts、timeline。

代码证据：

1. `apps/web/src/app/pages/Dashboard.tsx`
2. `apps/web/src/features/chat/chatHandoff.ts`
3. `apps/web/src/features/workflow/commandCenter.ts`
4. `apps/web/src/features/workflow/hooks/useWorkflowHydration.ts`

测试证据：

1. `apps/web/src/features/chat/chatHandoff.test.ts`
2. `apps/web/src/features/chat/hooks/useChatHandoff.test.tsx`
3. `apps/web/src/features/workflow/commandCenter.test.ts`
4. `apps/web/src/features/workflow/hooks/useWorkflowHydration.test.tsx`
5. `docs/plans/v4_0/reports/2026-05-02_v4_0_phase_1_closeout_report.md`

版本归属：

1. 这是 `v4.0-1` 的核心已关闭能力。

## 4.3 搜索与外部论文发现

已实现功能：

1. 本地 library search。
2. unified search。
3. fusion search。
4. multimodal search。
5. 外部搜索：arXiv、Semantic Scholar、DOI resolve。
6. Search -> Import to KB 主链入口。

代码证据：

1. 前端页面与组件：
   - `apps/web/src/app/pages/Search.tsx`
   - `apps/web/src/features/search/components/SearchWorkspace.tsx`
   - `SearchResultsPanel.tsx`
   - `SearchKnowledgeBaseImportModal.tsx`
2. 后端：
   - `apps/api/app/api/search/external.py`
   - `apps/api/app/api/search/library.py`
   - `apps/api/app/api/search/multimodal.py`
   - `apps/api/app/api/search/__init__.py`

测试证据：

1. 前端：
   - `apps/web/src/app/pages/Search.test.tsx`
   - `apps/web/src/features/search/hooks/useSearchImportFlow.test.tsx`
   - `apps/web/src/features/search/components/SearchKnowledgeBaseImportModal.test.tsx`
   - `apps/web/src/features/search/components/SearchResultsPanel.test.tsx`
2. 后端：
   - `apps/api/tests/test_external_search.py`
   - `apps/api/tests/test_unified_search.py`
   - `apps/api/tests/integration/test_multimodal_search.py`
   - `apps/api/tests/integration/test_multimodal_search_api.py`
   - `apps/api/tests/integration/test_compare_metric_queries.py`
   - `apps/api/tests/integration/test_rag_query_planning_flow.py`

版本归属：

1. Search -> Import 主线在 `v2.0` 报告中已成基础骨架。
2. `External Search + Import to KB` 是 `v3.0-B` 的显式主线。

## 4.4 上传、导入、解析与知识库

已实现功能：

1. 文件上传、批量上传、上传历史。
2. ImportJob-first 导入状态机。
3. 分片 upload session：create / parts / complete / abort。
4. KB CRUD、batch delete/export、storage stats。
5. KB upload / import-url / import-arxiv / batch-upload。
6. 导入去重决策、导入事件流、导入重试/取消。
7. 知识库内 papers 列表、检索、query、review drafts、runs。

代码证据：

1. 前端：
   - `apps/web/src/app/pages/KnowledgeBaseList.tsx`
   - `apps/web/src/app/pages/KnowledgeBaseDetail.tsx`
   - `apps/web/src/features/kb/components/KnowledgeWorkspaceShell.tsx`
   - `KnowledgeImportPanel.tsx`
   - `KnowledgePapersPanel.tsx`
   - `KnowledgeRunHistoryPanel.tsx`
2. 后端：
   - `apps/api/app/api/uploads.py`
   - `apps/api/app/api/imports/*`
   - `apps/api/app/api/kb/*`
   - `apps/api/app/api/papers/paper_upload.py`
   - `apps/api/app/api/papers/paper_status.py`

测试证据：

1. 前端：
   - `apps/web/src/app/pages/KnowledgeBaseDetail.test.tsx`
   - `apps/web/src/features/kb/hooks/useImportJobsPolling.test.tsx`
   - `apps/web/src/features/kb/hooks/useKnowledgeBaseQueries.test.tsx`
   - `apps/web/src/features/kb/hooks/useKnowledgeBaseWorkspace.test.tsx`
   - `apps/web/src/features/kb/hooks/useKnowledgeWorkflowRefresh.test.tsx`
2. 后端：
   - `apps/api/tests/integration/test_upload_session_lifecycle.py`
   - `apps/api/tests/integration/test_pipeline_recovery.py`
   - `apps/api/tests/integration/test_pipeline_partial_success.py`
   - `apps/api/tests/unit/test_import_job_transitions.py`
   - `apps/api/tests/unit/test_import_pipeline_reliability.py`
   - `apps/api/tests/unit/test_kb_upload_api.py`
   - `apps/api/tests/unit/test_kb_papers_api.py`
   - `apps/api/tests/unit/test_storage_manager_chunk_rows.py`

版本归属：

1. `v2.0` 已把 Upload/Import -> Parse/Index -> KB 作为主链讨论核心。
2. `v3.0-B` 把它正式提升为版本主线。
3. `v4.0-2` 补了 online provider、Milvus 维度自愈、SQL chunk truth 和 walkthrough 证据。

## 4.5 Paper、Read、高亮与阅读进度

已实现功能：

1. Paper CRUD、搜索、batch delete、batch star。
2. 单篇 paper status、download、chunks、summary。
3. regenerate chunks / regenerate notes。
4. Read 页面 source sidenote、source chunk highlight。
5. 阅读进度读取与更新。

代码证据：

1. 前端：
   - `apps/web/src/app/pages/Read.tsx`
   - `apps/web/src/features/read/components/EvidenceSideNote.tsx`
   - `apps/web/src/features/read/components/SourceChunkHighlight.tsx`
2. 后端：
   - `apps/api/app/api/papers/paper_crud.py`
   - `apps/api/app/api/papers/paper_status.py`
   - `apps/api/app/api/reading_progress.py`
   - `apps/api/app/api/evidence.py`

测试证据：

1. 后端：
   - `apps/api/tests/test_reading_card_service.py`
   - `apps/api/tests/test_reading_notes_service.py`
   - `apps/api/tests/unit/test_citation_source_endpoint.py`
   - `apps/api/tests/unit/test_kb_papers_api.py`
2. 浏览器/closeout：
   - `docs/plans/v4_0/reports/2026-05-04_v4_0_phase_2_closeout_report.md`

版本归属：

1. v2.0 已形成 Read + Notes + RAG 的闭环骨架。
2. v4.0-2 明确验证了 `KB search -> Read -> highlight`。

## 4.6 Chat、RAG、证据与 SSE

已实现功能：

1. Chat 页面与 session sidebar。
2. Chat normal send + stream。
3. confirm / cancel / retry。
4. fast path 与 scoped RAG path 并存。
5. answer contract、evidence panel、citation panel、reasoning panel、tool timeline。
6. paper-scoped retrieval、single-paper Chat。
7. `evidence/source/{source_chunk_id}` 跳转。
8. SSE streaming contract。

代码证据：

1. 前端：
   - `apps/web/src/app/pages/Chat.tsx`
   - `apps/web/src/features/chat/workspace/ChatWorkspaceV2.tsx`
   - `apps/web/src/features/chat/components/*`
   - `apps/web/src/features/chat/hooks/*`
2. 后端：
   - `apps/api/app/api/chat.py`
   - `apps/api/app/api/search/__init__.py` (`/evidence`)
   - `apps/api/app/api/evidence.py`
   - `apps/api/app/api/rag.py`
   - `apps/api/app/rag_v3/main_path_service.py`
   - `apps/api/app/rag_v3/retrieval/hierarchical_retriever.py`

测试证据：

1. 前端：
   - `apps/web/src/app/pages/Chat.test.tsx`
   - `apps/web/src/features/chat/hooks/useChatSend.test.tsx`
   - `useChatRun.test.tsx`
   - `useChatRuntimeBridge.test.ts`
   - `useChatScopeController.test.ts`
   - `MessageFeed.test.tsx`
   - `EvidencePanel.test.tsx`
   - `CitationPanel.test.tsx`
2. 后端：
   - `apps/api/tests/e2e/test_rag_streaming.py`
   - `apps/api/tests/e2e/test_rag_citations.py`
   - `apps/api/tests/integration/test_rag_api_unified.py`
   - `apps/api/tests/unit/test_answer_contract.py`
   - `apps/api/tests/unit/test_chat_fast_path.py`
   - `apps/api/tests/unit/test_hierarchical_retriever_routing.py`
   - `apps/api/tests/unit/test_main_path_service_scope_routing.py`
   - `apps/api/tests/unit/test_rag_error_state_contract.py`

版本归属：

1. `v1.0` 明确收口了 evidence-first UI 与 trace/cost/error_state。
2. `v2.0` 完成 SSE adapter、Chat V2、RAG contract 收口。
3. `v3.0-C/H/I` 分别强化 citation/claim、online-first runtime、truthfulness + route。
4. `v4.0-1/2` 补 durable handoff、session isolation、single-paper chat recovery。

## 4.7 Notes

已实现功能：

1. Note CRUD。
2. 按 paper 查询 notes。
3. generate / regenerate notes。
4. export。
5. 从 evidence 直接保存 note。
6. Notes 页面支持分组、标签、linked evidence。

代码证据：

1. 前端：
   - `apps/web/src/app/pages/Notes.tsx`
   - `apps/web/src/features/notes/components/LinkedEvidenceList.tsx`
2. 后端：
   - `apps/api/app/api/notes.py`

测试证据：

1. 前端：
   - `apps/web/src/features/notes/ownership.test.ts`
2. 后端：
   - `apps/api/tests/test_notes.py`
   - `apps/api/tests/test_notes_api_contract.py`
   - `apps/api/tests/test_notes_generator.py`
   - `apps/api/tests/test_notes_worker.py`
   - `apps/api/tests/unit/test_notes_evidence_save.py`
   - `apps/api/tests/unit/test_notes_contract_helpers.py`
3. 浏览器/closeout：
   - `docs/plans/v4_0/reports/2026-05-04_v4_0_phase_2_closeout_report.md`

版本归属：

1. Notes 是 v1.0 RC、v2.0 主链、v4.0 walkthrough 都明确覆盖的持续能力。

## 4.8 Compare

已实现功能：

1. multi-paper compare。
2. evolution timeline。
3. evidence-backed compare v4。
4. Compare 页面支持 evidence 跳转、保存笔记、继续到 Chat。

代码证据：

1. 前端：
   - `apps/web/src/app/pages/Compare.tsx`
   - `apps/web/src/features/chat/components/CompareCard.tsx`
2. 后端：
   - `apps/api/app/api/compare.py`
   - `apps/api/app/services/compare_service.py`

测试证据：

1. 前端：
   - `apps/web/src/features/chat/components/CompareCard.test.tsx`
2. 后端：
   - `apps/api/tests/test_comparison.py`
   - `apps/api/tests/integration/test_compare_metric_queries.py`
3. 浏览器/closeout：
   - `docs/plans/v4_0/reports/2026-05-04_v4_0_phase_2_closeout_report.md`

版本归属：

1. v2.0 closeout framework 已把 multi-paper compare 列为 RAG lane。
2. v4.0-2 明确修复并验证了 Compare 页面。

## 4.9 Review / Review Draft

已实现功能：

1. KB review draft create / list / detail / retry。
2. claim repair。
3. review runs。
4. 前端 Review panel 与 run history。

代码证据：

1. 前端：
   - `apps/web/src/features/kb/components/KnowledgeReviewPanel.tsx`
   - `KnowledgeRunHistoryPanel.tsx`
2. 后端：
   - `apps/api/app/api/kb/kb_review.py`

测试证据：

1. 前端：
   - `apps/web/src/features/kb/components/KnowledgeReviewPanel.test.tsx`
2. 后端：
   - `apps/api/tests/integration/test_rag_claim_verification.py`
   - `apps/api/tests/unit/test_claim_verifier.py`
   - `apps/api/tests/unit/test_citation_verifier.py`
3. closeout 证据：
   - `docs/plans/v4_0/reports/2026-05-04_v4_0_phase_2_closeout_report.md`

版本归属：

1. v3.0-C 强化了 claim/citation/review 方向。
2. v4.0-2 已把 review 保留为真实可运行但可能 `partial` 的能力。

## 4.10 Entities 与 Graph

已实现功能：

1. entity extraction。
2. 为 paper build graph。
3. graph status。
4. graph nodes / neighbors / subgraph / pagerank。

代码证据：

1. `apps/api/app/api/entities.py`
2. `apps/api/app/api/graph.py`

测试证据：

1. `apps/api/tests/e2e/test_graph_e2e.py`
2. `apps/api/tests/test_graph/test_graph_api.py`
3. `apps/api/tests/test_graph/test_graph_builder.py`
4. `apps/api/tests/test_graph/test_pagerank.py`

版本归属：

1. 这是代码中已实现但版本文档中不总是作为主线强调的能力。
2. 本报告按“代码事实”计入。

## 4.11 Analytics / Evals

已实现功能：

1. `/analytics` 页面。
2. eval overview / runs / run detail / diff 读取。
3. benchmark / release gate artifacts 可消费。

代码证据：

1. 前端：
   - `apps/web/src/app/pages/Analytics.tsx`
2. 后端：
   - `apps/api/app/api/evals.py`
   - `apps/api/tests/benchmarks/*`

测试证据：

1. 前端：
   - `apps/web/src/app/pages/Analytics.test.tsx`
2. 后端：
   - `apps/api/tests/unit/test_eval_service.py`
   - `apps/api/tests/unit/test_benchmark_reporting.py`
3. 文档证据：
   - `docs/plans/v3_0/reports/release/v3_6_release_gate_report.md`

版本归属：

1. v1.0 RC、v2.0 closeout framework、v3.0 J/release gate 都直接消费这条能力线。

## 4.12 健康检查、系统诊断与治理

已实现功能：

1. health：live / basic / ready / deep / degraded。
2. system：storage、logs stream、system health。
3. tasks：list / detail / progress / retry / delete。
4. token usage。
5. phase / branch / contract / fallback / e2e gate 脚本。

代码证据：

1. 后端：
   - `apps/api/app/api/health.py`
   - `apps/api/app/api/system.py`
   - `apps/api/app/api/tasks.py`
   - `apps/api/app/api/token_usage.py`
2. 治理脚本：
   - `scripts/check-phase-tracking.sh`
   - `scripts/check-branch-lifecycle.sh`
   - `scripts/check-contract-gate.sh`
   - `scripts/check-fallback-expiry.sh`
   - `scripts/check-e2e-gate.sh`

测试证据：

1. `apps/api/tests/unit/test_health_probes.py`
2. `apps/api/tests/test_task_status_transitions.py`
3. `docs/plans/v2_0/reports/2026-04-18_落实计划C_工程治理与交付体系重构.md`

版本归属：

1. 这条能力线在 `v2.0 Plan C` 之后成为仓库长期基线。

## 4.13 Projects、Annotations 与用户设置

已实现功能：

1. Projects CRUD。
2. paper -> project assignment。
3. Annotations CRUD（highlight / note / bookmark）。
4. Settings 页面与 profile / localization / display / security / diagnostics / api 分区。
5. 用户设置与 monthly token usage 读取接口。

代码证据：

1. 前端：
   - `apps/web/src/app/pages/Settings.tsx`
   - `apps/web/src/features/settings/*`
   - `apps/web/src/hooks/useProjects.ts`
   - `apps/web/src/services/projectsApi.ts`
   - `apps/web/src/app/components/TokenUsageCard.tsx`
2. 后端：
   - `apps/api/app/api/projects.py`
   - `apps/api/app/api/annotations.py`
   - `apps/api/app/api/token_usage.py`
   - `apps/api/app/api/users.py`

测试证据：

1. 前端：
   - `apps/web/src/app/pages/Settings.test.tsx`
2. 后端：
   - `apps/api/tests/unit/test_extended.py`
   - `apps/api/tests/test_notes_api_contract.py`
   - `apps/api/tests/test_reading_notes_service.py`

版本归属：

1. 这些能力长期存在于仓库，但通常不是 v1.0-v4.0 报告中的主卖点。
2. 本报告按“代码事实”计入。

## 4.14 Semantic Scholar 专项接口

已实现功能：

1. Semantic Scholar batch get papers。
2. paper detail / citations / references。
3. autocomplete。
4. author search 与 author papers。

代码证据：

1. `apps/api/app/api/semantic_scholar.py`
2. `apps/api/app/core/semantic_scholar_service.py`

测试证据：

1. `apps/api/tests/test_external_search.py`
2. `apps/api/tests/integration/test_api.py`

版本归属：

1. Search 外部发现主线在 v3.0-B 中被正式提升。
2. 这些接口本身是当前可调用的真实支持面。

## 5. 当前线上模型真相

当前主链模型按 `v4.0 Phase 2 closeout` 与代码实现，可确认是：

1. generation：在线 GLM
2. embedding：DashScope `text-embedding-v4`
3. rerank：DashScope `qwen3-rerank`

代码/文档证据：

1. `apps/api/app/core/embedding/factory.py`
2. `apps/api/app/core/reranker/factory.py`
3. `apps/api/app/core/dashscope_runtime.py`
4. `docs/plans/v4_0/reports/2026-05-04_v4_0_phase_2_closeout_report.md`

## 6. 不应被写成“已全面完成”的事项

以下内容不计入“已经实现且可测试功能完成态”：

1. `v4.0` Phase 3-7 的正式 closeout。
2. `controlled-beta-ready`、public beta、release-pass。
3. staging/cloud controlled beta gate。
4. 所有 Review / single-paper Chat 都稳定 full support。
5. 单次 fresh-state 全链路自动化 release verdict。

## 7. 代码事实与文档声明的差异

本轮盘点中，以下能力更接近“代码事实强于版本文档显式叙述”：

1. entity extraction / graph / pagerank
2. health 多层探针
3. system diagnostics / logs stream
4. upload history / upload session lifecycle
5. tasks retry/progress/delete
6. token usage
7. projects / annotations
8. semantic scholar 专项接口
9. settings 分区页

这些能力在代码与测试里都存在，但并不总是被 `v1.0-v4.0` 的版本报告当作主线卖点强调。

## 8. 自审查漏

本报告已按以下检查清单自审：

1. 页面面：
   - landing
   - login/register/reset
   - dashboard
   - search
   - knowledge base list/detail
   - read
   - chat
   - notes
   - compare
   - analytics
   - settings
2. 后端域：
   - auth
   - sessions
   - papers
   - uploads
   - imports
   - kb
   - reading progress
   - chat/rag/evidence
   - notes
   - compare
   - projects
   - annotations
   - entities/graph
   - semantic scholar
   - evals
   - system/health/tasks
   - token usage / users settings
3. 证据面：
   - 版本 closeout / release 文档
   - 当前代码入口
   - 前端测试
   - 后端 unit / integration / e2e

当前仍可能继续补强但不构成本报告缺漏的部分：

1. 更细粒度的 Settings 分区功能逐项盘点
2. Projects / Annotations 域的单独事实盘点
3. benchmark 目录下每一条 runner 的功能对照表

## 9. 结论

如果只问“当前仓库到底已经实现了什么，并且今天能从代码/测试/closeout 中证明什么”，最准确的结论是：

1. ScholarAI 已经不是单点 RAG demo，而是具备：
   - 发现论文
   - 导入知识库
   - 阅读与高亮
   - 证据型问答
   - 笔记沉淀
   - 多论文比较
   - review draft
   - analytics/eval
   - workflow continuity
   的完整研究工作流骨架。
2. `v1.0-v4.0` 的能力不是彼此替换，而是逐步叠加；大量 `v2.0/v3.0` 能力仍然构成 `v4.0` 的底盘。
3. 当前仓库最强的事实状态不是“全部版本全量完结”，而是：
   - 多数关键功能已实现
   - 多条主链已有自动化测试
   - `v4.0` 当前已验证到 `Phase 0-2`
   - 产品主链已进入 `demo-ready`，但不是 release-pass

## 10. 2026-05-07 Browser Refresh Note

后续 round1 浏览器复验继续确认了以下页面与壳层：

1. `landing` / `login` / `dashboard`
2. `search`
3. `knowledge-bases` / `knowledge-bases/:id`
4. `read`
5. `chat`
6. `notes`
7. `compare`
8. `analytics`
9. `settings`
10. global shell / sidebar

复验结论：

1. 主页面与主工作流整体仍可用。
2. `/settings` 与 `/analytics` 的字体属性警告已清。
3. Notes 的历史 JSON 外泄已清。
4. 仍有两个已验证残余 gap：
   - KB/sidebar 测试式种子内容泄漏
   - compare-scoped chat 的 evidence 质量偏弱
