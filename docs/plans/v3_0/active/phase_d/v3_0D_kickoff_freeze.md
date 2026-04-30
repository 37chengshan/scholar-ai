# v3.0D Kickoff Freeze

日期：2026-04-29
状态：freeze
范围：Phase D（Real-world Validation）
上游：
- docs/plans/v3_0/active/overview/06_v3_0_overview_plan.md
- docs/plans/v3_0/active/phase_d/10_v3_0D_execution_plan.md
- docs/plans/v3_0/active/phase_d/2026-04-29_v3_0D_Real_World_Validation_研究文档.md

## 1. 冻结目标

Phase D 只做真实工作流验证，不新造平行前端或评测专用入口。

主链冻结为：

```txt
external search
-> import to KB
-> import status / dedupe / indexing
-> Read
-> Chat
-> Notes
-> Compare
-> Review Draft
-> failure / recovery capture
-> close-out report
```

## 2. Freeze 条款

### Freeze-01：必须使用正式入口

- 所有验证 run 必须通过现有正式 UI 主链执行。
- 禁止新建"验证专用"或"演示专用"平行前端路径。
- 正式入口清单：
  - `apps/web/src/features/search/components/SearchWorkspace.tsx`
  - `apps/web/src/features/kb/components/KnowledgeWorkspaceShell.tsx`
  - `apps/web/src/features/chat/workspace/ChatWorkspaceV2.tsx`
  - `apps/web/src/features/kb/components/KnowledgeReviewPanel.tsx`

### Freeze-02：样本必须覆盖高风险类型

- 真实验证集必须包含研究文档中定义的八类样本。
- 禁止只选"好跑"的理想论文。
- 每类高风险样本至少有一个可复现 case。
- 样本台账使用 `v3_0D_sample_registry.md` 作为唯一记录来源。

### Freeze-03：失败分桶口径统一

- 所有失败统一分成三类：`blocking / degrading / paper_cut`。
- 不允许散落在截图、零散 issue 或口头描述里。
- 失败分桶定义使用 `v3_0D_failure_bucket_spec.md` 作为唯一规范。

### Freeze-04：workflow 验证必须跨页面

- 不以单页面通过替代整链路通过。
- 每个 run 必须显式记录每个 workflow step 的输入/输出状态。
- "上一环输出是否真能被下一环消费"是必检项。

### Freeze-05：诚实性表达必须显式检查

- `metadata-only / fulltext-ready` 区分是否真实，必须检查。
- unsupported claim 是否真实暴露在 UI 中，必须检查。
- 系统不能把失败伪装成"质量差一点的成功"。

### Freeze-06：close-out 报告是唯一输出真源

- Phase D 的结论必须收口成 `docs/reports/v3_0_real_world_validation.md`。
- 不以 raw logs / 截图 / 口头结论替代正式报告。
- 后续 Phase G Public Beta 必须引用此报告，不重新做结论。

## 3. 结果记录字段冻结

每个真实验证 run 必须包含以下字段：

| 字段 | 含义 |
|---|---|
| `run_id` | 唯一标识 |
| `sample_set` | 引用 sample_registry 中的样本集名 |
| `workflow_steps[]` | 每步的输入状态与输出状态 |
| `success_state` | pass / partial / blocked |
| `failure_points[]` | 每个失败点，含分桶类型 |
| `recovery_actions[]` | 是否存在可操作恢复路径 |
| `evidence_quality_notes` | citation / claim 质量的文字摘要 |
| `user_visible_confusions` | 用户可见的混淆或误导点 |

## 4. 执行顺序冻结

1. WP0 Validation Scope Freeze
2. WP1 Real Sample Intake
3. WP2 Workflow Path Validation
4. WP3 Failure Mode Capture
5. WP4 Evidence Quality Review
6. WP5 Recovery + Honesty Check
7. WP6 Close-out Report

原因：scope 和样本不先固定，后续所有 run 的结果不可比，也无法形成可引用的真源。

## 5. 风险冻结

- 禁止以单点测试（如只测 retrieval）替代全链路验证。
- 禁止以"感觉好多了"替代失败分桶记录。
- 禁止以 benchmark 通过率替代真实工作流通过率。
- 禁止让 Phase D 报告依赖未完成的 Phase A/B/C 产物。

## 6. 验收闸门

通过条件：

1. 真实论文验证集结构已冻结，样本台账已填入。
2. 至少 20 个完整 workflow run 被正式记录。
3. 所有失败被分桶为 blocking / degrading / paper_cut，无散落记录。
4. `metadata-only / fulltext-ready` 诚实性已显式检查。
5. close-out 报告已写入 `docs/reports/v3_0_real_world_validation.md`。
