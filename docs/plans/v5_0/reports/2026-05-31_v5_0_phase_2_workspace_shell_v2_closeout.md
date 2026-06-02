---
phase_id: 5.0-2
name: WorkspaceShell v2 Closeout Report
status: completed
completed_at: 2026-05-31
---

## Phase 5.0-2 WorkspaceShell v2 -- Closeout Report

### Summary

Successfully upgraded WorkspaceShell from fixed three-column desktop layout to responsive stack (desktop 3-col / tablet 2-col / mobile single-col), integrated bundle budget enforcement, and added four-state coverage for major pages.

### Task Completion Status

| Task | Name | Status | Notes |
|------|------|--------|-------|
| T0 | Security fixes | Pre-existing | SSRF + XSS + CSS injection fixed in research phase |
| T1 | Layout.tsx split | Pre-existing | Already 104 lines, SidebarContent/SessionList/UserProfile extracted |
| T2 | useBreakpoint hook | Pre-existing | Already in use-mobile.ts with proper breakpoints |
| T3 | WorkspaceShell responsive | **Completed** | 3-col desktop, 2-col tablet, 1-col mobile with InspectorDrawer |
| T4 | Bundle analysis (visualizer) | Pre-existing | rollup-plugin-visualizer configured in vite.config.ts |
| T5 | manualChunks config | **Completed** | vendor-react, vendor-query, vendor-radix, vendor-motion, vendor-icons |
| T6 | MUI/Emotion removal | **Completed** | 45 packages removed, no source imports existed |
| T7 | Dynamic imports | **Completed** | react-markdown, katex, highlight.js, mermaid moved to lazy chunk |
| T8 | size-limit CI | **Completed** | .size-limit.json + GitHub Actions workflow |
| T9 | Lighthouse CI | **Completed** | .lighthouserc.json + GitHub Actions workflow |
| T10 | Four-state standardization | **Completed** | UnifiedFeedbackState typed, Skeleton system unified |
| T11 | Page skeletons | **Completed** | SearchResults, KnowledgeBase, Analytics, Notes skeletons |
| T12 | PageErrorFallback | **Completed** | Exponential backoff retry, route-level ErrorBoundary |
| T13 | Final verification | **Completed** | All checks pass |

### Success Criteria Results

| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| Main entry gzip | <= 500 KB | **213.59 kB** | PASS |
| Lighthouse CI configured | Yes | `.lighthouserc.json` + workflow | PASS |
| WorkspaceShell responsive | 320/768/1024/1440 | Implemented with useBreakpoint | PASS |
| Four-state coverage | 6 pages | 6 pages (Search, KB, Analytics, Notes, Dashboard, Chat) | PASS |
| Layout.tsx lines | < 300 | 104 (pre-existing) | PASS |
| TypeScript zero errors | `npm run type-check` | Passes | PASS |
| Tests no new failures | `npm run test:run` | 5 pre-existing failures, 0 new | PASS |

### Bundle Analysis (Post-Optimization)

| Chunk | Raw Size | Gzip Size |
|-------|----------|-----------|
| Main entry (index-DKGvT7li.js) | 517.12 kB | 162.66 kB |
| vendor-radix | 267.75 kB | 85.19 kB |
| vendor-react | 95.81 kB | 32.54 kB |
| vendor-motion | 96.17 kB | 31.76 kB |
| vendor-icons | 53.22 kB | 10.33 kB |
| vendor-query | 41.21 kB | 12.26 kB |
| MarkdownRendererInner (lazy) | 1,054.32 kB | 281.80 kB |

**Total main entry gzip: 213.59 kB** (size-limit measurement including all synchronous chunks)

### Files Created

| File | Purpose |
|------|---------|
| `apps/web/src/app/components/layout/InspectorDrawer.tsx` | Responsive inspector overlay/drawer for tablet/mobile |
| `apps/web/src/app/components/MarkdownRendererInner.tsx` | Heavy markdown rendering (dynamically imported) |
| `apps/web/src/app/components/PageErrorFallback.tsx` | Error fallback with exponential backoff retry |
| `apps/web/src/app/components/PageSkeletons.tsx` | Page-level skeleton components (Search, KB, Analytics, Notes) |
| `apps/web/.size-limit.json` | Bundle size budget configuration |
| `.lighthouserc.json` | Lighthouse CI configuration |
| `.github/workflows/lighthouse.yml` | Lighthouse CI GitHub Actions workflow |
| `.github/workflows/size-limit.yml` | Bundle size check GitHub Actions workflow |

### Files Modified

| File | Changes |
|------|---------|
| `apps/web/src/app/components/layout/WorkspaceShell.tsx` | Responsive layout with useBreakpoint, InspectorDrawer integration |
| `apps/web/src/app/components/UnifiedFeedbackState.tsx` | Replaced `any` types with strict interfaces |
| `apps/web/src/app/components/MarkdownRenderer.tsx` | Converted to lazy-load wrapper |
| `apps/web/src/app/components/AISummaryPanel.tsx` | Dynamic import for react-markdown in legacy path |
| `apps/web/src/app/components/AISummaryPanel.test.tsx` | Updated test for async rendering |
| `apps/web/src/app/routes.tsx` | Added RouteErrorBoundary + page-specific skeleton fallbacks |
| `apps/web/vite.config.ts` | Added manualChunks configuration |
| `apps/web/package.json` | Removed MUI/Emotion, added size-limit, added size script |

### Dependencies Removed

- `@mui/material` (7.3.5)
- `@mui/icons-material` (7.3.5)
- `@emotion/react` (11.14.0)
- `@emotion/styled` (11.14.1)

**45 packages removed** (no source code imports existed)

### Dependencies Added

- `size-limit` (devDependency)
- `@size-limit/preset-app` (devDependency)

### Pre-existing Test Failures (Not Introduced)

- `MessageFeed.test.tsx` -- 4 failures (streaming content, metadata updates, token/cost fallback, abstain normalization)
- `KnowledgeBaseDetail.test.tsx` -- 1 failure (KB retrieval results rendering)

These failures exist on the branch prior to Phase 5.0-2 changes.

### Risk Items for Phase 5.0-3

1. **Bundle 500KB target**: Achieved (213.59 kB gzip). No follow-up needed.
2. **react-resizable-panels mobile touch**: Mitigated by skipping PanelGroup on mobile, using single column + Sheet/Drawer.
3. **Lighthouse CI environment波动**: Mitigated by `numberOfRuns: 3` with median.
4. **CLS from Skeleton mismatch**: Skeleton components built to match actual page layouts.
