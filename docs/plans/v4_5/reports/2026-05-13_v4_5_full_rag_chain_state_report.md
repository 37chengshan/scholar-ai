---
owner: product-engineering
status: done
last_verified_at: 2026-05-13
depends_on:
  - 26_v4_5_phase_0_execution_plan
  - 24_v4_0_phase_6_execution_plan
  - 22_v4_0_phase_3_execution_plan
evidence_commits:
  - working-tree-v4-5-rag-chain-audit
  - working-tree-v4-5-full-rag-sweep
  - working-tree-v4-5-rag-sweep-remediation
---

# 2026-05-13 v4.5 Full RAG Chain State Report

## 1. Completion Audit

本轮按用户目标做完成审计，不再把 earlier focused suite 当成“全量 RAG 已验证”。

目标拆解为 4 个可核对交付物：

| requirement | evidence | status |
|---|---|---|
| 深度研究当前 RAG 整体链路 | 本报告第 3-8 节的 surface map、live benchmark、full sweep、风险分类 | complete |
| 跑全量 RAG 测试，不是小测试 | `apps/api/artifacts/validation-results/v4_5/full_rag_sweep/2026-05-13T23-10-00Z/`，`669` 项 sweep | complete |
| 覆盖所有已实现的 RAG 功能面 | 第 3 节按 canonical surface 列出 chat/search/query/compare/KB/review/graph/evidence/stream 覆盖状态 | complete with explicit uncovered live gaps |
| 多维度报告现状 | 第 4-8 节给出 runtime、contract、automation debt、dependency drift、release verdict | complete |

这里的 `complete` 仅表示“研究与审计交付物完成”，不表示 release pass。

## 2. Artifacts

本轮新增或更新的 machine-readable artifacts：

1. live benchmark
   - `artifacts/validation-results/v4_5/live_rag_benchmark/2026-05-13T23-00-53Z/summary.json`
   - `artifacts/validation-results/v4_5/live_rag_benchmark/2026-05-13T23-00-53Z/summary.md`
   - `artifacts/validation-results/v4_5/live_rag_benchmark/2026-05-13T23-00-53Z/backend.log`
   - `artifacts/validation-results/v4_5/live_rag_benchmark/2026-05-13T23-40-34Z/summary.json`
   - `artifacts/validation-results/v4_5/live_rag_benchmark/2026-05-13T23-40-34Z/summary.md`
   - `artifacts/validation-results/v4_5/live_rag_benchmark/2026-05-13T23-40-34Z/backend.log`
2. full RAG sweep
   - `apps/api/artifacts/validation-results/v4_5/full_rag_sweep/2026-05-13T23-10-00Z/junit.xml`
   - `apps/api/artifacts/validation-results/v4_5/full_rag_sweep/2026-05-13T23-10-00Z/pytest.log`
   - `apps/api/artifacts/validation-results/v4_5/full_rag_sweep/2026-05-13T23-10-00Z/summary.json`
   - `apps/api/artifacts/validation-results/v4_5/full_rag_sweep/2026-05-13T23-10-00Z/summary.md`
   - `apps/api/artifacts/validation-results/v4_5/full_rag_sweep/2026-05-13T23-10-00Z/exit_code.txt`
   - `apps/api/artifacts/validation-results/v4_5/full_rag_sweep/2026-05-13T15-36-54Z/junit.xml`
   - `apps/api/artifacts/validation-results/v4_5/full_rag_sweep/2026-05-13T15-36-54Z/pytest.log`
   - `apps/api/artifacts/validation-results/v4_5/full_rag_sweep/2026-05-13T15-36-54Z/summary.json`
   - `apps/api/artifacts/validation-results/v4_5/full_rag_sweep/2026-05-13T15-36-54Z/summary.md`
   - `apps/api/artifacts/validation-results/v4_5/full_rag_sweep/2026-05-13T15-36-54Z/exit_code.txt`

本轮实际执行的核心命令：

