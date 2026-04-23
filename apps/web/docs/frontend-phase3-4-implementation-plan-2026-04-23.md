# Frontend Phase 3-4 Implementation Plan

Date: 2026-04-23

Scope:
- `apps/web/src/app`
- `apps/web/src/features/chat`
- `apps/web/src/features/kb`
- `apps/web/src/styles`

Reference inputs:
- `apps/web/docs/frontend-usability-audit-2026-04-23.md`
- `apps/web/docs/frontend-canonical-surfaces-2026-04-23.md`
- `build-web-apps:frontend-skill`
- `build-web-apps:web-design-guidelines`
- `build-web-apps:react-best-practices`

## Objective

Ship the next two frontend phases as a product-surface unification program, not a visual reboot.

The goal is:
- make `Dashboard`, `Search`, `Chat`, `Knowledge Base`, and `Read` feel like one product
- preserve the current editorial design language
- remove brittle and over-boxed product UI patterns
- avoid introducing generic admin-dashboard card grids

## Visual Guardrails

This plan follows the existing `frontend-skill` direction:
- editorial hierarchy over component quantity
- layout before chrome
- cardless by default
- one accent color as the primary action/state signal
- sparse, utility-first product copy

Hard bans for all future implementation work:
- no large chunky block UI
- no dashboard-card mosaics as the default page structure
- no thick borders around every region
- no routine product views made of stacked heavy cards
- no new decorative gradients behind work surfaces
- no extra accent colors unless already required by state semantics
- no hero-style marketing copy inside product workspaces

Working visual thesis:
- "paper-like research workbench"

That means:
- thin dividers
- clear type hierarchy
- long horizontal rhythm instead of boxed tiles
- selective use of surfaces only where the surface is the interaction
- calm side panels and inspectors, not floating control centers

## Product UI Rules

Use these rules as acceptance criteria during implementation:

1. A workspace should read as:
   - header
   - primary working surface
   - secondary context
   - one restrained action lane

2. Cards are allowed only when:
   - the card itself is the direct object of action
   - list rows or split layout would be less clear

3. Prefer:
   - rows
   - lists
   - gutters
   - dividers
   - side rails
   - panel sections

4. Avoid:
   - square dashboard tiles for everything
   - boxed summary strips
   - nested cards inside cards
   - over-framed filters and inspectors

## Phase Breakdown

### Phase 3A: Workspace Shell Unification

Goal:
- Create one shared workspace language for all product surfaces.

Primary files:
- `apps/web/src/app/pages/Dashboard.tsx`
- `apps/web/src/features/search/components/SearchWorkspace.tsx`
- `apps/web/src/features/chat/workspace/ChatWorkspaceV2.tsx`
- `apps/web/src/app/pages/KnowledgeBaseList.tsx`
- `apps/web/src/app/pages/Read.tsx`

Implementation tasks:
- Extract a shared workspace header pattern:
  - eyebrow or section label
  - title
  - one-line operational description
  - primary actions on the right
- Extract one shared section-label pattern for inner areas.
- Extract one shared action-row pattern for filters, sort, and secondary actions.
- Extract one shared panel chrome pattern for right-side inspectors and supporting rails.
- Normalize spacing rhythm:
  - page frame
  - section gaps
  - panel padding
  - title-to-body spacing

Do not:
- redesign the landing style into the app
- add full-card wrappers to every section
- create new global "dashboard" blocks

Acceptance criteria:
- `Dashboard`, `Search`, `Chat`, `Knowledge Base`, and `Read` share the same shell logic.
- Headers feel related without becoming identical clones.
- Inspectors and side panels feel calm and light, not boxed and dominant.

### Phase 3B: Chat As The Flagship Surface

Goal:
- Turn chat into the clearest and most trustworthy product workspace.

Primary files:
- `apps/web/src/features/chat/workspace/ChatWorkspaceV2.tsx`
- `apps/web/src/features/chat/components/message-feed/MessageFeed.tsx`
- `apps/web/src/features/chat/components/composer-input/ComposerInput.tsx`
- `apps/web/src/features/chat/components/ChatRightPanel.tsx`
- `apps/web/src/features/chat/components/tool-timeline/ToolTimelinePanel.tsx`

Implementation tasks:
- Reduce visible conceptual layers in the main workspace.
- Rebalance the page so the message feed is visually primary.
- Simplify the session rail:
  - lighter chrome
  - stronger list hierarchy
  - fewer "widget-like" treatments
- Make the composer feel like a durable research input, not a floating tool box.
- Make tool timeline and reasoning UI read as supporting evidence, not competing surfaces.
- Align right-panel chrome with Search and Read inspectors.

Specific UI direction:
- use separators and list rhythm before introducing cards
- tool and run state should look embedded in the workflow, not attached as extra modules
- keep one accent for active state

