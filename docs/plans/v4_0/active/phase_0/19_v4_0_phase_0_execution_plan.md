---
owner: product-engineering
status: done
depends_on:
  - 18_v4_0_overview_plan
  - 2026-04-29_v3_0_closeout_checklist
last_verified_at: 2026-05-02
evidence_commits:
  - historical-v4-0-phase-0-closeout
---

# 19 v4.0-0 执行计划：Version Gate and v3.0 Residual Close-out

> 日期：2026-05-02  
> 状态：execution-plan  
> 上游研究：`docs/plans/v4_0/active/phase_0/2026-05-02_v4_0_phase_0_research.md`  
> 上游总览：`docs/plans/v4_0/active/overview/18_v4_0_overview_plan.md`

## 0. 执行状态

Phase 4.0-0 已完成 close-out。它不新增产品功能，目标是完成 v3.0 残留项分类、当前验证证据回填、full-chain walkthrough evidence 口径回读和 Phase 4.0-1 readiness verdict。

## 1. 目标

Phase 4.0-0 的目标是建立 v4.0 可执行基线，并把 v3.0 遗留项分类收口：

```txt
v4.0 docs/gov baseline
-> v3.0 residual blocker readback
-> backend/frontend smoke rerun
-> full-chain walkthrough evidence
-> beta material carry-forward
-> v4.0 phase 1 readiness verdict
```

本阶段不新增产品功能。只有当 v3.0 残留风险被验证、归档或明确转入 v4.0 后，才允许进入 Phase 4.0-1。

## 2. 执行前先读什么

1. `docs/plans/v4_0/active/overview/18_v4_0_overview_plan.md`
2. `docs/plans/v4_0/active/phase_0/2026-05-02_v4_0_phase_0_research.md`
3. `docs/plans/v4_0/search/2026-05-02_v4_0_research_decision_note.md`
4. `docs/plans/v3_0/active/overview/2026-04-29_v3_0_closeout_checklist.md`
5. `docs/plans/v3_0/reports/general/2026-04-29_v3_0_strict_closeout_report.md`
6. `docs/plans/v3_0/reports/general/2026-05-01_backend_system_review.md`
7. `docs/plans/v3_0/reports/general/2026-05-01_frontend_system_review.md`
8. `docs/plans/PLAN_STATUS.md`
9. `docs/specs/governance/phase-delivery-ledger.md`

## 3. 当前已验证输入

| item | status | evidence | conclusion |
|---|---|---|---|
| branch baseline | passed | `feat/v4-0-major-iteration`, clean before edits | v4.0 已从当前 HEAD 独立建分支 |
| backend smoke: TaskService | passed | `cd apps/api && python3 -m pytest -q tests/unit/test_services.py --maxfail=1` -> 16 passed | v3.0 checklist 中 CO-BLK-005 已被后续代码修复，但需文档回填 |
| backend contract group | passed | `cd apps/api && python3 -m pytest -q tests/unit/test_chat_persistence_flow.py tests/unit/test_phase_h_runtime_contract.py tests/unit/test_phase_j_comparative_gate.py tests/unit/test_auth_rate_limit_and_failclosed.py --maxfail=5` -> 21 passed | Chat persistence / replay-only、Phase H runtime truth、Phase J comparative gate、auth fail-closed 当前可作为 Phase 0 基线 |
| frontend type-check | passed | `cd apps/web && npm run type-check` | TypeScript 编译基线通过 |
| frontend test runner | passed | `cd apps/web && npm run test:run -- --reporter=dot` -> 81 files / 308 tests passed | 2026-05-01 记录的 SDK resolution / router mock 类阻断未在当前基线复现 |

## 4. 待收口阻断

| id | source | status | required action |
|---|---|---|---|
| V4G-001 | v3.0 Phase D | carried-forward | 进入 `docs/plans/v4_0/reports/2026-05-02_v4_0_phase_0_closeout_report.md`，转交 Phase 4.0-2 / 4.0-7 继续补 fresh-state 单次全链 walkthrough |
| V4G-002 | v3.0 Phase F/G | carried-forward | 进入 `docs/plans/v4_0/active/phase_0/2026-05-02_v4_0_phase_0_beta_asset_inventory.md`，转交 Phase 4.0-2 制作 Beta assets |
| V4G-003 | 2026-05-01 backend review | verified | Chat persistence / Last-Event-ID replay-only 目标组已复测通过，后续如改 Chat runtime 必须继续保留此测试组 |
| V4G-004 | 2026-05-01 frontend review | verified | `npm run type-check` 与完整 Vitest runner 已复测通过；剩余 console noise 暂不作为 release blocker |
| V4G-005 | governance | verified | 文档、计划、Phase tracking、结构、代码边界、runtime hygiene 与总治理脚本均已通过 |

