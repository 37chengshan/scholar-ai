---
owner: product-engineering
status: review-ready
last_verified_at: 2026-05-26
review_model: gpt-5.5-high multi-agent read-only audit
scope:
  - apps/web
  - apps/api
  - packages/sdk
  - packages/types
  - docs/specs
  - scripts/check-*
---

# 2026-05-26 v4.5 Frontend / Backend Multidimensional Audit

## 1. Executive Verdict

本次审查结论：当前 v4.5 不能写成 release-pass，也不建议直接进入只做 UI polish 的收尾状态。

未发现明确 P0 阻断，但 P1 风险数量较多，且集中在真实产品链路：

1. 后端鉴权与用户可见性校验存在多处越权风险。
2. 上传、导入、重试、任务进度、Milvus 写入与清理存在“状态显示成功但实际未完成”的风险。
3. 前端 Chat / Search / KB 的关键契约字段和轮询条件存在用户可见回归。
4. Search / Semantic Scholar / error envelope / SDK contract 仍在多处漂移。
5. 新增 workflow / runtime 状态文件的治理边界不完整，存在本地状态误提交风险。

本报告只表示审查与问题归档完成，不表示 v4.5 已达到 release-candidate 或 release-pass。

## 2. Audit Method

本轮使用 4 个只读子代理并行审查，全部为 `gpt-5.5 high`：

| audit lane | reviewed surfaces | result |
|---|---|---|
| frontend | `apps/web/src/app`, `apps/web/src/features`, `apps/web/src/services`, `packages/sdk`, design spec | completed |
| backend API/service | `apps/api/app/api`, `apps/api/app/services`, `apps/api/app/models`, API contract | completed |
| backend data/reliability | `apps/api/app/rag_v3`, `app/core`, `app/workers`, import/indexing/task paths | completed |
| cross-layer governance | docs source of truth, structure gates, runtime hygiene, SDK/API contract, security/config | completed |

审查原则：

1. 以 `docs/specs/architecture/api-contract.md`、`docs/specs/domain/resources.md`、`docs/specs/design/frontend/DESIGN_SYSTEM.md` 为主要真源。
2. 不修改业务代码。
3. 不启动长期服务。
4. 只运行轻量、聚焦的只读验证命令。
5. 按用户可见影响、安全影响、数据正确性、治理风险排序。

## 3. Verification Performed

前端子代理执行：

```bash
cd apps/web
npm run type-check
npx vitest run --maxWorkers=1 \
  src/features/search/hooks/useSearchImportFlow.test.tsx \
  src/features/kb/components/KnowledgeWorkspaceShell.test.tsx \
  src/features/chat/hooks/useChatSend.test.tsx \
  src/services/sseService.test.ts
```

结果：

1. `npm run type-check`: passed
2. focused Vitest: 4 files / 27 tests passed

后端 API/service 子代理执行：

```bash
cd apps/api
.venv/bin/python -m pytest -q \
  tests/unit/test_chat_fast_path.py \
  tests/unit/test_kb_query_contract.py \
  tests/test_notes_api_contract.py \
  --maxfail=1
```

结果：

1. 13 passed
2. `tests/test_comparison.py tests/unit/test_paper_model.py` 组合验证失败，分别暴露旧 compare patch target 与 index 命名漂移。
3. `tests/unit/test_paper_model.py` 单独失败，当前 ORM index 名为 `idx_papers_userId`，测试期待 `idx_papers_user_id`。

后端数据/任务可靠性子代理执行：

```bash
cd apps/api
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q \
  tests/test_import_processing_state_sync.py \
  tests/test_task_status_transitions.py \
  --maxfail=1 -p no:cacheprovider

PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q \
  tests/unit/test_import_pipeline_reliability.py \
  tests/unit/test_answer_contract.py \
  --maxfail=1 -p no:cacheprovider
```

结果：

1. 13 passed
2. 17 passed
3. `test_answer_contract` 仍有既有 runtime warning

治理子代理执行：

```bash
bash scripts/check-runtime-hygiene.sh tracked
bash scripts/check-doc-governance.sh
bash scripts/check-structure-boundaries.sh
bash scripts/check-code-boundaries.sh
bash scripts/check-governance.sh
bash scripts/check-runtime-hygiene.sh strict
```

结果：

