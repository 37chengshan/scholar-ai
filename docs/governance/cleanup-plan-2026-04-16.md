# Engineering Cleanup Plan

Date: 2026-04-16

## Goal

Deliver a stable engineering file architecture so future work stays under `scholar-ai/`, with one documentation root, one process baseline, and clear migration targets for later code cleanup.

## Phase 1: Repository Governance

- Merge `doc/` into `docs/`.
- Route imported API/vendor notes into `docs/reference/`.
- Route reports into `docs/reports/`.
- Create `logs/` as the canonical archive for runtime logs.
- Expand `.gitignore` for runtime and cache paths.
- Correct wrong naming directories at the outer workspace boundary.

## Phase 2: Documentation Governance

- Add `docs/architecture/system-overview.md`.
- Add `docs/architecture/api-contract.md`.
- Add `docs/architecture/resources.md`.
- Add `docs/engineering/coding-standards.md`.
- Add `docs/engineering/pr-process.md`.

## Phase 3: Code Governance

- Frontend: converge on `frontend/src/app` as the feature root.
- Backend: converge on grouped API packages and remove `_new` or `legacy` duplication.
  - 2026-04-16 progress: empty duplicate API directories `app/api/papers_new` and `app/api/search_new` retired.
  - Remaining backend compatibility holdout: `app/legacy/rag_service_deprecated.py`, still kept for legacy RAG test coverage.
- Response schema: standardize envelope, pagination, and error payloads.
- Naming: frontend camelCase, backend snake_case, API boundary conversion centralized.

## Phase 4: Process Governance

- Add PR template.
- Add issue templates.
- Start ADR log.
- Define testing baseline.
- Write AI collaboration rules into `AGENTS.md`.

## Non-Goals For This Change

- No large feature rewrite.
- No risky route-level merge of backend duplicate modules in the same commit.
- No dependency expansion for governance-only work.
