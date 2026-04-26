# Real Golden Expansion v2.5 Report

## Scope
- Step5 only: real golden generation, consistency checks, and small smoke.
- Not executed: 64x3 official benchmark; 50-paper full benchmark.

## Corpus Consistency
- status: PASS
- manifest paper_count: 50
- parse paper_count: 50
- chunk paper_count(raw/rule/llm): 50/50/50
- collection entity_count(raw/rule/llm): 1222/1222/1222
- source_chunk_id alignment: True
- global_source_chunk_id_unique: True

## Golden Generation
- status: PASS
- paper_count covered: 50
- query_count: 98
- synthetic_paper_id_count: 0

## Family Coverage
- family_coverage_status: PASS
- queries_by_family: {'method': 25, 'fact': 25, 'numeric': 8, 'compare': 8, 'hard': 8, 'cross_paper': 8, 'table': 8, 'figure': 8}
- content_type_coverage: {'text': 98}

## Golden Consistency
- status: PASS
- expected_paper_id_exists: True
- expected_source_chunk_id_exists_in_artifact: True
- expected_source_chunk_id_exists_in_collection: True
- missing_evidence_count: 0

## Benchmark Guard
- status: PASS
- update: official mode requires explicit real golden path and enforces EVAL_BLOCKED on corpus mismatches.
- synthetic golden isolation: synthetic only allowed for smoke mode.
- verification_tests: apps/api/tests/test_benchmark_rejects_synthetic_official.py, apps/api/tests/test_benchmark_eval_blocked_on_corpus_mismatch.py, apps/api/tests/test_benchmark_runtime_profile_guard.py

## Small Validation Smoke
- status: PASS
- selected_count: 8
- missing_families: []

## Final Decision
- Corpus consistency: PASS
- Golden generation: PASS
- Golden consistency: PASS
- Family coverage: PASS
- Benchmark guard: PASS
- Next step allowed: Official RAG Evaluation ALLOWED
