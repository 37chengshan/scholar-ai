---
标题：ScholarAI v3.0-A Academic Benchmark 3.0 研究文档
日期：2026-04-28
状态：research
范围：学术级 benchmark 扩容、gold evidence 标注、blind eval、gate 升级
---

# 1. 研究目标

本文件定义 ScholarAI `v3.0-A: Academic Benchmark 3.0` 的详细研究方案。

它回答的核心问题不是“要不要继续做 benchmark”，而是：

```txt
怎样把当前偏工程验证型的评测集，
升级成能够持续约束 ScholarAI 学术严谨性的正式评测体系。
```

本文件只定义研究结论、目标结构、标注协议、指标体系与接入策略；不直接展开到脚本改造任务清单、模型选择或逐文件开发实施。

# 2. 执行摘要

当前仓库已经有一套可工作的 benchmark / gate 基础：

1. `apps/api/artifacts/benchmarks/phase6/corpus.json` 已冻结一版语料。
2. 当前 corpus 规模为 `50 papers / 128 queries / 8 query families`。
3. `scripts/evals/phase6_gate.py` 与 `apps/api/app/services/eval_service.py` 已能执行离线 gate。
4. 现有报告已经覆盖 retrieval、citation jump、answer support、groundedness、abstain precision、latency、cost 等关键指标。

这套体系足以支撑 `v2.0` 的 release gate，但还不足以支撑 `v3.0` 所要求的“学术严谨性升级”，核心原因是：

1. 规模仍偏小，容易被固定题集优化。
2. 学科覆盖不足，当前更接近单域工程语料。
3. gold answer / gold evidence 粒度不够系统，尤其缺少 claim/evidence 明确映射。
4. 图表、表格、公式、多文献综合、不可回答问题等高难度场景覆盖不足。
5. 尚未形成 public set + blind set 双层评测机制。

因此，`Academic Benchmark 3.0` 的定位应为：

```txt
在保留 phase6 文件系统 gate 机制的前提下，
建立一个更大、更异构、更可审计、
同时明确区分 public benchmark / blind benchmark 的学术级评测框架。
```

# 3. 当前基线盘点

## 3.1 现有仓库能力

当前仓库中与 benchmark 直接相关的真实资产包括：

1. 冻结语料：
   - `apps/api/artifacts/benchmarks/phase6/corpus.json`
2. gate 与 artifact 读取：
   - `scripts/evals/phase6_gate.py`
   - `apps/api/app/services/eval_service.py`
3. retrieval eval harness：
   - `scripts/eval_retrieval.py`
4. answer eval harness：
   - `scripts/eval_answer.py`
5. 数据准备脚本：
   - `scripts/prepare_real_retrieval_dataset.py`
6. 现有 v3.0 早期报告：
   - `docs/plans/v3_0/reports/official_rag_evaluation/v3_0_phase1_report.md`
   - `docs/plans/v3_0/reports/official_rag_evaluation/v3_0_phase5_6_report.md`

## 3.2 当前 corpus 事实基线

基于 `apps/api/artifacts/benchmarks/phase6/corpus.json` 的实际读取结果：

1. `paper_count = 50`
2. `query_count = 128`
3. 当前 families：
   - `single_fact`
   - `method`
   - `experiment_result`
   - `table`
   - `figure_caption`
   - `multi_paper_compare`
   - `kb_global`
   - `no_answer`
4. family 分布：
   - `experiment_result = 20`
   - `figure_caption = 10`
   - `kb_global = 16`
   - `method = 20`
   - `multi_paper_compare = 15`
   - `no_answer = 12`
   - `single_fact = 20`
   - `table = 15`

这说明当前 benchmark 已经不是“零”，而是一套针对 retrieval / answer / citation gate 的最小可用框架。

## 3.3 当前 gate 事实基线

现有 `phase6` candidate run 的主要指标已达到：

1. `retrieval_hit_rate = 0.903`
2. `recall_at_5 = 0.886`
3. `citation_jump_valid_rate = 0.949`
4. `answer_supported_rate = 0.879`
5. `groundedness = 0.842`
6. `abstain_precision = 0.923`
7. `fallback_used_count = 2`
8. `latency_p95 = 3.72s`
9. `cost_per_answer = 0.003`

结论不是“当前评测不行”，而是：

```txt
当前评测更像 v2.0 的工程质量门禁，
还不是 v3.0 的学术级 benchmark。
```

# 4. 为什么当前 benchmark 不足以支撑 v3.0

