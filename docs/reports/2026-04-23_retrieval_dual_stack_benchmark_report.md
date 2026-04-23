# 2026-04-23 Retrieval Dual Stack Benchmark Report

## Matrix execution status

| dataset | model_stack | reranker | round | status |
|---|---|---|---|---|
| large | bge_dual | off | round1 | ok |
| large | bge_dual | off | round2 | ok |
| large | bge_dual | on | round1 | ok |
| large | bge_dual | on | round2 | ok |
| large | qwen_dual | off | round1 | ok |
| large | qwen_dual | off | round2 | ok |
| large | qwen_dual | on | round1 | ok |
| large | qwen_dual | on | round2 | ok |
| xlarge | bge_dual | off | round1 | ok |
| xlarge | bge_dual | off | round2 | ok |
| xlarge | bge_dual | on | round1 | ok |
| xlarge | bge_dual | on | round2 | ok |
| xlarge | qwen_dual | off | round1 | ok |
| xlarge | qwen_dual | off | round2 | ok |
| xlarge | qwen_dual | on | round1 | ok |
| xlarge | qwen_dual | on | round2 | ok |

## Table 1 - 12 papers summary

| model_stack | reranker | round1_recall@5 | round2_recall@5 | avg_recall@5 | avg_mrr | avg_paper_hit | avg_section_hit | avg_chunk_hit | avg_cross_paper_r@5 | avg_hard_hit | avg_latency_ms | p95_latency_ms |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| bge_dual | off | 0.9306 | 0.9306 | 0.9306 | 1.0000 | 0.9306 | 0.1354 | 0.0000 | 1.0000 | 0.5000 | 861.4472 | 941.0154 |
| bge_dual | on | 0.8819 | 0.8819 | 0.8819 | 1.0000 | 0.8819 | 0.1354 | 0.0000 | 1.0000 | 0.2500 | 1603.9134 | 3727.3871 |
| qwen_dual | off | 0.8889 | 0.8889 | 0.8889 | 1.0000 | 0.8889 | 0.1354 | 0.0000 | 1.0000 | 0.2000 | 2241.6154 | 2712.4329 |
| qwen_dual | on | 0.8889 | 0.8889 | 0.8889 | 1.0000 | 0.8889 | 0.1354 | 0.0000 | 1.0000 | 0.2000 | 5431.5113 | 14328.0583 |

## Table 2 - 50 papers summary

| model_stack | reranker | round1_recall@5 | round2_recall@5 | avg_recall@5 | avg_mrr | avg_paper_hit | avg_section_hit | avg_chunk_hit | avg_cross_paper_r@5 | avg_hard_hit | avg_latency_ms | p95_latency_ms |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| bge_dual | off | 0.9800 | 0.9800 | 0.9800 | 0.9800 | 0.9800 | 0.2450 | 0.0000 | 0.0000 | 0.0000 | 1058.8251 | 1214.1302 |
| bge_dual | on | 0.9800 | 0.9800 | 0.9800 | 0.9800 | 0.9800 | 0.2450 | 0.0000 | 0.0000 | 0.0000 | 1039.1042 | 1145.0083 |
| qwen_dual | off | 0.9800 | 0.9800 | 0.9800 | 0.9800 | 0.9800 | 0.2450 | 0.0000 | 0.0000 | 0.0000 | 2555.8887 | 4762.9547 |
| qwen_dual | on | 0.9800 | 0.9800 | 0.9800 | 0.9800 | 0.9800 | 0.2450 | 0.0000 | 0.0000 | 0.0000 | 2613.6965 | 5273.8231 |

## Table 3 - reranker A/B gain

