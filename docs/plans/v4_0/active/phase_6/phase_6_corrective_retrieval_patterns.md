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

# v4.0 Phase 6 Corrective Retrieval Patterns

## 1. 目的

本文件把 corrective retrieval 从“临场补救”收口成受控模式，确保每一次纠偏都有触发条件、预算和停止规则。

## 2. 可用模式

| pattern | trigger | allowed scope | stop rule |
|---|---|---|---|
| query rewrite | query 过宽、歧义或目标不清 | chat / compare / review | 最多一次 rewrite |
| focused retry | 第一轮 evidence 命中错层级或错 section | long paper / numeric / figure / table | 最多一次额外 retrieval round |
| scope expansion | compare / survey 证据覆盖面不足 | compare / cross_paper / related_work | 只能扩一次 scope |
| claim repair retrieval | claim 已抽取但支持不足 | chat / compare / review | claim repair 失败后必须 partial 或 abstain |
| review-only graph expansion | 综述类全局主题不足 | review / survey / related_work | graph 不可用则明确 fallback local-only |

## 3. 默认预算

Phase 6 的 corrective retrieval 默认预算：

1. 每次请求最多一轮额外 corrective retrieval
2. 每次请求最多一次 query rewrite
3. 每个 claim 最多一次 repair retrieval
4. graph/global synthesis 只允许作为 review 支线实验，不可叠加多轮

## 4. 触发优先级

建议顺序：

1. 先判断 evidence 是否真的弱
2. 再选择最小 corrective action
3. 若 corrective 失败，尽快转 partial / abstain

不允许的顺序：

1. 先无限重试，再考虑降级
2. 先走 graph，再回头找局部证据
3. 先生成完整答案，再事后修补 claim

## 5. 与 claim verification 的关系

corrective retrieval 不是独立子系统，它必须与 claim verification 串联：

1. retrieval 不足 -> corrective retrieval
2. claim 支撑不足 -> claim repair retrieval
3. 仍不足 -> partial 或 abstain

## 6. 风险控制

| risk | control |
|---|---|
| latency 激增 | 单次额外 corrective round 上限 |
| cost 失控 | 不允许多轮级联重试 |
| 行为不可解释 | 每次 corrective 都写入 trace 与 recovery action |
| graph 路线越界 | 限定 review / survey / related_work |

## 7. 结论

Phase 6 的 corrective retrieval 只做两件事：少量、明确、可回滚的纠偏；以及把“为什么还不够”转成显式恢复动作。