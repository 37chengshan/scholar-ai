---
标题：ScholarAI Retrieval Benchmark 阶段性验证报告（Milvus 主线）
作者：GitHub Copilot
日期：2026-04-21
状态：v1.1-stage
范围：Gate1-7 收口、Dataset-S 真实检索评估、Milvus 主线阶段性验证
---

> 说明：本报告只覆盖 Milvus 主线与 bge-m3 口径下的阶段性真实验证结果，不代表 qwen 双模型多轮验证或 Milvus / Qdrant 对照已完成。

# 1. 执行摘要

本报告记录 ScholarAI 在 Gate1-7 收口后的阶段性 retrieval benchmark 验证结果。

验证对象不是历史上的 simulated benchmark runner，而是当前正式链路：

- `scripts/preflight_retrieval_env.py`
- `scripts/prepare_real_retrieval_dataset.py`
- `scripts/eval_retrieval.py`

本次使用真实论文文本构建 Dataset-S，在 Milvus 主线后端上完成三轮检索评估，结论如下：

1. 正式链路已经可以在本地稳定执行，不再依赖静默 mock 才能产出结果。
2. Dataset-S 三轮评估结果完全一致，说明当前主线链路在 warm repeat 与 trace 开启场景下都具备稳定性。
3. 检索对论文级目标的命中已经达标，`Paper Hit Rate = 100%`，`Recall@10 = 100%`，`MRR = 100%`。
4. `Recall@5 = 93.75%` 的唯一损失点出现在一条 cross-paper query 上，表明前五结果的跨论文排序仍有优化空间。
5. `Section Hit Rate = 68.75%` 明显低于论文级命中率，说明当前系统更擅长“找到对的论文”，但对“把正确段落排到前面”的能力仍需继续提升。

当前可以把结论定性为：

主线 Milvus retrieval 已具备阶段性真实评估可执行性与稳定论文级命中能力，但段落级排序质量和跨论文 Top-5 排序仍是下一阶段优化重点。

# 2. 验证范围与证据

## 2.1 正式验证范围

本报告只覆盖正式 retrieval 验证链路，不包含下列 simulated runner 的结论：

- `apps/api/tests/benchmarks/run_rag_benchmark.py`
- `apps/api/tests/benchmarks/run_perf_baseline.py`

它们仍可用于开发期演练，但不作为本报告的真实 benchmark 依据。

## 2.2 证据文件

真实数据与结果来自以下仓内文件：

- 数据集清单：`artifacts/benchmarks/real/dataset_manifest.json`
- 评估查询集：`artifacts/benchmarks/real/golden_queries_dataset_s.json`
- Round 1：`artifacts/benchmarks/real/eval_retrieval_real_round1.json`
- Round 2：`artifacts/benchmarks/real/eval_retrieval_real_round2.json`
- Round 3 Trace：`artifacts/benchmarks/real/eval_retrieval_real_round3_trace.json`

相关代码与脚本：

- `scripts/eval_retrieval.py`
- `scripts/preflight_retrieval_env.py`
- `scripts/prepare_real_retrieval_dataset.py`
- `apps/api/tests/unit/test_eval_retrieval_harness.py`

## 2.3 本次使用的真实论文

Dataset-S 共包含 3 篇测试论文。它们是为本次验证手动下载并纳入测试资产的论文样本，用于真实检索行为验证，不属于产品默认内容库。

1. GPT-4 Technical Report
2. DINOv2
3. WizardLM

# 3. 环境与数据集说明

## 3.1 运行环境

- Python: 3.11.15
- Python 环境: `/Users/cc/.virtualenvs/scholar-ai-api/bin/python`
- 主线后端: `milvus`
- 本地运行形态: Milvus server 不可达时自动 fallback 到 Milvus Lite
- Embedding model: `bge-m3`
- Embedding dimension: `1024`

## 3.2 Dataset-S 数据规模

根据 `dataset_manifest.json`，本次索引规模如下：

