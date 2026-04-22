---
标题：ScholarAI Retrieval Benchmark 大规模真实数据测试报告
作者：GitHub Copilot
日期：2026-04-22
状态：v1.0-large-real
范围：优化后 RAG 在大型真实论文集上的三轮稳定性验证
---

# 1. 执行摘要

本次基于优化后的 RAG 流程，新增并执行了大规模真实数据评测：

1. 新建 Large 数据集构建能力，直接使用仓内真实测试论文。
2. 生成并导入 12 篇论文、178 个检索 chunk。
3. 在真实后端链路上连续执行 3 轮评测（含 trace 轮）。
4. 三轮结果完全一致，说明当前链路在大数据集下具有稳定可重复性。

核心指标（三轮一致）：

- Total Queries: 32
- Recall@5: 96.875%
- Recall@10: 98.4375%
- MRR: 100%
- Paper Hit Rate: 96.875%
- Section Hit Rate: 51.5625%
- Top5 Cross-paper Completeness: 96.875%

# 2. 本次新增能力

## 2.1 大规模真实数据集构建脚本

已扩展脚本：

- scripts/prepare_real_retrieval_dataset.py

新增能力：

- 支持 profile=large
- 从 tests/evals/fixtures/papers 自动扫描并构建大型数据集
- 自动生成 dataset-l-* 论文 ID 与查询集
- 生成对应 golden queries 文件

## 2.2 评测脚本口径修复

已修复脚本：

- scripts/eval_retrieval.py

修复内容：

- 增加 --user-id 参数，避免真实评测命中错误用户数据
- 修复 Recall/MRR 口径：当 gold 为 expected_paper_ids 时按 paper_id 计分，不再误用 source_id

## 2.3 预检脚本兼容修复

已修复脚本：

- scripts/preflight_retrieval_env.py

修复内容：

- 对 canonical/normalize 配置函数增加兼容 fallback，避免导入失败导致预检无法运行

# 3. 数据集规模与产物

本次 large 数据集信息：

- 论文数：12
- 每篇索引页数：4
- 总 chunk 数：178
- 总写入数：178
- 用户隔离：benchmark-user-large

关键产物：

- 数据集清单：artifacts/benchmarks/real_large/dataset_manifest.json
- 查询集：artifacts/benchmarks/real_large/golden_queries_dataset_l.json
- Round1：artifacts/benchmarks/real_large/eval_retrieval_large_round1.json
- Round2：artifacts/benchmarks/real_large/eval_retrieval_large_round2.json
- Round3(trace)：artifacts/benchmarks/real_large/eval_retrieval_large_round3_trace.json
- 预检报告：artifacts/benchmarks/real_large/preflight_report_large_milvus.json

# 4. 执行命令记录

## 4.1 构建 large 真实数据集

```bash
VECTOR_STORE_BACKEND=milvus \
EMBEDDING_MODEL=bge-m3 \
EMBEDDING_DIMENSION=1024 \
MILVUS_COLLECTION_CONTENTS_V2=paper_contents_v2_large_20260422 \
/Users/cc/.virtualenvs/scholar-ai-api/bin/python scripts/prepare_real_retrieval_dataset.py \
  --profile large \
  --limit-papers 12 \
  --user-id benchmark-user-large \
  --pages-per-paper 4 \
  --output-dir artifacts/benchmarks/real_large
```

## 4.2 三轮真实评测

```bash
VECTOR_STORE_BACKEND=milvus \
EMBEDDING_MODEL=bge-m3 \
EMBEDDING_DIMENSION=1024 \
MILVUS_COLLECTION_CONTENTS_V2=paper_contents_v2_large_20260422 \
/Users/cc/.virtualenvs/scholar-ai-api/bin/python scripts/eval_retrieval.py \
  --golden artifacts/benchmarks/real_large/golden_queries_dataset_l.json \
  --user-id benchmark-user-large \
  --paper-id dataset-l-001 dataset-l-002 dataset-l-003 dataset-l-004 dataset-l-005 dataset-l-006 dataset-l-007 dataset-l-008 dataset-l-009 dataset-l-010 dataset-l-011 dataset-l-012 \
  --output artifacts/benchmarks/real_large/eval_retrieval_large_round1.json

VECTOR_STORE_BACKEND=milvus \
EMBEDDING_MODEL=bge-m3 \
EMBEDDING_DIMENSION=1024 \
MILVUS_COLLECTION_CONTENTS_V2=paper_contents_v2_large_20260422 \
/Users/cc/.virtualenvs/scholar-ai-api/bin/python scripts/eval_retrieval.py \
  --golden artifacts/benchmarks/real_large/golden_queries_dataset_l.json \
  --user-id benchmark-user-large \
  --paper-id dataset-l-001 dataset-l-002 dataset-l-003 dataset-l-004 dataset-l-005 dataset-l-006 dataset-l-007 dataset-l-008 dataset-l-009 dataset-l-010 dataset-l-011 dataset-l-012 \
  --output artifacts/benchmarks/real_large/eval_retrieval_large_round2.json

RETRIEVAL_TRACE_ENABLED=1 \
VECTOR_STORE_BACKEND=milvus \
EMBEDDING_MODEL=bge-m3 \
EMBEDDING_DIMENSION=1024 \
MILVUS_COLLECTION_CONTENTS_V2=paper_contents_v2_large_20260422 \
/Users/cc/.virtualenvs/scholar-ai-api/bin/python scripts/eval_retrieval.py \
  --golden artifacts/benchmarks/real_large/golden_queries_dataset_l.json \
  --user-id benchmark-user-large \
  --paper-id dataset-l-001 dataset-l-002 dataset-l-003 dataset-l-004 dataset-l-005 dataset-l-006 dataset-l-007 dataset-l-008 dataset-l-009 dataset-l-010 dataset-l-011 dataset-l-012 \
  --output artifacts/benchmarks/real_large/eval_retrieval_large_round3_trace.json
```

# 5. 三轮结果

| Round | Mode | Total Queries | Recall@5 | Recall@10 | MRR | Paper Hit Rate | Section Hit Rate | Top5 Cross-paper Completeness |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Round 1 | real | 32 | 96.875% | 98.4375% | 100% | 96.875% | 51.5625% | 96.875% |
| Round 2 | warm repeat | 32 | 96.875% | 98.4375% | 100% | 96.875% | 51.5625% | 96.875% |
| Round 3 | trace enabled | 32 | 96.875% | 98.4375% | 100% | 96.875% | 51.5625% | 96.875% |

# 6. 结论

1. 大规模真实数据链路已跑通，并可稳定复现。
2. 论文级命中与首命中排序表现稳定（Paper Hit Rate 与 MRR 高）。
3. Section 粒度命中仍明显低于论文粒度，是下一阶段重点优化点。
4. 三轮一致表明优化后的 RAG 在当前大数据测试集上无明显随机漂移。

# 7. 风险与后续建议

1. 当前自动标题提取仍有噪声，建议在 large profile 中增加标题清洗规则，以进一步提升 query 质量。
2. 建议补充更强约束的 section/chunk-level gold，减少仅 paper-level 指标掩盖排序问题。
3. 建议下一轮增加 20+ 论文、50+ 查询，并分层统计 single/cross-paper 两类查询表现。
