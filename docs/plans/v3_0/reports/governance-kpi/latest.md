# Governance KPI Report

- generated_at: 2026-04-18
- window: 14d
- since: 2026-04-04

## Delivery Consistency

| metric | value | threshold |
|---|---:|---:|
| phase_coverage_rate | 0.33 | >= 1.00 |
| planning_delivery_rate | 0.78 | >= 0.85 |
| rollback_rate | 0.00 | <= 0.10 |

## Contract Health

| metric | value | threshold |
|---|---:|---:|
| fallback_expired_active | 0 | = 0 |
| fallback_active_days_avg | 2.00 | <= 14 |
| fallback_active_count | 1 | monitor |

## Release Quality

| metric | value | threshold |
|---|---:|---:|
| e2e_gate_pass_rate | N/A | >= 0.95 |
| post_merge_48h_incident_rate | N/A | <= 0.05 |

## Raw Counters

- total_plans: 11
- done_plans: 7
- in_progress_plans: 2
- blocked_plans: 0
- ledger_phase_count: 3
- e2e_pass: 0
- e2e_fail: 0
- commits_in_window: 462
- reverts_in_window: 0
