---
phase: v3_0D_real_world_validation
reviewed: 2026-04-29T00:49:59Z
depth: standard
files_reviewed: 6
files_reviewed_list:
  - apps/api/app/services/real_world_validation_service.py
  - scripts/evals/v3_0_real_world_validation_report.py
  - apps/api/tests/unit/test_real_world_validation_service.py
  - artifacts/validation-results/phase_d/real_world_validation.json
  - docs/specs/domain/resources.md
  - docs/reports/v3_0_real_world_validation.md
findings:
  critical: 1
  warning: 2
  info: 0
  total: 3
status: issues_found
---

# Phase D: Narrow Code Review Report

**Reviewed:** 2026-04-29T00:49:59Z
**Depth:** standard
**Files Reviewed:** 6
**Status:** issues_found

## Summary

Reviewed the Phase D real-world validation service, report generator, unit tests, payload seed, resource contract, and generated report. The main issues are recommendation logic ignoring blocked runs, validator drift from the documented minimum run schema, and workflow coverage reporting that counts failed or skipped chains as full-chain coverage.

## Critical Issues

### CR-01: Blocked runs can still produce beta_readiness=ready

**File:** apps/api/app/services/real_world_validation_service.py:213-217,346-380
**Issue:** Recommendation generation only considers `total_runs`, failure buckets, and failed honesty checks. It ignores `success_state_counts`, so a payload containing a run with `success_state="blocked"` but no recorded failure bucket or honesty failure is summarized as `beta_readiness: ready`. This is a functional bug in the release gate because a blocked real-world run should never yield a ready verdict.
**Fix:** Thread `success_state_counts` into `_recommendation()` and force `not_ready` whenever any run is `blocked` or when non-pass runs exist without explicit bucket classification. Add a unit test covering a blocked run with empty `failure_points`.

## Warnings

### WR-01: Validator does not enforce the documented minimum run schema

**File:** apps/api/app/services/real_world_validation_service.py:122-145
**Issue:** The resource contract says each run minimally includes `failure_points[]`, `recovery_actions[]`, `evidence_reviews[]`, `honesty_checks{}`, and `user_visible_confusions[]`, but the validator only type-checks `failure_points` and loosely type-checks `honesty_checks` when it is truthy. Missing `recovery_actions`, `evidence_reviews`, empty or absent `honesty_checks`, and missing `user_visible_confusions` all pass validation. That allows under-specified runs to be treated as valid inputs and then silently collapse to zero-valued summaries, which weakens the report contract.
**Fix:** Make these fields explicitly required in `validate_real_world_payload()`, validate their container types even when empty, and reject runs that omit any contract-required section. Add negative tests for each missing field.

### WR-02: full_chain_runs counts failed or skipped chains as covered

**File:** apps/api/app/services/real_world_validation_service.py:176-187,254-289
**Issue:** `full_chain_runs` increments when all standard step names merely appear in `workflow_steps`, regardless of each step status. A run containing `import=failed` and the rest `skipped` still reports `full_chain_runs: 1`. Because the generated report surfaces this in the “Workflow 覆盖” section, it overstates end-to-end coverage and can mislead close-out readers.
**Fix:** Count a run as full-chain only when every step in `STANDARD_CHAIN` exists and has `status="passed"` or define a separate metric like `full_chain_attempted_runs` vs `full_chain_passed_runs`. Add a unit test with failed/skipped steps.

---

_Reviewed: 2026-04-29T00:49:59Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
