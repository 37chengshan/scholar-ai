---
owner: product-engineering
status: done
depends_on:
  - 20_v4_0_phase_1_execution_plan
  - 21_v4_0_phase_2_execution_plan
  - v4_0_phase_3_citation_backed_review_artifacts_research
last_verified_at: 2026-05-08
evidence_commits:
  - working-tree-v4-0-phase-3-execution-plan
---

# 22 v4.0-3 执行计划：Citation-backed Review Artifacts

> 日期：2026-05-08
> 状态：execution-plan
> 上游研究：`docs/plans/v4_0/active/phase_3/2026-05-08_v4_0_phase_3_citation_backed_review_artifacts_research.md`
> 上游 Phase 2 closeout：`docs/plans/v4_0/reports/2026-05-04_v4_0_phase_2_closeout_report.md`

## 0. 执行状态

Phase 4.0-3 当前进入执行计划阶段。它的目标不是重做 Review / Notes / Compare 页面，而是把已有的结构化产物收束为一套可交付、可回跳、可审计的 citation-backed artifact bundle。

本计划只定义 Phase 3 的执行拆解和验收口径。后续真正执行时，必须按本计划逐项补齐 artifact contract、citation audit、known limitations、return path 和 closeout report。

## 1. 目标

Phase 4.0-3 的目标是完成 citation-backed review artifact hardening：

```txt
Review Draft
-> Citation Audit
-> Evidence Note
-> Compare Matrix
-> Known Limitations
-> Run Trace / Return Path
-> artifact closeout
```

Phase 3 完成后最多只能声明 `artifact-ready` 或 `citation-backed-ready`。它不能声明 beta-ready、public beta、production release 或 release-pass。

## 2. 执行前先读什么

1. `docs/plans/v4_0/active/overview/18_v4_0_overview_plan.md`
2. `docs/plans/v4_0/active/phase_3/2026-05-08_v4_0_phase_3_citation_backed_review_artifacts_research.md`
3. `docs/plans/v4_0/reports/2026-05-04_v4_0_phase_2_closeout_report.md`
4. `docs/plans/v4_0/reports/2026-05-04_v4_0_top_level_status_report.md`
5. `docs/specs/design/frontend/DESIGN_SYSTEM.md`
6. `docs/specs/architecture/api-contract.md`
7. `docs/specs/domain/resources.md`
8. `apps/api/app/models/review_draft.py`
9. `apps/api/app/services/review_draft_service.py`
10. `apps/api/app/api/kb/kb_review.py`
11. `apps/api/app/api/notes.py`
12. `apps/api/app/api/compare.py`
13. `apps/web/src/features/kb/components/KnowledgeReviewPanel.tsx`
14. `apps/web/src/services/kbReviewApi.ts`
15. `apps/web/src/services/notesApi.ts`
16. `apps/web/src/services/compareApi.ts`

## 3. 当前可直接消费的真实能力

| area | current state | Phase 3 usage |
|---|---|---|
| ReviewDraft / ReviewRun | 已有结构化资源、run trace、evidence、recovery actions | 作为 artifact bundle 主体 |
| Notes evidence persistence | 已有 `linked_evidence`、note title normalization、source tags | 作为 evidence note 与 return path 容器 |
| Compare v4 | 已有 evidence-backed compare matrix 与 compare card | 作为 cross-paper artifact |
| KB review panel | 已能读取 review draft / run trace、显示 citation coverage、repair claim | 作为交付与修复入口 |
| chat handoff | 已支持 review / compare / read -> Chat 的 prefill-only 跳转 | 作为 artifact return path |
| governance | 现有 PLAN_STATUS / phase ledger 机制已可回填 | 新 artifact 产物必须同步台账 |

## 4. 术语约束

执行过程中只能使用以下结论词：

| term | allowed when |
|---|---|
| `artifact-ready` | review draft、citation audit、evidence note、compare matrix、known limitations、run trace 均存在 |
| `citation-backed-ready` | 每个 claim 可回跳 evidence，且 return path 可复查 |
| `blocked` | 任一 artifact contract 或 return path 失败 |
| `partial` | 存在真实证据不足或 unsupported claim，需要进入修复或 carry-forward |

禁止在 Phase 3 closeout 中写 `beta-ready`、`public-beta-ready`、`production-ready` 或 `release-pass`，除非后续 Phase 4.0-7 给出独立 release verdict。

## 5. Work Packages

## WP1：Artifact Contract Freeze

目标：

1. 冻结 Phase 3 的 artifact 类型、字段和回跳语义。
2. 明确 review draft、citation audit、evidence note、compare matrix、known limitations、run trace 的统一口径。

输出：

1. artifact contract 文档
2. artifact 类型表
3. support / coverage / limitation 词汇表

验收：

1. 不能再把 Review、Notes、Compare 分别当成三个孤立产品定义。
2. 每个 artifact 都有明确 source / target / return 关系。

## WP2：Citation Audit and Claim Repair

目标：

1. 让 Review Draft 的 claim verification、citation coverage、repair 路径变成可交付审计面。
2. 明确 `partial` 与 `insufficient_evidence` 的用户可见语义。

输出：

1. citation audit 结果结构
2. claim repair 规则
3. unsupported / weakly supported 处理规则

验收：

1. `partial` 不能被误写成成功完成。
2. 每个 unsupported claim 都能回到 evidence 或进入 repair。

## WP3：Evidence Note Productization