1. tracked / doc / structure / code / governance gates: passed
2. strict runtime hygiene: failed，主要来自本地 `test-results`、`uploads`、`apps/web/test-results`、`apps/api/.venv/**/__pycache__`

## 4. 2026-05-26 Closeout Update

本轮在 `feat/v4-5-bridge-closeout` 上继续修复了一组高价值但可局部验证的问题，并保留 Milvus / cancel / legacy RAG 这类高风险链路到下一批。

已落地修复：

1. `P2-CONTRACT-002`：`apps/web/src/utils/apiClient.ts` 现在在解 envelope 时保留顶层 `meta`，列表调用可直接消费 `meta.total/limit/offset`。
2. `P2-CONTRACT-003`：`/api/v1/search/unified` 增加 `source` filter、`meta` envelope，并统一 Semantic Scholar canonical source 为 `semantic_scholar`。
3. `P2-CONTRACT-004`：`/api/v1/search/evidence` 现在返回标准 envelope，而不是 raw object。
4. `P1-FE-004`：`WorkspaceShell` 在窄屏下切为单列 stack，避免固定横向三栏。
5. `P2-UX-001`：Search 作者弹窗与 KB 导入弹窗迁移到 Radix `Dialog` 基础组件。
6. `P1-GOV-001`：`data/` 已补入 `.gitignore` 与 `scripts/check-runtime-hygiene.sh` tracked gate。
7. Search source 过滤链路已打通到请求层，Search sidebar 的 Semantic Scholar 统计与 active source 已改为 canonical `semantic_scholar`。
8. `BE-V45-006`：`retrieve_evidence()` 现在会对 `paper_scope == []` 执行真实收窄，不再把空 KB scope 放宽成全局候选池。
9. `BE-V45-005`：`/api/v1/rag/query` 现在显式暴露 `query_family`、`planner_query_count`、`decontextualized_query`、`second_pass_used`、`second_pass_gain`、`phase6_runtime`，并保证 cache 命中同构。
10. `P2-CONTRACT-005` / `BE-V45-008`：新增 canonical `POST /api/v1/papers/{paperId}/star`，保留 `PATCH /starred` 作为兼容别名；`POST /api/v1/papers/batch-delete` 现在返回 `deletedIds` 与带 reason 的失败列表。
11. `P2-CONTRACT-005` 前端适配：`apps/web/src/services/papersApi.ts` 已切到 canonical `/star` 路由、snake_case `paper_ids` 请求体，并消费 traceable batch-delete / batch-star 返回结构。
12. `P2-TASK-001`：`PDFCoordinator.process()` 现在在成功/失败收口后清理临时 PDF 文件，避免 `delete=False` 残留。
13. `P1-DATA-002`：Milvus 现在支持按 `paper_id` 清理 content v2、summary、image、table 四类向量；该清理已接入 `delete_paper`、`batch_delete`、`regenerate-chunks` 和 storage rerun 路径，避免旧证据残留。

本轮新增验证：

```bash
cd apps/web
npx vitest run --maxWorkers=1 \
  src/utils/apiClient.test.ts \
  src/features/search/components/SearchKnowledgeBaseImportModal.test.tsx \
  src/features/search/components/SearchAuthorPanel.test.tsx \
  src/app/components/layout/WorkspaceShell.test.tsx \
  src/features/kb/components/KnowledgeWorkspaceShell.test.tsx
npm run type-check

cd apps/api
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q \
  tests/unit/test_search_evidence_api.py \
  tests/unit/test_search_uses_v3_retriever.py \
  tests/unit/test_search_contracts_v45.py \
  tests/test_unified_search.py \
  --maxfail=1 -p no:cacheprovider

cd ..
bash scripts/check-runtime-hygiene.sh tracked

PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q \
  tests/unit/test_main_path_service_scope_routing.py \
  tests/unit/test_paper_contracts_v45.py \
  tests/integration/test_rag_api_unified.py \
  --maxfail=1 -p no:cacheprovider

cd apps/web
npx vitest run --maxWorkers=1 \
  src/services/papersApi.test.ts \
  src/utils/apiClient.test.ts
npm run type-check

cd apps/api
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q \
  tests/unit/test_pdf_coordinator.py -k temporary_pdf \
  --maxfail=1 -p no:cacheprovider

PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q \
  tests/unit/test_paper_contracts_v45.py \
  tests/unit/test_storage_manager_embedding_runtime.py \
  tests/unit/core/test_milvus_unified.py -k "delete_by_paper_contents or delete_all_vectors_by_paper" \
  --maxfail=1 -p no:cacheprovider
```