## 5. Work Packages

## WP0：v4.0 Planning Baseline

输出：

1. `docs/plans/v4_0/README.md`
2. `docs/plans/v4_0/search/2026-05-02_v4_0_research_decision_note.md`
3. `docs/plans/v4_0/active/overview/18_v4_0_overview_plan.md`
4. `docs/plans/v4_0/active/phase_0/19_v4_0_phase_0_execution_plan.md`
5. `docs/plans/PLAN_STATUS.md` v4.0 entries
6. `docs/specs/governance/phase-delivery-ledger.md` v4.0 deliverable units

验收：

1. docs 入口能直接定位 v4.0 当前主线。
2. v4.0 active 计划有 status、owner、evidence、DU 编号。

## WP1：v3.0 Residual Classification

输出：

1. `closed`: 已被后续代码或验证关闭的阻断项。
2. `carried-forward`: 需要作为 v4.0 Phase 0 或后续 phase 继续处理的项。
3. `rejected`: 不再符合 v4.0 方向的旧目标。

验收：

1. 不再出现“v3.0 完成”与“仍有未验证项”并存的状态失真。
2. 所有 carry-forward 项都有 v4.0 gate id。
3. 分类至少覆盖 `closed / carried-forward / rejected` 三类。

## WP2：Backend Smoke and Contract Rerun

必跑命令：

```bash
cd apps/api && python3 -m pytest -q tests/unit/test_services.py --maxfail=1
cd apps/api && python3 -m pytest -q tests/unit/test_chat_persistence_flow.py tests/unit/test_phase_h_runtime_contract.py tests/unit/test_phase_j_comparative_gate.py tests/unit/test_auth_rate_limit_and_failclosed.py --maxfail=5
```

验收：

1. `TaskService.retry_task` 契约清楚：只允许 failed task 重试。
2. Chat reconnect 必须 replay-only。
3. Phase H runtime truth 与 Phase J comparative gate 不能回退。

## WP3：Frontend Smoke and Runner Rerun

必跑命令：

```bash
cd apps/web && npm run type-check
cd apps/web && npm run test:run -- --reporter=dot
```

验收：

1. type-check 通过。
2. 如果 Vitest runner 失败，必须明确是测试环境配置问题还是产品代码问题。
3. 新增 v4.0 代码前先修 test runner 的可信度。

## WP4：Full-chain Walkthrough Evidence

必须覆盖：

```txt
Search -> Import -> KB -> Read -> Chat -> Notes -> Compare -> Review
```

输出：

1. workflow run 记录或手工 walkthrough report。
2. 成功/失败分桶。
3. screenshots 或 artifact path。
4. carry-forward issue list。

验收：

1. 至少一条 fresh-account 或 clean-state full-chain evidence。
2. 失败项不得被写成 release-pass。

## WP4.5：Beta Minimal Asset Inventory

目标：

1. 定义 Phase 4.0-2 需要制作的最低 Beta asset 清单
2. 避免 Phase 0 膨胀成完整 Beta 制作阶段

输出：

1. demo dataset requirement
2. demo account requirement
3. quickstart outline
4. known limitations outline
5. feedback channel requirement
6. walkthrough script requirement

验收：

1. 每个资产有 owner、目标路径或后续 phase、是否阻断 Phase 4.0-1 的判断。

## WP5：Phase 4.0-1 Readiness Verdict

输出：

1. `ready`: 可开始 Productized Research Workflow。
2. `conditional`: 可开始文档/契约设计，但不能写产品代码。
3. `blocked`: 继续 Phase 0 修复。

当前 close-out 结论：`conditional`。详见 `docs/plans/v4_0/reports/2026-05-02_v4_0_phase_0_closeout_report.md`。

验收：

1. verdict 必须引用测试命令、artifact 和 PLAN_STATUS 状态。

## 6. 当前执行顺序

1. 完成 WP0：v4.0 planning baseline。
2. 完成 WP1：v3.0 residual classification。
3. 完成 WP2/WP3：后端和前端目标验证复测。
4. 完成 WP4：full-chain walkthrough evidence。
5. 完成 WP4.5：Beta minimal asset inventory。
6. 完成 WP5：Phase 4.0-1 readiness verdict。

## 7. Open Questions

1. Full-chain walkthrough 是否使用本地 demo account，还是创建新的 clean account。
2. Phase 4.0-2 是否同步生成 Beta quickstart / walkthrough script 初稿模板。
3. Phase 4.0-7 是否需要把 single fresh-state full-chain rerun 升级为硬性 release gate。
