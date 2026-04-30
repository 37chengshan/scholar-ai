# Governance KPI Spec

## Purpose

定义工程治理 KPI 的计算口径与阈值，支撑双周审计闭环。

## Scope

适用于 Plan A/B/C 及后续治理计划的执行审计。

## Source of Truth

- 计划状态：docs/plans/PLAN_STATUS.md
- Phase 台账：docs/specs/governance/phase-delivery-ledger.md
- fallback 台账：docs/specs/governance/fallback-register.yaml
- E2E 门禁：scripts/check-e2e-gate.sh
- KPI 报告脚本：scripts/audit-governance-kpi.sh

## Rules

指标定义：

1. phase_coverage_rate = 有交付单元记录的 phase / 全部活跃 phase。
2. planning_delivery_rate = done 计划数 / (done + in-progress + blocked 计划数)。
3. fallback_expired_active = 到期但仍 active 的 fallback 数量。
4. fallback_active_days_avg = active fallback 平均存活天数。
5. e2e_gate_pass_rate = 最近窗口内通过次数 / (通过 + 失败)。
6. post_merge_48h_incident_rate = 合并后 48 小时故障 PR 数 / 合并 PR 总数。

阈值建议：

- phase_coverage_rate >= 1.00
- planning_delivery_rate >= 0.85
- fallback_expired_active = 0
- fallback_active_days_avg <= 14
- e2e_gate_pass_rate >= 0.95
- post_merge_48h_incident_rate <= 0.05

## Required Updates

- 新增治理指标：同步更新本文件和 scripts/audit-governance-kpi.sh。
- 调整指标阈值：同步更新 KPI 报告说明与审计模板。

## Verification

- bash scripts/audit-governance-kpi.sh --window 14d --output docs/plans/v3_0/reports/governance-kpi/latest.md
- test -f docs/plans/v3_0/reports/governance-kpi/latest.md
- bash scripts/check-doc-governance.sh

## Open Questions

- 48小时故障率是否需要接入监控平台自动采样。
- 是否需要按模块拆分 KPI 维度（web/api/infra）。
