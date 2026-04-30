# Phase Delivery Ledger

## Purpose

定义 Phase 交付单元台账，确保规划项、实现项、验证项和证据提交一一对应，可追踪、可审计、可回溯。

## Scope

适用于 scholar-ai 全仓库的计划执行与 PR 交付。

## Source of Truth

- 计划状态总览：docs/plans/PLAN_STATUS.md
- PR 流程：docs/specs/development/pr-process.md
- 测试策略：docs/specs/development/testing-strategy.md
- 契约文档：docs/specs/architecture/api-contract.md
- 资源模型：docs/specs/domain/resources.md

## Rules

1. 每个交付单元必须有唯一编号：DU-YYYYMMDD-XXX。
2. 每个交付单元必须关联且仅关联一个 Phase。
3. 每个交付单元必须关联至少一个 PR 或 commit 证据。
4. 交付单元未完成时，必须列出未覆盖项与风险等级。
5. 交付单元完成后 24 小时内必须回填验证结果。

## Ledger Template

| deliverable_unit_id | phase_id | owner | pr_or_commit | code_scope | test_scope | doc_scope | status | risk_level | uncovered_items | last_verified_at |
|---|---|---|---|---|---|---|---|---|---|---|
| DU-20260418-001 | PlanB-W0-W2 | ai-runtime | 9e0ebec | apps/api/app/config.py,apps/api/app/main.py | tests/unit/test_runtime_profile.py | docs/plans/v2_0/reports/2026-04-18_落实计划B_后端稳定性与RAG能力重构.md | done | medium | - | 2026-04-18 |
| DU-20260418-002 | PlanB-W4-W6 | ai-runtime | 389b3b7 | apps/api/app/api/rag.py,apps/api/app/core/agentic_retrieval.py | tests/unit/test_rag_confidence.py,tests/unit/test_agentic_citations.py | docs/specs/architecture/api-contract.md | done | high | - | 2026-04-18 |
| DU-20260418-003 | PlanC-W1-W2 | ai-platform | in-progress | scripts/check-phase-tracking.sh,scripts/check-contract-gate.sh | tests/e2e/placeholder | docs/specs/governance/phase-delivery-ledger.md | in-progress | medium | governance-kpi自动回填待上线 | 2026-04-18 |
| DU-20260420-001 | KWC-W0 | product-engineering | planning-doc-20260420 | docs/plans/archive/complete/knowledge-workflow-closure-phase-plan.md,docs/plans/PLAN_STATUS.md | - | docs/plans/v3_0/reports/general/2026-04-20_下一大迭代研究报告.md | in-progress | high | 子计划代码落地、验证证据与 PR 回填待补齐 | 2026-04-20 |
| DU-20260428-001 | V3.0-W0 | product-engineering | planning-doc-20260428 | docs/plans/v3_0/active/overview/06_v3_0_overview_plan.md,docs/plans/PLAN_STATUS.md | bash scripts/check-doc-governance.sh,bash scripts/check-governance.sh | docs/specs/governance/phase-delivery-ledger.md | in-progress | high | 各 phase 详细研究、接口方案、执行拆解与证据回填待后续补齐 | 2026-04-28 |
| DU-20260428-002 | V3.0-A-W0 | ai-platform | planning-doc-20260428-v3a | docs/plans/v3_0/active/phase_a/2026-04-28_v3_0A_Academic_Benchmark_3_0_研究文档.md,docs/plans/PLAN_STATUS.md | bash scripts/check-doc-governance.sh,bash scripts/check-governance.sh | docs/specs/governance/phase-delivery-ledger.md | in-progress | high | schema freeze、benchmark namespace、blind set 实施方案与脚本改造证据待后续补齐 | 2026-04-28 |
| DU-20260428-003 | V3.0-A-W1 | ai-platform | planning-doc-20260428-v3a-exec | docs/plans/v3_0/active/phase_a/07_v3_0A_execution_plan.md,docs/specs/contracts/v3_0_academic_benchmark_schema.md,docs/plans/v3_0/active/phase_a/2026-04-28_v3_0A_annotation_guide.md,docs/plans/v3_0/active/phase_a/2026-04-28_v3_0A_artifact_gate_design.md,docs/plans/v3_0/active/phase_a/2026-04-28_v3_0A_execution_plan_review.md,docs/plans/v3_0/active/phase_a/2026-04-28_v3_0A_kickoff_freeze.md | bash scripts/check-doc-governance.sh,bash scripts/check-governance.sh | docs/specs/governance/phase-delivery-ledger.md | in-progress | high | kickoff freeze 已收口未决策项；后续实现 PR、数据构建证据与 gate 跑数待补齐 | 2026-04-28 |
| DU-20260428-004 | V3.0-B-W0 | product-engineering | planning-doc-20260428-v3b | docs/plans/v3_0/active/phase_b/2026-04-28_v3_0B_External_Search_Import_研究文档.md,docs/plans/PLAN_STATUS.md | bash scripts/check-doc-governance.sh,bash scripts/check-governance.sh | docs/specs/governance/phase-delivery-ledger.md | in-progress | high | provider 抽象、ExternalPaper canonical model、metadata-only/fulltext-ready 资源表达与实际实现证据待后续补齐 | 2026-04-28 |
| DU-20260428-005 | V3.0-B-W1 | product-engineering | planning-doc-20260428-v3b-exec | docs/plans/v3_0/active/phase_b/08_v3_0B_execution_plan.md,docs/plans/v3_0/active/phase_b/2026-04-28_v3_0B_kickoff_freeze.md | bash scripts/check-doc-governance.sh,bash scripts/check-governance.sh | docs/specs/governance/phase-delivery-ledger.md | in-progress | high | SearchWorkspace 主入口、ImportJob-first 主链、dedupe 用户可见反馈与 async progress 实装证据待后续补齐 | 2026-04-28 |
| DU-20260428-006 | V3.0-C-W0 | ai-runtime | planning-doc-20260428-v3c | docs/plans/v3_0/active/phase_c/2026-04-28_v3_0C_Span_Citation_Claim_Verification_研究文档.md,docs/plans/PLAN_STATUS.md | bash scripts/check-doc-governance.sh,bash scripts/check-governance.sh | docs/specs/governance/phase-delivery-ledger.md | in-progress | high | span locator canonical model、claim repair contract、Review/Chat 统一 verifier 方案与实际实现证据待后续补齐 | 2026-04-28 |
| DU-20260428-007 | V3.0-C-W1 | ai-runtime | planning-doc-20260428-v3c-exec | docs/plans/v3_0/active/phase_c/09_v3_0C_execution_plan.md,docs/plans/PLAN_STATUS.md | bash scripts/check-doc-governance.sh,bash scripts/check-governance.sh | docs/specs/governance/phase-delivery-ledger.md | in-progress | high | claim locator contract、kickoff freeze、repair loop design 与 UI/后端统一实施证据待后续补齐 | 2026-04-28 |
| DU-20260429-001 | V3.0-D-W0 | product-engineering | planning-doc-20260429-v3d | docs/plans/v3_0/active/phase_d/2026-04-29_v3_0D_Real_World_Validation_研究文档.md,docs/plans/PLAN_STATUS.md | bash scripts/check-doc-governance.sh,bash scripts/check-governance.sh | docs/specs/governance/phase-delivery-ledger.md | in-progress | high | 真实样本台账、workflow run 记录规范、失败分桶标准与 close-out 报告模板待后续补齐 | 2026-04-29 |
| DU-20260429-002 | V3.0-D-W1 | product-engineering | planning-doc-20260429-v3d-exec | docs/plans/v3_0/active/phase_d/10_v3_0D_execution_plan.md,docs/plans/PLAN_STATUS.md | bash scripts/check-doc-governance.sh,bash scripts/check-governance.sh | docs/specs/governance/phase-delivery-ledger.md | in-progress | high | sample registry、failure bucket spec、workflow run 记录格式与 close-out 报告执行证据待后续补齐 | 2026-04-29 |
| DU-20260429-003 | V3.0-CLOSEOUT-W0 | product-engineering | working-tree-closeout-20260429 | docs/plans/v3_0/active/overview/2026-04-29_v3_0_closeout_checklist.md,docs/plans/v3_0/reports/general/2026-04-29_v3_0_strict_closeout_report.md,docs/plans/PLAN_STATUS.md | bash scripts/check-doc-governance.sh,bash scripts/check-phase-tracking.sh | docs/specs/governance/phase-delivery-ledger.md | in-progress | high | Wave 0 测试结果、门禁结果、Beta 放行结论待回填 | 2026-04-29 |
| DU-20260429-004 | V3.0-E-W0 | product-engineering | working-tree-closeout-20260429 | docs/plans/v3_0/active/phase_e/12_v3_0E_execution_plan.md | cd apps/web && npm run type-check,cd apps/api && python3 -m pytest -q tests/unit/test_services.py --maxfail=1 | docs/specs/governance/phase-delivery-ledger.md | in-progress | high | async/error/recovery 统一验证与运行证据待补齐 | 2026-04-29 |
| DU-20260429-005 | V3.0-F-W0 | web-platform | working-tree-closeout-20260429 | docs/plans/v3_0/active/phase_f/13_v3_0F_execution_plan.md,apps/web/src/features/search/components/SearchKnowledgeBaseImportModal.tsx,apps/web/src/features/search/hooks/useSearchImportFlow.ts | cd apps/web && npm run test -- useSearchImportFlow SearchResultsPanel | docs/specs/governance/phase-delivery-ledger.md | in-progress | high | 仍需整链验证状态透明度与下一步动作 | 2026-04-29 |
| DU-20260429-006 | V3.0-G-W0 | product-engineering | working-tree-closeout-20260429 | docs/plans/v3_0/active/phase_g/14_v3_0G_execution_plan.md | bash scripts/check-governance.sh | docs/specs/governance/phase-delivery-ledger.md | in-progress | high | demo dataset/account/quickstart/walkthrough 尚未回填 | 2026-04-29 |
| DU-20260430-001 | V3.0-H-W0 | ai-runtime | planning-doc-20260430-v3h | docs/plans/v3_0/active/phase_h/2026-04-30_v3_0H_RAG_Online_Transition_研究文档.md,docs/plans/v3_0/active/overview/06_v3_0_overview_plan.md,docs/plans/PLAN_STATUS.md | bash scripts/check-doc-governance.sh,bash scripts/check-phase-tracking.sh | docs/specs/governance/phase-delivery-ledger.md | in-progress | high | 线上 provider inventory、主链切换顺序、fallback 策略、真实运行验证与执行计划待后续补齐 | 2026-04-30 |
| DU-20260430-002 | V3.0-I-W0 | ai-runtime | planning-doc-20260430-v3i | docs/plans/v3_0/active/phase_i/2026-04-30_v3_0I_Academic_Custom_RAG_Framework_研究文档.md,docs/plans/v3_0/active/overview/06_v3_0_overview_plan.md,docs/plans/PLAN_STATUS.md | bash scripts/check-doc-governance.sh,bash scripts/check-phase-tracking.sh | docs/specs/governance/phase-delivery-ledger.md | done | high | 研究结论已冻结；后续仅保留 benchmark gate 与更强框架候选的比较，不影响本轮 Phase I 首批完成定义 | 2026-04-30 |
| DU-20260430-003 | V3.0-J-W0 | ai-platform | planning-doc-20260430-v3j | docs/plans/v3_0/active/phase_j/2026-04-30_v3_0J_RAG_Benchmark_研究文档.md,docs/plans/v3_0/active/overview/06_v3_0_overview_plan.md,docs/plans/PLAN_STATUS.md | bash scripts/check-doc-governance.sh,bash scripts/check-phase-tracking.sh | docs/specs/governance/phase-delivery-ledger.md | in-progress | high | comparative benchmark schema、baseline/candidate/diff protocol、release gate 接入与阈值方案待后续补齐 | 2026-04-30 |
| DU-20260430-004 | V3.0-H-W1 | ai-runtime | planning-doc-20260430-v3h-exec | docs/plans/v3_0/active/phase_h/15_v3_0H_execution_plan.md,docs/plans/PLAN_STATUS.md | bash scripts/check-doc-governance.sh,bash scripts/check-phase-tracking.sh | docs/specs/governance/phase-delivery-ledger.md | in-progress | high | provider inventory 文档、contract freeze、runtime validation matrix、代码与验证证据待后续补齐 | 2026-04-30 |
| DU-20260430-005 | V3.0-I-W1 | ai-runtime | planning-doc-20260430-v3i-exec | docs/plans/v3_0/active/phase_i/16_v3_0I_execution_plan.md,docs/plans/PLAN_STATUS.md | bash scripts/check-doc-governance.sh,bash scripts/check-phase-tracking.sh | docs/specs/governance/phase-delivery-ledger.md | done | high | 执行计划、truthfulness spec、route/runtime 接线与验收路径已冻结；完整 benchmark 执行延后到 Phase J，不属于本轮未完成项 | 2026-04-30 |
| DU-20260430-006 | V3.0-H-W2 | ai-runtime | planning-doc-20260430-v3h-provider | docs/plans/v3_0/active/phase_h/v3_0H_provider_inventory.md,docs/plans/PLAN_STATUS.md | bash scripts/check-doc-governance.sh,bash scripts/check-phase-tracking.sh | docs/specs/governance/phase-delivery-ledger.md | in-progress | high | retrieval/generation plane contract freeze、真实 provider 回填与 runtime validation matrix 待后续补齐 | 2026-04-30 |
| DU-20260430-007 | V3.0-I-W2 | ai-runtime | planning-doc-20260430-v3i-matrix | docs/plans/v3_0/active/phase_i/v3_0I_framework_decision_matrix.md,docs/plans/PLAN_STATUS.md | bash scripts/check-doc-governance.sh,bash scripts/check-phase-tracking.sh | docs/specs/governance/phase-delivery-ledger.md | done | high | mainline adoption 结论已冻结为首批只落 Adaptive-RAG pattern + truthfulness substrate；更强候选保留到 comparative benchmark | 2026-04-30 |
| DU-20260430-008 | V3.0-H-W3 | ai-runtime | planning-doc-20260430-v3h-contract | docs/plans/v3_0/active/phase_h/v3_0H_contract_freeze.md,docs/plans/PLAN_STATUS.md | bash scripts/check-doc-governance.sh,bash scripts/check-phase-tracking.sh | docs/specs/governance/phase-delivery-ledger.md | in-progress | high | runtime validation matrix、字段级回填与 release/benchmark 消费实现待后续补齐 | 2026-04-30 |
| DU-20260430-009 | V3.0-I-W3 | ai-runtime | planning-doc-20260430-v3i-blueprint | docs/plans/v3_0/active/phase_i/v3_0I_academic_kernel_blueprint.md,docs/plans/PLAN_STATUS.md | bash scripts/check-doc-governance.sh,bash scripts/check-phase-tracking.sh | docs/specs/governance/phase-delivery-ledger.md | done | high | kernel-to-code map、truthfulness layer 与 route/runtime contract 已完成首批映射；STORM-lite 与 Graph-enhanced global synthesis 仍属后续能力扩展 | 2026-04-30 |
| DU-20260430-010 | V3.0-I-W4 | ai-runtime | working-tree-phase-i-truth-route | apps/api/app/services/phase_i_routing_service.py,apps/api/app/services/truthfulness_service.py,apps/api/app/rag_v3/main_path_service.py,apps/api/app/services/compare_service.py,apps/api/app/services/review_draft_service.py,apps/api/app/api/chat.py,docs/plans/v3_0/active/phase_i/v3_0I_claim_truthfulness_spec.md,docs/plans/v3_0/active/phase_i/v3_0I_execution_plan_review.md | cd apps/api && python3 -m pytest -q tests/unit/test_phase_i_routing_service.py tests/unit/test_truthfulness_service.py tests/unit/test_claim_verifier.py tests/unit/test_answer_contract.py tests/unit/test_rag_trace_contract.py tests/unit/test_phase4_hybrid_compare.py tests/unit/test_review_draft_service.py tests/unit/test_chat_fast_path.py --maxfail=1,bash scripts/check-doc-governance.sh,bash scripts/check-structure-boundaries.sh | docs/specs/governance/phase-delivery-ledger.md,docs/specs/architecture/api-contract.md,docs/specs/domain/resources.md | done | high | 首批 Truth + Route 已实现并验证；global synthesis 主链替换、GraphRAG、STORM full stack 与强 verifier 明确保留到后续 benchmark gate | 2026-04-30 |
| DU-20260430-011 | V3.0-J-W1 | ai-platform | working-tree-phase-j-closeout | scripts/evals/run_phase_j_comparative_gate.py,scripts/evals/run_phase_j_closeout.py,apps/api/app/services/real_world_validation_service.py,apps/api/tests/unit/test_phase_j_comparative_gate.py,apps/api/tests/unit/test_real_world_validation_service.py,docs/plans/PLAN_STATUS.md | cd apps/api && python3 -m pytest -q tests/unit/test_phase_j_comparative_gate.py tests/unit/test_real_world_validation_service.py --maxfail=1,python3 scripts/evals/run_phase_j_closeout.py --academic-baseline-run run_v3_academic_baseline_001 --academic-candidate-run run_v3_academic_candidate_001 --workflow-baseline artifacts/validation-results/phase_d/real_world_validation.json --workflow-candidate artifacts/validation-results/phase_d/real_world_validation.json --output-dir artifacts/validation-results/phase_j/2026-04-30-closeout | docs/specs/governance/phase-delivery-ledger.md,docs/plans/v3_0/active/phase_j/17_v3_0J_execution_plan.md,artifacts/validation-results/phase_j/2026-04-30-closeout/closeout_summary.md | done | high | 当前 academic/workflow 均通过 adapter 进入 Phase J comparative contract；workflow candidate 仍复用同一 Phase D closeout payload，后续若要裁决新真实候选需补独立 candidate workflow run | 2026-04-30 |

## Required Updates

- 新增 Phase 执行：增加至少一条台账记录。
- 调整交付单元字段：同步更新 scripts/check-phase-tracking.sh 的字段校验规则。
- 变更状态定义：同步更新 docs/plans/PLAN_STATUS.md 的状态约束。

## Verification

- bash scripts/check-phase-tracking.sh
- bash scripts/check-plan-governance.sh
- bash scripts/check-governance.sh

## Open Questions

- 是否将交付单元自动同步到 GitHub Projects。
- 是否引入自动回填机器人减少人工维护成本。
