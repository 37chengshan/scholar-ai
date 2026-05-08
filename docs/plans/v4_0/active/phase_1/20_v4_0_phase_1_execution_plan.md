---
owner: product-engineering
status: done
depends_on:
  - 19_v4_0_phase_0_execution_plan
  - 18_v4_0_overview_plan
last_verified_at: 2026-05-02
evidence_commits:
  - historical-v4-0-phase-1-workflow-closeout
---

# 20 v4.0-1 执行计划：Productized Research Workflow

> 日期：2026-05-02  
> 状态：execution-plan  
> 上游研究：`docs/plans/v4_0/active/phase_1/2026-05-02_v4_0_phase_1_research.md`  
> 上游 gate：`docs/plans/v4_0/reports/2026-05-02_v4_0_phase_0_closeout_report.md`

## 0. 执行状态

Phase 4.0-1 本轮已完成第一批 workflow continuity closeout。它仍不等于 Beta-ready 或 full-chain release-pass，但已经完成 durable cross-page context、command-center 接线与 workflow shell continuity 的首批实现。

## 1. 目标

Phase 4.0-1 的目标是把现有页面主链升级为可连续使用的研究工作流：

```txt
workflow truth
-> durable cross-page context
-> command-center dashboard
-> status semantics unification
-> chat-centered execution continuity
```

本阶段不新增平行工作台，不重做信息架构，不做 Beta 材料制作。

## 2. 执行前先读什么

1. `docs/plans/v4_0/active/overview/18_v4_0_overview_plan.md`
2. `docs/plans/v4_0/reports/2026-05-02_v4_0_phase_0_closeout_report.md`
3. `docs/plans/v4_0/active/phase_1/2026-05-02_v4_0_phase_1_research.md`
4. `docs/specs/design/frontend/DESIGN_SYSTEM.md`
5. `docs/specs/architecture/api-contract.md`
6. `apps/web/src/features/workflow/types.ts`
7. `apps/web/src/features/workflow/hooks/useWorkflowHydration.ts`
8. `apps/web/src/features/workflow/commandCenter.ts`
9. `apps/web/src/features/chat/chatHandoff.ts`
10. `apps/web/src/features/chat/hooks/useChatHandoff.ts`
11. `apps/web/src/features/search/components/SearchWorkspace.tsx`
12. `apps/web/src/features/kb/components/KnowledgeWorkspaceShell.tsx`

## 3. 当前可直接消费的真实能力

| area | current state | conclusion |
|---|---|---|
| workflow types/store | 已存在 `WorkflowScope / WorkflowRun / WorkflowArtifact / timeline` | 可作为 workflow truth 第一版骨架 |
| workflow hydration | 已能从 pathname / chat scope / active run 生成视图模型 | 可先复用，但需要从“推导视图”升级到“共享上下文” |
| Dashboard command center | 已存在 `ResearchCommandItem` 与 readiness item 构建逻辑 | 可承接 command center，不必另造新模型 |
| Search handoff | 已支持 `Continue in Chat` 与 prefill-only | 可作为第一条连续链落地 |
| KB readiness | 已有 readiness 卡片、runs、review、chat 入口 | 可作为第二条连续链落地 |
| Review handoff | 已支持 `Continue in Chat` | 可作为第三条连续链落地 |

## 4. Work Packages

## WP1：Workflow Context Freeze

目标：

1. 冻结 workflow context 的前端真源结构。
2. 明确 scope、run、next actions、recoverable tasks、artifacts、timeline 的最小字段。

输出：

1. workflow context 字段清单
2. 页面间共享规则
3. durable handoff 最小要求

验收：

1. 不再靠各页面自定义状态名称表达同一类 workflow 状态。
2. `Dashboard / Search / KB / Chat / Review` 对 workflow context 的消费关系清楚。

## WP2：Durable Handoff Contract

目标：

1. 把 `navigateToChatWithHandoff(...)` 从单次导航技巧升级为可恢复 contract。
2. 保证 scope、prompt draft、returnTo、evidence refs 具备 durable 恢复路径。

输出：

1. handoff contract 冻结
2. Search / KB / Review 三条 handoff 路径的统一消费规则
3. 刷新或跨页恢复策略