```bash
python3 scripts/evals/run_v4_5_live_rag_benchmark.py --launch-backend
cd apps/api
PYTHONPATH=$PWD .venv/bin/pytest -q <669-item rag sweep>
```

## 3. Canonical RAG Surface Map

以下矩阵只看当前仓库的 canonical surface，不再把旧 `/rag/*`、旧 `/search/*`、旧 `read_url` 视为主链真源。

| surface | canonical route or module | live evidence | broad sweep evidence | current reading |
|---|---|---|---|---|
| single-paper chat | `POST /api/v1/chat` | pass | pass | 当前主链可用 |
| chat stream | `POST /api/v1/chat/stream` | no live probe | pass | 单测稳定，未纳入 live sweep |
| evidence search | `POST /api/v1/search/evidence` | pass | pass | paper / KB scope 都已闭环 |
| multimodal search | `POST /api/v1/search/multimodal` | no live probe | partial | 旧测试仍打错路径与响应形态 |
| blocking query | `POST /api/v1/queries/query` | pass | mixed | 旧 `/rag/query` 测试大量过时 |
| query stream | `POST /api/v1/queries/stream` | no live probe | pass | 当前以自动化为主 |
| compare | `POST /api/v1/compare/v4` | pass | pass | honesty fields 与 matrix contract 已验证 |
| KB query | `POST /api/v1/knowledge-bases/{kb_id}/query` | pass | pass | primary KB membership 可运行 |
| evidence source | `GET /api/v1/evidence/source/{source_chunk_id}` | no live probe | partial | 旧测试仍追 `read_url` |
| review draft service | `ReviewDraftService` | no live mutate probe | pass | service-level coverage 足够，route-level live 仍缺 |
| review draft routes | `review-drafts` / `runs` APIs | no live mutate probe | partial | 以 service-level unit 为主 |
| graph retrieval | `GraphRetrievalService` + graph flows | no dedicated live probe | mixed | integration pass，但 graph e2e 仍有红点 |

## 4. Live Benchmark Truth

首次 live benchmark 结果：

1. `passed = 7`
2. `failed = 0`
3. `blocked = 0`
4. `success_rate = 1.0`
5. `p95_latency_ms = 10076.61`

修复与测试树收敛后的复跑结果：

1. `passed = 7`
2. `failed = 0`
3. `blocked = 0`
4. `success_rate = 1.0`
5. `p95_latency_ms = 28016.6`

case 结果：

| case | result | key signal |
|---|---|---|
| `single-paper-chat` | pass | 命中目标 `paper_id` |
| `single-paper-evidence` | pass | 返回 evidence rows |
| `multi-paper-compare` | pass | compare-style blocking route 可运行 |
| `compare-v4-contract` | pass | `response_type=compare` 且 compare matrix 可消费 |
| `kb-scoped-chat` | pass | 命中 KB 内论文 |
| `kb-scoped-evidence` | pass | KB 内 evidence 返回正常 |
| `kb-query` | pass | answer + citations 命中 KB 内论文 |

这说明当前 phase4.5 canonical backend main path 仍是可运行的。

## 5. Full RAG Sweep Truth

相比 earlier `77 + 10` focused suites，本轮 broad sweep 把 unit / integration / e2e / root-level RAG tests 一起拉进来。

初次 broad sweep 结果：

1. `collected = 669`
2. `passed = 609`
3. `failed = 55`
4. `errors = 2`
5. `skipped = 3`
6. `pass_rate_collected = 91.03%`
7. `pass_rate_executed = 91.44%`
8. `duration = 128.06s`

含义：

1. 当前仓库的“RAG 自动化版图”远大于 earlier focused suite。
2. canonical main path live benchmark 通过，并不等于整个 RAG automation tree 已经健康。
3. 红点的主要来源不是 single-paper / compare / KB main path 本身，而是遗留测试债、旧契约、旧模块假设与环境依赖漂移。

