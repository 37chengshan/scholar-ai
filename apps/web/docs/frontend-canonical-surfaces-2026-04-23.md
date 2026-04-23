# Frontend Canonical Surfaces

Date: 2026-04-23

Purpose:
- Freeze the canonical implementation path for core frontend surfaces.
- Keep compatibility bridges read-only while cleanup continues.

## Canonical Components

- Search result card:
  - Canonical: `apps/web/src/app/components/SearchResultCard.tsx`
  - Legacy or non-canonical neighbor: `apps/web/src/app/components/tools/SearchResultCard.tsx`
  - Rule: new search-result UX work lands only in the canonical card.

- Tool call card:
  - Canonical: `apps/web/src/app/components/ToolCallCard.tsx`
  - Compatibility bridge: `apps/web/src/components/ToolCallCard.tsx`

- Thinking detail modal:
  - Canonical: `apps/web/src/app/components/ThinkingDetailModal.tsx`
  - Compatibility bridge: `apps/web/src/components/ThinkingDetailModal.tsx`

- Step timeline:
  - Canonical: `apps/web/src/app/components/StepTimeline.tsx`
  - Compatibility bridge: `apps/web/src/components/StepTimeline.tsx`

## Canonical Product Surfaces

- Chat workspace:
  - Canonical implementation: `apps/web/src/features/chat/workspace/ChatWorkspaceV2.tsx`
  - Compatibility bridges:
    - `apps/web/src/features/chat/components/ChatLegacy.tsx`
    - `apps/web/src/features/chat/components/ChatRunContainer.tsx`
    - `apps/web/src/features/chat/components/ChatWorkspace.tsx`
  - Rule: do not add new business logic to bridge files.

- Knowledge base detail:
  - Canonical implementation path:
    - `apps/web/src/features/kb/components/KnowledgeWorkspaceShell.tsx`
    - via `apps/web/src/features/kb/components/KnowledgeBaseDetailV2.tsx`
  - Compatibility bridge:
    - `apps/web/src/features/kb/components/KnowledgeBaseDetailLegacy.tsx`

## Bridge Policy

- Compatibility bridges may re-export or wrap the canonical implementation.
- Compatibility bridges should not introduce new state, styling forks, or business logic.
- New polish, bug fixes, and accessibility work must land in canonical files first.
