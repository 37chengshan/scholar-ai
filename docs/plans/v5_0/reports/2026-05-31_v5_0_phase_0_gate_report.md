# v5.0 Release Gate Report -- 2026-05-31

## Verdict: BLOCKED
> gate_version: `5.0-0`  |  generated_at: `2026-05-31T09:03:13Z`

## Face Results

| Face | Result | Key Detail |
|------|--------|------------|
| Face A -- Audit | **BLOCK** | input_missing |
| Face B -- Benchmark | **BLOCK** | academic_artifact_missing |
| Face C -- Walkthrough | **BLOCK** | input_missing |
| Face D -- Governance | **BLOCK** | checks_failed=['all_phases_closeout'] |
| Face E -- Perf | **BLOCK** | input_missing |

## Face A -- Audit

Status: **BLOCK**

- `p1_count_open`: null
- `p2_count_open`: null
- `last_audit_date`: null
- `audit_dimensions_covered`: []
- `audit_report_path`: null

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

- `journey_passed_count`: null
- `journey_failed_count`: null
- `journey_skipped_count`: null
- `journey_details`: []
- `last_run_at`: null
- `playwright_report_path`: null

## Face D -- Governance

Status: **BLOCK**

- `doc_governance`: true
- `plan_governance`: true
- `phase_tracking`: true
- `governance`: true
- `runtime_hygiene`: true
- `all_phases_closeout`: false
- `governance_check_timestamp`: "2026-05-31T09:03:13Z"

## Face E -- Perf

Status: **BLOCK**

- `lighthouse_scores`: {}
- `lighthouse_min_score`: null
- `bundle_first_screen_kb_gz`: null
- `bundle_total_main_routes_kb_gz`: null
- `cwv_lcp_ms`: null
- `cwv_inp_ms`: null
- `cwv_cls`: null
- `cwv_fcp_ms`: null
- `cwv_tbt_ms`: null
- `perf_snapshot_date`: null

## Block Reasons

- face_a: input_missing
- face_b: academic_artifact_missing
- face_c: input_missing
- face_d: checks_failed=['all_phases_closeout']
- face_e: input_missing

## Recommended Next Actions

- Hold release. Resolve all block reasons before re-running.
- Priority: resolve block reasons in order above.
- Re-run: `python scripts/evals/run_v5_release_gate.py`