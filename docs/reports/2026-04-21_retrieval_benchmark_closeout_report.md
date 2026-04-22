---
标题：ScholarAI Retrieval Benchmark Close-out 总报告
作者：GitHub Copilot
日期：2026-04-21
状态：v1.0-closeout
范围：qwen 双模型多轮真实验证、Milvus/Qdrant 同口径对照、Dataset-S 收口结论
---

# 1. 执行摘要

本报告是在保留阶段性 Milvus 报告前提下，对本轮 retrieval benchmark 剩余项完成后的正式 close-out 结论。

本次补完了两条此前未完成的验证线：

1. qwen3-vl-2b embedding + qwen3-vl-reranker 多轮真实验证。
2. Qdrant 同口径 paired benchmark。

基于当前 Dataset-S 的正式结论如下：

1. qwen 双模型在 Milvus 主线上三轮结果完全一致，`Recall@5 = 100%`，`Recall@10 = 100%`，`MRR = 100%`，`Paper Hit Rate = 100%`。
2. Qdrant 对照链路已真实跑通，且三轮结果完全一致，`Recall@10 = 100%`，`MRR = 100%`，`Paper Hit Rate = 100%`。
3. 与 Milvus 相比，Qdrant 在当前 Dataset-S 上稳定少 1 个 Top-5 cross-paper 目标论文，表现为 `Recall@5 = 93.75%`，低于 Milvus 的 `100%`。
4. 两个后端的 `Section Hit Rate` 均为 `68.75%`，说明当前主要短板仍是 section/chunk 排序质量，而不是论文级召回。
5. 在当前真实数据规模与查询集下，没有证据支持把主线从 Milvus 切换到 Qdrant；Qdrant 更适合作为已打通、可继续扩展的对照后端。

# 2. 验证边界

本报告与阶段性报告的边界如下：

1. 阶段性报告 `2026-04-21_retrieval_benchmark_validation.md` 只覆盖早先 Milvus 主线阶段性验证，不替代本报告。
2. 本报告覆盖的是 qwen 双模型真实多轮结果与 Milvus/Qdrant 同口径对照。
3. 本报告仍只基于 Dataset-S，尚不能外推为更大规模生产语料上的最终性能承诺。

# 3. 证据文件

## 3.1 qwen + Milvus

- 预检：`artifacts/benchmarks/real/preflight_report_qwen_milvus.json`
- 数据集：`artifacts/benchmarks/real/qwen/dataset_manifest.json`
- 查询集：`artifacts/benchmarks/real/qwen/golden_queries_dataset_s.json`
- Round 1：`artifacts/benchmarks/real/qwen/eval_retrieval_real_round1.json`
- Round 2：`artifacts/benchmarks/real/qwen/eval_retrieval_real_round2.json`
- Round 3 Trace：`artifacts/benchmarks/real/qwen/eval_retrieval_real_round3_trace.json`

## 3.2 qwen + Qdrant

- 预检：`artifacts/benchmarks/real/preflight_report_qwen_qdrant_local.json`
- 数据集：`artifacts/benchmarks/real/qwen_qdrant/dataset_manifest.json`
- 查询集：`artifacts/benchmarks/real/qwen_qdrant/golden_queries_dataset_s.json`
- Round 1：`artifacts/benchmarks/real/qwen_qdrant/eval_retrieval_real_round1.json`
- Round 2：`artifacts/benchmarks/real/qwen_qdrant/eval_retrieval_real_round2.json`
- Round 3 Trace：`artifacts/benchmarks/real/qwen_qdrant/eval_retrieval_real_round3_trace.json`

# 4. 环境与执行口径

## 4.1 共同口径

- Python: 3.11.15
- Embedding model: `qwen3-vl-2b`
- Reranker model: `qwen3-vl-reranker`
- Embedding dimension: `2048`
- 查询总数: 8
- 数据集规模: 3 papers / 36 chunks
- Eval 参数: `--user-id benchmark-user --use-reranker --paper-id dataset-s-001 dataset-s-002 dataset-s-003`

## 4.2 后端差异