## 4.1 规模问题

`50 papers / 128 queries` 足以发现回归，但不足以评估跨学科泛化、复杂 evidence 组合、以及 blind generalization。

风险：

1. 小样本导致分数波动大。
2. 模型或 prompt 可能对固定题集过拟合。
3. 多个 query family 实际样本仍偏少，特别是图、表、不可回答和多论文综合。

## 4.2 领域覆盖问题

当前 fixtures 以仓库已有 PDF 为主，仍明显偏向本项目历史语料。

这与 v3.0 的目标不一致。v3.0 明确需要覆盖：

1. CS
2. 医学
3. 经济
4. 数学
5. 教育

如果 benchmark 不扩学科，后续任何“学术严谨性”结论都容易只在单域成立。

## 4.3 gold 标注粒度问题

现有 `expected_paper_ids`、`expected_sections`、`expected_chunks` 足以做 retrieval 级评估，但仍不够覆盖：

1. 规范化 gold answer
2. claim 级支撑关系
3. 单 claim 对应多 evidence 的情况
4. evidence span / quote / offset 级定位

这会直接限制后续 `Phase 3.0-C span-level citation + claim verification` 的真实评测。

## 4.4 学术复杂场景覆盖问题

学术问答中，最容易“表面答对、证据不对”的恰恰是：

1. 表格比较
2. 图表解读
3. 数值问答
4. 公式与数学符号解释
5. 跨论文冲突与 limitation 分析
6. 不可回答或证据不足时的 abstain

当前 benchmark 已经开始覆盖 `table`、`figure_caption` 和 `no_answer`，但深度和样本量仍不够。

## 4.5 缺少 blind benchmark

没有 blind set，就很难区分：

1. 系统真的更强了
2. 还是只是对现有 benchmark 产生了“题库记忆”

对于 ScholarAI 这种要强调学术可信性的产品，blind benchmark 不是锦上添花，而是核心防作弊机制。

# 5. 外部前沿实现给出的设计信号

本节只采纳与 ScholarAI `Academic Benchmark 3.0` 直接相关的外部方法信号。

## 5.1 RAGAs：提醒我们不能只看最终答案

`RAGAs` 将 RAG 评测拆成 retrieval quality、faithfulness、answer quality 等不同维度，而不是只看一个答案分数。

对 ScholarAI 的启发：

1. benchmark 需要拆成 retrieval、evidence、answer、abstain 四层指标。
2. 不能只看 `answer_correct`，否则会掩盖 evidence 不足却“碰巧答对”的情况。

来源：
- https://aclanthology.org/2024.eacl-demo.16/

## 5.2 ARES：提醒我们人标很贵，judge 体系要混合设计

`ARES` 说明高质量 RAG 评测不可能完全靠纯人工，也不应完全依赖黑箱 LLM judge，而应采用：

1. 少量高质量人工标注
2. 规则与模型 judge 混合
3. 通过校准减少 judge 偏差

对 ScholarAI 的启发：

1. public / blind set 的 gold 必须由人标控制。
2. 部分大规模 answer quality 可以用 LLM judge 辅助，但不能替代 gold evidence。
3. judge 需要定期对人工子集做校准。

来源：
- https://aclanthology.org/2024.naacl-long.20/

## 5.3 BEIR：提醒我们 benchmark 必须异构，不能只在单一分布里好看

`BEIR` 的价值不在于任务和 ScholarAI 完全相同，而在于它证明：

1. retrieval benchmark 如果分布太单一，泛化结论会失真。
2. 零样本/跨域表现与单域表现常常差异很大。

对 ScholarAI 的启发：

1. `Academic Benchmark 3.0` 必须跨学科。
2. 必须保留 domain split 和 family split 报告。
3. 不能只输出 overall score。

来源：
- https://openreview.net/forum?id=wCu6T5xFjeJ

## 5.4 SciFact：提醒我们 scientific claim verification 需要 claim + rationale 双标注

`SciFact` 的关键点在于同时标注：

1. scientific claims
2. supporting / refuting evidence
3. rationale

对 ScholarAI 的启发：

1. v3.0-A 不能只收集问题与答案。
2. 必须显式记录 gold evidence 与 claim support 关系。
3. 后续 claim-level verification 必须以此为数据真源。

来源：
- https://aclanthology.org/2020.emnlp-main.609/

## 5.5 UAEval4RAG：提醒我们“不回答能力”必须单独评测

