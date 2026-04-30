# 07 v3.0-A 执行计划：Academic Benchmark 3.0

> 日期：2026-04-28  
> 状态：execution-plan  
> 上游研究：`docs/plans/v3_0/active/phase_a/2026-04-28_v3_0A_Academic_Benchmark_3_0_研究文档.md`

## 1. 目标

`v3.0-A` 的执行目标是把 `Academic Benchmark 3.0` 从研究结论推进成可实施的评测基础设施。

阶段性交付目标：

```txt
1. 冻结 Benchmark 3.0 schema
2. 建立 public / blind 双层结构
3. 完成 P0 规模目标：200 papers / 500-800 queries
4. 建立 baseline / candidate / diff / verdict 主链
5. 保留 phase6 为 v2.x 冻结门禁，不直接覆盖
```

## 2. 范围

### 包含

```txt
1. v3_0_academic 命名空间
2. corpus / query / evidence / claim schema freeze
3. public set / blind set 结构
4. 标注与复核规范
5. artifact / gate 设计
6. family / discipline / modality / answerability 分桶
```

### 不包含

```txt
1. External Search + Import to KB 主链实现
2. span-level citation UI
3. real-world validation 实测
4. 模型替换与 reranker 选型
```

## 3. Work Packages

## 3.1 执行前先读什么

执行者开始前，必须按以下顺序读取文档：

1. `docs/plans/v3_0/active/phase_a/2026-04-28_v3_0A_Academic_Benchmark_3_0_研究文档.md`
   - 理解为什么要做 `Benchmark 3.0`
2. `docs/plans/v3_0/active/phase_a/2026-04-28_v3_0A_kickoff_freeze.md`
   - 获取 kickoff 后不再讨论的冻结决策
3. `docs/specs/contracts/v3_0_academic_benchmark_schema.md`
   - 以 schema 为数据与 artifact 真源
4. `docs/plans/v3_0/active/phase_a/2026-04-28_v3_0A_annotation_guide.md`
   - 按标注规范构建 public / blind 数据
5. `docs/plans/v3_0/active/phase_a/2026-04-28_v3_0A_artifact_gate_design.md`
   - 按 artifact / gate 设计接入 baseline / candidate / diff
6. `docs/plans/v3_0/active/phase_a/2026-04-28_v3_0A_execution_plan_review.md`
   - 了解审核发现与风险边界

执行规则：

1. 先冻结结构，再采数据。
2. 先建 public + blind 骨架，再扩 query 数量。
3. 先让 artifact / gate 可读，再谈大规模跑分。

## WP0：Schema Freeze

目标：

1. 冻结 `Benchmark 3.0` 的字段、目录和 split 结构。

输出：

1. `docs/specs/contracts/v3_0_academic_benchmark_schema.md`

验收：

1. public / blind / run artifact 使用同一 schema。

执行方式：

1. 以 `docs/specs/contracts/v3_0_academic_benchmark_schema.md` 为唯一字段真源。
2. 遇到 `formula`、`claims[]`、blind 访问边界等未定点时，直接服从 `2026-04-28_v3_0A_kickoff_freeze.md`。
3. 不允许为 blind 单独创造第二套字段模型。

## WP1：Corpus Strategy

目标：

1. 确定 `200 papers` 的 P0 语料结构、学科配比和复杂度标签。

输出：

1. discipline / complexity taxonomy
2. paper intake checklist

验收：

1. 每篇 paper 可映射到 discipline + complexity bucket。

执行方式：

1. 按 `2026-04-28_v3_0A_kickoff_freeze.md` 中的 discipline quota 建 paper intake 表。
2. 每篇 paper 录入时同步写入复杂度标签，不能后补。
3. 若某 discipline 超额或缺额，先调 sourcing，不要靠后期 query 补平。

## WP2：Public Benchmark Build

目标：

1. 构建 `public_dev + public_test`。

输出：

1. `corpus_public.json`
2. P0 query family 数据集
3. gold short answer / long answer / evidence

验收：

1. public set 可独立跑 retrieval / answer / abstain 报告。

执行方式：