- Milvus：本机无独立服务时 fallback 到 Milvus Lite。
- Qdrant：本机 `localhost:6333` 无服务，因此本轮对照使用仓内补上的本地持久化 Qdrant 模式完成真实写入与检索。

这意味着本次 Qdrant 结果是“真实后端对照”，但不是“远程 Qdrant server 部署验证”。

# 5. 结果汇总

## 5.1 后端总体对照

| Backend | Round 1 | Round 2 | Round 3 Trace | Recall@5 | Recall@10 | MRR | Section Hit Rate | Paper Hit Rate |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| qwen + Milvus | stable | stable | stable | 100.00% | 100.00% | 100.00% | 68.75% | 100.00% |
| qwen + Qdrant | stable | stable | stable | 93.75% | 100.00% | 100.00% | 68.75% | 100.00% |

两条后端链路都表现出：

1. 三轮结果完全一致。
2. Trace 开启不会改变结果。
3. 论文级召回与首命中排序都稳定。

## 5.2 关键差异

Milvus 与 Qdrant 的唯一区别出现在 `ds-cp2`：

- Query: `Which paper is about instruction following or model alignment?`
- Target papers: `dataset-s-001`, `dataset-s-003`

Milvus：

- `Recall@5 = 1.0`

Qdrant：

- `Recall@5 = 0.5`
- `Recall@10 = 1.0`
- `MRR = 1.0`

这说明 Qdrant 在该 cross-paper 查询上，第一相关结果仍然排在首位，但第二目标论文稳定落在 Top-5 之外、Top-10 之内。

## 5.3 如何解读

这组结果更接近“排序差异”，而不是“召回崩坏”：

1. 如果是检索失效，`Recall@10` 与 `Paper Hit Rate` 不会保持 100%。
2. 如果是第一结果错误，`MRR` 不会保持 100%。
3. 当前 Qdrant 的问题是 cross-paper 第二目标论文前置能力弱于 Milvus。

# 6. 补完项与新增修正

为完成本次 close-out，还补齐了 Qdrant 真实执行所需的最小工程能力：

1. 安装 `qdrant-client`。
2. 在 `app.core.qdrant_service` 中增加本地持久化 client、collection bootstrap 与 batched upsert。
3. 让 `scripts/prepare_real_retrieval_dataset.py` 能按 `VECTOR_STORE_BACKEND` 将 Dataset-S 写入 Qdrant。
4. 为 Qdrant 本地模式补充 round-trip 集成测试。

这些修正的作用不是改变主线结论，而是把此前“代码里声明支持 Qdrant，但真实 benchmark 跑不起来”的状态，推进到“可以真实跑出 paired benchmark 结果”。

# 7. 最终结论

基于当前 Dataset-S 与 qwen 双模型口径，本次 retrieval benchmark close-out 的最终判定为：

1. qwen 双模型主线验证已完成，Milvus 三轮稳定通过。
2. Qdrant 同口径对照已完成，且结果稳定复现。
3. 现阶段主线仍应保持 Milvus，不建议基于这轮结果切换到 Qdrant。
4. 下一阶段真正值得优化的不是“是否立刻换后端”，而是提升 section/chunk 排序与 cross-paper 二目标前置能力。

# 8. 风险与剩余限制

1. Dataset-S 仍然偏小，只能作为真实收口验证，不能替代更大规模回归集。
2. 当前没有 multimodal query 样本，`Multimodal Hit Rate = 0` 不能解读为失败。
3. 当前 Qdrant 对照使用的是本地持久化模式，不代表远程 Qdrant 集群部署的运维与性能结论。
4. 当前差异只在单条 cross-paper query 上观测到，后续应扩充 cross-paper 查询数再确认差异曲线。

# 9. 建议的下一步

1. 扩充 cross-paper 查询与更多论文样本，确认 Qdrant 的 Top-5 差异是否具有统计稳定性。
2. 补 section/chunk-level gold，避免长期只看 paper-level 成功率。
3. 在具备真实远程 Qdrant server 后，再追加一轮“local Qdrant vs remote Qdrant vs Milvus”的部署形态对照。