`Unanswerability Evaluation for Retrieval Augmented Generation` 的核心信号是：

1. 很多 RAG 框架只评 answerable queries。
2. 但真实系统是否能正确 abstain，同样重要。

对 ScholarAI 的启发：

1. `no_answer` family 不应只是小配角。
2. 应扩展为更细的不可回答子类。
3. abstain precision / acceptable abstain 应成为正式 gate 指标。

来源：
- https://aclanthology.org/2025.acl-long.415/

## 5.6 ChartQA / OpenCQA / SciVQA / M3DocVQA：提醒我们图表与多模态证据不能附带评测

这些工作共同说明：

1. 图表问答与文本问答是不同难度层级。
2. 多页、多文档、多模态检索与推理会显著拉低性能。

对 ScholarAI 的启发：

1. 图、表、视觉元素必须有独立 query family。
2. 单独报告 figure/table family，不能混在总分里。
3. 如果未来进入多页、多文档视觉问答，benchmark 结构要预留 multimodal evidence 标注。

来源：
- ChartQA: https://aclanthology.org/2022.findings-acl.177/
- OpenCQA: https://aclanthology.org/2022.emnlp-main.811/
- SciVQA 2025: https://aclanthology.org/2025.sdp-1.18/
- M3DocVQA: https://openaccess.thecvf.com/content/ICCV2025W/Findings/html/Cho_M3DocVQA_Multi-modal_Multi-page_Multi-document_Understanding_ICCVW_2025_paper.html

## 5.7 FaithfulRAG：提醒我们冲突知识与事实级 faithfulness 需要单独约束

`FaithfulRAG` 强调当 retrieved context 与模型参数知识冲突时，系统仍可能生成不忠实答案。

对 ScholarAI 的启发：

1. benchmark 需要有 conflict / contradiction 型 query。
2. answer faithfulness 不能只看 fluent 或 semantic similarity。
3. 必须显式惩罚“答案看起来合理但不忠于证据”的情况。

来源：
- https://aclanthology.org/2025.acl-long.1062/

# 6. Academic Benchmark 3.0 的正式目标

`Academic Benchmark 3.0` 应同时满足以下六个目标：

1. `规模化`
   - 从 `50 papers / 128 queries` 升到 `200-500 papers / 500-1500 queries`
2. `异构化`
   - 覆盖多学科、多文档结构、多问题类型
3. `证据化`
   - 每题有 gold answer / gold evidence / rationale
4. `盲评化`
   - 形成 public set + blind set 双层结构
5. `可门禁化`
   - 能继续输出 baseline / candidate / diff / verdict
6. `可演进化`
   - 能为后续 claim verification、span citation、real-world validation 复用

# 7. 推荐的 benchmark 总体架构

建议将 `Benchmark 3.0` 拆成四层：

## 7.1 Layer 1：Corpus Layer

负责定义：

1. 论文集合
2. 学科标签
3. 文档复杂度标签
4. PDF 质量标签
5. modality 标签（text / table / figure / formula）

## 7.2 Layer 2：Query Layer

负责定义：

1. 问题文本
2. query family
3. 难度等级
4. 是否 answerable
5. 需要单篇还是多篇 evidence

## 7.3 Layer 3：Gold Annotation Layer

负责定义：

1. gold short answer
2. gold long answer
3. gold evidence blocks
4. claim -> evidence 对齐关系
5. abstain 原因

## 7.4 Layer 4：Run / Gate Layer

负责定义：

1. baseline / candidate / diff artifact
2. family/domain/difficulty 切片统计
3. gate 阈值
4. blind benchmark 裁决

# 8. 推荐的数据规模与样本结构

## 8.1 论文规模

建议目标范围：

```txt
P0 最小可用：200 papers
P1 稳定版：300 papers
P2 学术发布版：500 papers
```

原因：

1. 200 已足够显著拉开与当前 `50 papers` 的差距。
2. 300 足以给多学科 + 多 family 分桶。
3. 500 才更接近“长期学术 benchmark”规模，但前期标注成本更高。

## 8.2 学科分布

建议最小分布：

1. CS：25%
2. 医学：20%
3. 经济：15%
4. 数学：15%
5. 教育：15%
6. 跨学科 / 社科 / 其他：10%

原则：

1. 不追求绝对均匀。
2. 优先覆盖 ScholarAI 真实目标用户会问的问题类型。
3. 数学和医学即使样本量较少，也必须单独保留，因为它们最能暴露系统短板。

## 8.3 文档复杂度分层

