---
owner: product-engineering
status: review-ready
last_verified_at: 2026-05-27
scope:
  - apps/api/app/rag_v3
  - apps/api/tests/unit
  - apps/api/tests/e2e
  - docs/plans/v4_5/reports
---

# 2026-05-27 v4.5 RAG Drift Recheck

## 1. Executive Verdict

本次复核结论：

1. `2026-05-13_v4_5_full_rag_chain_state_report.md` 中列为 `current_contract_or_behavior_drift` 的 4 个红点，按当前代码和当前测试已不再成立。
2. 当前更准确的表述应当是：这 4 个点已经完成收口，其中至少 1 个点在 2026-05-13 之后被测试重写为 current-contract coverage，不应继续被归类为“真实 drift”。
3. 这不等于 v4.5 已经 `release-pass`；它只表示旧报告中“优先调查的 4 个真实差异”这条结论已经过期。

## 2. Recheck Scope

本轮只针对 2026-05-13 报告第 6.4 节列出的 4 个点做重新验证：

1. `tests/unit/test_citation_verifier.py::test_prune_unsupported_claims_appends_notice_when_support_low`
2. `tests/unit/test_rag_v3_schemas.py::test_retrieve_evidence_contract`
3. `tests/unit/test_rag_v3_schemas.py::test_evidence_quality_and_answer_policy`
4. `tests/e2e/test_graph_e2e.py::test_pagerank_calculation_e2e`

## 3. Verification Performed

执行命令：

```bash
cd apps/api
PYTHONPATH=$PWD .venv/bin/python -m pytest -q \
  tests/unit/test_citation_verifier.py::test_prune_unsupported_claims_appends_notice_when_support_low \
  tests/unit/test_rag_v3_schemas.py::test_retrieve_evidence_contract \
  tests/unit/test_rag_v3_schemas.py::test_evidence_quality_and_answer_policy \
  tests/e2e/test_graph_e2e.py::test_pagerank_calculation_e2e \
  -rs
```

结果：

1. `4 passed`
2. 无 skip
3. 无失败

补充验证：

```bash
cd apps/api
PYTHONPATH=$PWD .venv/bin/python -m pytest -q \
  tests/unit/test_hierarchical_retriever_routing.py \
  tests/unit/test_rag_v3_schemas.py \
  --maxfail=1
```

结果：

1. `5 passed`

## 4. Red-Point Reclassification

| item from 2026-05-13 report | old reading | current evidence | updated reading |
|---|---|---|---|
| `test_prune_unsupported_claims_appends_notice_when_support_low` | verifier 输出 contract 仍有真实差异 | 2026-05-27 复跑通过 | 已收口，不再属于 current drift |
| `test_retrieve_evidence_contract` | live retrieval 返回 `0` candidates，测试期待 `10` | 当前测试已改为 deterministic current-contract coverage，2026-05-27 复跑通过 | 旧失败根因是 stale helper/test path，不再属于 current drift |
| `test_evidence_quality_and_answer_policy` | `answer_mode` 与预期存在真实差异 | 2026-05-27 复跑通过 | 已收口，不再属于 current drift |
| `test_pagerank_calculation_e2e` | graph pagerank 与 fixture 断言不一致 | 2026-05-27 复跑通过 | 已收口，不再属于 current drift |

## 5. What Actually Changed Since 2026-05-13

对照当前代码，最关键的变化有两类：

1. `apps/api/tests/unit/test_rag_v3_schemas.py` 已从依赖默认 disabled retriever 的 live-Milvus 假设，改为直接验证 `HierarchicalRetriever` 的 current contract。
2. 先前被标为“真实 drift”的其余 3 个点，在当前测试树和当前实现下已经能稳定通过，说明 2026-05-13 报告中的结论具有时间性，不应再作为当前状态引用。

## 6. Current Implication

截至 2026-05-27，可以更准确地写成：

```txt
the previously flagged 4 current drift points have been rechecked and are no longer red in the current tree
```

当前仍然不能直接写成：

1. `release-pass`
2. `full rag automation green`
3. `all historical rag tests are aligned with current architecture`

## 7. Next Actions

1. 在后续状态报告中，不再把这 4 个点计入 `current_contract_or_behavior_drift`。
2. 若需要继续提高 v4.5 RAG 可信度，下一优先级应回到旧报告里已明确的 `legacy_test_debt` 与 `legacy_route_contract_debt`。
3. 如需保留 2026-05-13 历史报告原文，建议把本文件作为后续勘误/补充结论，而不是重写历史时间点上的原始报告。
