# v3.0-H Runtime Validation Matrix

## Focus

- Validate that every critical chain can report resolved runtime truth.
- Reject silent fallback from `online` request to `local` / `shim` / `lite`.

## Matrix

| Test Case | Requested Mode | Resolved Truth Required | Current expectation |
| --- | --- | --- | --- |
| Search -> Read -> Chat | `online` | answer payload or trace includes runtime truth | may report degraded if embedding is still local |
| KB -> Review | `online` | review run / validation report includes runtime truth | may report degraded if retrieval or vector path falls back |
| Compare | `online` | compare benchmark must declare shim parity explicitly | currently shim-backed until real online embedding path exists |
| Offline academic baseline | `public_offline` | `meta.json.runtime_truth` present | required for gate |
| Candidate vs baseline | `public_offline` | `mode_parity_with_baseline` present | required for gate |

## Interpretation

- `resolved_mode=online` means true online provider usage.
- `resolved_mode=local` means the app path still used node-local models.
- `resolved_mode=shim` means deterministic benchmark/retrieval compatibility path.
- `resolved_mode=lite` means Milvus server degraded to Milvus Lite.
