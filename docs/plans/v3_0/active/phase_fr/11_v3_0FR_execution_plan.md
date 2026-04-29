# 11 v3.0FR 执行计划：Frontend Reliability Refactor

> 日期：2026-04-29  
> 状态：execution-plan  
> 上游研究：`docs/plans/v3_0/active/phase_fr/2026-04-29_v3_0FR_Frontend_Reliability_Refactor_研究文档.md`

## 1. 目标

`v3.0FR` 的目标不是做一轮新的 UI 大改版，而是在真实前端主链上完成第一轮结构清障，让后续 `Phase F` 产品化打磨建立在更稳定的页面基线上。

阶段性交付目标：

```txt
1. 清理 Chat / KB 的 legacy bridge
2. 为 KB 论文列表补齐 virtualization
3. 将 Read / Notes 偏好状态持久化
4. 去除 Notes 的 Hover-only 删除交互
5. 形成后续 giant page 深拆的冻结边界
```

## 2. 执行前先读什么

执行者开始前，按以下顺序读取：

1. `docs/plans/v3_0/active/overview/06_v3_0_overview_plan.md`
2. `docs/plans/v3_0/active/phase_fr/2026-04-29_v3_0FR_Frontend_Reliability_Refactor_研究文档.md`
3. `docs/plans/v3_0/active/phase_fr/v3_0FR_kickoff_freeze.md`
4. `docs/plans/v3_0/active/phase_fr/v3_0FR_refactor_scope_matrix.md`
5. `docs/plans/v3_0/active/phase_fr/v3_0FR_ui_preference_persistence_spec.md`
6. `docs/plans/v3_0/active/phase_fr/v3_0FR_execution_plan_review.md`
7. `docs/specs/design/frontend/DESIGN_SYSTEM.md`
8. `apps/web/src/features/chat/workspace/ChatWorkspaceV2.tsx`
9. `apps/web/src/features/kb/components/KnowledgeWorkspaceShell.tsx`
10. `apps/web/src/app/pages/Read.tsx`
11. `apps/web/src/app/pages/Notes.tsx`

执行规则：

1. 不新造平行页面或第二套工作台。
2. 先做 bridge / preference / virtualization 这类低风险改动，再考虑 giant page 深拆。
3. 一轮只做一个安全切片，做完立刻验证。

## 3. Work Packages

## WP0：Scope Freeze

目标：

1. 冻结本轮允许修改的页面与组件边界。
2. 明确哪些事项留到后续切片，不在本轮混做。

验收：

1. 执行者不会把整套 Chat / KB 重写混入本轮。

## WP1：Legacy Bridge Cleanup

目标：

1. 删除 `ChatLegacy.tsx`。
2. 删除 `KnowledgeBaseDetailLegacy.tsx`。

验收：

1. 主链入口仍然通过 `ChatWorkspaceV2` 和 `KnowledgeWorkspaceShell` 工作。
2. 仓内不再保留这两个 bridge 文件。

## WP2：KB List Virtualization

目标：

1. 为 `KnowledgePapersPanel` 增加面向大列表的虚拟化渲染。

验收：

1. 在高数据量场景下，论文列表不再一次性渲染全部项目。
2. 小列表场景不丢失原有行为与高亮滚动体验。

## WP3：Read / Notes Preference Persistence

目标：

1. 把 `Read` 的界面偏好状态外提到持久化 store。
2. 把 `Notes` 的浏览偏好状态外提到持久化 store。

验收：

1. 刷新页面后，`Read` 的 panel width、panel open、tab 选择可恢复。
2. 刷新页面后，`Notes` 的 folder 选择与 tag filter 可恢复。

## WP4：Interaction Safety Fix

目标：

1. 修复 `Notes` 删除按钮只能 Hover 出现的问题。

验收：

1. 在非 Hover 场景下，用户仍能看见删除入口。
2. 不影响现有删除确认逻辑。

## 4. 实际执行顺序

执行者按以下顺序推进：

1. `WP0 Scope Freeze`
2. `WP1 Legacy Bridge Cleanup`
3. `WP2 KB List Virtualization`
4. `WP3 Read / Notes Preference Persistence`
5. `WP4 Interaction Safety Fix`

原因：

1. bridge 不先清，后续重构边界仍会反复摇摆。
2. virtualization 与 preference persistence 属于可独立验证的中小切片。
3. Hover-only 修复应在结构收口后同步完成，避免遗漏在触屏主路径中。

## 5. 下层文档

1. `docs/plans/v3_0/active/phase_fr/v3_0FR_kickoff_freeze.md`
2. `docs/plans/v3_0/active/phase_fr/v3_0FR_refactor_scope_matrix.md`
3. `docs/plans/v3_0/active/phase_fr/v3_0FR_ui_preference_persistence_spec.md`
4. `docs/plans/v3_0/active/phase_fr/v3_0FR_execution_plan_review.md`

## 6. 验收标准

Phase FR P0 可视为完成，当且仅当：

1. 两个 legacy bridge 文件被删除。
2. KB 论文列表具备 virtualization 路径。
3. `Read / Notes` 偏好状态进入持久化 store。
4. `Notes` 删除操作不再依赖 Hover 才能发现。
5. `apps/web` 类型检查和相关测试通过。

## 7. 风险

1. 若直接深拆 `ChatWorkspaceV2`，将显著放大 SSE 回归风险。
2. 若在 virtualization 中强行统一所有列表高度，可能引入布局截断问题。
3. 若把业务状态与偏好状态混在同一个 store，会导致恢复语义变脏。