# v3.0-H Execution Plan Review

## Status

Phase H has been rebuilt from the acceptance criteria instead of the previous self-certification note.

## Shipped in this pass

### WP0 / WP1

- Added `app.core.runtime_contract.RuntimeBinding` to freeze requested-vs-resolved runtime truth.
- Provider inventory and contract documents now distinguish `online`, `local`, `shim`, and `lite` by actual wiring, not intention.

### WP2

- Main multimodal app entry points now resolve through `app.core.embedding.factory` rather than importing `get_qwen3vl_service()` directly:
  - `workers/pdf_coordinator.py`
  - `workers/extraction_pipeline.py`
  - `workers/pdf_worker.py`
  - `core/image_extractor.py`
  - `core/table_extractor.py`
  - `core/multimodal_indexer.py`
  - `core/page_clustering.py`
  - `core/semantic_cache.py`
  - `core/celery_config.py`

### WP3

- `model_gateway.py` shim provider now exposes explicit runtime binding metadata.
- `milvus_service.py` now reports `online` vs `lite` truth through a stable binding instead of silent fallback.
- The previous false “done” state in `milvus_service.py` that introduced an `IndentationError` has been removed.

### WP4 / WP5

- `rag_v3/main_path_service.py` now surfaces runtime truth in retrieval diagnostics/payloads.
- `real_world_validation_service.py` now renders run-level `runtime_truth` when present.
- `eval_service.py` now validates `runtime_truth` and candidate baseline parity metadata for `v3_0_academic`.
- `scripts/evals/v3_0_seed_runs.py` now seeds runtime truth and parity metadata.

## Remaining gap to call Phase H fully complete

Phase H is now honest, but it is not yet the same thing as “all critical paths are truly online”.

The remaining blocker is explicit:

1. Main app embedding/reranker paths still resolve to local model services by default.
2. Retrieval benchmark paths still use deterministic shim providers.
3. Therefore `RUNTIME_MODE=online` can now be detected as degraded when the resolved provider is actually `local` or `shim`.

## Review conclusion

This pass completes the Phase H honesty/unification work and removes the false-positive review state. It does not claim that a real online embedding provider has already replaced the local/shim implementations.
