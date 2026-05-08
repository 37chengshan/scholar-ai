# v4.0 Phase 2 Controlled Beta Gate Report

> 日期：2026-05-08  
> phase: `4.0-2`  
> status: `gate-complete`  
> verdict: `controlled-beta-ready`

## 1. 结论

在保留 `2026-05-04_v4_0_phase_2_closeout_report.md` 的原始 `demo-ready` 结论不变的前提下，Phase 4.0-2 现在可以补充升级为 `controlled-beta-ready`。

升级依据不是“重新解释 5 月 4 日的 walkthrough”，而是 5 月 8 日已经把当时缺失的 controlled release gate 证据补齐到 repo truth：

1. access policy 已明确
2. feedback triage 不再只是模板，而已有真实 queue
3. rollback / pause / disable / resume 规则已写入 environment policy
4. 当前结论仍然严格限制在 `local controlled beta`

因此，本报告的结论是：

- 允许写 `controlled-beta-ready`
- 不允许写 `public-beta-ready`
- 不允许写 `production-ready`
- 不允许写 `release-pass`

## 2. 输入证据

### 2.1 原始 Phase 2 closeout

`docs/plans/v4_0/reports/2026-05-04_v4_0_phase_2_closeout_report.md` 已经提供：

1. asset gate 已完成
2. fresh-state walkthrough 已执行
3. online provider mainline 与 browser walkthrough 有真实证据
4. Review `partial / insufficient_evidence` 被诚实保留

### 2.2 新增 controlled release gate 证据

本轮新增或明确化的 repo truth：

1. `docs/plans/v4_0/active/phase_2/demo_environment_policy.md`
   - 新增 controlled beta access policy
   - 新增 rollback / pause / disable / resume rule
2. `docs/plans/v4_0/active/phase_2/2026-05-08_phase_2_feedback_queue.md`
   - 将 Run A / Run B 的真实 `blocked / partial` 项落成 triage queue
3. `docs/plans/v4_0/active/phase_2/fresh_state_walkthrough_script.md`
   - 将 `walkthrough verdict` 与 `phase closeout verdict` 拆开，避免把 `Review partial` 直接混同为 phase gate 失败

## 3. Controlled Release Gate Audit

| gate item | required by research/plan | current evidence | result |
|---|---|---|---|
| access control | 只允许受控试用者，不得漂移为 public beta | environment policy 已定义 `primary operator` / `internal reviewer` / `invited observer` | pass |
| reset policy | fresh-state run 仍需可证明 | 原有 walkthrough reset proof 仍然有效，且 environment policy 保留 reset checklist | pass |
| known limitations | limitation 必须用户可见 | `known_limitations.md` + `beta_quickstart.md` 已存在 | pass |
| feedback triage | 至少一个真实 `partial` 或 `blocked` 进入 triage | `2026-05-08_phase_2_feedback_queue.md` 已记录 4 条真实反馈 | pass |
| rollback / pause | gate owner 与停止规则明确 | environment policy 已新增 pause / disable / resume 规则 | pass |
| verdict scope | 不得越级写成 public/prod/release | 本报告和 PLAN_STATUS 仅声明 `controlled-beta-ready` | pass |

## 4. Why Review Partial Does Not Block Controlled Beta

`Review partial / insufficient_evidence` 仍然存在，但当前不再视为阻断 `local controlled beta` 的硬失败，原因是：

1. 它已经是用户可见 limitation，而不是隐藏失败
2. walkthrough 证据表明 Review artifact 能生成，并有 run trace 可回读
3. feedback queue 已把该 limitation 明确标为 `carry-forward` 到 Phase 4.0-3 / 4.0-7
4. Phase 2 的 controlled beta 目标是“可试用、可反馈、可暂停”，不是“所有 artifact 已 full-green”

如果后续该 limitation 误导了试用者，或不能再被 citation / run trace 解释，则 gate owner 必须按 pause rule 降级 verdict。

## 5. Go / No-Go

| item | decision | note |
|---|---|---|
| local controlled beta | go | 可以按 quickstart 组织受控试用，并要求参与者填写 feedback |
| staging controlled beta | no-go | 仍然 gated，不作为本轮放行对象 |
| cloud/public beta | no-go | 超出 Phase 2 范围 |

## 6. State Update

本报告补充后的 Phase 2 真实状态应为：

- `closeout-complete / controlled-beta-ready`

而不是：

- `walkthrough-complete / demo-ready`

后者仍然保留为 2026-05-04 的历史节点，不应被删除。

## 7. Verification

- `bash scripts/check-doc-governance.sh`
- `bash scripts/check-plan-governance.sh`
- `bash scripts/check-phase-tracking.sh`
- `bash scripts/check-governance.sh`

## 8. Handoff

1. Phase 3 继续接手 `FB-20260504-REVIEW-PARTIAL-HONESTY`，把 Review partial honesty 收束成 citation-backed artifact contract。
2. Phase 4.0-7 若要给 release verdict，必须额外验证 staging/cloud、evaluation、frontend quality 与更强的 workflow gate。
