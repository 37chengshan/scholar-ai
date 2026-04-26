# API Flash Ingestion v2.4 Report

## Scope

- Official provider/model: tongyi / tongyi-embedding-vision-flash-2026-03-06
- Runtime profile target: api_flash_qwen_rerank_glm
- Collection target suffix: v2_4
- Output directory: artifacts/benchmarks/v2_4

## Gate Results (11 Items)

| # | Check | Result | Evidence |
|---|---|---|---|
| 1 | Provider probe main gate | PASS | provider_probe.json: status=PASS, dimension=1024 |
| 2 | Artifact consistency gate | BLOCKED | artifact_consistency_report.json: artifact_root_missing_or_empty:artifacts/papers |
| 3 | Ingest dry-run gate | BLOCKED | api_flash_ingest_report_dry_run.json: INGEST_BLOCKED:artifact_root_missing_or_empty |
| 4 | Ingest real-run gate | BLOCKED | api_flash_ingest_report.json: INGEST_BLOCKED:artifact_root_missing_or_empty |
| 5 | Schema audit gate | PASS | api_flash_schema_audit.json: status=PASS, required fields present, dim=1024 |
| 6 | Preflight search/hydration gate | BLOCKED | api_flash_preflight.json: preflight_stage_failed:raw (0 entities) |
| 7 | Smoke 1x3 gate | BLOCKED | api_flash_smoke_1x3.json: smoke_stage_failed:raw (0 entities) |
| 8 | Ingest fallback usage gate | PASS | api_flash_ingest_report.json: fallback_used=false |
| 9 | Ingest deprecated branch usage gate | PASS | api_flash_ingest_report.json: deprecated_branch_used=false |
| 10 | Preflight fallback usage gate | PASS | api_flash_preflight.json: fallback_used=false |
| 11 | Smoke deprecated branch usage gate | PASS | api_flash_smoke_1x3.json: deprecated_branch_used=false |

## Key Observations

- Provider text and batch embedding are healthy and dimension-stable at 1024.
- Provider image probe returns 400 on aliased model (recorded as non-blocking note), while core embedding readiness is PASS.
- The primary blocker is empty/missing official artifacts root at artifacts/papers.
- Because no ingest source exists, downstream retrieval-based gates (preflight/smoke) are expected BLOCKED.

## Next Step Allowed

- Decision: NOT ALLOWED
- Reason: Official ingestion source artifacts are missing, so ingestion must remain blocked by policy.

## Required Unblock Action

1. Materialize official parse/chunk artifacts under artifacts/papers/{paper_id}/
2. Ensure each paper has parse_artifact.json, chunks_raw.json, chunks_rule.json, chunks_llm.json
3. Re-run this sequence:
   - scripts/evals/v2_4_provider_probe.py
   - scripts/evals/v2_4_validate_artifacts.py
   - scripts/evals/v2_4_build_api_flash_collections.py --dry-run
   - scripts/evals/v2_4_build_api_flash_collections.py
   - scripts/evals/v2_4_api_flash_schema_audit.py
   - scripts/evals/v2_4_api_flash_preflight.py
   - scripts/evals/v2_4_api_flash_smoke_1x3.py
