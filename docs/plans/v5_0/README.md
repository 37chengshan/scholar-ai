# v5.0 Plans

ScholarAI v5.0 是 v4.x 之后的全面重启迭代版本。它把 v4.0 残留 phase、v4.5 release-readiness bridge 与新一代学术阅读体验全部整合进同一个版本计划,目标是在阶段完成后形成 ScholarAI 的首个**诚实可宣称 release-pass** 的版本。

## Directory Layout

- `active/overview/`: v5.0 版本定位、研究决策摘要与顶层 overview 计划
- `active/phase_0/`: v5.0 启动期 — Foundation & v4.x 维护态切换的真源材料
- `active/phase_1/` … `active/phase_7/`: 后续 phase 的执行计划与冻结材料(逐 phase 落地)
- `search/`: v5.0 外部对标、技术路线取舍、缺口扫描与补充研究材料
- `reports/`: v5.0 walkthrough、benchmark、audit、closeout 与 release verdict 报告
- `complete/`: 已完成并归档的 v5.0 phase 文档

## Version Position

1. v5.0 **不替代** v4.x 的历史交付证据;v4.x 在 v5.0-0 完成迁移后转入 maintenance,以 superseded 状态保留在 `PLAN_STATUS.md`。
2. v5.0 的发布门禁以 `active/phase_7/` 下的 consolidated release gate 为准。
3. v5.0 任何 phase 文档在没有对应 closeout report + walkthrough 证据前,**不允许写成 release-candidate 或 release-pass**。
4. v5.0 在 `feat/v5-0-foundation` 等正式分支落地前,所有材料只作为版本骨架预热使用。

## Phase Status

| Phase | 名称 | 状态 | 完成日期 | closeout report |
|---|---|---|---|---|
| 5.0-0 | Foundation | done | 2026-05-31 | `reports/2026-05-31_v5_0_phase_foundation_closeout.md` |
| 5.0-1 | Design System v2 | done | 2026-05-31 | `reports/2026-05-31_v5_0_phase_design_system_v2_closeout.md` |
| 5.0-2 | WorkspaceShell v2 + Performance | done | 2026-05-31 | `reports/2026-05-31_v5_0_phase_2_workspace_shell_v2_closeout.md` |
| 5.0-3 | 主链精修: Search + Import + KB | done | 2026-05-31 | `reports/2026-05-31_v5_0_phase_upload_visualization_closeout.md` |
| 5.0-4 | 主链精修: Read + Pretext | done | 2026-05-31 | `reports/2026-05-31_v5_0_phase_read_pretext_closeout.md` |
| 5.0-5 | 主链精修: Chat + Compare | not-started | - | - |
| 5.0-6 | 主链精修: Review + Dashboard | not-started | - | - |
| 5.0-7 | 后端 Pipeline 稳定性 + Runtime Contract | not-started | - | - |
| 5.0-8 | RAG SOTA: RAPTOR-lite + Graph + Verifier | not-started | - | - |
| 5.0-9 | Release Gate (consolidated gate 最终执行) | not-started | - | - |

## First-Wave Entry Points (2026-05-31)

1. `active/overview/2026-05-31_v5_0_research_decision_note.md`
2. `active/overview/27_v5_0_overview_plan.md`
3. `active/phase_0/README.md` (phase 0 已 closeout)
4. `search/README.md`
5. `reports/README.md`
6. `complete/README.md`

## Rules

1. v5.0 内不开第二套并行实现路径;前端真源仍在 `apps/web`,后端真源仍在 `apps/api`。
2. v5.0 引入的新依赖必须先经 search-first 评估并记录在 `search/`。
3. v5.0 phase 执行必须按 GSD workflow 走 (`/gsd:plan-phase` → `/gsd:execute-phase` → `/gsd:verify-phase` → `/gsd:code-review`)。
4. v5.0 所有状态变化必须 24 小时内回填 `docs/plans/PLAN_STATUS.md` 与 `docs/specs/governance/phase-delivery-ledger.md`。