验收：

1. Chat 仍然只预填，不自动发送。
2. 跨页 handoff 不再只依赖一次性 `location.state` 才成立。

## WP3：Command Center Productization

目标：

1. 把 Dashboard 收口为真实 command center。
2. 让 Dashboard 只展示 “当前 scope / 阻塞 / 下一步 / 去哪恢复”。

输出：

1. research command priority 规则
2. blocked / active / ready / recent 的口径冻结
3. Dashboard 消费 workflow truth 的接线顺序

验收：

1. Dashboard 不执行任务。
2. Dashboard 给出的跳转与各页真实状态一致。

## WP4：Cross-page Status Semantics

目标：

1. 统一 `importing / evidence-ready / review-partial / blocked / recoverable` 口径。
2. 让 Search、KB、Read、Chat、Review 共享状态语义。

输出：

1. 状态语义表
2. 页面映射表
3. 非 happy-path 状态清单

验收：

1. 同一状态不再在不同页面用相互冲突的说法。
2. `partial / insufficient_evidence` 不得在任一页面被误表述成成功完成。

## WP5：Workflow Artifact and Return Path

目标：

1. 让 import job、run、review draft、chat session、evidence artifact 进入统一 workflow 引用关系。
2. 明确 return path 与 resume path。

输出：

1. artifact/ref mapping
2. return path 约束
3. recoverable task 约束

验收：

1. 用户可以从 Chat 回到来源页。
2. 来源页能理解这个 handoff 或 run 为什么存在。

## WP6：Phase 4.0-2 / 4.0-3 Readiness Handoff

目标：

1. 给 Beta Release Hardening 和 Citation-backed Review Artifacts 提供稳定底座。
2. 明确哪些能力在本阶段完成后，后续 phase 才允许承接。

输出：

1. 给 `Phase 4.0-2` 的 workflow 前置条件
2. 给 `Phase 4.0-3` 的 artifact continuity 前置条件

验收：

1. `Phase 4.0-2` 不再需要自己定义 workflow 真源。
2. `Phase 4.0-3` 不再需要自己补跨页 continuity。

## 5. 当前执行顺序

1. 完成 WP1：workflow context freeze。
2. 完成 WP2：durable handoff contract。
3. 完成 WP3：Dashboard command center productization。
4. 完成 WP4：cross-page status semantics。
5. 完成 WP5：workflow artifact / return path。
6. 完成 WP6：向 4.0-2 / 4.0-3 交接 readiness。

## 6. 边界

1. 不实现 Beta quickstart / demo dataset / walkthrough script。
2. 不重做 Search、KB、Chat、Review 的 IA。
3. 不扩大 compare 功能面。
4. 不做视觉主打磨。
5. 不做 RAG 路由、模型或 Graph 类优化。

## 7. 最小验证

文档与治理：

```bash
bash scripts/check-doc-governance.sh
bash scripts/check-plan-governance.sh
bash scripts/check-phase-tracking.sh
bash scripts/check-governance.sh
```

实现落地后必须补跑的前端验证：

```bash
cd apps/web && npm run type-check
cd apps/web && npm run test:run -- ChatWorkspaceV2 SearchWorkspace KnowledgeWorkspaceShell useChatHandoff useWorkflowHydration
```

如涉及 Chat / workflow contract 变更，必须同时复核：

1. `docs/specs/architecture/api-contract.md`
2. `docs/specs/design/frontend/DESIGN_SYSTEM.md`

## 8. 完成定义

Phase 4.0-1 完成时，至少满足：

1. workflow context 有共享真源，不再只是页面推导视图。
2. Search / KB / Review -> Chat handoff 连续性稳定。
3. Dashboard 真正只做 command center，并消费 workflow truth。
4. `partial / insufficient_evidence`、recoverable、blocked 等状态被统一表达。
5. Phase 4.0-2 与 Phase 4.0-3 可直接消费 workflow 底座，而不必重做它。

## 9. Open Questions

1. workflow truth 何时从前端 canonical store 升级为后端资源真源。
2. Dashboard 第二批是否扩到 `Read / Notes / Compare` 深度命令矩阵。
3. return path 与 recoverable task 是否在更多页面露出显式 CTA。