1. 按 `v3_0_academic_benchmark_schema.md` 生成 `corpus_public.json`。
2. 按 `annotation_guide` 先做 gold answer，再做 gold evidence，再做 reviewer 复核。
3. 对 `compare / cross_paper_synthesis / numeric / conflict_verification / limitation` 强制填写 `claims[]`。

## WP3：Blind Benchmark Build

目标：

1. 与 public 同步建立 blind set，避免泄漏。

输出：

1. `corpus_blind.json`
2. blind score-only 运行约束

验收：

1. blind run 可输出 aggregate verdict。

执行方式：

1. 以 `kickoff_freeze` 中的 blind owner 分工为准实施。
2. blind 数据结构与 public 保持同构，但物理隔离。
3. blind runner 只产出 aggregate metrics 和 failure bucket summary。

## WP4：Artifact + Gate Upgrade

目标：

1. 让 Benchmark 3.0 进入 baseline / candidate / diff / verdict 主链。

输出：

1. `retrieval.json`
2. `evidence.json`
3. `answer_quality.json`
4. `abstain_quality.json`
5. `family_breakdown.json`
6. `domain_breakdown.json`
7. `dashboard_summary.json`
8. `diff_from_baseline.json`

验收：

1. gate 不只看 overall score。

执行方式：

1. 以 `artifact_gate_design` 为 run artifact 真源。
2. 先保证 `baseline / candidate / diff` 跑通，再补 dashboard 美化。
3. `formula` family 进入 `family_breakdown`，但按 `kickoff_freeze` 保持 report-only。

## WP5：Annotation QA + Judge Calibration

目标：

1. 建立人标、复核、抽检、judge 校准机制。

输出：

1. `docs/plans/v3_0/active/phase_a/2026-04-28_v3_0A_annotation_guide.md`

验收：

1. 高风险 family 有强制复核规则。

执行方式：

1. 严格按 `annotation_guide` 的 reviewer checklist 执行。
2. `numeric / table / figure / formula / conflict_verification / no_answer` 必须重点复核。
3. 不允许用 LLM judge 替代 gold evidence。

## WP6：Adoption + Reporting

目标：

1. 让研发能用 Benchmark 3.0 跑真实对比。

输出：

1. baseline run
2. candidate run
3. diff report
4. markdown summary

验收：

1. 能支持研发判断，而不是只产出 JSON。

执行方式：

1. 先用 public set 产出首个 baseline run。
2. 再用同一 dataset_version 跑 candidate run。
3. 最后输出 family / discipline / modality / answerability 四类切片总结。

## 4. 实际执行顺序

执行者按以下顺序推进，不按周数推进：

1. `WP0 Schema Freeze`
2. `WP1 Corpus Strategy`
3. `WP2 Public Benchmark Build`
4. `WP5 Annotation QA + Judge Calibration`
5. `WP3 Blind Benchmark Build`
6. `WP4 Artifact + Gate Upgrade`
7. `WP6 Adoption + Reporting`

原因：

1. schema 不冻，后面全是返工。
2. public 不起，blind 无法同构推进。
3. blind 不建，public 很快会被污染。
4. artifact / gate 不通，跑再多数据也不能形成正式门禁。

## 5. 下层文档

1. `docs/specs/contracts/v3_0_academic_benchmark_schema.md`
2. `docs/plans/v3_0/active/phase_a/2026-04-28_v3_0A_annotation_guide.md`
3. `docs/plans/v3_0/active/phase_a/2026-04-28_v3_0A_artifact_gate_design.md`
4. `docs/plans/v3_0/active/phase_a/2026-04-28_v3_0A_execution_plan_review.md`
5. `docs/plans/v3_0/active/phase_a/2026-04-28_v3_0A_kickoff_freeze.md`

## 6. 验收标准

Phase A P0 可视为完成，当且仅当：

1. `v3_0_academic` 独立命名空间明确。
2. public / blind 双层结构冻结。
3. `200 papers / 500-800 queries` 的 P0 目标可执行。
4. family / discipline / modality / answerability 四维切片进入正式设计。
5. 后续实现团队无需再重造数据结构。

## 7. 风险

1. blind set 若延后建设，public set 会快速被调参污染。
2. 若继续只标 `expected_paper_ids`，后续 claim verification 无法真实评测。
3. `formula` 若过早进入 hard gate，可能把 extraction 短板误判成整体回退。
