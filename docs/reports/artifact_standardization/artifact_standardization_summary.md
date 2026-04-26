# ParseArtifact / ChunkArtifact Standardization Summary

## 1. Audit

- Completed parse/chunk/benchmark path audit and recorded current state risks.
- See `parse_chunk_current_audit.md` for file-level risk/action mapping.

## 2. Contracts

- Added canonical contracts in code:
  - `app/contracts/parse_artifact.py`
  - `app/contracts/chunk_artifact.py`
- Added contract docs:
  - `docs/contracts/parse_artifact_contract.md`
  - `docs/contracts/chunk_artifact_contract.md`
  - `docs/contracts/milvus_schema_v3_contract.md`

## 3. Pipeline Integration

- `PDFCoordinator` now builds and persists ParseArtifact to:
  - `artifacts/papers/{paper_id}/parse_artifact.json`
- `StorageManager` now:
  - consumes ParseArtifact items,
  - builds raw ChunkArtifact list,
  - derives rule/llm stage artifacts with shared source_chunk_id,
  - persists:
    - `chunks_raw.json`
    - `chunks_rule.json`
    - `chunks_llm.json`

## 4. Identity and Leakage Fix

- Fixed chunk metadata leakage risk by constructing text records from current chunk artifact fields only.
- Added first-class identity keys in record payload (`chunk_id`, `source_chunk_id`, `stage`, `parent_source_chunk_id`) and evidence metadata.

## 5. Benchmark Gate

- Official benchmark now requires ParseArtifact + stage chunk artifacts per paper.
- Missing artifact files now return `EVAL_BLOCKED`.
- Legacy rebuild script no longer parses PDFs; it consumes chunk artifacts.

## 6. Tests

Added tests:
- `test_parse_artifact_contract.py`
- `test_chunk_artifact_contract.py`
- `test_chunk_identity_regression.py`
- `test_benchmark_requires_artifacts.py`

Plus existing runtime benchmark guard tests continue to apply.