每篇 paper 应至少标注以下复杂度标签：

1. `scan_quality`
   - born_digital / lightly_noisy / scanned
2. `layout_complexity`
   - simple / medium / complex
3. `table_density`
   - none / low / high
4. `figure_density`
   - none / low / high
5. `formula_density`
   - none / low / high
6. `paper_length_bucket`
   - short / medium / long / very_long

这样做的目的不是美观，而是为了后续能回答：

```txt
系统到底是在“所有论文都好”，
还是只在“清爽的 born-digital CS 论文”上好。
```

# 9. 推荐的 query family 体系

## 9.1 总体原则

当前 `8 families` 应保留兼容，但不够。

`Benchmark 3.0` 建议升级为以下主 families：

1. `fact`
2. `method`
3. `experiment_result`
4. `numeric`
5. `table`
6. `figure`
7. `formula`
8. `limitation`
9. `compare`
10. `cross_paper_synthesis`
11. `citation_trace`
12. `kb_global`
13. `no_answer`
14. `conflict_verification`

## 9.2 family 解释

### `fact`

问单个明确事实。

用于评估：

1. 基础检索
2. 单段 evidence 命中
3. 简明 grounded answer

### `method`

问方法设计、模型结构、训练设置、实验协议。

用于评估：

1. section-aware retrieval
2. 方法描述 faithful summary

### `experiment_result`

问实验结论、结果对比、ablation 发现。

用于评估：

1. 结果 section 定位
2. 数值周边文本理解

### `numeric`

问具体数字、差值、提升幅度、指标变化。

用于评估：

1. 数值抽取
2. 单位与方向理解
3. hallucination 抑制

### `table`

问表格中的结果与对比。

用于评估：

1. table evidence retrieval
2. 行列对齐
3. 表格 reasoning

### `figure`

问图中趋势、结构示意、caption 对应含义。

用于评估：

1. figure caption + surrounding text evidence
2. 非纯文本证据使用能力

### `formula`

问公式定义、符号意义、损失函数关系、数学假设。

用于评估：

1. 公式周边文本理解
2. 数学表达 faithful paraphrase

### `limitation`

问论文自己承认的限制、边界条件、风险。

用于评估：

1. 负面信息检索
2. 防止只会总结优点

### `compare`

问两篇或多篇论文的差异。

用于评估：

1. multi-paper retrieval
2. structure-aligned synthesis

### `cross_paper_synthesis`

问多篇论文共同趋势、共识、分歧。

用于评估：

1. 多证据整合
2. 不能只拼接单篇摘要

### `citation_trace`

问某结论到底由哪一段、哪一页、哪一块证据支持。

用于评估：

1. citation jump
2. evidence traceability

### `kb_global`

问一个知识库层面的总结性问题。

用于评估：

1. 整库检索
2. evidence 聚合
3. partial answer / abstain

### `no_answer`

问知识库中没有、证据不足或超出范围的问题。

用于评估：

1. abstain precision
2. 不胡编能力

### `conflict_verification`

问存在论文间冲突、模型先验冲突、或结论反向的案例。

用于评估：

1. faithfulness under conflict
2. 是否把参数知识压过 retrieved evidence

# 10. 推荐的标注协议

## 10.1 论文级标注

每篇论文至少需要：

1. `paper_id`
2. `title`
3. `discipline`
4. `subfield`
5. `year`
6. `language`
7. `pdf_source_type`
8. `layout_complexity`
9. `table_density`
10. `figure_density`
11. `formula_density`
12. `scan_quality`

## 10.2 query 级标注

每条 query 至少需要：

1. `query_id`
2. `question`
3. `family`
4. `discipline`
5. `difficulty`
6. `answerability`
7. `paper_scope`
8. `gold_short_answer`
9. `gold_long_answer`
10. `must_abstain`
11. `abstain_reason`

## 10.3 evidence 级标注

每条 query 需要至少 1 个 gold evidence block，可扩展到 N 个：

1. `evidence_id`
2. `paper_id`
3. `page_num`
4. `section_path`
5. `char_start`
6. `char_end`
7. `quote`
8. `evidence_type`
   - text / table / figure / formula
9. `support_role`
   - primary / secondary / contrast / limitation
10. `citation_target`
   - 用于跳转定位

## 10.4 claim 级标注

为兼容后续 `Phase 3.0-C`，建议 query 附带可选 `claims[]`：

1. `claim_id`
2. `claim_text`
3. `support_required`
4. `evidence_ids[]`
5. `support_level`
   - supports / partially_supports / insufficient / refutes

