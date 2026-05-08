# v4.0 Phase 0 Close-out Report

> 日期：2026-05-02  
> phase: `4.0-0`  
> status: `closeout-complete`  
> readiness_verdict: `conditional`

## 1. 结论

Phase 4.0-0 已完成它自己的 gate 职责：v4.0 方向、台账、残留项分类、当前后端/前端/治理基线、walkthrough 证据回读口径、Beta 最低资产清单，已经全部进入 repo 内可追踪材料。

但 `Phase 4.0-1 readiness` 结论不是 `ready`，而是 `conditional`：

1. 可以开始 `Productized Research Workflow` 的研究、方案和契约设计。
2. 不应把 Phase 0 写成“已拿到完整 Beta 放行”。
3. 在补出新的 `Search -> Import -> KB -> Read -> Chat -> Notes -> Compare -> Review` 单次完整 fresh-state walkthrough 之前，不建议宣称产品代码主链已经拿到 release-pass。

## 2. 已关闭项

| id | status | evidence |
|---|---|---|
| V4G-003 | closed | `cd apps/api && python3 -m pytest -q tests/unit/test_chat_persistence_flow.py tests/unit/test_phase_h_runtime_contract.py tests/unit/test_phase_j_comparative_gate.py tests/unit/test_auth_rate_limit_and_failclosed.py --maxfail=5` |
| V4G-004 | closed | `cd apps/web && npm run type-check`；`cd apps/web && npm run test:run -- --reporter=dot` |
| V4G-005 | closed | `bash scripts/check-doc-governance.sh`；`bash scripts/check-plan-governance.sh`；`bash scripts/check-phase-tracking.sh`；`bash scripts/check-governance.sh` |
| CO-BLK-005 | closed | `cd apps/api && python3 -m pytest -q tests/unit/test_services.py --maxfail=1` |

## 3. Walkthrough Evidence Readback

Phase 0 没有伪造新的 full-green full-chain run，而是把当前 repo 内已有真实证据重新归档并明确边界。

### 3.1 已有真实主链证据

基于 `artifacts/validation-results/phase_d/real_world_validation.json` 与 `docs/plans/v3_0/reports/validation/v3_0_real_world_validation.md`：

1. `RW-004` 和 `RW-005` 已在 fresh account + real Milvus 条件下跑通 `search -> import -> read -> chat -> notes -> review` 的主链子集。
2. 这些 run 验证了：
   - search/import CTA 可用
   - fulltext import 完成后可进入 read
   - single-paper chat 能返回真实答案
   - notes endpoint 能返回非空 reading notes
   - review run 能完成并在 UI 回跳到 `runId`
3. 当前 repo 证据同时明确保留了两个 degraded 事实：
   - review 仍可能以 `partial / insufficient_evidence` 完成
   - fresh import 首轮端到端耗时仍约 `4.1 min`

### 3.2 Compare 证据边界

基于 `artifacts/validation-results/phase_j/2026-04-30-closeout/workflow_baseline.bundle.json`：

1. `RW-005:compare` 已作为 workflow compare case 进入 comparative gate。
2. 该 case 在 comparative bundle 中的 `workflow_success_state` 为 `partial`，不是 `blocked`。
3. 但这不是一条从 search 开始、单次串完全部 8 步的 fresh-state walkthrough 证据。

因此 Phase 0 的严谨结论是：

1. `compare` 不是“完全无证据”。
2. 但 `Search -> Import -> KB -> Read -> Chat -> Notes -> Compare -> Review` 仍缺一条单次 fresh-state 全链路 repo-local closeout 记录。
3. 这个缺口不能在 Phase 0 中被伪装成已完成，只能被诚实转入后续 gate。

## 4. Beta Minimal Asset Inventory

| asset | owner | target path or phase | phase_1 blocker | current status |
|---|---|---|---|---|
| demo dataset definition | product-engineering | `docs/plans/v4_0/active/phase_2/` | no | inventory-defined |
| demo account policy | product-engineering | `docs/plans/v4_0/active/phase_2/` | no | inventory-defined |
| beta quickstart | product-engineering | `docs/plans/v4_0/active/phase_2/` | no | inventory-defined |
| known limitations | product-engineering | `docs/plans/v4_0/active/phase_2/` + 本文档 | no | inventory-defined |
| feedback channel | product-engineering | `docs/plans/v4_0/active/phase_2/` | no | inventory-defined |
| 15-30 min walkthrough script | product-engineering | `docs/plans/v4_0/active/phase_2/` | yes | missing-script |

最低要求已经定义清楚，但 Phase 0 不承担这些 Beta 材料的完整制作，只负责明确资产边界与阻断关系。

## 5. Phase 4.0-1 Readiness Verdict

- verdict: `conditional`
- allowed_now:
  - `Phase 4.0-1` 的研究文档
  - `Phase 4.0-1` 的执行计划
  - workflow continuity、页面边界、契约与状态语义设计
- not_allowed_yet:
  - 把当前状态写成 Beta-ready
  - 以“full-chain walkthrough 已完成”为前提推进 release 叙事
  - 跳过新的 fresh-state 全链 evidence 直接宣称主链 release-pass

## 6. Carry-forward

| id | next owner | next phase | action |
|---|---|---|---|
| V4G-001 | product-engineering | 4.0-2 / 4.0-7 | 补 fresh-state 单次 full-chain walkthrough closeout |
| V4G-002 | product-engineering | 4.0-2 | 产出 Beta quickstart、demo dataset/account、walkthrough script、known limitations、feedback channel |

## 7. Verification

- `cd apps/api && python3 -m pytest -q tests/unit/test_services.py --maxfail=1`
- `cd apps/api && python3 -m pytest -q tests/unit/test_chat_persistence_flow.py tests/unit/test_phase_h_runtime_contract.py tests/unit/test_phase_j_comparative_gate.py tests/unit/test_auth_rate_limit_and_failclosed.py --maxfail=5`
- `cd apps/web && npm run type-check`
- `cd apps/web && npm run test:run -- --reporter=dot`
- `bash scripts/check-doc-governance.sh`
- `bash scripts/check-plan-governance.sh`
- `bash scripts/check-phase-tracking.sh`
- `bash scripts/check-governance.sh`
