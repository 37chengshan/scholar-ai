# v5.0 Release Gate Report -- 2026-06-02

## Verdict: BLOCKED
> gate_version: `5.0-9`  |  generated_at: `2026-06-02T11:30:27Z`

## Face Results

| Face | Result | Key Detail |
|------|--------|------------|
| Face A -- Audit | **PASS** | -- |
| Face B -- Benchmark | **BLOCK** | academic_artifact_missing |
| Face C -- Walkthrough | **BLOCK** | journeys_passed=0/7, failed=0 |
| Face D -- Governance | **PASS** | -- |
| Face E -- Perf | **BLOCK** | lighthouse_missing_route_landing |

## Face A -- Audit

Status: **PASS**

- `p1_count_open`: 0
- `p2_count_open`: 3
- `last_audit_date`: "2026-05-31"
- `audit_dimensions_covered`: ["frontend", "backend", "rag", "governance", "perf"]
- `audit_report_path`: "docs/plans/v5_0/reports/2026-05-31_v5_0_multidimensional_audit.md"

## Face B -- Benchmark

Status: **BLOCK**

- `academic_run_id`: null
- `academic_verdict`: null
- `workflow_run_id`: null
- `workflow_verdict`: null
- `rag_comparative_verdict`: null
- `regression_flag`: false
- `last_benchmark_date`: null

## Face C -- Walkthrough

Status: **BLOCK**

- `journey_passed_count`: 0
- `journey_failed_count`: 0
- `journey_skipped_count`: 7
- `journey_details`: [{"journey_id": "J1", "status": "skipped", "error_summary": null}, {"journey_id": "J2", "status": "skipped", "error_summary": null}, {"journey_id": "J3", "status": "skipped", "error_summary": null}, {"journey_id": "J4", "status": "skipped", "error_summary": null}, {"journey_id": "J5", "status": "skipped", "error_summary": null}, {"journey_id": "J6", "status": "skipped", "error_summary": null}, {"journey_id": "J7", "status": "skipped", "error_summary": null}]
- `last_run_at`: "2026-06-02T11:29:27Z"
- `playwright_report_path`: "apps/web/playwright-report"

## Face D -- Governance

Status: **PASS**

- `doc_governance`: true
- `plan_governance`: true
- `phase_tracking`: true
- `governance`: true
- `runtime_hygiene`: true
- `all_phases_closeout`: true
- `governance_check_timestamp`: "2026-06-02T11:30:27Z"

## Face E -- Perf

Status: **BLOCK**

- `lighthouse_scores`: {}
- `lighthouse_min_score`: null
- `a11y_scores`: {}
- `a11y_min_score`: null
- `bundle_first_screen_kb_gz`: null
- `bundle_total_main_routes_kb_gz`: null
- `cwv_lcp_ms`: null
- `cwv_inp_ms`: null
- `cwv_cls`: null
- `cwv_fcp_ms`: null
- `cwv_tbt_ms`: null
- `perf_snapshot_date`: null

## Block Reasons

- face_b: academic_artifact_missing
- face_c: journeys_passed=0/7, failed=0
- face_e: lighthouse_missing_route_landing

## Recommended Next Actions

- Hold release. Resolve all block reasons before re-running.
- Priority: resolve block reasons in order above.
- Re-run: `python scripts/evals/run_v5_release_gate.py`