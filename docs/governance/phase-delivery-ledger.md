# Phase Delivery Ledger

## Purpose

定义 Phase 交付单元台账，确保规划项、实现项、验证项和证据提交一一对应，可追踪、可审计、可回溯。

## Scope

适用于 scholar-ai 全仓库的计划执行与 PR 交付。

## Source of Truth

- 计划状态总览：docs/plans/PLAN_STATUS.md
- PR 流程：docs/development/pr-process.md
- 测试策略：docs/development/testing-strategy.md
- 契约文档：docs/architecture/api-contract.md
- 资源模型：docs/domain/resources.md

## Rules

1. 每个交付单元必须有唯一编号：DU-YYYYMMDD-XXX。
2. 每个交付单元必须关联且仅关联一个 Phase。
3. 每个交付单元必须关联至少一个 PR 或 commit 证据。
4. 交付单元未完成时，必须列出未覆盖项与风险等级。
5. 交付单元完成后 24 小时内必须回填验证结果。

## Ledger Template

| deliverable_unit_id | phase_id | owner | pr_or_commit | code_scope | test_scope | doc_scope | status | risk_level | uncovered_items | last_verified_at |
|---|---|---|---|---|---|---|---|---|---|---|
| DU-20260418-001 | PlanB-W0-W2 | ai-runtime | 9e0ebec | apps/api/app/config.py,apps/api/app/main.py | tests/unit/test_runtime_profile.py | docs/reports/2026-04-18_落实计划B_后端稳定性与RAG能力重构.md | done | medium | - | 2026-04-18 |
| DU-20260418-002 | PlanB-W4-W6 | ai-runtime | 389b3b7 | apps/api/app/api/rag.py,apps/api/app/core/agentic_retrieval.py | tests/unit/test_rag_confidence.py,tests/unit/test_agentic_citations.py | docs/architecture/api-contract.md | done | high | - | 2026-04-18 |
| DU-20260418-003 | PlanC-W1-W2 | ai-platform | in-progress | scripts/check-phase-tracking.sh,scripts/check-contract-gate.sh | tests/e2e/placeholder | docs/governance/phase-delivery-ledger.md | in-progress | medium | governance-kpi自动回填待上线 | 2026-04-18 |
| DU-20260420-001 | KWC-W0 | product-engineering | planning-doc-20260420 | docs/plans/activ/knowledge-workflow-closure-phase-plan.md,docs/plans/PLAN_STATUS.md | - | docs/reports/2026-04-20_下一大迭代研究报告.md | in-progress | high | 子计划代码落地、验证证据与 PR 回填待补齐 | 2026-04-20 |

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