| dataset | model_stack | metric | reranker_off_avg | reranker_on_avg | delta |
|---|---|---|---:|---:|---:|
| large | bge_dual | recall@5 | 0.9306 | 0.8819 | -0.0486 |
| large | bge_dual | section_hit | 0.1354 | 0.1354 | 0.0000 |
| large | bge_dual | chunk_hit | 0.0000 | 0.0000 | 0.0000 |
| large | bge_dual | cross_paper_r@5 | 1.0000 | 1.0000 | 0.0000 |
| large | qwen_dual | recall@5 | 0.8889 | 0.8889 | 0.0000 |
| large | qwen_dual | section_hit | 0.1354 | 0.1354 | 0.0000 |
| large | qwen_dual | chunk_hit | 0.0000 | 0.0000 | 0.0000 |
| large | qwen_dual | cross_paper_r@5 | 1.0000 | 1.0000 | 0.0000 |
| xlarge | bge_dual | recall@5 | 0.9800 | 0.9800 | 0.0000 |
| xlarge | bge_dual | section_hit | 0.2450 | 0.2450 | 0.0000 |
| xlarge | bge_dual | chunk_hit | 0.0000 | 0.0000 | 0.0000 |
| xlarge | bge_dual | cross_paper_r@5 | 0.0000 | 0.0000 | 0.0000 |
| xlarge | qwen_dual | recall@5 | 0.9800 | 0.9800 | 0.0000 |
| xlarge | qwen_dual | section_hit | 0.2450 | 0.2450 | 0.0000 |
| xlarge | qwen_dual | chunk_hit | 0.0000 | 0.0000 | 0.0000 |
| xlarge | qwen_dual | cross_paper_r@5 | 0.0000 | 0.0000 | 0.0000 |

## Table 4 - BGE vs Qwen

| dataset | reranker_state | metric | bge_avg | qwen_avg | delta(qwen-bge) |
|---|---|---|---:|---:|---:|
| large | off | recall@5 | 0.9306 | 0.8889 | -0.0417 |
| large | off | section_hit | 0.1354 | 0.1354 | 0.0000 |
| large | off | chunk_hit | 0.0000 | 0.0000 | 0.0000 |
| large | off | cross_paper_r@5 | 1.0000 | 1.0000 | 0.0000 |
| large | on | recall@5 | 0.8819 | 0.8889 | 0.0069 |
| large | on | section_hit | 0.1354 | 0.1354 | 0.0000 |
| large | on | chunk_hit | 0.0000 | 0.0000 | 0.0000 |
| large | on | cross_paper_r@5 | 1.0000 | 1.0000 | 0.0000 |
| xlarge | off | recall@5 | 0.9800 | 0.9800 | 0.0000 |
| xlarge | off | section_hit | 0.2450 | 0.2450 | 0.0000 |
| xlarge | off | chunk_hit | 0.0000 | 0.0000 | 0.0000 |
| xlarge | off | cross_paper_r@5 | 0.0000 | 0.0000 | 0.0000 |
| xlarge | on | recall@5 | 0.9800 | 0.9800 | 0.0000 |
| xlarge | on | section_hit | 0.2450 | 0.2450 | 0.0000 |
| xlarge | on | chunk_hit | 0.0000 | 0.0000 | 0.0000 |
| xlarge | on | cross_paper_r@5 | 0.0000 | 0.0000 | 0.0000 |

## Table 5 - failure query classification

