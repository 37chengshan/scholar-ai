---
owner: web-platform
status: in-progress
depends_on:
  - v4_0_phase_5_frontend_interaction_quality_research
  - 23_v4_0_phase_4_execution_plan
last_verified_at: 2026-05-11
evidence_commits:
  - working-tree-v4-0-phase-5-execution-plan
  - working-tree-v4-0-phase-5-p0-slice
---

# 24 v4.0-5 执行计划：Frontend Interaction Quality

> 日期：2026-05-11
> 状态：execution-plan / implementation-started
> 上游研究：`docs/plans/v4_0/active/phase_5/2026-05-11_v4_0_phase_5_frontend_interaction_quality_research.md`
> 上游 Phase 4：`docs/plans/v4_0/active/phase_4/23_v4_0_phase_4_execution_plan.md`

## 1. 目标

Phase 4.0-5 的第一批落地目标不是“全站交互都做完”，而是把主研究链上最明显、最可验证的交互债务切出一个可提交的起步版本：

```txt
link-first navigation
-> no hover-only core actions
-> responsive inspector policy
-> stale / pending / busy interaction hints
-> targeted tests + walkthrough gate
```

本执行计划首先冻结交互质量的实施顺序、文件边界和最小验收口径，然后在 P0 里直接落第一批代码。

## 2. 本轮范围

### 2.1 本轮必做

1. `Layout.tsx`
   - 把主路径中的 `button + navigate()` 收口为 link-first 导航。
   - 保持移动端菜单关闭逻辑与桌面行为一致。
2. `KnowledgeWorkspaceShell.tsx`
   - 把 KB 作用域 Chat 主动作改成语义化跳转。
   - 收口主 tab 的交互过渡，避免继续依赖 `transition-all`。
3. `MessageFeed.tsx`
   - 取消 assistant action bar 的 hover-only 显示方式。
   - 为复制和停止等动作补齐显式按钮语义与焦点可见性。
4. 文档与台账
   - 执行计划、`PLAN_STATUS`、phase ledger 同步到仓库真源。

### 2.2 本轮不做

1. 不重做 Compare / Review / Read 的完整响应式布局。
2. 不引入新的交互框架或手势库。
3. 不把 Phase 4.0-7 的 walkthrough / release verdict 提前写成已完成。
4. 不把 `pretext` 扩大成 Phase 5 的主工具。

## 3. 工作包

## WP1：Link-first Navigation

目标：

1. 主路径导航优先恢复 `<Link>` / `<NavLink>` 语义。
2. 保留移动端关闭菜单和 scope query 的正确行为。

本轮文件：

1. `apps/web/src/app/components/Layout.tsx`
2. `apps/web/src/features/kb/components/KnowledgeWorkspaceShell.tsx`

验收：

1. Dashboard logo、新对话、最近会话、知识库入口、设置入口不再依赖 `button + navigate()`。
2. KB 工作区“对整个知识库提问”改为语义化链接。

## WP2：Core Actions Are Not Hover-only

目标：

1. Chat assistant 消息的核心动作不再必须 hover 才能发现。
2. 动作在键盘 focus 下也可见且可操作。

本轮文件：

1. `apps/web/src/features/chat/components/message-feed/MessageFeed.tsx`
2. `apps/web/src/features/chat/components/message-feed/MessageFeed.test.tsx`

验收：

1. assistant message 的 copy / token info action bar 默认可见。
2. stop / copy 按钮具备显式 `type` 与焦点样式。
3. 对应测试能覆盖核心动作的可见性。

## WP3：Interaction Motion and Pending Policy

目标：

1. 继续清理主路径中的 `transition-all` 倾向。
2. 把 tab / shell 的过渡收口为更明确的颜色或 opacity 变化。

本轮文件：

1. `apps/web/src/features/kb/components/KnowledgeWorkspaceShell.tsx`

验收：

1. KB 主 tab 不再继续把 `transition-all` 作为默认基线。

## WP4：Phase 5 Start Evidence

目标：

1. 让本轮工作成为 Phase 5 的正式起步证据。
2. 明确后续 P1 / P2 顺序，不把本轮伪装成 Phase 5 closeout。

输出：

1. 本执行计划
2. `docs/plans/PLAN_STATUS.md`
3. `docs/specs/governance/phase-delivery-ledger.md`

验收：

1. Phase 5 顶层状态更新为 `execution-plan-complete / implementation-in-progress`。
2. phase ledger 有独立 Phase 5 执行记录。

## 4. 本轮后的下一顺序

本轮完成后，后续顺序冻结为：

1. P1：Search / Compare / Review 的 stale / pending / responsive 语义。
2. P1：Read / Notes / Chat handoff 的焦点落点与恢复动作。
3. P2：coarse pointer / reduced motion walkthrough。
4. P2：前端交互专项测试与浏览器级验证。

## 5. 最小验证

本轮最小验证：

```bash
cd apps/web && npm run type-check
cd apps/web && npm run test:run -- src/features/chat/components/message-feed/MessageFeed.test.tsx src/features/kb/components/KnowledgeWorkspaceShell.test.tsx
bash scripts/check-doc-governance.sh
bash scripts/check-plan-governance.sh
bash scripts/check-phase-tracking.sh
```

## 6. 当前结论

Phase 4.0-5 已进入 `execution-plan-complete / implementation-in-progress`，但只完成第一批 P0 交互切片，不能写成 phase closeout、walkthrough complete 或 release-pass。
