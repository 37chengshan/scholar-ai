# 10 v3.0-D 执行计划：Real-world Validation

> 日期：2026-04-29  
> 状态：execution-plan  
> 上游研究：`docs/plans/v3_0/active/phase_d/2026-04-29_v3_0D_Real_World_Validation_研究文档.md`  
> 文档前提：按“Phase A / Phase B / Phase C 结构性产物已完成并可复用”来组织执行，不代表仓库当前代码状态已完全完成

## 1. 目标

`Phase D` 的执行目标是把 `Real-world Validation` 从研究结论推进成可实施的真实工作流验证框架，形成：

```txt
real sample intake
-> workflow run execution
-> failure / recovery capture
-> evidence quality review
-> validation report
-> release / beta readiness input
```

## 2. 执行前先读什么

执行者开始前，按以下顺序读取：

1. `docs/plans/v3_0/active/overview/06_v3_0_overview_plan.md`
2. `docs/plans/v3_0/active/phase_d/2026-04-29_v3_0D_Real_World_Validation_研究文档.md`
3. `docs/plans/v3_0/active/phase_c/09_v3_0C_execution_plan.md`
4. `docs/plans/v3_0/active/phase_b/08_v3_0B_execution_plan.md`
5. `docs/plans/v3_0/active/phase_a/07_v3_0A_execution_plan.md`
6. `docs/reports/v3_0_academic_adoption_report.md`
7. `docs/plans/v3_0/reports/validation/2026-04-22_retrieval_benchmark_large_real_report.md`
8. `docs/plans/v3_0/reports/release/v3_6_release_gate_report.md`
9. `apps/web/src/features/search/components/SearchWorkspace.tsx`
10. `apps/web/src/features/kb/components/KnowledgeWorkspaceShell.tsx`
11. `apps/web/src/features/chat/workspace/ChatWorkspaceV2.tsx`
12. `apps/web/src/features/kb/components/KnowledgeReviewPanel.tsx`

执行规则：

1. 先固定真实样本结构，再跑工作流。
2. 先验证正式主链页面，再记录失败模式与恢复能力。
3. 任何验证都必须使用现有正式入口，不得新造“验证专用平行前端”。

## 3. Work Packages

## WP0：Validation Scope Freeze

目标：

1. 冻结 `Phase D` 的正式工作流范围
2. 冻结真实验证的最小记录字段

执行方式：

1. 以 Phase D 研究文档为准定义 workflow 主链、失败分桶和记录结构
2. 让所有 real-world run 使用同一套记录口径

验收：

1. 后续执行者不再各自定义“什么叫真实验证通过”。

## WP1：Real Sample Intake

目标：

1. 建立真实论文验证集
2. 覆盖高风险样本类型

执行方式：

1. 按研究文档中的八类样本结构建台账
2. 每个样本同步记录 `source_type / discipline / complexity / language_mix / expected_risk`
3. 不允许只挑“好跑”的论文做验证

验收：

1. 每类高风险样本至少有可复现 case。

## WP2：Workflow Path Validation

目标：

1. 固定 `Search -> Import -> KB -> Read -> Chat -> Notes -> Compare -> Review` 的正式验证主链
2. 验证上一环输出是否真能被下一环消费

执行方式：

1. 复用 `SearchWorkspace`、`KnowledgeWorkspaceShell`、`ChatWorkspaceV2`、`KnowledgeReviewPanel`
2. 对每个验证 run 显式记录是否贯通到下一环
3. 不以单页 pass 替代整链路通过

验收：

1. 每个 real-world run 都有明确的 workflow step 结果。

## WP3：Failure Mode Capture

目标：

1. 把真实失败模式正式收口
2. 区分阻断失败与退化失败

执行方式：

1. 将失败统一分成 `blocking / degrading / paper_cut`
2. 对 import、reading jump、chat evidence、compare、review 分别记录失败点
3. 不允许只截图不记原因

验收：

1. 所有失败都能被分桶，而不是散落在零散笔记里。

## WP4：Evidence Quality Review

目标：

1. 验证真实工作流中的 citation / claim verification 是否仍成立
2. 发现 benchmark 外的 evidence 质量问题

执行方式：

1. 对 Chat / Compare / Review 中的关键输出做 evidence 抽查
2. 重点检查 unsupported claim 是否真实暴露
3. 重点检查 citation jump 是否落到合理证据

验收：

1. 真实样本中的 evidence 问题可被系统化记录，而不是主观描述。

## WP5：Recovery + Honesty Check

目标：

1. 验证系统是否能诚实表达失败
2. 验证失败后的恢复路径是否存在

执行方式：

1. 重点检查 `metadata-only / fulltext-ready` 是否被诚实区分
2. 重点检查下载失败、解析失败、证据不足时是否有可解释结果
3. 重点检查局部失败是否污染整个 KB

验收：

1. 系统不会把失败伪装成成功，只是“质量差一点”。

## WP6：Close-out Report

目标：

1. 形成 `Phase D` 的正式 close-out 报告
2. 为 `Phase G Public Beta` 提供真实输入

执行方式：

1. 固定输出到 `docs/reports/v3_0_real_world_validation.md`
2. 报告至少包含样本组成、workflow 覆盖、成功率、失败分桶、高风险复盘、release 建议
3. 不以 raw logs 代替 close-out 报告

验收：

1. 产品、工程、演示与 release 可以引用同一份真实世界验证真源。

## 4. 实际执行顺序

执行者按以下顺序推进：

1. `WP0 Validation Scope Freeze`
2. `WP1 Real Sample Intake`
3. `WP2 Workflow Path Validation`
4. `WP3 Failure Mode Capture`
5. `WP4 Evidence Quality Review`
6. `WP5 Recovery + Honesty Check`
7. `WP6 Close-out Report`

原因：

1. scope 不冻，后续 run 结果不可比。
2. 样本不先建，workflow 验证会被“临时挑样本”污染。
3. 不先记失败模式，最后只会得到一堆“感觉哪里不对”的零散反馈。

## 5. 下层文档

当前 Phase D 已有：

1. `docs/plans/v3_0/active/phase_d/2026-04-29_v3_0D_Real_World_Validation_研究文档.md`

后续建议补齐：

1. `v3_0D_kickoff_freeze.md`
2. `v3_0D_sample_registry.md`
3. `v3_0D_failure_bucket_spec.md`
4. `v3_0D_execution_plan_review.md`

## 6. 验收标准

Phase D P0 可视为完成，当且仅当：

1. 真实论文验证集结构冻结。
2. `Search -> Import -> KB -> Read -> Chat -> Notes -> Compare -> Review` 被正式验证。
3. 高风险样本类型被覆盖，而不是只验证理想论文。
4. 失败被记录为 `blocking / degrading / paper_cut` 三类。
5. `metadata-only / fulltext-ready`、unsupported claim、citation jump 等关键诚实性问题被显式检查。
6. 形成正式 `v3_0_real_world_validation` 报告。

## 7. 风险

1. 若样本只挑“好跑”的论文，Phase D 会失去真实性。
2. 若只做单页验证，不做跨页面主链验证，结果会高估系统可用性。
3. 若失败不分桶，后续 Phase E / G 无法拿到可执行输入。
4. 若不检查诚实性表达，系统可能在真实世界里“看起来成功，实际上不可用”。
