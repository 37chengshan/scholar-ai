---
owner: ai-platform
status: done
depends_on:
  - 2026-05-12_v4_0_phase_7_testing_and_evaluation_gate_research
  - 24_v4_0_phase_6_execution_plan_followup
last_verified_at: 2026-05-12
evidence_commits:
  - working-tree-v4-0-phase-7-gate
---

# 25 v4.0-7 执行计划：Testing and Evaluation Gate

> 日期：2026-05-12  
> 状态：execution-complete  
> 上游研究：`docs/plans/v4_0/active/phase_7/2026-05-12_v4_0_phase_7_testing_and_evaluation_gate_research.md`

## 0. 执行状态

本轮执行目标不是把 v4.0 强行写成通过，而是把 Phase 7 本身执行完成：

```txt
phase status intake
-> gate runner
-> machine-readable result
-> markdown gate report
-> PLAN_STATUS / ledger truth update
```

## 1. 目标

1. 新增一个可直接运行的 v4.0 Phase 7 gate runner。
2. 读取并验证 Phase 2/3/4/5/6 的真实状态与必需 artifact。
3. 输出 `blocked / experiment-only / release-pass` 之一。
4. 把首轮 Phase 7 gate 结果回填到 repo truth。

## 2. Work Packages

## WP1：Freeze Gate Inputs

输入：

1. `docs/plans/PLAN_STATUS.md`
2. `docs/plans/v4_0/reports/2026-05-08_v4_0_phase_2_controlled_beta_gate_report.md`
3. `docs/plans/v4_0/reports/2026-05-08_v4_0_phase_3_closeout_report.md`
4. `artifacts/validation-results/phase_j/2026-04-30-closeout/comparative_verdict.json`
5. `artifacts/benchmarks/v3_0/official_gate_results.json`

验收：

1. 所有输入路径在脚本中显式声明。
2. 缺任何一个输入时，Phase 7 结果必须变成 `blocked`。

## WP2：Implement Gate Runner

输出：

1. `scripts/evals/run_v4_phase7_gate.py`

验收：

1. 脚本可输出 machine-readable JSON。
2. 脚本显式列出每个 gate check 的 `pass / fail`。
3. `release-pass` 只在全部 checks 通过时出现。

## WP3：Run First Gate

输出：

1. `artifacts/validation-results/phase_7/2026-05-12-gate/phase7_gate_results.json`
2. `docs/plans/v4_0/reports/2026-05-12_v4_0_phase_7_gate_report.md`

验收：

1. gate report 必须引用真实 artifact 与 status。
2. 若当前状态被阻断，必须诚实写成 `blocked`。

## WP4：Truth Backfill

输出：

1. `docs/plans/PLAN_STATUS.md`
2. `docs/specs/governance/phase-delivery-ledger.md`
3. `docs/plans/v4_0/README.md`

验收：

1. Phase 7 顶层状态不再停留在 `plan-required`。
2. phase ledger 有独立 Phase 7 交付记录。

## 3. 首轮 Gate 规则

首轮 gate 采用以下硬条件：

1. Phase 2 必须为 `controlled-beta-ready`
2. Phase 3 必须至少为 `artifact-ready`
3. Phase 4 必须完成 closeout
4. Phase 5 必须完成交互质量 closeout
5. Phase 6 必须完成最终可评测 closeout
6. comparative verdict 必须为 `pass`
7. official gate 必须为 `PASS`

首轮特殊规则：

1. 若 1-5 任一上游 phase 仍未完成，则最终 verdict 直接为 `blocked`
2. 只有在 1-7 全部通过且无 mode-parity / experiment-only 限制时，才允许写 `release-pass`

## 4. 当前首轮结果

本轮首跑的预期真实结果是：

1. Phase 2：pass
2. Phase 3：pass
3. Phase 4：pass
4. Phase 5：fail
5. Phase 6：fail
6. comparative verdict：pass
7. official gate：pass

因此本轮 Phase 7 gate 结论应为 `blocked`。

## 5. 最小验证

```bash
python3 scripts/evals/run_v4_phase7_gate.py --output artifacts/validation-results/phase_7/2026-05-12-gate/phase7_gate_results.json
bash scripts/check-doc-governance.sh
bash scripts/check-plan-governance.sh
bash scripts/check-phase-tracking.sh
bash scripts/check-governance.sh
```

## 6. 完成定义

Phase 7 本轮算执行完成，当且仅当：

1. gate runner 已落 repo
2. 首轮 gate result 已生成
3. gate report 已回填
4. `PLAN_STATUS.md` 与 phase ledger 已同步
5. 最终 verdict 被真实记录为 `blocked / experiment-only / release-pass` 之一

注意：本阶段“执行完成”不等于“release-pass 通过”。