结果：

1. 前端 Vitest：5 files / 25 tests passed
2. 前端 `npm run type-check`：passed
3. 后端 targeted pytest：17 passed
4. runtime hygiene tracked：passed
5. 后端 contract follow-up pytest：11 passed
6. 前端 papersApi / apiClient Vitest：2 files / 14 tests passed
7. 前端 `npm run type-check`：passed
8. PDF temp cleanup targeted pytest：1 passed
9. Milvus cleanup / delete / regenerate targeted pytest：10 passed（其中 Milvus 文件仅跑新增 cleanup 相关用例，避开无关旧断言）

仍保持未修复且优先级高的项：

1. `P1-DATA-001` / `P1-DATA-003`：Milvus fail-closed、dimension mismatch 自动 drop 仍未收口
2. `P1-DATA-004`：`/api/v1/rag/query` 仍未切到 shared AnswerContract 主路径；这轮只补了 planner / phase6 runtime 字段同构。
3. `BE-V45-004`：cancel 仍是 DB-only cancel，worker 继续运行

## 5. P1 Findings

### 4.1 Auth / Ownership / Visibility

| id | surface | evidence | impact | recommended fix |
|---|---|---|---|---|
| P1-AUTH-001 | `apps/api/app/api/chat.py:967` | `/chat/cancel` 直接 `sse_manager.disconnect(session_id)`，无 session ownership 校验 | 已登录用户可取消他人已知 session 的 active stream | 先查 session，校验 `session.user_id == current_user.id`，不通过返回 404/403 |
| P1-AUTH-002 | `apps/api/app/api/chat.py:1027` | `/chat/retry` 在 ownership 校验前读取 `message_service.get_messages(session_id=...)` | 可能读取他人 session 的消息元数据；后续 auth 错误又会被 SSE 200 包装 | retry 入口先校验 session ownership，auth 类错误不得转成成功 SSE |
| P1-AUTH-003 | `apps/api/app/api/notes.py:810`, `:880`, `:955` | notes generate / regenerate / export 只按 `Paper.id` 查 | 用户可对他人 paper id 生成、再生成、导出 reading notes | 所有查询加 `Paper.user_id == user_id`，不匹配返回 404 |
| P1-AUTH-004 | `apps/api/app/api/notes.py:1012` | evidence note canonical chunk 查询未 join `Paper.user_id` | 用户可持久化或读取不可见 paper/chunk 的 evidence link | `_find_best_evidence_source_payload_db` 传入 `user_id` 并 join `Paper` |
| P1-AUTH-005 | `apps/api/app/services/evidence_source_service.py:53` | SQL lookup 有 user scope，但 artifact fallback 直接 `get_evidence_source_payload(source_chunk_id)` | 猜测或陈旧 artifact id 可能泄露 evidence content | artifact fallback 前校验 paper ownership；或限制为公开 benchmark artifact |

### 4.2 Upload / Import / Task Reliability

| id | surface | evidence | impact | recommended fix |
|---|---|---|---|---|
| P1-TASK-001 | `apps/api/app/api/papers/paper_upload.py:259` | `upload_to_local_storage` 使用 `os.makedirs` 但未 import `os` | 本地上传路径会在验证后 `NameError` | import `os`，补上传单测 |
| P1-TASK-002 | `apps/api/app/schemas/upload_session.py:11`, `apps/api/app/services/upload_session_service.py:189` | 分片上传只校验 `sizeBytes > 0` 与 chunk size，完成时不跑 PDF magic bytes / 50MB 校验 | 可绕过 legacy upload 的 PDF 安全边界 | create 阶段限制总大小和类型，complete 阶段复用 `validate_pdf_content()` |
| P1-TASK-003 | `apps/api/app/api/imports/batches.py:171` | batch endpoint 创建 external `ImportJob` 后不调用 `process_import_job.delay(...)` | arxiv / doi / pdf_url / semantic_scholar 批量导入会长期停在 `queued` | commit 后逐项 enqueue，并记录 enqueue failure |
| P1-TASK-004 | `apps/api/app/api/tasks.py:223` | retry route 只重置 DB 状态，不 enqueue worker | 用户看到 `Task queued for retry`，但任务可能永远 pending | reset 后调用对应 Celery task；broker failure 时恢复 failed/retryable |
| P1-TASK-005 | `apps/api/app/tasks/pdf_tasks.py:52` | `_sync_import_job_stage()` 存在但未传给真实 coordinator | ImportJob 进度可能停在旧 stage 直到 terminal sync | 将 stage callback 接入 `coordinator.process(...)` |

