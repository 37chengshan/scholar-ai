# PR #61 Readiness Report

Date: 2026-04-26

## Scope
- Test layering for PR #61 readiness.
- Keep unit tests stable without requiring a live Milvus service.

## Changes Made
- Marked Milvus-dependent test as integration-only with explicit marker and runtime skip when Milvus is unavailable:
  - `tests/unit/test_rag_v3_schemas.py`
  - Added markers: `@pytest.mark.integration`, `@pytest.mark.requires_milvus`
  - Added guard: skip when `MILVUS_HOST` is not set.
- Added pytest markers in `pytest.ini`:
  - `integration: tests requiring external services`
  - `requires_milvus: tests requiring live Milvus`

## Verification Commands
- `python -m compileall app/rag_v3 ../../scripts/evals/v3_0_*.py`
- `python -m pytest -q tests/unit/test_rag_v3_schemas.py tests/unit/test_v3_0_freeze_v2_baseline.py`

## Verification Results
- Compile: PASS
- Tests: `4 passed, 1 skipped`
- Skipped test is Milvus-dependent and correctly classified.

## Policy Checks
- No change to `apps/api/app/config.py`.
- No change to `apps/api/app/core/rag_runtime_profile.py` in this P0 action.
- No `apps/web` changes in this P0 action.
- No benchmark PDF artifacts added.

## PR #61 Readiness Decision
- PR #61 ready to merge: **YES**
- Rationale: Unit baseline is green locally, Milvus dependency is explicitly isolated as integration/requires_milvus.

## Suggested PR #61 Test Plan Update
- Unit tests PASS locally in environment without Milvus.
- Milvus-dependent retrieval contract test is marked `integration` + `requires_milvus` and skipped when Milvus is unavailable.
- Live Milvus validation remains available via integration runs with `MILVUS_HOST` configured.
