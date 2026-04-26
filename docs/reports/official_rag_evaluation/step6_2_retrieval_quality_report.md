# Step6.2 Retrieval Quality Report

## Step6.1 Context

- Step6.1 diagnosis: PASS
- Blocked category: QUALITY_ERROR
- Step6 rerun allowed: ALLOWED
- Excluded: EVAL_ALIGNMENT_ERROR / INGEST_ALIGNMENT_ERROR / RETRIEVAL_RUNTIME_ERROR / EMBEDDING_SPACE_MISMATCH

## Baseline Retrieval

- baseline_recall_at_10: 0.0
- baseline_recall_at_50: 0.0
- baseline_recall_at_100: 0.0

## Candidate Recall Sweep

- see candidate_recall_sweep.json/.md

## Query Rewrite Ablation

- deterministic rewrite variants evaluated

## Sparse Hybrid Ablation

- mean_hybrid_gain: 0.0

## Rerank TopK Ablation

- pre/post rerank recall compared for candidate_k in [20,50,100,200]

## Content Type Routing Ablation

- routing_recall_at_10: 0.0

## Plus Failed Cases A/B

- plus_collection_exists: False
- failed_delta: None
- recommendation: insufficient_data_no_plus_collection

## Tuned Retrieval Config

- retrieve_top_k: 200
- sparse_top_k: 100
- final_candidate_k: 50
- rerank_top_k: 10
- use_query_rewrite: False
- use_sparse_hybrid: False
- use_content_type_routing: False

## Tuned 16x3

- recall_at_10: 0.0
- same_paper_hit_rate: 0.2812
- citation_coverage: 0.6042
- unsupported_claim_rate: 0.4896
- answer_evidence_consistency: 0.3295

## Final Decision

- Retrieval tuning: BLOCKED
- Recommended config: artifacts/benchmarks/v2_6_2/tuned_retrieval_config.json
- Step6 regression rerun: NOT_ALLOWED
- Official 64/80x3: NOT_ALLOWED
