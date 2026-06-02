# v5.0 Phase 0 Workspace

Phase 5.0-0 是 v5.0 的启动期 — **Foundation & v4.x 维护态切换**。

## Phase 0 状态: ✅ closeout-complete / all-deliverables-verified (2026-05-31)

## Phase 0 产物清单 (全部完成)

| # | 产物 | 行数 | 验证 |
|---|---|---|---|
| 1 | `26_v5_0_phase_0_execution_plan.md` | 287 | ✅ 结构完整，6 wave 对应 6 deliverable |
| 2 | `v5_0_v4x_migration_inventory.md` | 217 | ✅ 19 项映射，v4.0 phase_3/5/7 标 superseded |
| 3 | `v5_0_runtime_contract_freeze.md` | 303 | ✅ 继承 v4.5 + 预留 4 组 PLANNED 字段 |
| 4 | `v5_0_gate_input_matrix.md` | 384 | ✅ 5-face 定义与 runner 对齐 |
| 5 | `v5_0_perf_baseline_snapshot.md` | 182 | ✅ 静态测量，数据 spot check 通过 |
| 6 | `scripts/evals/run_v5_release_gate.py` | 392 | ✅ dry run verdict=blocked 符合预期 |
| 7 | `reports/2026-05-31_v5_0_phase_0_audit_baseline.md` | 281 | ✅ 合并 v4.5 审计 + drift + perf |

**总计**: 7 个 deliverable，2046 行

## 验证记录 (2026-05-31)

| 验证项 | 结果 |
|---|---|
| gate runner `--help` | ✅ 5 Face 参数正确 |
| gate runner dry run | ✅ verdict=blocked (Face A/B/C/E input_missing, Face D all_phases_closeout=false) |
| gate runner unit tests | ✅ 34/34 pass |
| `--playwright-report /etc` path traversal | ✅ SystemExit(2) correctly raised |
| `last_benchmark_date` from artifact timestamps | ✅ Populated from latest artifact |
| a11y score gate (a11y_min_score < 90) | ✅ Blocks correctly |
| check-doc-governance.sh | ✅ passed |
| check-plan-governance.sh | ✅ passed |
| check-structure-boundaries.sh | ✅ passed |
| check-runtime-hygiene.sh (tracked) | ✅ passed |
| gate matrix ↔ runner 5 Face 对齐 | ✅ |
| runtime contract vs phase6_runtime_service.py | ✅ 字段完整 |
| migration inventory vs PLAN_STATUS | ✅ 状态一致 |
| perf baseline 数据 spot check | ✅ 3.2MB/536KB/36MB 与实测一致 |
| TypeScript tsc --noEmit | ✅ passed |

## 治理回填状态

| # | 动作 | 状态 | 说明 |
|---|---|---|---|
| 1 | PLAN_STATUS: v5.0 面板新增 | done | 10 条 phase 条目已写入 |
| 2 | PLAN_STATUS: v4.0 phase_3/5/7 标 superseded | done | superseded-by-v5.0-{3,4,9} |
| 3 | phase-delivery-ledger: v5.0 DU 条目 | done | DU-20260531-001~008 |
| 4 | Runtime Contract status -> frozen | done | freeze-draft -> frozen |
| 5 | Migration Inventory status -> frozen | done | draft -> frozen |
| 6 | Gate runner regex 兼容 closeout-complete | done | 正则已扩展 |

## 当前边界

1. Phase 5.0-0 已完成 closeout，不阻断后续 phase 启动
2. Phase 5.0-1 (设计系统 v2) 和 5.0-7 (后端 Pipeline 稳定性) 可并行启动
3. perf baseline 是静态测量，5.0-2 必须重做动态 baseline (build + Lighthouse)
4. gate runner 当前 verdict=blocked 是预期行为，不构成发布结论

## Dependencies

- 上游: v4.5 bridge phase_0 (已 closeout) + 2026-05-26 multidimensional audit (已修闭环)
- 下游: 阻塞 v5.0 phase 1-9 全部启动 → 当前已解除

## Closeout Report

- 路径: `docs/plans/v5_0/reports/2026-05-31_v5_0_phase_foundation_closeout.md`
