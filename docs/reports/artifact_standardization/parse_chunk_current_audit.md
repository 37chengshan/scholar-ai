# Parse/Chunk Current Audit

## Scope

Audit target: parse/chunk production and benchmark dependency paths before ParseArtifact/ChunkArtifact standardization.

## Findings

| file | function/path | current output | destination | risk | action |
|---|---|---|---|---|---|
| apps/api/app/core/docling_service.py | parse_pdf | dict(markdown/items/page_count/metadata) | in-memory `ctx.parse_result` | no formal contract object | wrap into ParseArtifact and persist |
| apps/api/app/core/docling_service.py | _parse_pdf_with_pypdf | pypdf fallback parse_mode | in-memory only | fallback quality semantics not standardized | enforce ParseArtifact parse_mode/quality rules |
| apps/api/app/workers/storage_manager.py | _store_vectors | semantic chunk list + text records | Milvus insert payload | second-loop variable leakage risk | build records from per-chunk artifact only |
| apps/api/app/core/chunk_identity.py | build_stable_chunk_id | stage-agnostic chunk id | runtime metadata | cannot represent cross-stage source identity | introduce source_chunk_id in ChunkArtifact |
| scripts/evals/parse_and_rebuild.py | legacy parse path | script-level parse/rebuild | eval support script | violated no-self-parse policy | switch to artifact consumption |
| scripts/evals/v2_3_benchmark.py | official benchmark path | collection query-only | benchmark reports | no artifact presence gate | add ParseArtifact/ChunkArtifact dependency guard |

## Risk Summary

- Official benchmark could run without standardized parse/chunk provenance.
- Chunk identity fields could drift due to loop-local variable leakage.
- raw/rule/llm stage alignment had no formal invariant or contract test.

## Implemented Direction

- ParseArtifact and ChunkArtifact contracts added under app/contracts.
- PDF coordinator persists parse artifact to artifacts/papers/{paper_id}/parse_artifact.json.
- Storage manager now generates and persists chunks_raw/chunks_rule/chunks_llm artifacts and consumes raw artifact records for vector writes.
- Official benchmark adds EVAL_BLOCKED when required artifacts are missing.
