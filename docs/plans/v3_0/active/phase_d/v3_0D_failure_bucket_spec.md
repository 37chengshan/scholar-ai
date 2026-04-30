# v3.0D Failure Bucket Spec

日期：2026-04-29
状态：spec
范围：Phase D 失败分桶规范
上游：
- docs/plans/v3_0/active/phase_d/v3_0D_kickoff_freeze.md
- docs/plans/v3_0/active/phase_d/2026-04-29_v3_0D_Real_World_Validation_研究文档.md

## 1. 目的

本文档定义 Phase D 所有真实验证 run 中失败记录的唯一分桶口径。

- 执行者在记录失败时，必须按本规范分桶。
- 禁止以截图、口头描述或 issue URL 替代分桶记录。
- close-out 报告中的失败统计，必须基于本规范的分桶结果。

## 2. 三级分桶定义

### 2.1 blocking（阻断失败）

**定义**：主链无法继续执行，当前 run 被迫中止。

**判定标准**：

- 用户无法完成目标工作流步骤。
- 无法通过刷新、重试等简单操作恢复。
- 需要工程介入或换样本才能绕过。

**示例**：

| 示例 ID | 场景 | 判定为 blocking 的原因 |
|---|---|---|
| BL-01 | import 任务状态为 completed，但论文无法 Read / Chat | 主链断裂，无法继续 |
| BL-02 | PDF 解析失败，全文内容为空 | fulltext 不可消费 |
| BL-03 | KB 建立后 Chat 返回 500 | 页面完全不可用 |
| BL-04 | 扫描版 PDF 导入后 OCR 全部失败，零内容可检索 | 全文提取 0 |

### 2.2 degrading（退化失败）

**定义**：主链可以继续，但输出质量明显下滑，影响真实可用性。

**判定标准**：

- 用户可以完成操作，但结果质量偏低。
- unsupported claim 比例过高、evidence 明显错乱、citation jump 落点不可用。
- 可通过 repair / 换问法部分恢复，但用户无辅助工具时会误判。

**示例**：

| 示例 ID | 场景 | 判定为 degrading 的原因 |
|---|---|---|
| DG-01 | Chat 回答中 unsupported claim 比例 > 60% | 可继续，但 evidence 不可信 |
| DG-02 | citation jump 能跳页，但落点与 claim 无关 | 链路通但证据质量差 |
| DG-03 | Review Draft 生成了段落，但 unsupported claim 被写成正式结论 | 过度生成，诚实性失效 |
| DG-04 | 图表密集论文中，Chat 回答忽略所有 figure 内容 | 部分内容类型退化 |
| DG-05 | compare 生成了比较表，但所有 evidence 来自同一篇论文 | 跨论文综合失败 |
| DG-06 | 中文 query 返回全英文证据，quote 无法对齐 | 多语言处理退化 |

### 2.3 paper_cut（摩擦失败）

**定义**：不阻断主链，不严重影响质量，但会削弱用户体验、演示流畅性和真实采用意愿。

**判定标准**：

- 工作流可以完成，质量基本可接受。
- 但存在 UI 混淆、状态不同步、提示不够清晰等问题。
- 累积多个 paper_cut 会影响用户对系统的整体信心。

**示例**：

| 示例 ID | 场景 | 判定为 paper_cut 的原因 |
|---|---|---|
| PC-01 | import 完成后未自动跳转到 KB，用户需手动导航 | 不阻断，但流程不顺滑 |
| PC-02 | metadata-only 论文未显示明确提示，用户以为可全文问答 | 诚实性不足但未完全失败 |
| PC-03 | Chat 中 weakly_supported badge 颜色与 unsupported 接近，用户难以区分 | 视觉区分不足 |
| PC-04 | Review Draft 生成速度明显慢于 Chat，无进度提示 | UX 摩擦 |
| PC-05 | 从 Review 回到 KB 需要多次点击，路径不明确 | 页面间导航不顺滑 |
| PC-06 | Notes 内容在刷新后丢失 | 状态持久化问题 |

## 3. 失败记录格式

每条失败记录必须包含以下字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| `failure_id` | string | 唯一标识，格式：`F-{run_id}-{序号}` |
| `run_id` | string | 来自哪个 run |
| `sample_id` | string | 来自哪个样本 |
| `workflow_step` | string | 在哪个工作流步骤发生，如 `import / read / chat / review` |
| `bucket` | enum | `blocking / degrading / paper_cut` |
| `description` | string | 失败的具体现象描述（必须是可复现的事实，不是感受） |
| `is_recoverable` | bool | 是否存在已知恢复路径 |
| `recovery_path` | string | 如果可恢复，恢复操作是什么（若不可恢复，填 `none`） |
| `affects_honesty` | bool | 是否导致系统把失败伪装成成功 |
| `severity_notes` | string | 额外说明（可选） |

## 4. 工作流步骤分类

记录 `workflow_step` 时，使用以下标准名称：

| 步骤名 | 含义 |
|---|---|
| `search` | 外部搜索（SearchWorkspace） |
| `import` | 导入论文到 KB |
| `indexing` | KB 索引 / 解析 / 去重 |
| `read` | 文章阅读（Read 页面） |
| `chat` | KB 问答（Chat） |
| `notes` | 笔记记录（Notes） |
| `compare` | 多篇论文比较（Compare） |
| `review` | Review Draft 生成与审核 |
| `navigation` | 页面间跳转与状态传递 |

## 5. 分桶决策树

遇到失败时，按以下顺序判断：

```txt
步骤1：主链能否继续？
├─ 否 → blocking
└─ 是 → 步骤2

步骤2：输出质量是否严重下滑或诚实性失效？
├─ 是 → degrading
└─ 否 → 步骤3

步骤3：是否存在 UX 摩擦 / 状态不同步 / 提示不清晰？
├─ 是 → paper_cut
└─ 否 → 不记录（正常行为）
```

特别注意：

- `affects_honesty=true` 的失败，即使可以继续，也应优先考虑升级为 `degrading`。
- 多个 `paper_cut` 集中在同一步骤（≥3个），应评估是否需要升级。

## 6. 典型失败场景快查表

| 场景 | 推荐分桶 | 关键判定依据 |
|---|---|---|
| 导入成功但全文不可问答 | blocking | 主链断裂 |
| metadata-only 被误标为 fulltext-ready | degrading | 诚实性失效 |
| citation jump 能跳但落点无关 | degrading | 证据质量不可信 |
| review 把 unsupported 写成正式结论 | degrading | 过度生成 |
| 扫描版 PDF 全部解析失败 | blocking | 无内容可消费 |
| 图表内容被完全忽略 | degrading | 部分类型能力退化 |
| import 后未自动跳转 | paper_cut | 不阻断，只是摩擦 |
| badge 颜色难以区分 | paper_cut | UX 摩擦 |
| Notes 刷新后丢失 | paper_cut | 状态持久化问题 |
| 跨学科 KB 中 evidence 来源混乱 | degrading | 证据准确性下滑 |
| Chat 在公式密集论文中无法作答 | blocking 或 degrading | 取决于是否完全无回答 |
| compare 结果只引用一篇论文 | degrading | 跨论文综合能力退化 |

## 7. 失败汇总要求

Phase D close-out 报告中，失败统计必须包含：

1. 三类分桶各自的失败总数。
2. `affects_honesty=true` 的失败总数。
3. 按 `workflow_step` 分类的失败分布。
4. `blocking` 失败的完整列表（不允许聚合省略）。
5. 至少 3 个 blocking 样本的详细复盘。
