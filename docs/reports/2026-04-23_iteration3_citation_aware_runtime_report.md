# 2026-04-23 Iteration 3 Report

## Scope

Completed Iteration 3 backend upgrade for academic RAG:

- citation-aware iterative retrieval
- first-pass retrieval evaluator
- outline-guided synthesis
- citation-aware graph reasoning expansion
- RAG response contract extension for retrieval trace and synthesis quality metadata
- test suite update to match the new orchestration framework

This change was implemented on top of the existing Iteration 1 and Iteration 2 retrieval stack, without replacing the existing multimodal or hybrid retrieval paths.

## Implemented Changes

### 1. Orchestrator v2

Updated `apps/api/app/core/agentic_retrieval.py` from a plain multi-round retriever into an Iteration 3 orchestrator with these behaviors:

- run first-pass retrieval
- evaluate retrieval quality before synthesis
- trigger iterative retrieval when evidence is weak
- apply query rewrite / summary fallback / relation-aware expansion / citation expansion / multi-subquestion refinement
- build answer outline before final synthesis
- carry retrieval trace and citation-aware metadata into the final response
- keep claim verification, citation verification, and abstention policy as end-of-pipeline gates

Added metadata fields from the orchestrator:

- `retrieval_evaluator`
- `iterative_retrieval_triggered`
- `iterative_actions`
- `retrieval_trace`
- `answer_outline`
- `citation_aware_metadata`
- `scientific_synthesis_metrics`

### 2. Retrieval Evaluator

Added new module `apps/api/app/core/retrieval_evaluator.py`.

Evaluator checks:

- score coverage
- evidence diversity
- paper concentration
- cross-paper coverage
- expected evidence type hit rate
- citation expansion trigger necessity

Weak retrieval now blocks direct synthesis and routes into iterative actions.

### 3. Planner Upgrade

Updated `apps/api/app/core/query_planner.py` to emit Iteration 3 planning signals:

- `evidence_plan`
- `iterative_actions`

These planner hints now drive whether compare/evolution/survey/numeric queries should require:

- cross-paper coverage
- citation expansion
- summary fallback
- relation-aware expansion
- multi-subquestion retrieval

### 4. Graph Retrieval Upgrade

Updated `apps/api/app/core/graph_retrieval_service.py` with citation-aware reasoning support:

- foundational references
- follow-up work
- competing/refuting lines
- evolution chain hints
- merged candidate expansion output

This is still a lightweight reasoning layer, but it is now consumed by the retrieval runtime rather than existing as display-only support.

### 5. API Contract Upgrade

Updated `apps/api/app/api/rag.py` to expose new Iteration 3 response fields:

- `retrievalEvaluator`
- `iterativeRetrievalTriggered`
- `retrievalTrace`
- `citationAwareMetadata`
- `scientificSynthesisMetrics`

Cache read/write paths were updated so cached responses preserve the same Iteration 3 structure.

### 6. Reranker Compatibility Fix

Updated `apps/api/app/core/retrieval_scoring.py` to support both:

- full structured reranker document format
- compact legacy structured document format

This preserved compatibility with existing tests and older reranker payload shapes.

### 7. Documentation

Updated `docs/architecture/api-contract.md` with the Iteration 3 response contract additions.

## Test Updates

Added new tests:

- `apps/api/tests/unit/test_retrieval_evaluator.py`
- `apps/api/tests/unit/test_agentic_iteration3.py`

Updated existing tests:

- `apps/api/tests/unit/test_academic_query_planner.py`
- `apps/api/tests/unit/test_graph_retrieval_service.py`
- `apps/api/tests/integration/test_rag_claim_verification.py`

Coverage focus for Iteration 3:

- weak first-pass detection
- iterative retrieval trigger behavior
- citation-aware expansion metadata
- outline-guided synthesis metadata surface
- planner evidence plan / iterative action hints
- graph citation reasoning output
- RAG contract propagation

## Real Validation Run

Important clarification:

