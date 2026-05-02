# 计划状态总览

最后更新：2026-04-30

## 使用规则

1. 本文件是 docs/plans 下计划状态唯一真源。
2. 所有 active 计划必须同步更新：status、last_verified_at、evidence_commits。
3. 每次代码合并后，必须在 24 小时内回填对应计划状态。
4. 同主题计划只能有一份 active，其他必须标记 superseded。

## 状态定义

- `not-started`: 尚未开始
- `in-progress`: 正在推进
- `blocked`: 被依赖/资源阻塞
- `done`: 已完成并有证据
- `superseded`: 被新计划替代，不再执行

## v3.0 Strict Close-out 面板

| phase | owner | closeout_status | last_verified_at | truth_doc | notes |
|---|---|---|---|---|---|
| A | ai-platform | implementation-complete / verification-pending | 2026-04-29 | docs/plans/v3_0/active/phase_a/07_v3_0A_execution_plan.md | Academic gate 结果待读取并回填 |
| B | product-engineering | implementation-complete / verification-pending | 2026-04-29 | docs/plans/v3_0/active/phase_b/08_v3_0B_execution_plan.md | Search -> Import -> KB 主链阻断修复中 |
| C | ai-runtime | implementation-complete / verification-pending | 2026-04-29 | docs/plans/v3_0/active/phase_c/09_v3_0C_execution_plan.md | claim/evidence canonical payload 已落地，待整链验证 |
| D | product-engineering | closeout-required | 2026-04-29 | docs/plans/v3_0/active/phase_d/10_v3_0D_execution_plan.md | 真实世界验证仍为 `not_ready`，需新 run |
| E | product-engineering | closeout-required | 2026-04-29 | docs/plans/v3_0/active/phase_e/12_v3_0E_execution_plan.md | async/error/recovery 最小实现待验证 |
| F | web-platform | closeout-required | 2026-04-29 | docs/plans/v3_0/active/phase_f/13_v3_0F_execution_plan.md | 产品化状态透明度待完整 walkthrough |
| FR | web-platform | implementation-complete / verification-pending | 2026-04-29 | docs/plans/v3_0/active/phase_fr/11_v3_0FR_execution_plan.md | 与 E/F 合并验证 |
| G | product-engineering | closeout-required | 2026-04-29 | docs/plans/v3_0/active/phase_g/14_v3_0G_execution_plan.md | Beta 包与 walkthrough 资产待回填 |
| H | ai-runtime | research-required | 2026-04-30 | docs/plans/v3_0/active/phase_h/2026-04-30_v3_0H_RAG_Online_Transition_研究文档.md | 新增边界：RAG 主链全面转向线上，替代本地实验模型默认路径 |
| I | ai-runtime | implementation-complete / verification-passed | 2026-04-30 | docs/plans/v3_0/active/phase_i/16_v3_0I_execution_plan.md | P0+P1 首批 `Truth + Route` 已完成并验证；已冻结 taxonomy/kernel/truthfulness，主链接入 rag/chat/compare/review，后续仅保留 STORM/GraphRAG/强 verifier 等非本轮目标 |
| J | ai-platform | closeout-complete / verification-passed | 2026-04-30 | docs/plans/v3_0/active/phase_j/17_v3_0J_execution_plan.md | comparative gate、academic/workflow normalization、orchestration、verdict JSON/diff JSON/markdown report 已落地；当前证据见 `artifacts/validation-results/phase_j/2026-04-30-closeout/` |

## v3.0 Close-out 真源

- checklist: `docs/plans/v3_0/active/overview/2026-04-29_v3_0_closeout_checklist.md`
- running report: `docs/plans/v3_0/reports/general/2026-04-29_v3_0_strict_closeout_report.md`
- validation artifacts:
  - `artifacts/validation-results/phase_d/real_world_validation.json`
  - `artifacts/validation-results/phase_d/real_world_validation.summary.json`
  - `docs/plans/v3_0/reports/validation/v3_0_real_world_validation.md`
  - `artifacts/validation-results/phase_j/2026-04-30-closeout/comparative_verdict.json`
  - `artifacts/validation-results/phase_j/2026-04-30-closeout/comparative_diff.json`
  - `artifacts/validation-results/phase_j/2026-04-30-closeout/closeout_summary.md`

## 活跃计划面板

