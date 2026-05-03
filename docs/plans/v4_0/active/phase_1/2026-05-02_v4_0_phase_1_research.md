# v4.0-1 研究文档：Productized Research Workflow

> 日期：2026-05-02  
> 状态：research  
> 对应执行计划：`docs/plans/v4_0/active/phase_1/20_v4_0_phase_1_execution_plan.md`  
> 上游总览：`docs/plans/v4_0/active/overview/18_v4_0_overview_plan.md`  
> 上游 gate：`docs/plans/v4_0/reports/2026-05-02_v4_0_phase_0_closeout_report.md`

## 1. 研究问题

Phase 4.0-1 的目标不是新增功能页，而是把当前 ScholarAI 已有的主链页面收口为一个连续研究工作流。

本阶段要回答四个问题：

1. 当前真实代码里，哪些 workflow 能力已经存在，可以直接承接。
2. 当前 workflow 最大断点在哪里，为什么用户仍像在操作“页面集合”而不是“连续研究流程”。
3. 在不重做信息架构、不中断现有主链的前提下，最小可执行的 workflow 产品化应该落在哪些边界。
4. 哪些内容属于 Beta、前端精修、RAG 优化或测试 gate，不能混入本阶段。

## 2. 当前实现基线

### 2.1 设计与产品边界已冻结

根据 `docs/specs/design/frontend/DESIGN_SYSTEM.md`，当前已明确：

1. `Dashboard` 只做 command center，不承载功能执行。
2. `Search` 的主动作应收口为 `Open Read`、`Add to KB`、`Continue in Chat`。
3. `KnowledgeWorkspaceShell` 必须展示 readiness 摘要，从导入到 evidence ready 再到 Chat / Review ready。
4. `Chat` 是唯一执行内核，所有跨页 handoff 只允许预填，不允许自动发送。

这意味着 Phase 4.0-1 不是重新讨论 IA，而是把既有边界真正产品化。

### 2.2 前端已存在可复用的 workflow 骨架

当前前端并非没有 workflow 基础，而是“有骨架、缺统一真源”：

1. `apps/web/src/features/workflow/types.ts` 已定义 `WorkflowScope`、`WorkflowRun`、`WorkflowArtifact`、`WorkflowTimelineItem`。
2. `apps/web/src/features/workflow/state/workflowStore.ts` 已有 workflow store。
3. `apps/web/src/features/workflow/hooks/useWorkflowHydration.ts` 已能基于 URL、chat scope、active run 生成 workflow 视图模型。
4. `apps/web/src/features/workflow/commandCenter.ts` 已提供 `ResearchCommandItem`、KB readiness item 和 chat handoff 结构。

问题不在于完全缺实现，而在于这些能力尚未成为跨页面共用的 workflow 真源。

### 2.3 主链页面已有局部连续性能力

当前 repo 已有几条关键局部连续性：

1. `SearchWorkspace.tsx` 已支持 `Continue in Chat`，并通过 `navigateToChatWithHandoff(...)` 传入 `promptDraft`、`evidence`、`returnTo`。
2. `KnowledgeWorkspaceShell.tsx` 已有 readiness 卡片、import status、runs、review、chat 等主入口。
3. `KnowledgeReviewPanel.tsx` 已支持从 review 段落继续跳到 Chat。
4. `useChatHandoff.ts` 已实现 handoff prefill-only 逻辑。

这说明产品主链不是从零开始，而是已经具备了“跳转与预填”的第一层能力。

### 2.4 当前断点在哪里

虽然已有骨架，但当前仍然更像“页面集合”而不是“连续研究工作流”，主要因为以下断点：

1. `workflow context` 没有 durable shared truth，很多上下文仍通过 URL 或 `location.state` 临时传递。
2. `useWorkflowHydration.ts` 主要基于 pathname 推导 scope，而不是基于一个被各页面共同维护的 workflow 实体。
3. `Search -> KB -> Read -> Chat -> Notes -> Compare -> Review` 的状态语义并未统一对齐到同一张状态表。
4. `pending actions / recoverable tasks / artifacts / timeline` 已有结构，但没有成为 Dashboard、KB、Chat 等页面共同消费的稳定入口。
5. handoff 是可用的，但更像单次导航行为，不足以构成研究目标级的连续工作流。

## 3. 为什么 Phase 4.0-1 必须先做

Phase 0 已经给出 `readiness_verdict = conditional`。当前可以开始 Phase 4.0-1 的研究和执行设计，但不能直接宣称 Beta-ready。

这意味着最正确的下一步不是继续补 Beta 材料，也不是先做 RAG 优化，而是：

1. 先把当前真实主链变成“能连续使用的工作流产品”。
2. 让后续 Beta、Review artifact、前端精修和测试 gate 都建立在稳定 workflow 真源之上。

如果跳过 Phase 4.0-1，后续会出现两个问题：

1. Beta 材料只能围绕页面跳转写脚本，而不是围绕产品主链写脚本。
2. 前端视觉和交互打磨会缺少明确的 workflow 优先级，容易沦为页面局部优化。

## 4. 本阶段的最小产品定义