- In this report, `Real Validation Run` means the code was validated against the repository's real pytest regression suite in the current environment.
- It does **not** mean that a real-paper offline benchmark corpus was executed for the new Iteration 3 synthesis metrics.
- That omission happened because the existing repo benchmark tooling is split:
  - the current pytest/integration suite validates runtime behavior and contract propagation;
  - the existing retrieval benchmark harness targets retrieval metrics on a retrieval corpus;
  - the new Iteration 3 synthesis metrics (`citation_faithfulness`, `cross_paper_synthesis_quality`, `partial_abstain_quality`) are not yet wired into a real-corpus offline evaluation pipeline.
- Additionally, the default `tests/evals/golden_queries.json` retrieval harness dataset is a synthetic test dataset (`test-paper-001`, etc.), not the production-style real-paper corpus used by the dual-stack retrieval matrix.

### Passing Regression Batch

Executed from `apps/api`:

```bash
/Users/cc/.virtualenvs/scholar-ai-api/bin/python -m pytest \
  tests/unit/test_retrieval_scoring.py \
  tests/unit/test_multimodal_search_service_intent.py \
  tests/unit/test_retrieval_evidence_contract.py \
  tests/unit/test_retrieval_trace.py \
  tests/unit/test_sparse_recall.py \
  tests/unit/test_academic_query_planner.py \
  tests/unit/test_graph_retrieval_service.py \
  tests/unit/test_retrieval_evaluator.py \
  tests/unit/test_agentic_iteration3.py \
  tests/integration/test_rag_claim_verification.py \
  tests/integration/test_rag_query_planning_flow.py \
  tests/integration/test_graph_augmented_rag.py \
  -q
```

Result:

- `31 passed`
- `1 warning`
- total runtime about `390.42s`

### Focused Validation Runs

Also confirmed separately:

- `tests/unit/test_retrieval_scoring.py` -> passed after reranker compatibility fix
- focused Iteration 3 tests -> passed

## Known Blockers Observed During Validation

Two additional tests were not usable in the current environment because of a pre-existing FastAPI / Starlette compatibility issue during import-time router construction:

- `tests/unit/test_rag_confidence.py`
- `tests/integration/test_rag_api_unified.py`

Observed error:

```text
TypeError: Router.__init__() got an unexpected keyword argument 'on_startup'
```

This issue is environment/framework compatibility and is not introduced by the Iteration 3 change set.

## Acceptance Status Against Iteration 3 Goals

### A. Retrieval Evaluator

Status: implemented

- weak retrieval can now be detected before synthesis
- evaluator checks include score coverage, concentration, cross-paper coverage, and evidence-type coverage

### B. Iterative Retrieval

Status: implemented

- query rewrite
- citation expansion
- summary fallback
- relation-aware candidate expansion
- multi-subquestion refinement

### C. Citation-Aware Reasoning

Status: implemented in lightweight runtime form

- foundational
- follow-up
- competing/refuting
- evolution chain

### D. Outline-Guided Synthesis

Status: implemented

- answer outline is built before final synthesis
- synthesis prompt is outline-driven

### E. Scientific Synthesis Eval Alignment

Status: partially implemented at runtime metadata level

Runtime now surfaces:

- `citation_faithfulness`
- `unsupported_claim_rate`
- `cross_paper_synthesis_quality`
- `partial_abstain_quality`

What is still pending for a full production-grade scientific synthesis eval loop:

- offline benchmark dataset wiring for these metrics
- automated report generation over a real evaluation corpus

## Files Changed

- `apps/api/app/core/agentic_retrieval.py`
- `apps/api/app/core/retrieval_evaluator.py`
- `apps/api/app/core/query_planner.py`
- `apps/api/app/core/graph_retrieval_service.py`
- `apps/api/app/core/retrieval_scoring.py`
- `apps/api/app/api/rag.py`
- `apps/api/tests/unit/test_retrieval_evaluator.py`
- `apps/api/tests/unit/test_agentic_iteration3.py`
- `apps/api/tests/unit/test_academic_query_planner.py`
- `apps/api/tests/unit/test_graph_retrieval_service.py`
- `apps/api/tests/integration/test_rag_claim_verification.py`
- `docs/architecture/api-contract.md`

## Conclusion

Iteration 3 runtime is now in place and validated against the repository's existing retrieval-oriented regression slice.

Current status:

- Iteration 3 orchestration implemented
- tests updated to match the new framework
- real regression suite passed: `31/31`
- one pre-existing framework compatibility issue remains outside this change set and blocks two extra tests during import-time collection