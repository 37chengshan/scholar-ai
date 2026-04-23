# ScholarAI Frontend Usability And Resilience Audit

Date: 2026-04-23

Scope:
- `apps/web/src/app`
- `apps/web/src/features/search`
- `apps/web/src/features/chat`
- `apps/web/src/features/kb`
- `apps/web/src/styles`

Reference sources:
- Latest Web Interface Guidelines: `https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md`
- Vercel React Best Practices: `build-web-apps:react-best-practices`

## Executive Summary

The frontend already has a recognizable editorial visual direction on the landing page, but the product surfaces are materially less mature than the brand shell. The main issue is not "ugly UI"; it is that usability, state management, and implementation boundaries are inconsistent across pages. That inconsistency makes the interface feel fragile even when individual screens look acceptable.

The most important conclusion from this audit is:

1. The product currently has multiple parallel UI patterns for navigation, cards, session rails, chat surfaces, and knowledge-base detail flows.
2. Several core user journeys still rely on hover-only actions, button-driven navigation, fake or placeholder interactions, and large stateful page components.
3. The current code shape makes breakage likely when features expand, especially in `Chat`, `Read`, `Notes`, and `Knowledge Base` surfaces.

This is a product maturity problem, not only a styling problem.

## Overall Verdict

Current frontend status:
- Visual maturity: medium
- Interaction clarity: medium-low
- Accessibility and semantic robustness: low-medium
- State resilience across refresh, back/forward, and deep-linking: medium-low
- Maintainability of core product surfaces: low

Primary risk:
- The app can still impress in screenshots, but it does not yet feel consistently trustworthy in real use.

## Highest-Priority Findings

### P0. Parallel implementations are increasing UI drift and fragility

Evidence:
- Duplicate component names and parallel implementations exist for key surfaces:
  - `apps/web/src/app/components/SearchResultCard.tsx`
  - `apps/web/src/app/components/tools/SearchResultCard.tsx`
  - `apps/web/src/app/components/StepTimeline.tsx`
  - `apps/web/src/components/StepTimeline.tsx`
  - `apps/web/src/app/components/ThinkingDetailModal.tsx`
  - `apps/web/src/components/ThinkingDetailModal.tsx`
  - `apps/web/src/app/components/ToolCallCard.tsx`
  - `apps/web/src/components/ToolCallCard.tsx`
- Legacy bridge patterns are still present:
  - `apps/web/src/features/chat/workspace/ChatWorkspaceV2.tsx`
  - `apps/web/src/features/chat/components/ChatLegacy.tsx`
  - `apps/web/src/features/kb/components/KnowledgeBaseDetailLegacy.tsx`
- Rollout and replacement layers coexist:
  - `apps/web/src/features/chat/workspace/rollout.ts`
  - `apps/web/src/features/chat/components/ChatRunContainer.tsx`
  - `apps/web/src/features/chat/components/ChatWorkspace.tsx`

Impact:
- The same user concept is being rendered by multiple component families.
- Design consistency will keep regressing unless there is one canonical implementation per surface.
- Bug fixes and polish work are likely to land in one path and miss another.

Recommendation:
- Freeze non-canonical UI paths and document the single source of truth for each surface.
- As a cleanup program, eliminate duplicate presentational components before large-scale beautification.

### P0. Core product pages are too large and too stateful

Evidence:
- `apps/web/src/app/pages/Notes.tsx`: 952 lines
- `apps/web/src/app/pages/Read.tsx`: 692 lines
- `apps/web/src/app/pages/KnowledgeBaseList.tsx`: 671 lines
- `apps/web/src/features/chat/workspace/ChatWorkspaceV2.tsx`: 638 lines
- `apps/web/src/app/components/Layout.tsx`: 543 lines

Impact:
- These files mix layout, interaction orchestration, persistence, async effects, and presentational concerns.
- Local changes are likely to create unintended regressions.
- Small UX improvements become expensive because the page owns too many responsibilities.

Recommendation:
- Split by durable responsibilities, not by JSX size only.
- Move URL state, interaction controllers, and view composition into separate modules.
- Keep page roots focused on shell composition.

### P0. Navigation semantics are inconsistent and often button-driven