### 4.3 Vector / Retrieval Data Correctness

| id | surface | evidence | impact | recommended fix |
|---|---|---|---|---|
| P1-DATA-001 | `apps/api/app/core/milvus_service.py:1327`, `apps/api/app/workers/storage_manager.py:747` | Milvus insert 重试耗尽后 log and continue，storage manager 仍可标记成功 | paper 可能显示 searchable，但 Milvus 无向量 | required vector insert failure 应 fail stage 或显式 degraded/search-not-ready |
| P1-DATA-002 | `apps/api/app/workers/storage_manager.py:745`, `apps/api/app/services/paper_service.py:668` | reindex 删除 SQL chunks，但不清 Milvus content / summary；paper delete 也不删 Milvus | 删除或重试后的论文仍可能被检索到旧 evidence | reindex/delete 前按 `paper_id` 删除 Milvus v2 content 和 summary |
| P1-DATA-003 | `apps/api/app/core/milvus_service.py:521` | dimension mismatch 时直接 drop/recreate collection | embedding 配置漂移可清空向量，但 paper/task 仍显示完成 | 不自动 drop；改为 quarantine / reindex queue / not-search-ready 状态 |
| P1-DATA-004 | `apps/api/app/api/rag.py:354` | `/api/v1/rag/query` 返回 legacy `RAGQueryResponse`，未走 shared AnswerContract | claim/review/compare/retrieval 语义和 chat/search evidence 分叉 | 要么接入 `build_answer_contract_payload()`，要么在文档标为 legacy |

### 4.4 Model / Migration / Production Schema

| id | surface | evidence | impact | recommended fix |
|---|---|---|---|---|
| P1-SCHEMA-001 | `apps/api/app/models/paper.py:122` | ORM 使用 lower-case `issearchready`，迁移与 inventory 使用 quoted `"isSearchReady"` | Alembic-created DB 可能读写错列或 readiness 错判 | 对齐 ORM column name 或加 migration 统一列名 |
| P1-SCHEMA-002 | `apps/api/app/models/review_draft.py:22` | `review_drafts` / `review_runs` 只有 non-production create path，无 Alembic migration | 生产环境只跑 Alembic 时会缺表 | 新增正式 migration 和索引 |

### 4.5 Frontend Contract / State / UX

| id | surface | evidence | impact | recommended fix |
|---|---|---|---|---|
| P1-FE-001 | `apps/web/src/services/sseService.ts:540` | `done` event 重建 `doneData` 时丢 `trace_id`, `run_id`, `compare_matrix` | Chat compare matrix、run trace、trace id 在终态丢失 | `onDone` 透传完整 payload，补 regression test |
| P1-FE-002 | `apps/web/src/features/search/components/SearchAuthorPanel.tsx:67` | 作者论文导入只传 `{ source: 's2', externalId }`，import flow 要 `s2PaperId` | 作者弹窗里的 Semantic Scholar 论文导入失败 | 传 `s2PaperId: paper.paperId`，或 import flow 对 `externalId` fallback |
| P1-FE-003 | `apps/web/src/features/kb/components/KnowledgeWorkspaceShell.tsx:58` | KB import polling 漏 `queued`，但后端 initial status 是 `queued` | 导入后 papers/readiness/review/chat ready 不刷新 | `hasRunningJobs` 包含 `queued`，补导入完成路径测试 |
| P1-FE-004 | `apps/web/src/app/components/layout/WorkspaceShell.tsx:23` | 通用 workspace 固定 horizontal `PanelGroup`，Search 另有 `md:min-w-[500px]` | Search / KB / Notes 等三栏工作区窄屏不可用 | 在 `WorkspaceShell` 层做断点切换、drawer 或 column stack |

### 4.6 Governance / Runtime Hygiene