| 计划 | owner | status | depends_on | last_verified_at | evidence_commits | phase_unit_id | deliverable_unit_id | pr_link | coverage_scope | risk_level | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|
| PR3_执行方案_物理迁移到_apps | platform | done | - | 2026-04-17 | historical-pr3-commit-to-backfill | PR3 | DU-20260417-001 | historical | apps/web,apps/api | medium | 物理迁移已完成，后续只维护 |
| PR4_迁移后稳定化执行清单 | platform | done | PR3 | 2026-04-17 | historical-pr4-commit-to-backfill | PR4 | DU-20260417-002 | historical | scripts,docs | medium | 稳定化与门禁已落地 |
| PR5_共享契约收口_与_前端工作台可用性方案 | app-foundation | in-progress | PR4 | 2026-04-17 | a07490b,0a123c9 | PR5 | DU-20260417-003 | open | apps/web,apps/api,packages | high | 作为共享契约与工作台唯一 active 主计划 |
| PR6_共享契约收口_与_前端工作台可用性方案 | app-foundation | superseded | PR5 | 2026-04-17 | - | PR6 | DU-20260417-004 | superseded | docs/plans | low | 已被 PR5 计划替代，停止执行 |
| PR6_执行优化方案 | app-foundation | superseded | PR5 | 2026-04-17 | - | PR6-OPT | DU-20260417-005 | superseded | docs/plans | low | 作为历史优化记录，不再单独执行 |
| PR7_PR8_Chat稳定性_AgentNative_RAG升级实施方案 | ai-runtime | in-progress | PR5,PR10 | 2026-04-17 | wip-pr7-pr8,wip-review-2026-04-17 | PR7-PR8 | DU-20260417-006 | open | apps/web,apps/api | high | 本轮 PR7 P7-A/B/C 与 PR8 P8-A 已完成并通过严格复核 |
| PR10_KB_Chat_Search_workspace_分层与稳定化方案 | web-platform | in-progress | PR5 | 2026-04-17 | 9a7332e,9208b73,cecfccf,wip-review-2026-04-17 | PR10 | DU-20260417-007 | open | apps/web | high | 第一轮收尾清单已补录严格复核结果 |
| PR19_上传链路收口_与_完整上传体验重做计划_v3 | app-foundation | in-progress | PR5 | 2026-04-17 | wip-pr19-upload-workspace | PR19 | DU-20260417-008 | open | apps/web,apps/api | high | 上传链路收口与工作台体验重做推进中 |
| PR18_Celery_ImportPipeline_Stability_Refactor_Plan | app-foundation | superseded | PR19_上传链路收口_与_完整上传体验重做计划_v3 | 2026-04-18 | - | PR18 | DU-20260418-001 | superseded | docs/plans | low | 已并入 PR19 上传链路主计划，不再单独执行 |
| PR20_UI截图细节还原方案 | web-platform | superseded | PR10_KB_Chat_Search_workspace_分层与稳定化方案 | 2026-04-18 | - | PR20-UI | DU-20260418-002 | superseded | docs/plans | low | 已被统一工作台分层与稳定化计划覆盖 |
| PR20_前端杂志风美化与性能优化_深度落实方案 | web-platform | superseded | PR10_KB_Chat_Search_workspace_分层与稳定化方案 | 2026-04-18 | - | PR20-VISUAL | DU-20260418-003 | superseded | docs/plans | low | 已合并进入现行前端治理与工作台主线 |
| PR21_PR23_契约收口与持久化闭环三阶段执行计划 | app-foundation | in-progress | - | 2026-04-18 | wip-pr21-pr23-contract-close | PR21-PR23 | DU-20260418-007 | open | apps/api,apps/web,docs | high | 三阶段执行中，PR21已完成，PR22/PR23推进中 |
| knowledge-workflow-closure-phase-plan | product-engineering | in-progress | PR10,PR19,PR21-PR23,PR7-PR8 | 2026-04-20 | planning-doc-20260420 | KWC | DU-20260420-001 | pending | apps/web,apps/api,docs,tests | high | 作为 Upload->Import->KB->Chat->History 的统一执行总计划，不替代现有 active 子计划，而用于统筹 wave 顺序、验收与交付 |
| 06_v3_0_overview_plan | product-engineering | in-progress | knowledge-workflow-closure-phase-plan,PlanB,PR10 | 2026-04-28 | planning-doc-20260428 | V3.0 | DU-20260428-001 | pending | apps/web,apps/api,docs | high | 作为当前 v3.0 总入口真源，定义双主线、Phase 思路与优先级；后续细化研究与实施文档需围绕它展开 |
| v3_0A_academic_benchmark_3_0_research | ai-platform | in-progress | 06_v3_0_overview_plan,PR12,PlanB | 2026-04-28 | planning-doc-20260428-v3a | V3.0-A | DU-20260428-002 | pending | apps/api,docs,scripts | high | 作为 Academic Benchmark 3.0 研究真源，明确 corpus 扩容、gold evidence、blind set、artifact/gate 升级方向；后续实现计划另立文 |
| 07_v3_0A_execution_plan | ai-platform | in-progress | v3_0A_academic_benchmark_3_0_research | 2026-04-28 | planning-doc-20260428-v3a-exec | V3.0-A-EXEC | DU-20260428-003 | pending | apps/api,docs,scripts | high | 作为 Phase A 主执行计划真源，连同 schema/annotation/artifact-gate/review 文档形成实施闭环；代码与数据落地待后续 PR 补齐 |
| v3_0B_external_search_import_research | product-engineering | in-progress | 06_v3_0_overview_plan,07_v3_0A_execution_plan | 2026-04-28 | planning-doc-20260428-v3b | V3.0-B | DU-20260428-004 | pending | apps/web,apps/api,docs | high | 作为 External Search + Import to KB 研究真源，按“Phase A 结构性产物已完成”前提定义 Search -> Import -> KB 主链、provider、状态语义与导入边界 |
| 08_v3_0B_execution_plan | product-engineering | in-progress | v3_0B_external_search_import_research | 2026-04-28 | planning-doc-20260428-v3b-exec | V3.0-B-EXEC | DU-20260428-005 | pending | apps/web,apps/api,docs | high | 作为 Phase B 主执行计划真源，连同 kickoff freeze 文档定义外部搜索、ImportJob-first、metadata-only/fulltext-ready 与主链接入顺序 |
| v3_0C_span_citation_claim_verification_research | ai-runtime | in-progress | 08_v3_0B_execution_plan,07_v3_0A_execution_plan | 2026-04-28 | planning-doc-20260428-v3c | V3.0-C | DU-20260428-006 | pending | apps/api,apps/web,docs | high | 作为 Span-level Citation + Claim Verification 研究真源，按“Phase A/B 结构性产物已完成”前提定义 claim 单元、evidence anchor、verification 语义与 Chat/Review 统一消费方向 |
| 09_v3_0C_execution_plan | ai-runtime | in-progress | v3_0C_span_citation_claim_verification_research | 2026-04-28 | planning-doc-20260428-v3c-exec | V3.0-C-EXEC | DU-20260428-007 | pending | apps/api,apps/web,docs | high | 作为 Phase C 主执行计划真源，定义 claim unit、evidence anchor、unsupported surfacing、claim repair 与 Chat/Review/Read 主链接入顺序 |
| v3_0D_real_world_validation_research | product-engineering | in-progress | 09_v3_0C_execution_plan,08_v3_0B_execution_plan,07_v3_0A_execution_plan | 2026-04-29 | planning-doc-20260429-v3d | V3.0-D | DU-20260429-001 | pending | apps/web,apps/api,docs | high | 作为 Real-world Validation 研究真源，按“Phase A/B/C 结构性产物已完成”前提定义真实样本框架、完整工作流验证主链、失败模式与 close-out 报告方向 |
| 10_v3_0D_execution_plan | product-engineering | in-progress | v3_0D_real_world_validation_research | 2026-04-29 | planning-doc-20260429-v3d-exec | V3.0-D-EXEC | DU-20260429-002 | pending | apps/web,apps/api,docs | high | 作为 Phase D 主执行计划真源，定义真实样本 intake、整链路 workflow 验证、失败分桶、证据质量抽查与 close-out 报告顺序 |
| v3_0H_rag_online_transition_research | ai-runtime | in-progress | 06_v3_0_overview_plan,10_v3_0D_execution_plan | 2026-04-30 | planning-doc-20260430-v3h | V3.0-H | DU-20260430-001 | pending | apps/api,docs | high | 作为 RAG 全线上化研究真源，定义本地依赖清单、线上 provider 收口方向、fallback 边界与真实验证要求 |
| 15_v3_0H_execution_plan | ai-runtime | in-progress | v3_0H_rag_online_transition_research | 2026-04-30 | planning-doc-20260430-v3h-exec | V3.0-H-EXEC | DU-20260430-004 | pending | apps/api,docs | high | 作为 Phase H 主执行计划真源，定义 provider inventory、业务入口收口、fallback honesty、runtime validation 与 benchmark/release 消费顺序 |
| v3_0H_provider_inventory | ai-runtime | in-progress | 15_v3_0H_execution_plan | 2026-04-30 | planning-doc-20260430-v3h-provider | V3.0-H-PROVIDER | DU-20260430-006 | pending | apps/api,docs | high | 冻结 retrieval/generation 双平面 provider inventory、默认分层策略与待 benchmark 裁决项 |
| v3_0H_contract_freeze | ai-runtime | in-progress | v3_0H_provider_inventory | 2026-04-30 | planning-doc-20260430-v3h-contract | V3.0-H-CONTRACT | DU-20260430-008 | pending | apps/api,docs | high | 冻结 runtime mode、per-plane provider identity、fallback honesty 与 benchmark/release 消费字段 |
| v3_0I_academic_custom_rag_framework_research | ai-runtime | done | v3_0H_rag_online_transition_research,10_v3_0D_execution_plan | 2026-04-30 | planning-doc-20260430-v3i | V3.0-I | DU-20260430-002 | pending | apps/api,apps/web,docs | high | 研究结论已冻结，作为 Phase I Truth + Route 首批实现的理论真源；后续 comparative benchmark 交由 Phase J 消费 |
| 16_v3_0I_execution_plan | ai-runtime | done | v3_0I_academic_custom_rag_framework_research | 2026-04-30 | planning-doc-20260430-v3i-exec | V3.0-I-EXEC | DU-20260430-005 | pending | apps/api,apps/web,docs | high | 执行顺序、风险、验收与 Truth + Route 首批实现已落地；global synthesis 重写与强 verifier 保留到后续波次 |
| v3_0I_framework_decision_matrix | ai-runtime | done | 16_v3_0I_execution_plan | 2026-04-30 | planning-doc-20260430-v3i-matrix | V3.0-I-MATRIX | DU-20260430-007 | pending | apps/api,apps/web,docs | high | adopt/extend/experiment/reject 矩阵已冻结，并已用于确定首批只落 Adaptive-RAG pattern + truthfulness substrate |
| v3_0I_academic_kernel_blueprint | ai-runtime | done | v3_0I_framework_decision_matrix | 2026-04-30 | planning-doc-20260430-v3i-blueprint | V3.0-I-BLUEPRINT | DU-20260430-009 | pending | apps/api,apps/web,docs | high | academic kernel、双核结构、truthfulness layer 与 route/runtime contract 已冻结并完成首批代码映射 |
| v3_0J_rag_benchmark_research | ai-platform | in-progress | v3_0H_rag_online_transition_research,v3_0I_academic_custom_rag_framework_research,07_v3_0A_execution_plan | 2026-04-30 | planning-doc-20260430-v3j | V3.0-J | DU-20260430-003 | pending | apps/api,docs,scripts | high | 作为 RAG benchmark 与对比门禁研究真源，定义线上基线、候选框架、真实链路结果的统一对比体系 |
| 17_v3_0J_execution_plan | ai-platform | done | v3_0J_rag_benchmark_research | 2026-04-30 | working-tree-phase-j-closeout | V3.0-J-EXEC | DU-20260430-011 | pending | apps/api,docs,scripts | high | Phase J close-out 已落地：comparative contract、academic/workflow adapter、orchestrator、verdict JSON/diff JSON/markdown report 已生成并通过聚焦测试 |
| PR11_Harness_Observability_文件级实施方案 | ai-platform | done | PR10 | 2026-04-17 | 89a9d9a | PR11 | DU-20260417-009 | historical | scripts,docs | medium | 已完成，进入维护态 |
| PR12_Benchmark_基线评测_文件级实施方案 | ai-platform | done | PR11 | 2026-04-17 | 84fd597 | PR12 | DU-20260417-010 | historical | scripts/docs/reports | medium | 已完成，进入阈值维护态 |
| PlanA_前端架构与交互重构 | web-platform | done | PR10,PR7_PR8 | 2026-04-18 | 9f58bb9,9a2fc2c,0b01076,43fe5c9,e02c880 | PlanA | DU-20260418-004 | PR22 | apps/web,docs | high | W0-W6 全部完成，进入维护态 |
| PlanB_后端稳定性与RAG能力重构 | ai-runtime | done | PlanA,PR12 | 2026-04-18 | 9e0ebec,389b3b7,e5afcb0 | PlanB | DU-20260418-005 | PR23 | apps/api,docs | high | W0-W8 已完成并通过审查，进入维护态 |
| PlanC_工程治理与交付体系重构 | ai-platform | done | PlanA,PlanB | 2026-04-18 | historical-planc-governance-20260418 | PlanC | DU-20260418-006 | this-branch | scripts,.github,docs | high | 治理脚本、门禁工作流、E2E阻断、KPI审计已落地 |

## 回填模板

每次执行完成后按如下格式附加记录：

```markdown
### 2026-04-17 PR7 P7-A 回填
- status: done
- owner: ai-runtime
- changed_files:
  - apps/api/app/core/docling_service.py
  - apps/api/tests/unit/test_docling_service.py
- verification:
  - cd apps/api && pytest -q tests/unit/test_docling_service.py
  - bash scripts/check-governance.sh
- evidence_commits:
  - <commit-hash>
- reviewer:
  - gsd-code-reviewer (summary link or note)
```
