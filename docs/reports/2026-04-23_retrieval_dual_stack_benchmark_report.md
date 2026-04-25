# 2026-04-23 Retrieval Dual Stack Benchmark Report

## Matrix execution status

| dataset | model_stack | reranker | round | status |
|---|---|---|---|---|
| large | bge_dual | off | round1 | failed |
| large | bge_dual | off | round2 | failed |
| large | bge_dual | on | round1 | failed |
| large | bge_dual | on | round2 | failed |
| large | qwen_dual | off | round1 | failed |
| large | qwen_dual | off | round2 | failed |
| large | qwen_dual | on | round1 | failed |
| large | qwen_dual | on | round2 | failed |
| xlarge | bge_dual | off | round1 | failed |
| xlarge | bge_dual | off | round2 | failed |
| xlarge | bge_dual | on | round1 | failed |
| xlarge | bge_dual | on | round2 | failed |
| xlarge | qwen_dual | off | round1 | failed |
| xlarge | qwen_dual | off | round2 | failed |
| xlarge | qwen_dual | on | round1 | failed |
| xlarge | qwen_dual | on | round2 | failed |

## Table 1 - 12 papers summary

| model_stack | reranker | round1_recall@5 | round2_recall@5 | avg_recall@5 | avg_mrr | avg_paper_hit | avg_section_hit | avg_chunk_hit | avg_cross_paper_r@5 | avg_hard_hit | avg_latency_ms | p95_latency_ms |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| bge_dual | off | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| bge_dual | on | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| qwen_dual | off | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| qwen_dual | on | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |

## Table 2 - 50 papers summary

| model_stack | reranker | round1_recall@5 | round2_recall@5 | avg_recall@5 | avg_mrr | avg_paper_hit | avg_section_hit | avg_chunk_hit | avg_cross_paper_r@5 | avg_hard_hit | avg_latency_ms | p95_latency_ms |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| bge_dual | off | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| bge_dual | on | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| qwen_dual | off | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| qwen_dual | on | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |

## Table 3 - reranker A/B gain

| dataset | model_stack | metric | reranker_off_avg | reranker_on_avg | delta |
|---|---|---|---:|---:|---:|
| large | bge_dual | recall@5 | 0.0000 | 0.0000 | 0.0000 |
| large | bge_dual | section_hit | 0.0000 | 0.0000 | 0.0000 |
| large | bge_dual | chunk_hit | 0.0000 | 0.0000 | 0.0000 |
| large | bge_dual | cross_paper_r@5 | 0.0000 | 0.0000 | 0.0000 |
| large | qwen_dual | recall@5 | 0.0000 | 0.0000 | 0.0000 |
| large | qwen_dual | section_hit | 0.0000 | 0.0000 | 0.0000 |
| large | qwen_dual | chunk_hit | 0.0000 | 0.0000 | 0.0000 |
| large | qwen_dual | cross_paper_r@5 | 0.0000 | 0.0000 | 0.0000 |
| xlarge | bge_dual | recall@5 | 0.0000 | 0.0000 | 0.0000 |
| xlarge | bge_dual | section_hit | 0.0000 | 0.0000 | 0.0000 |
| xlarge | bge_dual | chunk_hit | 0.0000 | 0.0000 | 0.0000 |
| xlarge | bge_dual | cross_paper_r@5 | 0.0000 | 0.0000 | 0.0000 |
| xlarge | qwen_dual | recall@5 | 0.0000 | 0.0000 | 0.0000 |
| xlarge | qwen_dual | section_hit | 0.0000 | 0.0000 | 0.0000 |
| xlarge | qwen_dual | chunk_hit | 0.0000 | 0.0000 | 0.0000 |
| xlarge | qwen_dual | cross_paper_r@5 | 0.0000 | 0.0000 | 0.0000 |

## Table 4 - BGE vs Qwen

| dataset | reranker_state | metric | bge_avg | qwen_avg | delta(qwen-bge) |
|---|---|---|---:|---:|---:|
| large | off | recall@5 | 0.0000 | 0.0000 | 0.0000 |
| large | off | section_hit | 0.0000 | 0.0000 | 0.0000 |
| large | off | chunk_hit | 0.0000 | 0.0000 | 0.0000 |
| large | off | cross_paper_r@5 | 0.0000 | 0.0000 | 0.0000 |
| large | on | recall@5 | 0.0000 | 0.0000 | 0.0000 |
| large | on | section_hit | 0.0000 | 0.0000 | 0.0000 |
| large | on | chunk_hit | 0.0000 | 0.0000 | 0.0000 |
| large | on | cross_paper_r@5 | 0.0000 | 0.0000 | 0.0000 |
| xlarge | off | recall@5 | 0.0000 | 0.0000 | 0.0000 |
| xlarge | off | section_hit | 0.0000 | 0.0000 | 0.0000 |
| xlarge | off | chunk_hit | 0.0000 | 0.0000 | 0.0000 |
| xlarge | off | cross_paper_r@5 | 0.0000 | 0.0000 | 0.0000 |
| xlarge | on | recall@5 | 0.0000 | 0.0000 | 0.0000 |
| xlarge | on | section_hit | 0.0000 | 0.0000 | 0.0000 |
| xlarge | on | chunk_hit | 0.0000 | 0.0000 | 0.0000 |
| xlarge | on | cross_paper_r@5 | 0.0000 | 0.0000 | 0.0000 |

## Table 5 - failure query classification

| dataset | model_stack | reranker | query_id | query_type | failure_type | possible_cause |
|---|---|---|---|---|---|---|
