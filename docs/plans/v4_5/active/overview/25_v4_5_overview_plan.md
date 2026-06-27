---
owner: product-engineering
status: done
depends_on:
  - 2026-05-13_v4_5_release_readiness_bridge_research
  - 21_v4_0_phase_2_execution_plan
  - 22_v4_0_phase_3_execution_plan
  - 24_v4_0_phase_5_execution_plan
  - 24_v4_0_phase_6_execution_plan
last_verified_at: 2026-05-13
evidence_commits:
  - working-tree-v4-5-phase-0-kickoff
---

# 25 v4.5 纵览计划：Release Readiness Bridge

> 日期：2026-05-13  
> 状态：overview-frozen  
> 上游研究：`docs/plans/v4_5/active/overview/2026-05-13_v4_5_release_readiness_bridge_research.md`

## 0. 版本定位

`v4.5` 不是新的产品路线，也不是对 `v4.0` 的重写。它是把当前仓库里已经分散在 `v4.0` 多个 phase 的发布收口问题，重新整理成一条可验证、可执行、可报告的 release-readiness bridge。

统一表达为：

```txt
v4.5 =
release-readiness bridge
=
phase_3 artifact closeout carry-in
+ phase_5 interaction debt carry-in
+ phase_6 runtime truth freeze
+ real backend benchmark
+ consolidated gate input
+ honest release verdict
```

## 1. 启动前提

本计划建立在以下 repo 真相之上：

1. `v4.0` 当前不是“Phase 7 blocked”，而是 `direction-confirmed / plan-required`。
2. KB-scoped chat/search 的底层能力并非完全不存在，真实缺口在 route contract 和 end-to-end wiring。
3. runtime 语义已分散存在于 `truthfulness_summary`、`retrieval_plane_policy`、`degraded_conditions`、`recovery_actions` 等字段中，但还没有统一 shared contract。
4. 真实 backend 在受控环境下可启动，并有现成健康检查入口。
5. 当前本地数据允许 single-paper / compare / primary-KB benchmark；但 `knowledge_base_papers` 为空，many-to-many KB membership 语义仍不能被伪装成已闭环。

## 2. v4.5 的唯一目标

v4.5 的目标只有一个：把“能否诚实宣称 release-candidate”这件事变成 repo 内可执行、可阻断、可回填的事实判断，而不是继续让多个 phase 各自看起来局部完成。

## 3. Phase 4.5-0 范围

v4.5 当前只启动 `Phase 4.5-0`，范围冻结为：

1. 冻结 release bridge 的 shared runtime / benchmark / gate 输入口径。
2. 新增真实可运行的 live benchmark 入口。
3. 明确 single-paper、compare、KB-scope 三类 gate 输入的真实边界。
4. 产出 `PLAN_STATUS`、delivery ledger 和版本目录级真源，不再让 v4.5 停留在 research-only。

## 4. 不在本阶段做的事

1. 不在本阶段宣称 release-pass。
2. 不把 KB route 存在本身当成 KB benchmark ready。
3. 不新开第二套 runtime、第二套 chat surface 或平行前端路径。
4. 不把 Phase 3/5/6 的剩余代码债务伪装成“已有 gate runner 即完成”。

## 5. 当前第一批正式产物

1. `docs/plans/v4_5/active/phase_0/26_v4_5_phase_0_execution_plan.md`
2. `docs/plans/v4_5/active/phase_0/v4_5_runtime_contract_freeze.md`
3. `docs/plans/v4_5/active/phase_0/v4_5_gate_input_matrix.md`
4. `scripts/evals/run_v4_5_live_rag_benchmark.py`

## 6. 第一批验收口径

1. 真 backend 可在受控环境下启动并通过 `/health/live`。
2. live benchmark 不是 mock answers，而是实际调用本地 API 路由。
3. benchmark 必须输出 JSON 与 Markdown artifact。
4. KB-scoped benchmark 必须按真实 membership 运行：若存在 `Paper.knowledge_base_id` 样本就进入真实 pass/fail；若主 membership 与 association membership 都缺失才允许阻断。
5. 所有状态变化必须同步回填 `docs/plans/PLAN_STATUS.md` 与 `docs/specs/governance/phase-delivery-ledger.md`。