Acceptance criteria:
- A new user can visually identify:
  - current session
  - message feed
  - input
  - active run context
  - right-side evidence context
- The page no longer reads like multiple products stitched together.

### Phase 3C: Knowledge Base And Read Harmonization

Goal:
- Make library and reading flows feel like the same research workstation.

Primary files:
- `apps/web/src/app/pages/KnowledgeBaseList.tsx`
- `apps/web/src/features/kb/components/KnowledgeWorkspaceShell.tsx`
- `apps/web/src/app/pages/Read.tsx`

Implementation tasks for Knowledge Base:
- Replace toolbar heaviness with a lighter action row.
- Reduce dependence on boxy utility controls.
- Make list and card view share the same structural header.
- Treat storage stats and inspector content as secondary support, not primary landmarks.
- Keep collection management and collection exploration visually distinct.

Implementation tasks for Read:
- Make the top toolbar calmer and more document-like.
- Align right-side panel chrome with Search and Chat.
- Reduce "tool frame" feeling around PDF, notes, and summary panels.
- Preserve deep-link and page-jump behavior while simplifying the visible layout.

Acceptance criteria:
- `Knowledge Base` and `Read` both feel like extensions of the same workspace family.
- Neither page depends on large block panels for hierarchy.

### Phase 4A: Stateful Surface Refactor

Goal:
- Reduce fragility in the largest page roots without changing external behavior.

Primary files:
- `apps/web/src/features/chat/workspace/ChatWorkspaceV2.tsx`
- `apps/web/src/app/pages/KnowledgeBaseList.tsx`
- `apps/web/src/app/pages/Read.tsx`
- `apps/web/src/app/pages/Notes.tsx`

Implementation tasks:
- Split page roots by responsibility:
  - shell
  - url state
  - panel state
  - data loading
  - local interaction controllers
- Move durable preferences into URL or local persistence where appropriate.
- Reduce page-root ownership of unrelated toggles.
- Isolate non-urgent visual state from critical interaction state.

React-specific guidance:
- prefer extraction over page-root state accretion
- use `useDeferredValue` or transitions only where interaction lag exists
- do not introduce memoization noise without evidence

Acceptance criteria:
- Large page files stop growing as orchestration buckets.
- Navigation, refresh, and return flows preserve more durable UI state.

## Execution Order

Recommended order of delivery:

1. `Chat`
   - highest user-perceived trust impact
   - best place to establish the shared workspace pattern

2. `Knowledge Base`
   - currently the most obviously boxy operational surface
   - strong payoff from shell and action-row cleanup

3. `Read`
   - benefits from the shared panel language once Chat and Search are aligned

4. `Notes`
   - should follow after the structural patterns are already established

## Deliverables Per Work Package

For each surface, ship all of the following together:
- updated shell composition
- cleaned action hierarchy
- reduced card usage
- accessible interaction semantics
- test updates where behavior changed
- short doc note if canonical ownership changes

## Suggested Tickets

### Ticket Group A: Shared Workspace Primitives

Deliver:
- `WorkspaceHeader`
- `WorkspaceSectionLabel`
- `WorkspaceActionRow`
- `WorkspaceInspectorShell`

Constraints:
- no decorative block backgrounds
- no default card wrappers

### Ticket Group B: Chat Cleanup

Deliver:
- unified header and action strip
- lighter session rail
- calmer right panel
- simplified tool timeline presentation

### Ticket Group C: Knowledge Base Cleanup

Deliver:
- lighter toolbar
- unified list and card framing
- quieter inspector
- reduced control density above the fold

### Ticket Group D: Read Cleanup

Deliver:
- unified document header
- shared side panel chrome
- simplified reading control row
- better persistence boundaries for reading preferences

### Ticket Group E: Structural Refactors

Deliver:
- `ChatWorkspaceV2` orchestration split
- `KnowledgeBaseList` controller extraction
- `Read` panel-state extraction
- `Notes` shell split

## Verification

Required after each implementation slice:
- `cd apps/web && npm run type-check`

Recommended targeted validation:
- update or run the nearest relevant Vitest suites
- run route or page tests for the touched surface
- if interaction behavior changes materially, add one regression test

Review checklist:
- Does the page still feel like the current ScholarAI product?
- Did we avoid big chunky block UI?
- Could at least one card treatment be removed and replaced with layout?
- Is the primary working surface visually obvious within one glance?
- Are secondary panels clearly secondary?

## Definition Of Done

A phase is only done when:
- visual language is more unified
- semantics and state resilience do not regress
- the surface feels lighter, calmer, and more trustworthy
- the implementation does not add a new parallel UI path
- the page does not devolve into a card grid