Evidence:
- Many route changes are wired with `onClick={() => navigate(...)}` instead of links or `NavLink`.
  - `apps/web/src/app/pages/Dashboard.tsx`
  - `apps/web/src/app/pages/Landing.tsx`
  - `apps/web/src/app/pages/Read.tsx`
  - `apps/web/src/app/components/Layout.tsx`
- Landing page still contains `href="#"` placeholders:
  - `apps/web/src/app/pages/Landing.tsx:372`
  - `apps/web/src/app/pages/Landing.tsx:373`
  - `apps/web/src/app/pages/Landing.tsx:374`
  - `apps/web/src/app/pages/Landing.tsx:375`
  - `apps/web/src/app/pages/Landing.tsx:381`
  - `apps/web/src/app/pages/Landing.tsx:382`
  - `apps/web/src/app/pages/Landing.tsx:383`
  - `apps/web/src/app/pages/Landing.tsx:384`
  - `apps/web/src/app/pages/Landing.tsx:391`
  - `apps/web/src/app/pages/Landing.tsx:392`
  - `apps/web/src/app/pages/Landing.tsx:393`

Impact:
- Users cannot reliably open destinations in new tabs or preview link targets.
- Keyboard and assistive-tech behavior is less predictable.
- Fake links and fake buttons reduce product trust.

Recommendation:
- Links should go places. Buttons should mutate local state or submit actions.
- Remove dead-end actions from the landing page until real destinations exist.

### P1. Too many important actions are hidden behind hover

Evidence:
- Search result actions fade in only on hover:
  - `apps/web/src/app/components/SearchResultCard.tsx:84`
- Session delete action is hover-revealed:
  - `apps/web/src/features/chat/components/session-sidebar/SessionSidebar.tsx:206`
- Notes list destructive affordances rely on hover reveal:
  - `apps/web/src/app/pages/Notes.tsx:819`

Impact:
- Touch and keyboard users have worse discoverability.
- Dense surfaces feel fragile because primary actions do not look primary.

Recommendation:
- Keep destructive actions subdued, but visible on focus and visible enough without hover.
- Keep one primary action per card visible by default.

### P1. Several interfaces still use placeholder or non-trustworthy UI

Evidence:
- Search inspector contains synthetic bars and pseudo-analytics:
  - `apps/web/src/features/search/components/SearchWorkspace.tsx:244`
- Landing page includes a "完整技术白皮书" button without a destination:
  - `apps/web/src/app/pages/Landing.tsx:339`
- Login page contains cinematic system logs and decorative diagnostics:
  - `apps/web/src/app/pages/Login.tsx`

Impact:
- The UI feels like a prototype when decorative UI does not correspond to real functionality.
- Trust drops fastest on research tools where users expect precision and traceability.

Recommendation:
- Replace fake metrics with either real metadata or remove them.
- Reduce "terminal theater" on auth surfaces unless it carries actual product meaning.

## Page-Level Assessment

### Landing

Strengths:
- Strong visual thesis and brand energy.
- Clear editorial typography.
- Better hierarchy than most product pages.

Weaknesses:
- Too many click targets still route nowhere.
- The page uses more visual conviction than product truth.
- Several transitions use `transition-all`, which makes motion feel broad and noisy instead of intentional.

Main files:
- `apps/web/src/app/pages/Landing.tsx`
- `apps/web/src/app/components/landing/Testimonials.tsx`
- `apps/web/src/app/components/PaperTexture.tsx`

Recommendation:
- Keep the visual language.
- Remove non-functional actions.
- Add explicit `aria-label` values to testimonial controls.
- Convert the landing page from "beautiful demo" into a reliable front door.

### Auth Surfaces

Strengths:
- Memorable visual identity.
- Labels are mostly present in forms.

Weaknesses:
- The login/register experience prioritizes atmosphere over fast task completion.
- Decorative logs, dense prose, and split layout add cognitive load to a high-intent task.
- Mobile usability risk is elevated because both pages are visually heavy and tall.

Main files:
- `apps/web/src/app/pages/Login.tsx`
- `apps/web/src/app/pages/Register.tsx`
- `apps/web/src/app/pages/ForgotPassword.tsx`
- `apps/web/src/app/pages/ResetPassword.tsx`

