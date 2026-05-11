---
owner: ai-runtime
status: research
depends_on:
  - 18_v4_0_overview_plan
last_verified_at: 2026-05-11
evidence_commits:
  - working-tree-v4-0-phase-6-research
---

# v4.0 Phase 4.0-6 研究文档：Academic RAG Optimization

> 日期：2026-05-11  
> 状态：research  
> 对应执行计划：`docs/plans/v4_0/active/phase_6/24_v4_0_phase_6_execution_plan.md`  
> 上游总览：`docs/plans/v4_0/active/overview/18_v4_0_overview_plan.md`

## 1. 研究问题

Phase 4.0-6 的目标不是替换 ScholarAI 当前主链，而是在稳定的 academic RAG kernel 之上增加可解释、可纠偏、可回滚、可评测的优化层。

本阶段优先级冻结为：

1. 统一 evidence action contract。
2. 让 corrective retrieval 变成显式可观测动作。
3. 把 claim repair 从报告字段升级为可执行恢复语义。
4. graph/global synthesis 只允许保留为 review-only experiment。

## 2. 研究结论

Phase 6 的总策略冻结为：

```txt
mainline: extend
review branch: experiment
evaluation layer: adopt
second runtime: reject
```

这意味着本轮执行优先做：

1. `evidence action contract`
2. `claim repair + recovery action semantics`
3. `retrieval correction surfacing`

而不是：

1. 引第二套 runtime
2. 默认 GraphRAG 主链
3. 直接做 full-stack RAPTOR / STORM / LangGraph 迁移
