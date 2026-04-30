---
标题：ScholarAI v3.0-A Academic Benchmark 3.0 Kickoff Freeze
日期：2026-04-28
状态：freeze
用途：冻结 Phase A kickoff 前必须明确的 4 个缺口决策，供执行者直接遵循
---

# 1. 目的

本文件用于关闭 `Phase A` 审核记录中指出的 4 个高风险未冻结点。

执行原则：

```txt
如本文件与更早研究/设计文档存在未定项冲突，
以本文件为 kickoff 之后的执行真源。
```

# 2. 冻结项总览

本次 freeze 明确以下 4 个决策：

1. `formula` family 在 P0 阶段进入 taxonomy，但不进入 hard gate。
2. blind corpus / blind runner 的 owner 分工冻结。
3. `claims[]` 的 P0 覆盖范围冻结。
4. `200 papers / 500-800 queries` 的 discipline / family sourcing quota 冻结。

# 3. Freeze-01：`formula` gate 策略

## 决策

P0 阶段：

1. `formula` family 是正式 family。
2. `formula` query 必须进入 public / blind 数据集。
3. `formula` family **只进入 report-only，不进入 hard gate**。

## 原因

1. taxonomy 需要从一开始覆盖公式场景。
2. 当前 extraction / evidence span 主链对公式的稳定性还不足以直接承担阻断职责。
3. 过早进入 hard gate 会把 extraction 缺陷误判成 retrieval / answer 回退。

## 执行要求

执行者在实现 artifact / gate 时必须：

1. 让 `formula` 出现在 `family_breakdown.json`。
2. 让 `formula` 出现在 dashboard 的 report-only family 列表。
3. 不将 `formula` family 得分纳入 P0 release blocking verdict。

# 4. Freeze-02：Blind Owner 分工

## 决策

blind 相关 owner 分工如下：

1. `blind corpus owner`
   - `ai-platform`
2. `blind gold owner`
   - `ai-platform`
3. `blind runner owner`
   - `ai-platform`
4. `benchmark implementation consumer`
   - `ai-runtime`

## 权限边界

1. 普通研发链路默认只消费 `public_dev / public_test`。
2. blind gold 不进入普通开发工作区默认输出。
3. blind run 只返回 aggregate metrics + failure bucket summary。
4. blind 样本级 gold evidence 不回传给日常调参链路。

## 执行要求

执行者在实现 blind 流程时必须：

1. 将 blind corpus 与 public corpus 物理隔离。
2. 在文档和脚本中明确 blind 为 score-only 模式。
3. 避免把 blind query_id 对应 gold evidence 输出到 diff 报告中。

# 5. Freeze-03：`claims[]` 覆盖范围

## 决策

P0 阶段不是所有 answerable query 都要求 claim 标注。

P0 强制要求 `claims[]` 的 families：

1. `compare`
2. `cross_paper_synthesis`
3. `numeric`
4. `conflict_verification`
5. `limitation`

P0 非强制、但允许填写 `claims[]` 的 families：

1. `fact`
2. `method`
3. `experiment_result`
4. `table`
5. `figure`
6. `formula`
7. `citation_trace`
8. `kb_global`

## 原因

1. 这些 family 最容易出现“一个回答包含多个可独立验证断言”的情况。
2. 若要求全量 query 都拆 claim，P0 标注成本会显著膨胀。

## 执行要求

执行者在标注与数据校验时必须：

1. 对强制 family 做 `claims[]` presence 校验。
2. 对非强制 family 不做阻断，但保留兼容结构。

# 6. Freeze-04：Discipline / Family 配额

## 6.1 P0 论文配额

P0 目标固定为 `200 papers`。

建议配额：

1. `computer_science`: 50
2. `medicine`: 40
3. `economics`: 30
4. `mathematics`: 30
5. `education`: 30
6. `interdisciplinary`: 20

原则：

1. 允许单个 discipline 在执行中上下浮动 `±5`。
2. 不允许任何 discipline 缺失。
3. `computer_science` 不得超过 60。

## 6.2 P0 query 配额

P0 目标范围固定为 `500-800 queries`。

推荐目标值：`688 queries`（按下方 family quota 合计值执行）。

family 配额建议：

1. `fact`: 64
2. `method`: 64
3. `experiment_result`: 64
4. `numeric`: 48
5. `table`: 48
6. `figure`: 48
7. `formula`: 32
8. `limitation`: 48
9. `compare`: 48
10. `cross_paper_synthesis`: 48
11. `citation_trace`: 32
12. `kb_global`: 48
13. `no_answer`: 48
14. `conflict_verification`: 48

## 6.3 配额使用规则

1. `formula` 与 `citation_trace` 可作为相对低配额 family 进入 P0。
2. `no_answer` 不得低于 48。
3. `compare + cross_paper_synthesis + conflict_verification` 三者合计不得低于 144。
4. `table + figure + formula` 三者合计不得低于 128。

# 7. 执行者如何使用本文件

执行者必须按以下方式消费本文件：

1. 在读完研究文档后，先读取本文件，再开始 schema 与数据实施。
2. 若 schema / annotation / gate 文档中存在“未定项”，以本文件冻结值为准。
3. 若后续需要改动这 4 项，必须先更新本文件，再改实现。

# 8. 对现有文档的约束

本文件对以下文档形成补充约束：

1. `docs/plans/v3_0/active/phase_a/07_v3_0A_execution_plan.md`
2. `docs/specs/contracts/v3_0_academic_benchmark_schema.md`
3. `docs/plans/v3_0/active/phase_a/2026-04-28_v3_0A_annotation_guide.md`
4. `docs/plans/v3_0/active/phase_a/2026-04-28_v3_0A_artifact_gate_design.md`
5. `docs/plans/v3_0/active/phase_a/2026-04-28_v3_0A_execution_plan_review.md`

# 9. 结论

一句话结论：

```txt
Phase A kickoff 之后，
执行者不再需要自己判断 formula 是否阻断、claims 要不要全量、blind 谁负责、discipline 配额怎么分，
这些都以本文件为准直接执行。
```