| id | surface | evidence | impact | recommended fix |
|---|---|---|---|---|
| P1-GOV-001 | `.gitignore:128`, `scripts/check-runtime-hygiene.sh:12` | `data/` runtime state 未 ignore，也不在 tracked forbidden prefixes | 本地状态、stream payload、cache 可能误提交 | 明确 ignore `data/`，并把 runtime state 加入 hygiene gate |
| P1-GOV-002 | `architecture.md:11`, `docs/specs/architecture/system-overview.md:11` | `WORKFLOW.md`, `.codex/skills`, `scripts/symphony` 只同步到部分文档 | 编排入口和架构真源形成两套说法 | 明确 Symphony 是否为仓库编排子系统，并同步 architecture / system overview / testing strategy / doc gate |

## 6. P2 Findings

| id | surface | issue | impact | recommended fix |
|---|---|---|---|---|
| P2-CONTRACT-001 | `docs/specs/architecture/api-contract.md:404`, `apps/api/app/api/search/external.py:252`, `apps/web/src/services/searchApi.ts:158` | Semantic Scholar source 在文档为 `semantic_scholar`，后端/前端仍混用 `s2` | filter、cache、stats、import matching 可能分裂 | 选定 canonical 值；如保留 alias，文档和代码同时声明 |
| P2-CONTRACT-002 | `apps/web/src/utils/apiClient.ts:233`, `packages/sdk/src/kb/review.ts:43` | Axios interceptor 只保留 `data`，丢顶层 `meta` | review draft/run 列表 total 退化为当前页长度 | SDK HTTP client 保留 `{ data, meta }` 或 list endpoint 单独适配 |
| P2-CONTRACT-003 | `apps/api/app/api/search/library.py:259` | `/search/unified` 不接收 contract 中的 `source`，response 缺 `meta` 与 canonical fields | SDK/frontend 按文档消费会错 | 补 source/meta/canonical field，或更新文档 |
| P2-CONTRACT-004 | `apps/api/app/api/search/__init__.py:72` | `/search/evidence` 返回 raw object，异常也包装成成功样式 payload | failure semantics 与 API envelope 分叉 | 返回标准 envelope，并用 degraded / error 明确区分 |
| P2-CONTRACT-005 | `apps/api/app/api/papers/paper_status.py:143` | star route 和 batch delete response 与 contract 不一致 | 外部 client 按文档调用会错 | 增加 canonical route 或修正文档；batch delete 返回 per-item trace |
| P2-UX-001 | `apps/web/src/features/search/components/SearchAuthorPanel.tsx:39`, `SearchKnowledgeBaseImportModal.tsx:45` | 自制 fixed modal 缺 focus trap、ESC、`aria-modal` | 键盘/读屏用户在弹窗中容易迷失 | 替换为现有 Radix Dialog 基础组件 |
| P2-TASK-001 | `apps/api/app/workers/pdf_coordinator.py:146` | `delete=False` temp PDF 无 cleanup | repeated task 泄露磁盘文件 | `finally` unlink temp path |
| P2-TASK-002 | `apps/api/app/api/tasks.py:259` | cancel 只是 DB 标记，worker 不 revoke 也不检查 | cancelled task 仍可能写 chunks/vectors 并最终 completed | coordinator 每阶段检查 cancellation，防止 terminal overwrite |
| P2-GOV-001 | `docs/specs/development/testing-strategy.md:121`, `scripts/verify/run-all.sh:15`, `.github/workflows/*` | 本地验证矩阵与 CI workflow 不完全一致，Node 20/22 混用 | 本地 pass 与 CI pass 含义不一致 | 收敛 testing strategy、verify script、CI workflow |

## 7. Fix Order

建议按以下顺序修，不建议先处理视觉或文档小问题：

1. 安全与用户隔离：
   - `chat/cancel`
   - `chat/retry`
   - notes paper ownership
   - evidence source artifact fallback
2. 上传与任务真实排队：
   - local upload missing import
   - chunked upload validation
   - batch import enqueue
   - retry enqueue
   - import job stage sync
3. 向量数据正确性：
   - Milvus insert failure must fail/degrade
   - reindex/delete 清理 Milvus
   - dimension mismatch 不自动 drop collection
4. 前端关键链路：
   - SSE done payload 透传
   - SearchAuthorPanel 传 `s2PaperId`
   - KB polling 包含 `queued`
   - workspace mobile layout
5. Contract consolidation：
   - Semantic Scholar source canonicalization
   - API envelope / meta preservation
   - search unified contract
   - `/rag/query` legacy status