Recommendation:
- Simplify auth layouts.
- Keep the brand typography, but reduce ornamental system framing.
- Make form completion speed the top priority.

### Dashboard

Strengths:
- Information scent is decent.
- Navigation cards are understandable.

Weaknesses:
- Most cards are implemented as route-navigation buttons instead of links.
- The page reads like a lightweight launcher, not a trustworthy research home.
- Visual language is softer and more generic than the landing page.

Main file:
- `apps/web/src/app/pages/Dashboard.tsx`

Recommendation:
- Turn it into a real command center:
  - recent work
  - resumable actions
  - research status
  - saved contexts
- Use one consistent card system shared with Search and Knowledge Base pages.

### Search

Strengths:
- Good structure: left source rail, center results, right inspector.
- Debounced search exists via `useSearch`.

Weaknesses:
- Search toolbar contains a visible action button that does not represent a distinct action.
- Search result cards still rely on hover for important actions.
- Inspector content mixes real and fake information, reducing trust.

Main files:
- `apps/web/src/features/search/components/SearchWorkspace.tsx`
- `apps/web/src/features/search/components/SearchToolbar.tsx`
- `apps/web/src/features/search/components/SearchResultsPanel.tsx`
- `apps/web/src/app/components/SearchResultCard.tsx`
- `apps/web/src/hooks/useSearch.ts`

Recommendation:
- Make search feel deterministic.
- If search is auto-run, remove the fake submit affordance or wire a real submit mode.
- Promote result provenance, source quality, and import intent above decoration.

### Chat

Strengths:
- Significant architecture work is already visible.
- Stream handling, runtime state, and message model have progressed.

Weaknesses:
- The main workspace is still marked as migration-mode and carries too much responsibility.
- Product ergonomics are split between layout shell, runtime shell, right panel, legacy bridge, and session UI.
- Visual polish is uneven: product-grade architecture underneath, but operator-grade clutter on top.

Main files:
- `apps/web/src/features/chat/workspace/ChatWorkspaceV2.tsx`
- `apps/web/src/features/chat/components/session-sidebar/SessionSidebar.tsx`
- `apps/web/src/features/chat/components/composer-input/ComposerInput.tsx`
- `apps/web/src/features/chat/components/ChatRightPanel.tsx`

Recommendation:
- Treat Chat as the flagship product surface and reduce conceptual layers visible to the user.
- Consolidate session rail patterns with the global app shell.
- Make message feed, composer, and right-panel relationships simpler and more legible.

### Knowledge Base

Strengths:
- URL-synchronized state already exists for key filters.
- The page is trying to support both card and list modes.

Weaknesses:
- The page is too large and carries too many modes.
- Real data and fake inspector behaviors are mixed.
- Toolbar density is high; the page feels operational but brittle.

Main files:
- `apps/web/src/app/pages/KnowledgeBaseList.tsx`
- `apps/web/src/features/kb/components/KnowledgeBaseDetailV2.tsx`
- `apps/web/src/features/kb/components/KnowledgeBaseDetailLegacy.tsx`

Recommendation:
- Reduce mode-switching friction.
- Separate collection management from detail exploration more clearly.
- Keep only one detail implementation path.

### Read

Strengths:
- URL-based page navigation is a good resilience decision.
- The reading workspace has a real product concept behind it.

Weaknesses:
- Too much local UI state is held in one page.
- Manual panel resizing, fullscreen state, selection state, notes autosave, and reading progress all live together.
- The surface is powerful but vulnerable to interaction regressions.

Main file:
- `apps/web/src/app/pages/Read.tsx`

Recommendation:
- Break Read into shell, reading controls, annotation state, and notes integration modules.
- Persist durable reading preferences such as panel openness, width, and active tab.

### Notes

Strengths:
- Ambitious workflow surface.
- Seems intended to combine catalog, tree, and editor in one place.

Weaknesses:
- The file size alone indicates too much orchestration in one page.
- Hover-dependent list actions and multiple derived data layers increase fragility.
- This page is likely to accumulate behavioral bugs fastest as new note features land.

Main file:
- `apps/web/src/app/pages/Notes.tsx`

