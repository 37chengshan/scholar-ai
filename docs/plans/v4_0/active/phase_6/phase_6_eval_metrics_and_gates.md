---
owner: ai-runtime
status: asset-ready
depends_on:
  - 2026-05-11_v4_0_phase_6_academic_rag_optimization_research
  - 24_v4_0_phase_6_execution_plan
last_verified_at: 2026-05-12
evidence_commits:
  - working-tree-v4-0-phase-6-doc-restore
---

# v4.0 Phase 6 Eval Metrics And Gates

## 1. 目的

本文件定义 Phase 6 应如何为 Phase 7 gate 交付可评测、可对比、可阻断的优化证据。

## 2. Phase 6 不直接签发 release verdict

Phase 6 的职责是：

1. 形成更好的 evidence / correction / verification 行为
2. 给出可对比的 baseline / candidate 证据
3. 为 Phase 7 的 verdict 提供输入

Phase 6 不应直接把任何优化写成 release-pass。

## 3. 最低评测维度

### 3.1 Retrieval

至少跟踪：

1. recall@5
2. recall@10
3. MRR
4. section hit rate
5. paper hit rate
6. second-pass gain

### 3.2 Truthfulness

至少跟踪：

1. unsupported claim rate
2. supported claim count
3. citation coverage
4. citation faithfulness

### 3.3 Runtime

至少跟踪：

1. p50 latency
2. p95 latency
3. degraded rate
4. silent fallback count
5. cost estimate

### 3.4 Workflow

至少跟踪：

1. Chat 路径成功率
2. Compare 路径成功率
3. Review 路径成功率
4. recovery action 暴露率

## 4. 必需产物

每轮 Phase 6 优化至少要能产出：

1. baseline result
2. candidate result
3. diff summary
4. failure bucket summary
5. markdown 说明或等效执行记录

## 5. 建议命令锚点

当前仓库已有的评测锚点：

1. `python scripts/eval_retrieval.py --golden tests/evals/golden_queries.json`
2. `python scripts/eval_answer.py --golden tests/evals/golden_queries.json`
3. `python scripts/check-benchmark-thresholds.py`

如果某轮优化没有至少回到上述锚点之一，就不能被写成“已有评测证据”。

## 6. Gate 规则

1. 必须能区分 baseline 与 candidate
2. 必须能给出 diff，而不是只给单次结果
3. 必须明确哪些收益只存在于 review-only graph path
4. 必须明确哪些收益来自 corrective retrieval，而不是 prompt 偶然性

## 7. 明确禁止

1. 只用人工观察替代 baseline/candidate/diff
2. 只展示成功样例，不给 failure bucket
3. 把 review-only 实验收益写成全链收益
4. 用线上感觉替代 Phase 7 verdict

## 8. 结论

Phase 6 的评测目标是“把优化变成可比较输入”，不是提前代替 Phase 7 做最终放行。