---
owner: ai-platform
status: done
depends_on:
  - 18_v4_0_overview_plan
  - 21_v4_0_phase_2_execution_plan
  - 22_v4_0_phase_3_execution_plan
  - 24_v4_0_phase_6_execution_plan
last_verified_at: 2026-05-12
evidence_commits:
  - working-tree-v4-0-phase-7-research
---

# v4.0-7 研究文档：Testing and Evaluation Gate

> 日期：2026-05-12  
> 状态：research  
> 上游总览：`docs/plans/v4_0/active/overview/18_v4_0_overview_plan.md`

## 1. 研究问题

Phase 4.0-7 的职责不是继续修功能，而是把 v4.0 前六个 phase 已交付的产品、前端和 RAG 优化证据收束为一个可复现、可阻断、可解释的 gate。

本阶段要回答四个问题：

1. 哪些上游 verdict 和产物必须被 Phase 7 消费，而不能靠口头说明代替。
2. 当前仓库里哪些评测脚本和 artifact 已存在，可以直接复用。
3. 最终 release 词汇应如何收口，避免与 `controlled-beta-ready`、`artifact-ready`、`experiment-only` 冲突。
4. 在上游 phase 未完全 closeout 时，Phase 7 是否仍然应执行，并给出 `blocked` 结论。

## 2. 上游边界与仓库真相

### 2.1 Phase 7 的定位已经在总览中冻结

`18_v4_0_overview_plan.md` 已把 Phase 4.0-7 定义为：

1. full-chain workflow test
2. product acceptance test
3. RAG quality test
4. frontend quality test
5. release verdict

因此 Phase 7 的完成定义是“给出 gate verdict”，不是“替上游收尾代码”。

### 2.2 当前仓库已有可复用 gate 基座

当前 repo 已存在三类直接可复用输入：

1. 产品与 artifact verdict
   - Phase 2 controlled beta report：`controlled-beta-ready`
   - Phase 3 closeout report：`artifact-ready`
   - Phase 4 closeout：`closeout-complete / scope-limited`
2. 技术评测基座
   - `scripts/evals/phase6_gate.py`
   - `scripts/evals/run_phase_j_comparative_gate.py`
   - `scripts/evals/v3_0_official_gate.py`
3. 已落盘 artifact
   - `artifacts/validation-results/phase_j/2026-04-30-closeout/comparative_verdict.json`
   - `artifacts/benchmarks/v3_0/official_gate_results.json`

### 2.3 当前阻断现实必须被保留

截至 2026-05-12，`PLAN_STATUS.md` 的真实状态仍然是：

1. Phase 5：`execution-plan-complete / implementation-in-progress`
2. Phase 6：`implementation-in-progress / runtime-contract-extended`

这意味着 Phase 7 即使执行，也不能把当前仓库写成 `release-pass`。

## 3. Phase 7 必须消费的输入

Phase 7 至少要读取以下真源：

1. `docs/plans/PLAN_STATUS.md`
2. `docs/plans/v4_0/reports/2026-05-08_v4_0_phase_2_controlled_beta_gate_report.md`
3. `docs/plans/v4_0/reports/2026-05-08_v4_0_phase_3_closeout_report.md`
4. `artifacts/validation-results/phase_j/2026-04-30-closeout/comparative_verdict.json`
5. `artifacts/benchmarks/v3_0/official_gate_results.json`

如果这些输入缺失，Phase 7 本身就应记为 `blocked`。

## 4. Verdict 词汇冻结

Phase 7 只允许输出以下结论：

| verdict | allowed when |
|---|---|
| `blocked` | 任一必需上游 phase 未完成 closeout，或关键 gate artifact 缺失/失败 |
| `experiment-only` | 上游产品与前端层都已到位，但技术优化证据只适合保留为实验，不足以升级成 release-pass |
| `release-pass` | 产品、artifact、前端质量、RAG 质量和 comparative/official gate 全部通过 |

补充约束：

1. `controlled-beta-ready` 仍然只属于 Phase 2。
2. `artifact-ready` / `citation-backed-ready` 仍然只属于 Phase 3。
3. `experiment-only` 可以作为 Phase 7 最终 verdict，但不能被上游 phase 自行签发。

## 5. Gate 结构

Phase 7 需要把 gate 拆成以下五层：

1. Product readiness
   - Phase 2 controlled beta 是否成立
2. Artifact readiness
   - Phase 3 artifact 是否成立
3. Frontend quality readiness
   - Phase 4 是否 closeout
   - Phase 5 是否已经结束交互质量 closeout
4. Optimization evidence readiness
   - Phase 6 是否达到可被最终 gate 消费的状态
5. Comparative and official eval evidence
   - Phase J comparative verdict
   - official academic gate

## 6. Adopt / Extend / Reject

### 6.1 Adopt

直接采用现有能力：

1. `PLAN_STATUS.md` 作为 phase 状态唯一真源
2. Phase 2 / 3 的 closeout report 作为上游 verdict 真源
3. `comparative_verdict.json` 作为 candidate-vs-baseline 比较真源
4. `official_gate_results.json` 作为官方评测锚点真源

### 6.2 Extend

需要新增的最小能力：

1. 一个 v4.0 Phase 7 gate runner
2. 一个 machine-readable Phase 7 gate result JSON
3. 一个 repo 内 Phase 7 gate report

### 6.3 Reject

本阶段明确不做：

1. 不重新跑完整上游 benchmark 才能生成 Phase 7 verdict
2. 不用人工总结替代 machine-readable gate result
3. 不把上游未完成项通过降标准写成 `release-pass`

## 7. 最小交付

Phase 7 最小交付必须同时包含：

1. 研究文档
2. 执行计划
3. gate runner 脚本
4. gate result JSON
5. gate report
6. `PLAN_STATUS.md` 与 phase ledger 回填

## 8. 研究结论

Phase 4.0-7 的正确执行路径是：

```txt
collect upstream verdicts
-> validate required artifacts exist
-> combine product/frontend/optimization/eval gates
-> emit blocked / experiment-only / release-pass
-> write repo truth back to PLAN_STATUS and ledger
```

当前仓库最可能的首轮真实结果不是 `release-pass`，而是“Phase 7 已执行，但 verdict 为 `blocked`”。这不是失败，而是本阶段应该产出的真实门禁结论。