## 10.5 不可回答标注

`no_answer` 不能只靠 `must_abstain=true`。

建议细分 `abstain_reason`：

1. `out_of_corpus`
2. `missing_evidence`
3. `question_underspecified`
4. `ambiguous_entity`
5. `requires_external_knowledge`
6. `conflicting_without_resolution`

# 11. 推荐的 artifact 结构

## 11.1 不建议直接覆盖 phase6

`phase6` 当前已经服务于 `v2.0` close-out gate，不建议直接覆写。

建议：

1. 保留 `apps/api/artifacts/benchmarks/phase6/` 作为 `v2.x` 冻结门禁真源。
2. 新建独立命名空间承载 `Academic Benchmark 3.0`。

建议路径：

```txt
apps/api/artifacts/benchmarks/v3_0_academic/
```

## 11.2 推荐目录

```txt
v3_0_academic/
  corpus_public.json
  corpus_blind.json
  annotation_guide.md
  manifest.json
  runs/
    {run_id}/
      meta.json
      retrieval.json
      evidence.json
      answer_quality.json
      abstain_quality.json
      family_breakdown.json
      domain_breakdown.json
      diff_from_baseline.json
      dashboard_summary.json
```

## 11.3 与现有 phase6 的关系

推荐关系：

1. `phase6` 继续承担“v2 release gate”
2. `v3_0_academic` 承担“Academic Benchmark 3.0”
3. 两者在 artifact 模式上保持兼容，但不混写

这样能避免：

1. v3.0 大扩容破坏 v2 gate 稳定性
2. 团队在“是否替换旧门禁”上反复摇摆

# 12. 推荐的指标体系

## 12.1 Retrieval 层

最少保留：

1. `paper_hit_at_k`
2. `section_hit_at_k`
3. `recall_at_5`
4. `recall_at_10`
5. `mrr`
6. `ndcg_at_10`

新增建议：

1. `modality_hit_rate`
   - table / figure / formula 分 modality 命中率
2. `multi_evidence_recall`
   - 多证据题是否找齐关键 evidence
3. `blind_retrieval_gap`
   - blind 与 public 的 retrieval 性能差距

## 12.2 Evidence 层

新增为正式一级指标：

1. `exact_chunk_hit_rate`
2. `overlap_span_hit_rate`
3. `evidence_bundle_hit_count`
4. `citation_jump_valid_rate`
5. `primary_evidence_coverage`

其中 `overlap_span_hit_rate` 对后续 span citation 尤其关键。

## 12.3 Answer 层

建议区分：

1. `answer_correctness`
2. `answer_supported_rate`
3. `groundedness`
4. `conflict_faithfulness`
5. `partial_answer_quality`

## 12.4 Abstain 层

建议将 abstain 从附属指标升为正式 gate：

1. `abstain_precision`
2. `abstain_recall`
3. `acceptable_abstain_rate`
4. `false_answer_rate_on_unanswerable`

## 12.5 诊断层

每次 run 必须产出：

1. `by_family`
2. `by_discipline`
3. `by_difficulty`
4. `by_modality`
5. `by_answerability`

否则整体分数没有解释力。

# 13. blind benchmark 设计

## 13.1 为什么必须做 blind

`Benchmark 3.0` 的 blind set 是防止评测系统被“共同优化污染”的最低要求。

如果没有 blind set，后续任何 prompt、retriever、reranker、citation 策略的优化都会逐渐贴合 public set。

## 13.2 推荐结构

建议拆成：

1. `public_dev`
   - 对工程团队可见，用于日常迭代
2. `public_test`
   - 对团队可见，但不允许反复用作 prompt 手调
3. `blind_test`
   - 题目、gold、evidence 全部隐藏，仅经 gate 服务产出分数

## 13.3 blind set 比例

建议：

1. `public_dev = 50%`
2. `public_test = 20%`
3. `blind_test = 30%`

blind 的 query family 与 discipline 分布必须与 public 保持近似一致，但题目本身不重叠。

## 13.4 blind 运行原则

1. 工程本地只能直接运行 public。
2. blind 只在受控 runner 或 CI 产出汇总分。
3. blind 不回传样本级 gold evidence，只回传 failure bucket 与 aggregate breakdown。

# 14. 推荐的人工标注策略

## 14.1 标注角色

建议最少采用双角色：

1. `annotator`
   - 写 query、gold answer、gold evidence
