# v3.0D Execution Plan Review

日期：2026-04-29
状态：review
评审对象：docs/plans/v3_0/active/phase_d/10_v3_0D_execution_plan.md

## 1. 结论

执行计划方向正确，已满足"真实论文 + 真实工作流 + 失败收口"的核心验证主线要求。

Phase D 是 v3.0 进入 Public Beta（Phase G）前的最后一道真实世界门控，执行计划整体可执行。

## 2. 覆盖性检查

- WP0 合理：先冻结 scope，防止不同 run 用不同口径导致结果不可比。
- WP1 合理：先建样本台账，防止执行时"临时挑好跑的论文"污染结论。
- WP2 合理：验证主链跨页面贯通，而非单页通过。
- WP3 合理：把失败正式分桶，而非散落截图或零散 issue。
- WP4 合理：在真实场景中验证 citation / claim，而非只依赖 benchmark。
- WP5 合理：诚实性检查是 Phase D 的独特价值，不能跳过。
- WP6 合理：close-out 报告是唯一输出真源，后续 Phase G 必须引用。

## 3. 建议补充的执行检查点

### 3.1 WP0 Scope Freeze 检查点

- `v3_0D_kickoff_freeze.md` 已填写并对齐执行计划。
- `v3_0D_sample_registry.md` 已初始化样本台账结构。
- `v3_0D_failure_bucket_spec.md` 已确认三级分桶定义。
- 所有执行者已阅读以上三份文档后才开始运行。

### 3.2 WP1 Sample Intake 检查点

- 八类高风险样本类型均有至少一条 `sample_id` 填入。
- 无样本只来自"理想 PDF"或"benchmark 专用论文集"。
- 至少有 3 条 `expected_risk=known_failure` 的边界样本。
- `sample_id` 命名符合规范（`D-{序号}`）。

### 3.3 WP2 Workflow Validation 检查点

- 每个 run 明确记录 `workflow_steps[]`，不以"整体通过"掩盖中间步骤失败。
- 至少有一个 run 完整覆盖 `search->import->read->chat->notes->compare->review`。
- "上一环输出是否被下一环消费"在每个 step 有明确的 pass/fail 记录。
- 不允许单页面 pass（如只测 Chat）替代全链路 pass。

### 3.4 WP3 Failure Capture 检查点

- 所有失败均按 `blocking / degrading / paper_cut` 分桶，无游离记录。
- 每条失败记录含 `failure_id / run_id / sample_id / workflow_step / bucket / description`。
- `affects_honesty=true` 的失败被特别标记。
- blocking 失败已被优先复盘，而不是仅计数。

### 3.5 WP4 Evidence Quality 检查点

- 每个 run 对 Chat / Compare / Review 中关键输出抽查 evidence。
- `unsupportedClaimRate` 与真实 UI 呈现一致（badge 可见）。
- citation jump 落点已人工核查，而非只检查跳转状态码。
- 图表密集论文的 evidence 是否退化为纯文本描述，已记录。

### 3.6 WP5 Honesty 检查点

- `metadata-only / fulltext-ready` 状态在 UI 层可区分，已人工核查。
- 下载失败 / 解析失败时，系统是否诚实提示，已验证。
- 局部失败（一篇论文解析失败）是否会污染整个 KB 的 Chat，已测试。
- 系统不会在失败时只返回"质量差一点的结果"而不报错，已确认。

### 3.7 WP6 Close-out 检查点

- 报告路径：`docs/reports/v3_0_real_world_validation.md`（唯一输出）。
- 报告包含：样本组成、workflow 覆盖、成功率、失败分桶、高风险复盘、release 建议。
- blocking 失败全部在报告中出现，不能聚合省略。
- 报告有明确的 beta 可行性结论（建议进入 / 有条件进入 / 暂不建议进入 Phase G）。

## 4. 风险复核

### 4.1 样本污染风险

**风险**：执行者临时选择"好跑"的论文，样本集偏向乐观。

**缓解**：
- WP1 强制要求八类高风险类型各自有最少 case 数。
- `v3_0D_sample_registry.md` 是唯一台账，执行后补填 `observed_failures`，可追溯。

### 4.2 单页面验证风险

**风险**：执行者只验证 Chat 或 Search 单页面，声称"主链通过"。

**缓解**：
- WP2 要求每个 run 记录 `workflow_steps[]`，不以整体 pass 替代步骤级记录。
- 至少一个 run 覆盖完整主链（7 步）。

### 4.3 失败散落风险

**风险**：失败被记录在截图、Notion 或口头，无法汇总到 close-out 报告。

**缓解**：
- `v3_0D_failure_bucket_spec.md` 规范了唯一记录格式。
- WP6 close-out 报告的失败统计必须来自分桶记录，不允许另起汇总。

### 4.4 诚实性漏检风险

**风险**：`metadata-only` 误标为 fulltext-ready 的问题未被发现，直接进入 beta。

**缓解**：
- WP5 独立成一个 Work Package，不允许被合并到 WP2 或省略。
- `affects_honesty=true` 的失败需要在 close-out 报告中单独列出。

### 4.5 上游依赖未完成风险

**风险**：Phase A/B/C 的部分实现未收尾，但 Phase D 已开始运行。

**缓解**：
- 执行计划明确指出：Phase D 文档把 A/B/C 当作"已定义边界"，不是"已完成实现"。
- 遇到上游能力缺失时，记录为 `blocking` 或 `degrading`，不跳过，不假设上游已完成。

## 5. 建议补充的验收用例

以下用例在 Phase D 验收时应能被正面回答：

1. 一篇来自 arXiv 的外部论文，能完整走完 `search->import->chat->review`，且 Chat 中有 claim badge（supported / unsupported 均可出现）。
2. 一篇扫描版 PDF 在导入失败时，系统返回可解释错误，而非"空 KB + 200 OK"。
3. 一个图表密集论文的 KB，Chat 回答中引用了 figure 相关内容（即使以描述方式）。
4. 对一篇论文执行 Read -> Chat -> Review，三个页面中的 claim status 含义一致。
5. 从 Review 中对一条 `unsupported` claim 执行 repair，状态发生可解释变化。
6. 一个跨学科 KB（≥3 个学科），Compare 输出中的 evidence 来自多篇不同论文。
7. `metadata-only` 论文在 Chat 中明确提示"仅 metadata 可查询"，不伪装成全文可用。

## 6. 与上下游的衔接检查

### 6.1 Phase C 产物是否可被 Phase D 消费

- `claim_verification` 字段是否在真实 Review Draft 中出现：需在 WP4 中验证。
- `quote_text / source_offset` 是否在 citation jump 中可用：需在 WP4 中验证。
- `repair_claim` 接口在真实 KB 上是否可用：需在 WP5 中验证。

### 6.2 Phase B 产物是否可被 Phase D 消费

- arXiv / Semantic Scholar 导入的论文是否能进入 Read / Chat：需在 WP2 中验证。
- `canonical ExternalPaper` 字段（title / doi / abstract）是否真实展示：需在 WP1 中确认。

### 6.3 为 Phase G 提供的输出

- `v3_0_real_world_validation.md` 报告必须包含 beta 可行性结论。
- Phase G 启动时必须引用此报告，不重新定义"什么是真实世界可用"。