Phase 4.0-1 的最小产品，不是新页面，而是当前主链获得以下能力：

1. 用户始终知道当前研究 scope 是什么。
2. 用户始终知道当前阻塞项是什么、为什么阻塞、下一步去哪。
3. 跨页进入 Chat 时，scope、prompt draft、return path 和关键证据不会丢。
4. Dashboard、Search、KB、Read、Chat、Review 对 “进行中 / 可继续 / 证据不足 / 需要恢复” 的语义一致。
5. 关键 artifact 和 run 引用可以在主链内持续消费，而不是只停留在单页里。

## 5. 结构性研究结论

### 5.1 应该收口的统一真源

本阶段必须冻结一个 workflow context 的最小统一真源，至少包含：

1. scope：
   - `global`
   - `knowledge-base`
   - `paper`
2. source：
   - `search-import`
   - `library-import`
   - `read`
   - `chat`
   - `review`
3. status：
   - `idle`
   - `running`
   - `waiting`
   - `completed`
   - `failed`
   - `cancelled`
4. next actions / recoverable tasks / artifacts / timeline

当前 `features/workflow/types.ts` 已经基本具备这组字段，因此 Phase 4.0-1 应优先做“冻结和扩展”，而不是重造。

### 5.2 应该优先产品化的三条连续链

本阶段不要求一次把所有场景做到完美，但必须优先产品化三条连续链：

1. `Search -> Continue in Chat`
2. `KB readiness -> Review / Chat`
3. `Review / Search / KB -> Continue in Chat -> return`

原因是：

1. 这些链条已经有真实代码基础。
2. 它们直接体现“Chat 为执行内核”的产品方向。
3. 它们为 Phase 4.0-2 Beta 和 Phase 4.0-3 artifact 生成提供最短路径。

### 5.3 Dashboard 的角色必须收紧

Dashboard 不能演变成功能执行页。它只应该回答：

1. 现在在哪个研究 scope。
2. 当前哪个 run / import / review 卡住了。
3. 下一步最应该做什么。
4. 点进去该去哪个页面恢复。

这与 `commandCenter.ts` 现有 `ResearchCommandItem` 的设计方向一致，因此本阶段重点是让 Dashboard 真正消费 workflow truth，而不是新增操作能力。

### 5.4 Chat handoff 必须从“导航技巧”升级为“workflow contract”

当前 `chatHandoff.ts` 和 `useChatHandoff.ts` 已经支持 prefill-only，这是正确方向。

但它仍有两个不足：

1. handoff 主要依赖 `location.state`，刷新后连续性较弱。
2. handoff 是 Chat 侧消费逻辑，不是跨页共享的 workflow contract。

因此本阶段必须把 handoff 升级为 durable workflow context 的一部分，至少做到：

1. scope 可恢复
2. prompt draft 可恢复
3. returnTo 可恢复
4. evidence ref 可恢复

### 5.5 Compare 不应在本阶段被重做，但必须纳入语义

Phase 0 已经确认 compare 仍缺 fresh-state 全链 closeout，不适合在本阶段扩大 compare 功能面。

但 compare 仍要被纳入 workflow 语义：

1. `compare` 可以作为 handoff origin。
2. `compare` 可以作为 artifact 或 next action target。
3. Dashboard / Chat / KB 不得把 compare 当成“系统外功能”。

因此本阶段的 compare 原则是“接入 workflow 语义，不重做 compare 页面”。

## 6. 本阶段不做什么

1. 不制作 Beta quickstart、demo dataset、walkthrough script。
2. 不重做 Dashboard / Search / KB / Chat / Review 的 IA。
3. 不新开第二套 workflow runtime 或 agent runtime。
4. 不做 Graph / global synthesis / corrective retrieval 等 B 类优化。
5. 不把前端视觉重做混入本阶段。

## 7. 风险

| risk | impact | mitigation |
|---|---|---|
| workflow context 只停留在前端内存态 | 刷新或跨页后连续性仍弱 | 本阶段至少补 durable handoff context |
| Dashboard 被做成功能页 | 偏离 command center 边界 | command center 只允许跳转与解释，不执行任务 |
| 同时改太多页面 | 回归风险过高 | 先收口 workflow truth，再按 Search / KB / Chat / Review 的顺序接入 |
| 把 Beta / compare / visual polish 混入 | phase 边界再次失真 | 明确由 4.0-2 / 4.0-4 / 4.0-5 / 4.0-7 承接 |

## 8. 研究结论

Phase 4.0-1 应聚焦 “workflow truth + cross-page continuity + command center + status semantics” 四件事。

结论：

1. 当前代码已经具备 workflow 产品化的可复用骨架，不需要另起平行实现。
2. 最核心缺口不是页面缺失，而是缺少 durable shared workflow context。
3. Phase 4.0-1 应先收口 `Search / KB / Review -> Chat` 连续性和统一状态语义。
4. Dashboard 必须继续作为 command center，而不是操作页。
5. 本阶段完成后，Phase 4.0-2 Beta 和 Phase 4.0-3 artifact 才有稳定产品底座。