| dataset | model_stack | reranker | query_id | query_type | failure_type | possible_cause |
|---|---|---|---|---|---|---|
| large | bge_dual | off | hard-007 | hard | section_miss | section normalization or query mismatch |
| large | bge_dual | off | hard-009 | hard | section_miss | section normalization or query mismatch |
| large | bge_dual | off | hard-011 | hard | section_miss | section normalization or query mismatch |
| large | bge_dual | off | hard-012 | hard | section_miss | section normalization or query mismatch |
| large | bge_dual | off | hard-013 | hard | section_miss | section normalization or query mismatch |
| large | bge_dual | off | hard-014 | hard | section_miss | section normalization or query mismatch |
| large | bge_dual | off | hard-015 | hard | section_miss | section normalization or query mismatch |
| large | bge_dual | off | hard-016 | hard | section_miss | section normalization or query mismatch |
| large | bge_dual | off | hard-017 | hard | section_miss | section normalization or query mismatch |
| large | bge_dual | off | hard-018 | hard | section_miss | section normalization or query mismatch |
| large | bge_dual | off | hard-007 | hard | section_miss | section normalization or query mismatch |
| large | bge_dual | off | hard-009 | hard | section_miss | section normalization or query mismatch |
| large | bge_dual | off | hard-011 | hard | section_miss | section normalization or query mismatch |
| large | bge_dual | off | hard-012 | hard | section_miss | section normalization or query mismatch |
| large | bge_dual | off | hard-013 | hard | section_miss | section normalization or query mismatch |
| large | bge_dual | off | hard-014 | hard | section_miss | section normalization or query mismatch |
| large | bge_dual | off | hard-015 | hard | section_miss | section normalization or query mismatch |
| large | bge_dual | off | hard-016 | hard | section_miss | section normalization or query mismatch |
| large | bge_dual | off | hard-017 | hard | section_miss | section normalization or query mismatch |
| large | bge_dual | off | hard-018 | hard | section_miss | section normalization or query mismatch |
| large | bge_dual | on | hard-002 | hard | section_miss | section normalization or query mismatch |
| large | bge_dual | on | hard-004 | hard | section_miss | section normalization or query mismatch |
| large | bge_dual | on | hard-006 | hard | section_miss | section normalization or query mismatch |
| large | bge_dual | on | hard-007 | hard | section_miss | section normalization or query mismatch |
| large | bge_dual | on | hard-008 | hard | section_miss | section normalization or query mismatch |
| large | bge_dual | on | hard-009 | hard | section_miss | section normalization or query mismatch |
| large | bge_dual | on | hard-011 | hard | section_miss | section normalization or query mismatch |
| large | bge_dual | on | hard-012 | hard | section_miss | section normalization or query mismatch |
| large | bge_dual | on | hard-013 | hard | section_miss | section normalization or query mismatch |
| large | bge_dual | on | hard-014 | hard | section_miss | section normalization or query mismatch |
| large | bge_dual | on | hard-015 | hard | section_miss | section normalization or query mismatch |
| large | bge_dual | on | hard-016 | hard | section_miss | section normalization or query mismatch |
| large | bge_dual | on | hard-017 | hard | section_miss | section normalization or query mismatch |
| large | bge_dual | on | hard-018 | hard | section_miss | section normalization or query mismatch |
| large | bge_dual | on | hard-020 | hard | section_miss | section normalization or query mismatch |
| large | bge_dual | on | hard-002 | hard | section_miss | section normalization or query mismatch |
| large | bge_dual | on | hard-004 | hard | section_miss | section normalization or query mismatch |
| large | bge_dual | on | hard-006 | hard | section_miss | section normalization or query mismatch |
| large | bge_dual | on | hard-007 | hard | section_miss | section normalization or query mismatch |
| large | bge_dual | on | hard-008 | hard | section_miss | section normalization or query mismatch |
| large | bge_dual | on | hard-009 | hard | section_miss | section normalization or query mismatch |
| large | bge_dual | on | hard-011 | hard | section_miss | section normalization or query mismatch |
| large | bge_dual | on | hard-012 | hard | section_miss | section normalization or query mismatch |
| large | bge_dual | on | hard-013 | hard | section_miss | section normalization or query mismatch |
| large | bge_dual | on | hard-014 | hard | section_miss | section normalization or query mismatch |
| large | bge_dual | on | hard-015 | hard | section_miss | section normalization or query mismatch |
| large | bge_dual | on | hard-016 | hard | section_miss | section normalization or query mismatch |
| large | bge_dual | on | hard-017 | hard | section_miss | section normalization or query mismatch |
| large | bge_dual | on | hard-018 | hard | section_miss | section normalization or query mismatch |
| large | bge_dual | on | hard-020 | hard | section_miss | section normalization or query mismatch |
| large | qwen_dual | off | hard-001 | hard | section_miss | section normalization or query mismatch |
| large | qwen_dual | off | hard-003 | hard | section_miss | section normalization or query mismatch |
| large | qwen_dual | off | hard-005 | hard | section_miss | section normalization or query mismatch |
| large | qwen_dual | off | hard-006 | hard | section_miss | section normalization or query mismatch |
| large | qwen_dual | off | hard-008 | hard | section_miss | section normalization or query mismatch |
| large | qwen_dual | off | hard-009 | hard | section_miss | section normalization or query mismatch |
| large | qwen_dual | off | hard-010 | hard | section_miss | section normalization or query mismatch |
| large | qwen_dual | off | hard-011 | hard | section_miss | section normalization or query mismatch |
| large | qwen_dual | off | hard-012 | hard | section_miss | section normalization or query mismatch |
| large | qwen_dual | off | hard-013 | hard | section_miss | section normalization or query mismatch |
| large | qwen_dual | off | hard-014 | hard | section_miss | section normalization or query mismatch |
| large | qwen_dual | off | hard-015 | hard | section_miss | section normalization or query mismatch |
| large | qwen_dual | off | hard-017 | hard | section_miss | section normalization or query mismatch |
| large | qwen_dual | off | hard-018 | hard | section_miss | section normalization or query mismatch |
| large | qwen_dual | off | hard-019 | hard | section_miss | section normalization or query mismatch |
| large | qwen_dual | off | hard-020 | hard | section_miss | section normalization or query mismatch |
| large | qwen_dual | off | hard-001 | hard | section_miss | section normalization or query mismatch |
| large | qwen_dual | off | hard-003 | hard | section_miss | section normalization or query mismatch |
| large | qwen_dual | off | hard-005 | hard | section_miss | section normalization or query mismatch |
| large | qwen_dual | off | hard-006 | hard | section_miss | section normalization or query mismatch |
| large | qwen_dual | off | hard-008 | hard | section_miss | section normalization or query mismatch |
| large | qwen_dual | off | hard-009 | hard | section_miss | section normalization or query mismatch |
| large | qwen_dual | off | hard-010 | hard | section_miss | section normalization or query mismatch |
| large | qwen_dual | off | hard-011 | hard | section_miss | section normalization or query mismatch |
| large | qwen_dual | off | hard-012 | hard | section_miss | section normalization or query mismatch |
| large | qwen_dual | off | hard-013 | hard | section_miss | section normalization or query mismatch |
| large | qwen_dual | off | hard-014 | hard | section_miss | section normalization or query mismatch |
| large | qwen_dual | off | hard-015 | hard | section_miss | section normalization or query mismatch |
| large | qwen_dual | off | hard-017 | hard | section_miss | section normalization or query mismatch |
| large | qwen_dual | off | hard-018 | hard | section_miss | section normalization or query mismatch |
| large | qwen_dual | off | hard-019 | hard | section_miss | section normalization or query mismatch |
| large | qwen_dual | off | hard-020 | hard | section_miss | section normalization or query mismatch |
| large | qwen_dual | on | hard-001 | hard | section_miss | section normalization or query mismatch |
| large | qwen_dual | on | hard-003 | hard | section_miss | section normalization or query mismatch |
| large | qwen_dual | on | hard-005 | hard | section_miss | section normalization or query mismatch |
| large | qwen_dual | on | hard-006 | hard | section_miss | section normalization or query mismatch |
| large | qwen_dual | on | hard-008 | hard | section_miss | section normalization or query mismatch |
| large | qwen_dual | on | hard-009 | hard | section_miss | section normalization or query mismatch |
| large | qwen_dual | on | hard-010 | hard | section_miss | section normalization or query mismatch |
| large | qwen_dual | on | hard-011 | hard | section_miss | section normalization or query mismatch |
| large | qwen_dual | on | hard-012 | hard | section_miss | section normalization or query mismatch |
| large | qwen_dual | on | hard-013 | hard | section_miss | section normalization or query mismatch |
| large | qwen_dual | on | hard-014 | hard | section_miss | section normalization or query mismatch |
| large | qwen_dual | on | hard-015 | hard | section_miss | section normalization or query mismatch |
| large | qwen_dual | on | hard-017 | hard | section_miss | section normalization or query mismatch |
| large | qwen_dual | on | hard-018 | hard | section_miss | section normalization or query mismatch |
| large | qwen_dual | on | hard-019 | hard | section_miss | section normalization or query mismatch |
| large | qwen_dual | on | hard-020 | hard | section_miss | section normalization or query mismatch |
| large | qwen_dual | on | hard-001 | hard | section_miss | section normalization or query mismatch |
| large | qwen_dual | on | hard-003 | hard | section_miss | section normalization or query mismatch |
| large | qwen_dual | on | hard-005 | hard | section_miss | section normalization or query mismatch |
| large | qwen_dual | on | hard-006 | hard | section_miss | section normalization or query mismatch |
| large | qwen_dual | on | hard-008 | hard | section_miss | section normalization or query mismatch |
| large | qwen_dual | on | hard-009 | hard | section_miss | section normalization or query mismatch |
| large | qwen_dual | on | hard-010 | hard | section_miss | section normalization or query mismatch |
| large | qwen_dual | on | hard-011 | hard | section_miss | section normalization or query mismatch |
| large | qwen_dual | on | hard-012 | hard | section_miss | section normalization or query mismatch |
| large | qwen_dual | on | hard-013 | hard | section_miss | section normalization or query mismatch |
| large | qwen_dual | on | hard-014 | hard | section_miss | section normalization or query mismatch |
| large | qwen_dual | on | hard-015 | hard | section_miss | section normalization or query mismatch |
| large | qwen_dual | on | hard-017 | hard | section_miss | section normalization or query mismatch |
| large | qwen_dual | on | hard-018 | hard | section_miss | section normalization or query mismatch |
| large | qwen_dual | on | hard-019 | hard | section_miss | section normalization or query mismatch |
| large | qwen_dual | on | hard-020 | hard | section_miss | section normalization or query mismatch |
| xlarge | bge_dual | off | xlarge-p-034-topic | single_topic | section_miss | section normalization or query mismatch |
| xlarge | bge_dual | off | xlarge-p-034-section | single_section | section_miss | section normalization or query mismatch |
| xlarge | bge_dual | off | xlarge-p-034-topic | single_topic | section_miss | section normalization or query mismatch |
| xlarge | bge_dual | off | xlarge-p-034-section | single_section | section_miss | section normalization or query mismatch |
| xlarge | bge_dual | on | xlarge-p-034-topic | single_topic | section_miss | section normalization or query mismatch |
| xlarge | bge_dual | on | xlarge-p-034-section | single_section | section_miss | section normalization or query mismatch |
| xlarge | bge_dual | on | xlarge-p-034-topic | single_topic | section_miss | section normalization or query mismatch |
| xlarge | bge_dual | on | xlarge-p-034-section | single_section | section_miss | section normalization or query mismatch |
| xlarge | qwen_dual | off | xlarge-p-034-topic | single_topic | section_miss | section normalization or query mismatch |
| xlarge | qwen_dual | off | xlarge-p-034-section | single_section | section_miss | section normalization or query mismatch |
| xlarge | qwen_dual | off | xlarge-p-034-topic | single_topic | section_miss | section normalization or query mismatch |
| xlarge | qwen_dual | off | xlarge-p-034-section | single_section | section_miss | section normalization or query mismatch |
| xlarge | qwen_dual | on | xlarge-p-034-topic | single_topic | section_miss | section normalization or query mismatch |
| xlarge | qwen_dual | on | xlarge-p-034-section | single_section | section_miss | section normalization or query mismatch |
| xlarge | qwen_dual | on | xlarge-p-034-topic | single_topic | section_miss | section normalization or query mismatch |
| xlarge | qwen_dual | on | xlarge-p-034-section | single_section | section_miss | section normalization or query mismatch |