在本轮修复 `memory_search`、`page_clustering`、`multimodal/rag canonical route tests`、`citation verifier`、`rag_v3_schemas`、`deprecated rag-service compatibility tests` 之后，按同一批 RAG 测试文件复跑的结果是：

1. `collected = 666`
2. `passed = 632`
3. `failed = 31`
4. `errors = 0`
5. `skipped = 3`
6. `pass_rate_collected = 94.89%`
7. `pass_rate_executed = 95.32%`

这说明本轮不是只把 focused suite 跑绿，而是实质性削减了历史测试树的红点数量，尤其清掉了第一批 canonical route / old patch target / response envelope 漂移。

## 6. Failure Classification

以下分类来自 `summary.json` 的 heuristic grouping，目的是把“产品回归”与“测试债”分开看。

| category | count | interpretation |
|---|---:|---|
| `legacy_test_debt` | 32 | 测试仍 patch 已移除符号或追旧实现路径 |
| `legacy_route_contract_debt` | 13 | 测试仍请求旧路由或旧 request/response contract |
| `runtime_dependency_or_fixture_drift` | 8 | runtime backend、optional deps、fixture 假设与当前环境不一致 |
| `current_contract_or_behavior_drift` | 4 | 需要继续审视的真实行为/契约差异 |

### 6.1 Legacy Test Debt

代表样本：

1. `tests/unit/test_citation_source_endpoint.py`
   - 仍要求 `read_url`，而 canonical field 已切换到 `citation_jump_url`
2. `tests/unit/test_memory_search.py`
   - 仍 patch `get_db_connection`，而实现已改为 SQLAlchemy `AsyncSessionLocal`
3. `tests/unit/test_page_clustering.py`
   - 仍假设同步函数和 `get_bge_m3_service` patch target；当前 `cluster_pages(...)` 已是 async 并走 unified embedding factory
4. `tests/test_comparison.py` / `tests/test_evolution_timeline.py`
   - 仍 patch `app.api.compare.get_db_connection` / `litellm`，与当前 compare 模块真实依赖不符
5. `tests/test_rag_service_reranking.py`
   - 仍要求 `app.core.rag_service` 与 legacy reranking contract

结论：这批红点主要是 test debt，不足以单独证明 canonical phase4.5 main path 坏掉。

### 6.2 Legacy Route / Contract Debt

代表样本：

1. `tests/integration/test_multimodal_search_api.py`
   - 全部请求 `/search/multimodal`
   - 当前 canonical route 是 `/api/v1/search/multimodal`
   - 当前响应是 `success + data` envelope，不是裸 payload
2. `tests/integration/test_rag_api_unified.py`
   - 仍请求旧 `/rag/query`
   - 仍要求 request 中显式 `user_id`
   - 当前 canonical route 是 `/api/v1/queries/query`，用户身份走 auth dependency
3. `tests/e2e/test_rag_citations.py::test_rag_query_response_structure`
4. `tests/e2e/test_rag_streaming.py::test_rag_stream_endpoint_returns_sse`
5. `tests/test_rag.py::test_rag_query_endpoint`

结论：这 13 个红点主要是旧 surface 仍留在测试树里，说明 test tree 尚未跟 canonical `/api/v1/*` 统一。

### 6.3 Runtime / Dependency / Fixture Drift

代表样本：

1. `tests/integration/test_multimodal_search_enhanced.py`
   - scientific text branch 实际触发 `specter2` import 路径，当前环境报 `BERT_INPUTS_DOCSTRING` 相关失败
2. `tests/integration/test_qdrant_search.py`
   - 当前 settings 不含 `QDRANT_LOCAL_PATH`
3. `tests/test_rag.py::TestPaperQA2Integration::test_paperqa_settings`
   - 缺 `paper-qa` PDF parser extra
4. `tests/test_rag_integration.py`
   - 仍假设固定 `1024-dim BGE` 路径与旧 `app.core.embedding_service`