6. Governance：
   - `data/` runtime ignore + hygiene gate
   - Symphony / WORKFLOW 架构真源同步
   - testing matrix 与 CI 收敛

## 8. Suggested Acceptance Gates

每组修复完成后建议至少跑以下门禁：

### Backend security and ownership

```bash
cd apps/api
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q \
  tests/test_notes_api_contract.py \
  tests/unit/test_chat_fast_path.py \
  --maxfail=1 -p no:cacheprovider
```

还需要新增：

1. cross-user `/chat/cancel` negative test
2. cross-user `/chat/retry` negative test
3. notes generate/regenerate/export cross-user negative tests
4. evidence source artifact fallback cross-user negative test

### Upload / import / task reliability

```bash
cd apps/api
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q \
  tests/test_import_processing_state_sync.py \
  tests/test_task_status_transitions.py \
  tests/unit/test_import_pipeline_reliability.py \
  --maxfail=1 -p no:cacheprovider
```

还需要新增：

1. chunked upload non-PDF rejection test
2. batch external import enqueue test
3. retry route enqueue test
4. cancellation mid-pipeline test

### Vector / retrieval correctness

```bash
cd apps/api
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q \
  tests/unit/test_answer_contract.py \
  tests/unit/test_rag_v3_schemas.py \
  --maxfail=1 -p no:cacheprovider
```

还需要新增：

1. all Milvus insert batches fail
2. partial Milvus insert fail
3. reindex removes stale vectors
4. paper deletion removes Milvus content and summaries

### Frontend

```bash
cd apps/web
npm run type-check
npx vitest run --maxWorkers=1 \
  src/services/sseService.test.ts \
  src/features/search/hooks/useSearchImportFlow.test.tsx \
  src/features/kb/components/KnowledgeWorkspaceShell.test.tsx
```

还需要新增：

1. `sseService` done payload preserves `trace_id`, `run_id`, `compare_matrix`
2. author panel import sends `s2PaperId`
3. KB `queued` job keeps polling
4. mobile workspace layout visual/browser check

### Governance

```bash
bash scripts/check-runtime-hygiene.sh tracked
bash scripts/check-doc-governance.sh
bash scripts/check-structure-boundaries.sh
bash scripts/check-code-boundaries.sh
bash scripts/check-governance.sh
```

如果修 runtime ignore，应增加 strict 或 equivalent check，确保 `data/` 不再成为可提交状态文件。

## 8. Residual Risk

本次审查未覆盖：

1. 没有启动 Postgres / Redis / Milvus / Celery 做真实 broker 与 vector integration。
2. 没有做 Chrome DevTools MCP 或 Computer Use 真实浏览器 walkthrough。
3. 没有跑全量 Vitest、全量 pytest、E2E。
4. 没有联网确认 GitHub CI 最近状态。
5. 没有读取 `data/*.bin` 等本地状态内容，以避免不必要地触碰本地隐私或 runtime payload。

因此，本报告中的静态 findings 需要通过 focused unit tests 先固化，再用一次受控 integration run 验证。

## 9. Multidimensional Report Review

本节是对本报告本身的审核，不是对代码的新一轮修复。

| dimension | verdict | notes |
|---|---|---|
| phase alignment | pass | 报告落在 `docs/plans/v4_5/reports/`，没有继续使用旧报告路径 |
| source coverage | pass | 覆盖 frontend、backend API/service、backend data/reliability、cross-layer governance 四条线 |
| severity calibration | pass | 未把无 live proof 的问题升级为 P0；P1 主要给安全、数据正确性、任务真实完成、用户可见断链 |
| evidence quality | pass | 每个 P1/P2 均包含文件路径、证据、影响、修复方向 |
| actionability | pass | 第 6 节给出修复顺序，第 7 节给出验收命令和需要新增的测试 |
| release honesty | pass | 明确本报告不代表 release-candidate / release-pass |
| known gaps | pass | 第 8 节列出未跑 live service、浏览器 walkthrough、全量测试和 CI 的风险 |
| duplication control | pass | 合并了重复的 Semantic Scholar source、search contract、runtime hygiene 问题 |

自审结论：报告可以作为 v4.5 当前修复 backlog 的输入，但还不能作为 closeout 报告。下一步应从第 6 节第 1-2 组 P1 开始落修复与回归测试。