## Analysis and recommendations

### Key findings

- Matrix completeness is achieved: all 16 combinations (12-paper and 50-paper, BGE/Qwen, reranker on/off, 2 rounds) completed with `ok` status.
- Stability is good: each combination shows identical round1/round2 recall@5, indicating deterministic and reproducible behavior under current setup.
- For the 12-paper set, BGE without reranker gives the best recall@5 (0.9306) and lowest latency among strong-performing options.
- For the 50-paper set, recall@5 converges to 0.98 for all model/reranker combinations, while latency differentiates stacks (BGE faster than Qwen).
- Reranker does not improve recall in this matrix; for `large/bge_dual` it decreases recall@5 by 0.0486 and significantly increases latency.

### Interpretation

- Current retrieval quality is dominated by first-stage retrieval and dataset/query construction rather than reranker gains.
- Section-level misses are concentrated in hard/single-section cases and likely reflect section label normalization and query-to-section mapping issues.
- With no measurable quality gain and clear latency cost, reranker is not cost-effective as the default in this benchmark profile.

### Recommendations

1. Set default stack to `bge_dual` with reranker `off` for production baseline where latency and throughput are priorities.
2. Keep `qwen_dual` as optional profile for multimodal-heavy scenarios, but gate with stricter latency SLOs.
3. Add a section-normalization pass in dataset build/eval (canonical section taxonomy and alias mapping) to reduce `section_miss` failures.
4. Expand hard-query design with explicit expected section anchors and per-query failure buckets (retrieval miss vs section mismatch).
5. Re-run this matrix as a CI/nightly benchmark and alert on deltas: $\Delta recall@5 < -0.01$ or latency increase $> 20\%$.

### Suggested next benchmark iteration

- Keep the same 16-run matrix for comparability.
- Add one variable at a time:
	- pages per paper: 1 vs 2
	- reranker top-k candidate size
	- section normalization enabled vs disabled
- Track additional KPIs: retrieval variance across rounds and per-query latency tail by query type.
