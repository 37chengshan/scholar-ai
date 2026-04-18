# E2E Failure Handbook

## Purpose

定义关键链路 E2E 失败分级和标准处置流程，防止失败被静默忽略。

## Scope

覆盖 Chat、Knowledge Base、Retrieval 三条关键链路的 E2E 门禁失败处置。

## Source of Truth

- 测试策略：docs/development/testing-strategy.md
- E2E 门禁脚本：scripts/check-e2e-gate.sh
- E2E 工作流：.github/workflows/e2e-gate.yml

## Rules

失败分级：

1. P0：关键链路不可用（登录后无法进入核心页面、提交请求完全失败）。
2. P1：核心交互可用但数据一致性失败（状态不一致、响应字段错误）。
3. P2：非关键视觉或性能退化（不阻断合并，但必须记录）。

阻断策略：

1. P0/P1 必须阻断主干合并。
2. P2 可放行，但必须在 48 小时内补修复任务。
3. 快速通道必须附带补审计记录与责任人。

## Required Updates

- 新增关键链路：同步更新 scripts/check-e2e-gate.sh 与 .github/workflows/e2e-gate.yml。
- 调整失败分级：同步更新本手册与 PR 模板中的风险项。

## Verification

- bash scripts/check-e2e-gate.sh --mode manifest
- bash scripts/check-e2e-gate.sh --mode run

## Open Questions

- 是否对 P1 增设自动截图差异比对结果归档。
- 是否将处置时效纳入团队绩效指标。
