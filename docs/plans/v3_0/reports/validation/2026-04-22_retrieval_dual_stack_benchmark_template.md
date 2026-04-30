# 2026-04-22 Retrieval Dual Stack Benchmark Report Template

## Table 1 - 12 papers summary

| model_stack | reranker | round1_recall@5 | round2_recall@5 | avg_recall@5 | avg_mrr | avg_paper_hit | avg_section_hit | avg_chunk_hit | avg_cross_paper_r@5 | avg_latency_ms | p95_latency_ms |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| bge_dual | off | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| bge_dual | on | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| qwen_dual | off | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| qwen_dual | on | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |

## Table 2 - 50 papers summary

| model_stack | reranker | round1_recall@5 | round2_recall@5 | avg_recall@5 | avg_mrr | avg_paper_hit | avg_section_hit | avg_chunk_hit | avg_cross_paper_r@5 | avg_latency_ms | p95_latency_ms |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| bge_dual | off | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| bge_dual | on | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| qwen_dual | off | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| qwen_dual | on | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD |

## Table 3 - reranker A/B gain

| dataset | model_stack | metric | reranker_off_avg | reranker_on_avg | delta |
|---|---|---|---:|---:|---:|
| large | bge_dual | recall@5 | TBD | TBD | TBD |
| large | bge_dual | section_hit | TBD | TBD | TBD |
| large | bge_dual | chunk_hit | TBD | TBD | TBD |
| large | qwen_dual | recall@5 | TBD | TBD | TBD |
| large | qwen_dual | section_hit | TBD | TBD | TBD |
| large | qwen_dual | chunk_hit | TBD | TBD | TBD |
| xlarge | bge_dual | recall@5 | TBD | TBD | TBD |
| xlarge | bge_dual | section_hit | TBD | TBD | TBD |
| xlarge | bge_dual | chunk_hit | TBD | TBD | TBD |
| xlarge | qwen_dual | recall@5 | TBD | TBD | TBD |
| xlarge | qwen_dual | section_hit | TBD | TBD | TBD |
| xlarge | qwen_dual | chunk_hit | TBD | TBD | TBD |

## Table 4 - BGE vs Qwen

| dataset | reranker_state | metric | bge_avg | qwen_avg | delta(qwen-bge) |
|---|---|---|---:|---:|---:|
| large | off | recall@5 | TBD | TBD | TBD |
| large | on | recall@5 | TBD | TBD | TBD |
| large | off | section_hit | TBD | TBD | TBD |
| large | on | section_hit | TBD | TBD | TBD |
| xlarge | off | recall@5 | TBD | TBD | TBD |
| xlarge | on | recall@5 | TBD | TBD | TBD |
| xlarge | off | section_hit | TBD | TBD | TBD |
| xlarge | on | section_hit | TBD | TBD | TBD |

## Table 5 - failure query classification

| dataset | model_stack | reranker | query_id | query_type | failure_type | possible_cause |
|---|---|---|---|---|---|---|
| large | bge_dual | off | TBD | single_topic | section_miss | metadata noise |

## Raw artifact index

- `artifacts/benchmarks/matrix_runs/large/bge_dual/*.json`
- `artifacts/benchmarks/matrix_runs/large/qwen_dual/*.json`
- `artifacts/benchmarks/matrix_runs/xlarge/bge_dual/*.json`
- `artifacts/benchmarks/matrix_runs/xlarge/qwen_dual/*.json`