| Paper ID | Title | Indexed Pages | Chunks |
| --- | --- | ---: | ---: |
| dataset-s-001 | GPT-4 Technical Report | 4 | 11 |
| dataset-s-002 | DINOv2 | 4 | 12 |
| dataset-s-003 | WizardLM | 4 | 13 |
| Total | 3 papers | 12 | 36 |

## 3.3 评估查询组成

`golden_queries_dataset_s.json` 共定义 8 条查询：

- 单论文查询：6 条
- Cross-paper 查询：2 条
- Multimodal 查询：0 条

其中 paper-level gold 采用 `expected_paper_ids` 标注，不再强制依赖 chunk-level gold。这要求评估脚本在没有 `expected_chunks` 时，必须按 `paper_id` 计算 Recall/MRR。

# 4. 执行过程与校正项

## 4.1 执行前校验

正式评估前已完成以下前置工作：

1. embedding model alias 与 dimension 自动对齐，避免 `BAAI/bge-m3` / `2048` 这类历史配置造成伪失败。
2. `scripts/preflight_retrieval_env.py --backend milvus` 校验通过。
3. `scripts/prepare_real_retrieval_dataset.py --user-id benchmark-user --pages-per-paper 4` 完成数据导入。

## 4.2 关键口径修正

真实 benchmark 首轮曾出现“全部为 0 但无报错”的假阴性，根因有两项：

1. 评估脚本默认使用 `eval-user`，而真实导入数据使用的是 `benchmark-user`。
2. paper-level gold 仍按 chunk/source id 计分，导致论文命中无法正确反映到 Recall/MRR。

为此，`scripts/eval_retrieval.py` 已完成两项修正：

1. 新增 `--user-id` 参数并向下透传。
2. 当 gold 仅提供 `expected_paper_ids` 时，Recall@K 与 MRR 改为基于返回结果中的 `paper_id` 计算。

同时增加了回归测试 `apps/api/tests/unit/test_eval_retrieval_harness.py`，用于约束 mock dry-run 不再出现 paper-level 假阴性或假阳性。

# 5. 三轮真实 benchmark 结果

## 5.1 总体指标

三轮结果完全一致：

| Round | Mode | Recall@5 | Recall@10 | MRR | Section Hit Rate | Paper Hit Rate |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Round 1 | real | 93.75% | 100.00% | 100.00% | 68.75% | 100.00% |
| Round 2 | warm repeat | 93.75% | 100.00% | 100.00% | 68.75% | 100.00% |
| Round 3 | trace enabled | 93.75% | 100.00% | 100.00% | 68.75% | 100.00% |

这说明：

1. 指标不依赖冷启动偶然性。
2. 打开 trace 不会破坏检索结果口径。
3. 当前问题不是随机抖动，而是稳定存在的排序特征。

## 5.2 查询级结果

8 条查询中：

- 7 条在 `Recall@5` 达到 1.0
- 1 条在 `Recall@5` 为 0.5
- 全部查询 `Recall@10 = 1.0`
- 全部查询 `MRR = 1.0`
- 全部查询 `Paper Hit Rate = 1.0`

唯一的 `Recall@5` 损失发生在 `ds-cp1`：

- Query: `Which paper focuses on multimodal large models and which one focuses on visual representation learning?`
- Target papers: `dataset-s-001`, `dataset-s-002`

这意味着系统在前 5 个结果里已经命中其中一篇目标论文，但第二篇目标论文未能及时进入 Top-5；不过在 Top-10 内已全部召回。

## 5.3 如何解读这组结果

当前指标说明系统存在如下特征：

1. 论文级召回已经稳定。
2. 第一相关结果的排序已经稳定，否则 `MRR` 不会持续为 100%。
3. Cross-paper 的“第二目标论文前置能力”仍需继续优化。
4. section 级别排序弱于 paper 级别命中，反映 chunk / section ranking 仍是下一步重点。