Recommendation:
- Separate note catalog, folder tree, and editor shell into stable subdomains.
- Move derived summaries and filtering logic closer to selectors or dedicated hooks.

## Cross-Cutting UX Problems

### 1. Hover is used as a substitute for hierarchy

Symptoms:
- Buttons, arrows, action rows, and delete affordances often become visible only on hover.

Why it matters:
- High-quality interfaces use hover to enhance confidence, not to reveal the existence of core actions.

### 2. Motion is broad rather than intentional

Symptoms:
- Repeated `transition-all` usage across multiple surfaces.
- Decorative movement is often more prominent than state-change clarity.

Why it matters:
- Motion should support structure, focus, and feedback.
- Broad transitions create visual mush.

### 3. Product surfaces are not yet visually unified

Symptoms:
- Landing page uses an editorial, branded language.
- Dashboard, Search, Chat, and Knowledge Base pages drift toward generic admin UI.

Why it matters:
- Users feel the discontinuity as "fragility" even before they can describe why.

### 4. State durability is inconsistent

Good signs:
- `KnowledgeBaseList` uses URL state.
- `Read` supports `?page=` deep links.

Weak signs:
- Many important UI states remain local-only.
- Shared surfaces still rely heavily on component-local toggles and hidden ephemeral state.

Why it matters:
- Research workflows are interrupt-driven. Users need reliable return points.

## React And Performance Notes

Aligned with `react-best-practices`, the main frontend risks are less about micro-optimizations and more about structural rendering cost.

Notable concerns:
- Large page components own too many responsibilities and re-render surfaces together.
- Repeated local state and inline navigation handlers are spread across many pages.
- There is still clear opportunity to:
  - split expensive page roots
  - isolate non-urgent visual state
  - defer secondary panels
  - virtualize larger result sets and dense catalogs

Concrete examples:
- `apps/web/src/app/pages/KnowledgeBaseList.tsx` already has a TODO for virtualization.
- `apps/web/src/features/chat/workspace/ChatWorkspaceV2.tsx` uses `useDeferredValue`, which is a good direction, but the page root remains overloaded.

## Recommended Remediation Plan

### Phase 1: Trust And Semantics

Ship first:
- Remove all `href="#"` and non-functional hero/footer actions.
- Replace route-navigation buttons with links where navigation is the primary action.
- Make primary actions visible without hover.
- Add missing labels and accessibility text to search, carousel, and secondary controls.

### Phase 2: Canonical Surface Cleanup

Ship second:
- Define canonical implementations for:
  - search result card
  - tool call card
  - thinking detail modal
  - step timeline
  - chat workspace
  - knowledge base detail
- Delete or freeze parallel implementations.

### Phase 3: Product-Surface Unification

Ship third:
- Build one workspace design system for `Dashboard`, `Search`, `Chat`, `Knowledge Base`, and `Read`.
- Reuse:
  - page headers
  - section labels
  - action rows
  - card patterns
  - panel chrome

### Phase 4: Stateful Surface Refactor

Ship fourth:
- Split `Notes`, `Read`, `KnowledgeBaseList`, and `ChatWorkspaceV2` into smaller orchestration layers.
- Persist durable UI preferences where they matter.
- Reduce page-root ownership of unrelated state.

## Suggested Priority Backlog

### Immediate

- Fix dead links and dead buttons on landing.
- Fix search toolbar semantics.
- Fix search result card action discoverability.
- Add missing accessibility labels in testimonial controls and similar interactive UI.

### Near Term

- Canonicalize duplicate components.
- Refactor `ChatWorkspaceV2` and `KnowledgeBaseList` boundaries.
- Simplify auth layouts for faster completion and better mobile behavior.

### Strategic

- Redesign internal product surfaces as a coherent "research workstation" system.
- Introduce a documented UI ownership map for core surfaces.

## Final Assessment

The frontend can absolutely be elevated, but the next win should not be "make it prettier everywhere." The highest-value move is to make the product surfaces more truthful, more semantic, and more canonical. Once those foundations are in place, visual beautification will compound instead of fighting the codebase.

If we only polish visuals now, the app will look better in screenshots but still feel brittle in daily use. If we fix semantics, surface ownership, and action clarity first, the visual layer will finally have something stable to sit on.