5. `tests/test_rag_service.py::test_retrieve_uses_1024_dim_embedding`
   - 仍追旧 embedding call path

结论：这批更多是 runtime stack 与 historical fixture 假设漂移，不是 phase4.5 KB/chat/search wiring 本轮刚引入的问题。

### 6.4 Current Contract / Behavior Drift

这 4 个最值得继续追：

1. `tests/unit/test_citation_verifier.py`
   - `support_score` 缺失，说明 verifier 输出 contract 与测试预期仍有真实差异
2. `tests/unit/test_rag_v3_schemas.py::test_retrieve_evidence_contract`
   - live Milvus retrieval contract 返回 `0` candidates，而测试期待 `10`
3. `tests/unit/test_rag_v3_schemas.py::test_evidence_quality_and_answer_policy`
   - `answer_mode` 当前是 `abstain`，测试预期 `partial`
4. `tests/e2e/test_graph_e2e.py::test_pagerank_calculation_e2e`
   - graph pagerank 结果与 fixture 断言不一致

这 4 个不能直接归入“纯旧测试债”，后续若要继续提高 phase4.5 可信度，应优先处理。

## 7. Multi-Dimensional Current State

### 7.1 Main Path Truth

1. canonical phase4.5 backend main path 仍然能跑通。
2. single-paper / compare / KB scope 的 route truth 已被 live evidence 证明。
3. `knowledge_base_id` 已真正下推为 retrieval `paper_scope`，不再只是 diagnostics metadata。

### 7.2 Automation Truth

1. earlier focused suites 只覆盖了“当前修复附近”的主链。
2. broad sweep 证明仓库里仍存在大量 historical RAG tests 与当前 canonical architecture 脱节。
3. 因此“main path 可运行”与“RAG automation tree 干净”是两个不同结论。

### 7.3 Runtime Truth

1. `/health/live` 与 `/health/ready` 在 live benchmark 中通过。
2. embedding / reranker / Milvus 在 benchmark run 中均显示 `available`。
3. compare v4 仍会诚实返回退化信号，不应被误写成 full-success only。

### 7.4 Contract Truth

1. `api-contract.md` 与 `resources.md` 已同步到 current KB scope truth、blocking chat、search/evidence request shape、compare honesty 字段。
2. broad sweep 同时暴露出测试树仍有大量旧 `/rag/*`、旧 `/search/*`、旧 `read_url`、旧 `get_db_connection` 假设。

### 7.5 Live Coverage Gaps

当前仍未纳入 dedicated live probe 的 canonical surface：

1. `POST /api/v1/chat/stream`
2. `POST /api/v1/queries/stream`
3. `POST /api/v1/search/multimodal`
4. `GET /api/v1/evidence/source/{source_chunk_id}`
5. review draft 的 create / retry / repair mutation routes

这不影响本次“现状研究”交付，但意味着 release verdict 仍不能只靠本报告给出。

## 8. Final Reading

当前可以诚实写成：

```txt
v4.5 rag current-state audit
=
canonical backend main path live-passing
+ broad rag sweep landed and remediated
+ 632 tests passing in current comparable sweep
- 31 red points remain in current comparable sweep
- canonical live benchmark remains 7/7 pass
- remaining red points are now concentrated in older comparison/evolution/rag-integration/runtime-fixture debt
- release verdict still not granted
```

当前不能写成：

1. `release-pass`
2. `full rag automation green`
3. `all historical rag tests are aligned with current architecture`
4. `review-draft route live walkthrough complete`

## 9. Next Actions

1. 先清理 `legacy_test_debt + legacy_route_contract_debt`，恢复测试树的信号质量。
2. 为 `chat/stream`、`queries/stream`、`search/multimodal`、`evidence/source` 增加 canonical live probes。
3. 优先调查 4 个 `current_contract_or_behavior_drift` 红点。
4. 把 `knowledge_base_papers` 与 `Paper.knowledge_base_id` 的双真相继续收口成单一真源。
