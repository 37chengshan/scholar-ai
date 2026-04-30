---
phase: EP-2026-04-20-battle-a-workflow-ui-ia-reset
reviewed: 2026-04-20T00:00:00Z
depth: standard
files_reviewed: 22
files_reviewed_list:
  - apps/web/src/app/components/Layout.tsx
  - apps/web/src/app/routes.tsx
  - apps/web/src/app/pages/Landing.tsx
  - apps/web/src/features/workflow/index.ts
  - apps/web/src/features/workflow/hooks/useWorkflowHydration.ts
  - apps/web/src/features/workflow/components/WorkflowShell.tsx
  - apps/web/src/features/workflow/components/ActiveScopeBanner.tsx
  - apps/web/src/features/workflow/components/CurrentRunBar.tsx
  - apps/web/src/features/workflow/components/PendingActionsPanel.tsx
  - apps/web/src/features/workflow/components/RecoverableTasksPanel.tsx
  - apps/web/src/features/workflow/components/ActivityTimelineDrawer.tsx
  - apps/web/src/features/workflow/components/ArtifactsDrawer.tsx
  - apps/web/src/features/workflow/adapters/workflowAdapters.ts
  - apps/web/src/features/workflow/resolvers/workflowResolvers.ts
  - apps/web/src/features/workflow/state/workflowStore.ts
  - apps/web/src/features/workflow/state/workflowActions.ts
  - apps/web/src/features/workflow/state/workflowSelectors.ts
  - apps/web/src/features/workflow/state/workflowStore.types.ts
  - apps/web/src/features/workflow/types.ts
  - docs/specs/design/frontend/workflow-ui-ia-reset.md
  - docs/specs/design/frontend/page-audit-workflow-reset.md
  - docs/plans/archive/exec-plans/active/EP-2026-04-20-battle-a-workflow-ui-ia-reset.md
findings:
  critical: 0
  warning: 4
  info: 0
  total: 4
status: issues_found
---

# Phase EP-2026-04-20: Code Review Report

**Reviewed:** 2026-04-20
**Depth:** standard
**Files Reviewed:** 22
**Status:** issues_found

## Summary

本次 battle A 改动方向正确，路由收敛、Workflow Shell 注入和文案重写都已落地。主要风险集中在 Workflow 作用域判定边界、浏览器存储访问健壮性、类型安全以及文档与实现一致性。

## Warnings

### WR-01: Knowledge Base 列表页作用域误判为 Global

**File:** `apps/web/src/features/workflow/hooks/useWorkflowHydration.ts:40`
**Issue:** `deriveScope` 仅判断 `pathname.startsWith('/knowledge-bases/')`，未覆盖 `/knowledge-bases` 本身。由于 `WorkflowShell` 在 `/knowledge-bases` 会展示，列表页将显示 Global Scope，和 IA 预期的 Library 语义不一致，存在功能回归风险。
**Fix:**
```ts
if (pathname === '/knowledge-bases' || pathname.startsWith('/knowledge-bases/')) {
  const kbId = pathname.split('/')[2] || null;
  return {
    type: 'knowledge-base',
    id: kbId,
    title: 'Library Workflow',
    subtitle: kbId ? `Managing import and retrieval for ${kbId}` : 'Library workflow context',
  };
}
```

### WR-02: sessionStorage 访问未做异常防护

**File:** `apps/web/src/features/workflow/hooks/useWorkflowHydration.ts:89`
**Issue:** 直接访问 `window.sessionStorage.getItem`。在隐私模式、受限 WebView 或存储被禁用场景中可能抛异常，导致 Workflow Shell 渲染链路中断。
**Fix:**
```ts
let persisted: string | null = null;
try {
  persisted = window.sessionStorage.getItem(SEARCH_IMPORT_STORAGE_KEY);
} catch {
  persisted = null;
}
```

### WR-03: artifacts 局部变量丢失类型约束

**File:** `apps/web/src/features/workflow/hooks/useWorkflowHydration.ts:119`
**Issue:** `const artifacts = []` 推断为 `any[]`，削弱编译期约束，后续 push 非法结构不会被类型系统阻止。
**Fix:**
```ts
const artifacts: WorkflowHydratedPayload['artifacts'] = [];
```

### WR-04: 文档定义的一级导航与实现不一致

**File:** `docs/specs/design/frontend/workflow-ui-ia-reset.md:8`
**Issue:** 文档声明一级导航为 `Chat / Workspace / Library / Search / Settings`，但 `Layout` 中 `navItems` 仅含 chat、knowledge-bases、search，settings 以右侧图标入口呈现而非同级导航项，可能导致验收口径和回归测试断言不一致。
**Fix:**
```text
二选一：
1) 更新文档，将 Settings 明确为“utility entry（右上角）”而非一级导航 tab；
2) 或在 Layout navItems 中加入 settings，和文档保持一致。
```

---

_Reviewed: 2026-04-20_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
