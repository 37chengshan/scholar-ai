# Benchmark Artifact Dependency Report

## Objective

Ensure official benchmark execution depends on standardized ParseArtifact/ChunkArtifact outputs and does not perform ad-hoc PDF parsing.

## Changes

- `scripts/evals/v2_3_benchmark.py`
  - Added `validate_required_artifacts(rows, artifacts_root)`.
  - Official gate now checks, per paper_id, required files:
    - parse_artifact.json
    - chunks_raw.json
    - chunks_rule.json
    - chunks_llm.json
  - Missing files cause `BenchmarkGuardError` with `EVAL_BLOCKED` reason.

- `scripts/evals/parse_and_rebuild.py`
  - Removed script-level PDF parsing path.
  - Rebuild now loads standardized `chunks_raw.json` artifacts.
  - Destructive collection drop requires explicit `--allow-drop-collection`.

## Policy Alignment

- Official benchmark path no longer supports self-parse behavior.
- Artifact completeness is now a hard precondition for official gate.
- Synthetic smoke and local ad-hoc tooling remain separate from official eval gate semantics.
