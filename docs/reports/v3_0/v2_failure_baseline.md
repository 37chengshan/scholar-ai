# ScholarAI v3.0 - v2 Failure Baseline

## Frozen Baseline

- source: v2_6_2
- status: FROZEN
- retrieval_tuning: BLOCKED
- step6_regression_rerun: NOT_ALLOWED
- official_64_80x3: NOT_ALLOWED

## Metrics

- recall@10: 0.0
- recall@50: 0.0
- recall@100: 0.0
- same_paper_hit_rate: 0.2812
- citation_coverage: 0.6042
- unsupported_claim_rate: 0.4896
- answer_evidence_consistency: 0.3295

## Hard Constraints

- do not modify Step5 real golden
- do not re-parse PDF / re-chunk
- do not rebuild v2_4 evidence chunk collection
- do not replace primary embedding model
- do not re-introduce BGE/SPECTER2/local qwen into main chain
- do not run official 64/80x3 before v3 16x3 pass