目标：

1. 把 Notes 侧的 `linked_evidence`、note title normalization 与 source tags 收束为 artifact 面。
2. 明确阅读笔记与 evidence note 的交付口径。

输出：

1. evidence note contract
2. note title / evidence title 规范
3. note-to-review / note-to-chat return path

验收：

1. Note 页面与 Review/Chat 的 evidence 语义一致。
2. 不能再把 raw claim / raw evidence 直接暴露成不受控标题。

## WP4：Compare Matrix as Artifact

目标：

1. 把 compare/v4 的 `compare_matrix` 定义为正式 artifact。
2. 明确 compare 的 cross-paper insights、return path 与 Chat handoff 语义。

输出：

1. compare matrix contract
2. cross-paper artifact rules
3. compare -> chat handoff rules

验收：

1. compare matrix 必须具备可回跳证据。
2. compare 不得脱离 artifact bundle 单独宣称完成。

## WP5：Known Limitations and Return Path

目标：

1. 把 known limitations 变成 Phase 3 artifact bundle 的必需项。
2. 明确 run trace、return path、repair path 的回跳语义。

输出：

1. known limitations 说明
2. run trace / return path 表
3. repair / resume path 约束

验收：

1. limitation 不是附录，而是 artifact bundle 的组成部分。
2. 用户能从 artifact 回到来源页或 Chat。

## WP6：Phase 3 Closeout

目标：

1. 汇总 artifact contract、citation audit、notes、compare、limitations、return path。
2. 给出 `blocked / artifact-ready / citation-backed-ready` 之一的结论。

输出：

1. `docs/plans/v4_0/reports/2026-05-08_v4_0_phase_3_closeout_report.md`
2. go/no-go table
3. carried-forward issues
4. downstream handoff to Phase 4 / 5 / 6 / 7

验收：

1. closeout 必须引用具体 artifact 路径和 evidence。
2. 不能把 partial 伪装成 full success。
3. 后续前端精修和测试 gate 必须明确接手未解决的体验/验证项。

## 6. 当前执行顺序

1. 完成 WP1：artifact contract freeze。
2. 完成 WP2：citation audit and claim repair。
3. 完成 WP3：evidence note productization。
4. 完成 WP4：compare matrix as artifact。
5. 完成 WP5：known limitations and return path。
6. 完成 WP6：Phase 3 closeout。

不允许跳过 WP1-WP5 直接执行 closeout。closeout 的意义是验证 artifact bundle，不是临时探索页面。

## 7. 最小验证

文档与治理：

```bash
bash scripts/check-doc-governance.sh
bash scripts/check-plan-governance.sh
bash scripts/check-phase-tracking.sh
bash scripts/check-governance.sh
```

执行前的建议 smoke：

```bash
cd apps/api && pytest -q tests/unit/test_review_draft_service.py tests/unit/test_notes_evidence_canonicalization.py tests/unit/test_phase4_hybrid_compare.py --maxfail=1
cd apps/web && npm run test:run -- src/features/kb/components/KnowledgeReviewPanel.test.tsx src/features/chat/chatHandoff.test.ts src/features/chat/hooks/useChatHandoff.test.tsx src/features/workflow/commandCenter.test.ts
```

如果 Phase 3 触发前端或后端代码修复，必须按改动范围追加：

1. 前端改动：`cd apps/web && npm run type-check`
2. 后端改动：`cd apps/api && pytest -q tests/unit/test_review_draft_service.py tests/unit/test_notes_evidence_canonicalization.py tests/unit/test_phase4_hybrid_compare.py --maxfail=1`
3. API 形态变化：同步检查 `docs/specs/architecture/api-contract.md`
4. 资源状态变化：同步检查 `docs/specs/domain/resources.md`

## 8. 完成定义

Phase 4.0-3 完成时，至少满足：

1. Review Draft、Citation Audit、Evidence Note、Compare Matrix、Known Limitations、Run Trace 都已成为稳定 artifact。
2. 每个 claim / evidence / note / compare row 都可回跳。
3. `partial`、`insufficient_evidence`、`unsupported` 保持真实可见。
4. closeout report 给出 `blocked / artifact-ready / citation-backed-ready` 之一。
5. PLAN_STATUS 与 phase-delivery-ledger 已回填。

## 9. 边界

1. 不重做 Review / Notes / Compare 的 IA。
2. 不新增通用文档编辑器。
3. 不做 Beta quickstart / demo dataset / walkthrough script。
4. 不做前端视觉主打磨。
5. 不做 Graph / global synthesis / corrective retrieval 优化。
6. 不新增根级 doc、tmp、legacy、平行实现目录。

## 10. 风险与处理

| risk | handling |
|---|---|
| artifact 仍然分散在各页面 | 冻结统一 artifact bundle 与 return path |
| citation audit 只停留在文本层 | 保留 partial / insufficient_evidence |
| Notes / Review / Compare 口径不一 | 统一 support / coverage / limitation 词汇 |
| 把前端精修混进来 | 由 Phase 4.0-4 / 4.0-5 承接 |

## 11. Open Questions

1. artifact bundle 是否需要新增独立的后端资源真源，还是继续由现有 ReviewDraft / Note / Compare 资源承接。
2. known limitations 是否应进入 KB review panel 的首屏显式区域。
3. return path 是否需要浏览器 walkthrough 作为硬门禁，还是只在 closeout report 中记录。
