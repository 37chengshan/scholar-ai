# Branch Lifecycle Policy

## Purpose

建立统一分支生命周期状态机，消除长期漂移分支和孤岛改动，确保分支治理可度量、可执行。

## Scope

适用于 scholar-ai 仓库所有 feature/fix/chore/docs 分支。

## Source of Truth

- PR 流程：docs/specs/development/pr-process.md
- 计划状态：docs/plans/PLAN_STATUS.md
- 分支治理脚本：scripts/check-branch-lifecycle.sh

## Rules

状态机定义：

1. created
2. active
3. review-ready
4. merged
5. superseded
6. archived

约束：

1. 分支创建后必须在 2 天内进入 active 或 superseded。
2. active 状态分支超过 14 天无更新，视为 stale，CI 失败。
3. review-ready 超过 7 天未处理，必须补充处置说明。
4. superseded 分支必须标注替代分支。
5. archived 分支不得再承载新需求。

## Branch Registry

| branch_name | lifecycle_state | owner | last_activity_date | decision | replacement_branch |
|---|---|---|---|---|---|
| feat/plan-b-backend-rag-rebuild-20260418 | merged | ai-runtime | 2026-04-18 | Plan B merged into PR23 | - |
| feat/pr8-rag-qa-contract-upgrade | superseded | ai-runtime | 2026-04-18 | split into PlanB waves | feat/plan-b-backend-rag-rebuild-20260418 |
| feat/pr6-contracts-kb-chat | superseded | app-foundation | 2026-04-18 | superseded by PR5 shared contract plan | PR5_共享契约收口_与_前端工作台可用性方案 |

## Required Updates

- 新增长期分支：必须在本表登记。
- 分支状态变化：必须在 24 小时内回填状态和决策。
- 调整阈值：同步更新 scripts/check-branch-lifecycle.sh。

## Verification

- bash scripts/check-branch-lifecycle.sh
- bash scripts/check-governance.sh

## Open Questions

- 是否将生命周期状态与分支保护规则自动关联。
- 是否按团队维度设置不同 stale 阈值。
