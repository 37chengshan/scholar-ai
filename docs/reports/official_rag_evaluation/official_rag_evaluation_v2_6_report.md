# Official RAG Evaluation v2.6

## Inputs

- golden_file: ../../artifacts/benchmarks/v2_5/golden_queries_real_50.json
- consistency_file: /Users/cc/scholar-ai-deploy/scholar-ai-project/scholar-ai/artifacts/benchmarks/v2_5/golden_consistency_50.json
- family_stats_file: /Users/cc/scholar-ai-deploy/scholar-ai-project/scholar-ai/artifacts/benchmarks/v2_5/golden_family_stats_50.json
- runtime_profile: api_flash_qwen_rerank_glm
- collection_suffix: v2_4
- raw_collection: paper_contents_v2_api_tongyi_flash_raw_v2_4
- rule_collection: paper_contents_v2_api_tongyi_flash_rule_v2_4
- llm_collection: paper_contents_v2_api_tongyi_flash_llm_v2_4

## Regression 16x3

- status: BLOCKED
- reasons: citation_coverage, unsupported_claim_rate
- total: 48
- citation_coverage: 0.7431
- unsupported_claim_rate: 0.4507
- answer_evidence_consistency: 0.3191
- recall_at_10: 0.0

## Official Stage Results

## Comparison


## Failures

- failed_queries: 0
- timeout_queries: 0

## Final Gate

- Official 64/80x3: BLOCKED
- Default stage: raw
- API flash as official RAG: NOT_ALLOWED
- Step7 Product Integration: NOT_ALLOWED