2. `reviewer`
   - 复核 evidence 与 answer 是否一致

高风险 family 建议双审：

1. `numeric`
2. `table`
3. `figure`
4. `formula`
5. `conflict_verification`

## 14.2 标注粒度原则

1. gold answer 要尽量短，但足以唯一判定。
2. gold long answer 要可被 faithful paraphrase。
3. gold evidence 优先标最小支撑片段，而不是整页整段。
4. 如需多证据才能回答，必须明确 `primary` 与 `secondary`。

## 14.3 质检规则

每批标注必须抽查：

1. query 是否真的 answerable / unanswerable
2. gold answer 是否被 evidence 真实支撑
3. evidence span 是否可定位
4. multi-paper query 是否确实需要多篇论文
5. abstain 标注是否不是“因为 annotator 懒得找”

# 15. 推荐的实施节奏

## 15.1 Stage A：Schema Freeze

输出：

1. `Benchmark 3.0` schema
2. family taxonomy
3. annotation guide

目标：

先冻结数据形态，再做大规模采集。

## 15.2 Stage B：Public Set Build

输出：

1. `200 papers`
2. `500-800 queries`
3. gold answer / gold evidence 基线

目标：

先让 public benchmark 能跑通 end-to-end。

## 15.3 Stage C：Blind Set Build

输出：

1. blind set 独立封装
2. blind runner / score-only pipeline

目标：

避免 benchmark 一边构建一边被污染。

## 15.4 Stage D：Gate Upgrade

输出：

1. `baseline / candidate / diff`
2. family/domain/modality breakdown
3. 新阈值建议

目标：

让 `Academic Benchmark 3.0` 成为真正约束 RAG 迭代的体系。

# 16. 与后续 phase 的关系

## 16.1 对 3.0-B 的作用

External Search + Import to KB 会显著扩大学科和文档来源，`Benchmark 3.0` 必须提前定义好异构语料与 metadata 标注规则。

## 16.2 对 3.0-C 的作用

没有 claim/evidence 标注，后续 span-level citation 和 claim verification 无法被真实评测。

## 16.3 对 3.0-D 的作用

real-world validation 不是 benchmark 的替代品，而是 benchmark 的外部验证层。二者必须结构兼容。

## 16.4 对 3.0-E 的作用

一旦 benchmark 扩到 `500-1500 queries`，latency / cost / cache / batch runtime 会成为正式问题，因此 benchmark 设计必须能记录这些运行指标。

# 17. 风险与决策点

## 17.1 最大风险

最大风险不是“采样不到 500 篇论文”，而是：

```txt
做成了一个更大的题库，
但没有把 gold evidence、blind set、family breakdown 建完整，
结果只是把旧 benchmark 放大了一圈。
```

## 17.2 关键决策点

后续实施前必须确认：

1. `Benchmark 3.0` 是否独立命名空间，不覆盖 `phase6`
2. `public / blind` 的具体比例
3. `formula` 是否作为正式 family 第一阶段上线
4. `LLM judge` 在 answer quality 中承担多大权重
5. 哪些 family 需要双人审核

# 18. 正式建议

基于仓库现状与外部前沿信号，我对 `v3.0-A Academic Benchmark 3.0` 的正式建议是：

1. 保留当前 `phase6` 作为 `v2.x` 冻结门禁，不直接改写。
2. 新建独立 `v3_0_academic` benchmark 命名空间。
3. 第一阶段目标设为 `200 papers / 500-800 queries`，而不是一开始就冲 `500 papers / 1500 queries`。
4. family 从当前 `8` 类扩展到 `14` 类，重点补 `numeric / figure / formula / limitation / conflict_verification`。
5. 每题必须有 `gold answer + gold evidence`，并预留 `claims[]` 结构。
6. blind benchmark 必须与 public benchmark 同时建设，而不是等 public 用旧了再补。
7. gate 报告必须默认输出 `family / discipline / modality / answerability` 四维切片，而不是只看 overall。

# 19. 结论

一句话总结：

```txt
Academic Benchmark 3.0 不是把 50 篇扩成 500 篇这么简单，
而是把 ScholarAI 的评测体系从“工程回归门禁”
升级成“跨学科、证据驱动、可盲评、可支撑 claim-level 学术严谨性”的正式基础设施。
```

如果只扩规模，不升级：

1. family taxonomy
2. gold evidence 协议
3. blind set
4. modality / discipline breakdown

那它仍然不是 v3.0 需要的 benchmark。
