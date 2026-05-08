# v4.0-3 研究文档：Citation-backed Review Artifacts

> 日期：2026-05-08  
> 状态：research  
> 对应执行计划：`docs/plans/v4_0/active/phase_3/22_v4_0_phase_3_execution_plan.md`  
> 上游总览：`docs/plans/v4_0/active/overview/18_v4_0_overview_plan.md`

## 1. 研究问题

Phase 4.0-3 的目标不是重做 Review/Notes/Compare 页面，而是把已有的研究产物收束成一套可交付、可回跳、可审计的 citation-backed artifact 体系。

本阶段要回答四个问题：

1. 现有代码里，哪些 artifact 已经存在，且能直接承接。
2. Review、Notes、Compare 三条线目前分别在哪里生成证据，在哪里丢失统一口径。
3. 什么样的最小 artifact contract 才算真正“citation-backed”。
4. 哪些能力必须留给后续前端精修、Beta 或测试评测阶段，不能混进本阶段。

## 2. 当前实现基线

### 2.1 Review 侧已经有正式资源

后端已经有 `ReviewDraft` / `ReviewRun` 资源：

1. `apps/api/app/models/review_draft.py`
2. `apps/api/app/services/review_draft_service.py`
3. `apps/api/app/api/kb/kb_review.py`

当前 Review 资源已包含：

1. `outline_doc`
2. `draft_doc`
3. `quality`
4. `steps`
5. `tool_events`
6. `artifacts`
7. `evidence`
8. `recovery_actions`

这说明 Review 已经不是临时文本输出，而是可追踪的结构化产物。

### 2.2 Notes 侧已经支持 evidence persistence

Notes 侧已经有证据保存与规范化能力：

1. `apps/api/app/api/notes.py`
2. `apps/api/app/services/reading_notes_service.py`
3. `apps/api/app/models/orm_note.py`
4. `apps/web/src/services/notesApi.ts`

当前 Notes 已支持：

1. `linked_evidence`
2. evidence note 标题规范化
3. 阅读笔记与 evidence note 的持久化
4. `compare / review / read / chat` 来源标记

这意味着 Notes 已经是 artifact 容器的一部分，而不是纯手写便签。

### 2.3 Compare 侧已经有 evidence-backed matrix

Compare 侧已经存在证据驱动矩阵：

1. `apps/api/app/api/compare.py`
2. `apps/api/app/services/compare_service.py`
3. `apps/web/src/services/compareApi.ts`
4. `apps/web/src/features/chat/components/CompareCard.tsx`

当前 compare/v4 已能输出：

1. `compare_matrix`
2. `answer contract`
3. 结构化 cross-paper insights
4. 回跳 Chat 的 handoff 入口

这说明 Compare 已经具备 artifact 化基础。

### 2.4 前端已能消费 review artifacts

前端 review surface 已可消费这些结构：

1. `apps/web/src/features/kb/components/KnowledgeReviewPanel.tsx`
2. `apps/web/src/services/kbReviewApi.ts`
3. `packages/types/src/kb/review.ts`

它已经能：

1. 读取 review draft / run trace
2. 显示 citation coverage
3. 修复 claim
4. 从 evidence 继续跳到 Chat

所以 Phase 4.0-3 不是“从零做 Review”，而是把已有 Review 能力产品化成交付物。

## 3. 当前断点

虽然产物已经存在，但现在仍然更像“多个结构化输出”，而不是“统一的 citation-backed artifact 体系”。

主要断点有四个：

1. Review、Notes、Compare 各自有自己的 schema 和展示面，但没有一个统一的 artifact 目录。
2. citation coverage、unsupported claim、partial draft、linked evidence 这些概念还没有被统一成 phase 级口径。
3. 用户能从单个页面回跳 Chat，但还没有一份面向交付的 artifact bundle 把 return path、claim repair、evidence jump 一起串起来。
4. 现有产物能用，但还没有明确的 phase-level completion criteria 去判定“artifact-backed”是否真的达标。

## 4. 本阶段最小产品定义

Phase 4.0-3 的最小产品不是新页面，而是一套稳定的 artifact bundle：

1. Review Draft
2. Citation Audit
3. Evidence Note
4. Compare Matrix
5. Known Limitations
6. Run Trace / Return Path

这些产物必须满足：

1. 每个 claim 都能回到 evidence。
2. 每个 evidence 都能回到来源页或 Chat。
3. `partial` / `insufficient_evidence` 必须被保留为真实状态。
4. 交付物必须可复查，而不是只在页面里“看起来完成”。

## 5. 需要冻结的契约

本阶段应冻结以下最小契约：

1. artifact 类型
   - `review_draft`
   - `citation_audit`
   - `evidence_note`
   - `compare_matrix`
   - `known_limitations`
   - `run_trace`
2. 支撑状态
   - `covered`
   - `insufficient`
   - `supported`
   - `weakly_supported`
   - `unsupported`
3. 回跳语义
   - source -> artifact
   - artifact -> evidence
   - evidence -> chat
   - review -> repair

## 6. 本阶段不做什么

1. 不重做 Review / Notes / Compare 的 IA。
2. 不新增通用文档编辑器。
3. 不做 Beta quickstart、demo dataset、walkthrough script。
4. 不做前端视觉主打磨。
5. 不做 Graph / global synthesis / corrective retrieval 优化。

## 7. 风险

| risk | impact | mitigation |
|---|---|---|
| artifact 仍然分散在各页面 | 交付时难以形成统一证据链 | 冻结 artifact bundle 与统一 return path |
| citation audit 只停留在文本层 | unsupported claim 仍会被包装成完成 | 保留 partial / insufficient_evidence |
| Review/Notes/Compare 口径不一 | 用户理解成本高 | 统一 support / coverage / limitation 词汇 |
| 把前端精修混进来 | 研究阶段失焦 | 由 Phase 4.0-4 / 4.0-5 承接视觉与交互细节 |

## 8. 研究结论

Phase 4.0-3 应聚焦 “citation-backed artifact bundle + claim/evidence 回跳 + known limitations + run trace”。

结论：

1. 当前代码已经具备 Review / Notes / Compare 的结构化基础。
2. 最核心缺口不是能力不存在，而是缺少统一 artifact contract。
3. Phase 4.0-3 应把 Review Draft、Notes、Compare 和 evidence audit 收束成一套可交付产物。
4. 该阶段完成后，后续前端精修和评测 gate 才有稳定的研究产物可消费。