# 6. 阶段性结论与判定

## 6.1 本次验证结论

本次真实 benchmark 支持以下结论：

1. ScholarAI 当前主线 Milvus retrieval 已经具备真实评估执行能力。
2. Gate1-7 的环境修复、数据准备、eval harness 收口已经达到可交付状态。
3. 真实 benchmark 的核心风险已从“跑不起来 / 结果全零”转为“如何继续提升 section-level 与 cross-paper Top-5 排序质量”。

## 6.2 当前是否可以作为阶段性交付结论

可以，但只能作为阶段性交付结论。

原因不是“原计划所有目标都已完成”，而是：

1. 正式链路已被明确区分出 simulated runner。
2. 数据集、预检、真实评估、回归测试已经闭环。
3. 三轮结果一致，足以证明当前结论稳定，不是一次性偶然结果。

这一定义不包含以下事项：

1. qwen3-vl-2b embedding + qwen3-vl-reranker 的多轮真实验证。
2. Milvus / Qdrant 同口径 paired benchmark。
3. Dataset-L 大规模真实测试与最终迁移判断。

# 7. 已知限制与未完成项

本报告仍有以下边界：

1. 本报告仅验证了 Milvus 主线后端，未完成真实 Qdrant 对照 benchmark。
2. Dataset-S 规模较小，仅 3 篇论文、8 条查询，更适合做收口验证，不足以替代更大规模回归集。
3. 当前没有 multimodal query 样本，因此 `Multimodal Hit Rate` 为 0 不是失败结论，而是本轮数据集未覆盖该维度。
4. `Section Hit Rate` 只验证命中 section，不等同于更细粒度的 paragraph / citation anchor 精度。
5. 当前三轮验证使用的是 `bge-m3`，并未完成 qwen 双模型口径下的同批次真实验证。

# 8. 后续动作建议

下一阶段建议按优先级推进：

1. 为 cross-paper query 增加更稳定的二目标论文前置排序能力，优先改善 `Recall@5`。
2. 补充 section / chunk-level gold，避免长期只停留在 paper-level 评估。
3. 扩大真实数据集规模，至少补到 10+ 论文、30+ 查询。
4. 先补 qwen 双模型多轮验证，再在具备真实 qdrant 环境后补跑同一套 Dataset-S，形成 Milvus / Qdrant 对照报告。

# 9. 验证命令记录

## 9.1 真实评估命令

```bash
/Users/cc/.virtualenvs/scholar-ai-api/bin/python scripts/eval_retrieval.py \
  --golden artifacts/benchmarks/real/golden_queries_dataset_s.json \
  --backend milvus \
  --user-id benchmark-user \
  --paper-id dataset-s-001 dataset-s-002 dataset-s-003 \
  --output artifacts/benchmarks/real/eval_retrieval_real_round1.json
```

```bash
/Users/cc/.virtualenvs/scholar-ai-api/bin/python scripts/eval_retrieval.py \
  --golden artifacts/benchmarks/real/golden_queries_dataset_s.json \
  --backend milvus \
  --user-id benchmark-user \
  --paper-id dataset-s-001 dataset-s-002 dataset-s-003 \
  --output artifacts/benchmarks/real/eval_retrieval_real_round2.json
```

```bash
RETRIEVAL_TRACE_ENABLED=1 \
/Users/cc/.virtualenvs/scholar-ai-api/bin/python scripts/eval_retrieval.py \
  --golden artifacts/benchmarks/real/golden_queries_dataset_s.json \
  --backend milvus \
  --user-id benchmark-user \
  --paper-id dataset-s-001 dataset-s-002 dataset-s-003 \
  --output artifacts/benchmarks/real/eval_retrieval_real_round3_trace.json
```

## 9.2 回归测试命令

```bash
cd apps/api && /Users/cc/.virtualenvs/scholar-ai-api/bin/python -m pytest tests/unit/test_eval_retrieval_harness.py -q
```

结果：2 passed