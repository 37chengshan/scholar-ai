---
owner: product-engineering
status: done
depends_on:
  - 20_v4_0_phase_1_execution_plan
  - 2026-05-03_v4_0_phase_2_beta_release_hardening_research
last_verified_at: 2026-05-04
evidence_commits:
  - working-tree-v4-0-phase-2-execution-plan
  - working-tree-v4-0-phase-2-closeout
---

# 21 v4.0-2 执行计划：Beta Release Hardening

> 日期：2026-05-03  
> 状态：execution-plan  
> 上游研究：`docs/plans/v4_0/active/phase_2/2026-05-03_v4_0_phase_2_beta_release_hardening_research.md`  
> 上游 Phase 1 closeout：`docs/plans/v4_0/reports/2026-05-02_v4_0_phase_1_closeout_report.md`

## 0. 执行状态

Phase 4.0-2 当前进入执行计划阶段。它的目标不是新增复杂产品能力，而是把已有主链包装成可演示、可试用、可反馈的 controlled beta。

本计划只定义 Phase 2 的执行拆解和验收口径。后续真正执行时，必须按本计划逐项补齐 Beta assets、fresh-state walkthrough 和 closeout report。

## 1. 目标

Phase 4.0-2 的目标是完成 controlled beta hardening：

```txt
asset contract
-> demo dataset
-> resettable demo environment
-> beta quickstart
-> known limitations
-> feedback triage
-> fresh-state walkthrough
-> controlled beta go/no-go
```

Phase 2 完成后最多只能声明 `controlled-beta-ready`。它不能声明 public beta、production release 或 full release-pass。

## 2. 执行前先读什么

1. `docs/plans/v4_0/active/overview/18_v4_0_overview_plan.md`
2. `docs/plans/v4_0/active/phase_2/2026-05-03_v4_0_phase_2_beta_release_hardening_research.md`
3. `docs/plans/v4_0/reports/2026-05-02_v4_0_phase_0_closeout_report.md`
4. `docs/plans/v4_0/reports/2026-05-02_v4_0_phase_1_closeout_report.md`
5. `docs/plans/v4_0/active/phase_0/2026-05-02_v4_0_phase_0_beta_asset_inventory.md`
6. `docs/specs/design/frontend/DESIGN_SYSTEM.md`
7. `docs/specs/architecture/api-contract.md`
8. `docs/specs/domain/resources.md`
9. `docs/specs/governance/e2e-failure-handbook.md`

## 3. 当前可直接消费的真实能力

| area | current state | Phase 2 usage |
|---|---|---|
| workflow continuity | Phase 1 已完成 durable handoff、Chat prefill recovery、WorkflowHydration waiting-state、Dashboard command center continuity | quickstart 与 walkthrough 可直接引用这些恢复路径 |
| Search / KB / Chat / Review mainline | 现有页面主链已存在，但缺 fresh-state 单次全链 release-pass | walkthrough 必须真实执行并记录 partial / fail |
| Review / Compare evidence semantics | 已有 partial / insufficient evidence 口径 | known limitations 必须显式写出 |
| governance | Phase 0/1 已接入 PLAN_STATUS 与 phase ledger | Phase 2 新资产必须同步台账 |
| Beta inventory | Phase 0 已列出最小资产 | Phase 2 负责把 inventory 变成可执行文档和证据 |

## 4. 术语约束

执行过程中只能使用以下结论词：

| term | allowed when |
|---|---|
| `asset-ready` | demo dataset、environment policy、quickstart、limitations、feedback template、walkthrough script 均存在 |
| `demo-ready` | 指定 dataset/account 能按 walkthrough 完成演示，且有证据 |
| `controlled-beta-ready` | controlled release gate 通过，受控试用者可按 quickstart 使用并反馈 |
| `blocked` | 任一 asset gate 或 fresh-state walkthrough gate 失败 |

禁止在 Phase 2 closeout 中写 `public-beta-ready`、`production-ready`、`release-pass`，除非后续 Phase 4.0-7 给出独立 release verdict。

## 5. Work Packages

## WP1：Beta Asset Contract

目标：

1. 冻结 Phase 2 所有资产目录、文件名、必填字段和 pass/fail 口径。
2. 明确哪些资产是人读文档，哪些后续可升级为机器可读 artifact。

输出：

1. 本执行计划确认的资产路径。
2. 每个资产的 owner、状态字段和验收条件。
3. `asset-ready` 判定表。

目标路径：

1. `docs/plans/v4_0/active/phase_2/demo_dataset.md`
2. `docs/plans/v4_0/active/phase_2/demo_environment_policy.md`
3. `docs/plans/v4_0/active/phase_2/beta_quickstart.md`
4. `docs/plans/v4_0/active/phase_2/known_limitations.md`
5. `docs/plans/v4_0/active/phase_2/feedback_triage_template.md`
6. `docs/plans/v4_0/active/phase_2/fresh_state_walkthrough_script.md`
7. `docs/plans/v4_0/reports/2026-05-04_v4_0_phase_2_closeout_report.md`

`asset-ready` 判定表：

| asset | owner | status field | acceptance condition |
|---|---|---|---|
| `demo_dataset.md` | product-engineering | `asset-ready / blocked` | 至少 1 组 dataset_id、固定 search/import 入口、evidence probe、degraded/fallback 已定义 |
| `demo_environment_policy.md` | product-engineering | `asset-ready / blocked` | local controlled beta、reset proof、环境变量边界、staging/cloud gate 已定义 |
| `beta_quickstart.md` | product-engineering | `asset-ready / blocked` | happy path、degraded path、timing、recovery、not supported 已写明 |
| `known_limitations.md` | product-engineering | `asset-ready / blocked` | partial / insufficient evidence、prefill-only handoff、AI 审查约束等限制已显式用户可见 |
| `feedback_triage_template.md` | product-engineering | `asset-ready / blocked` | reporter、workflow step、artifact、severity、owner、decision 字段齐全 |
| `fresh_state_walkthrough_script.md` | product-engineering | `walkthrough-complete / blocked` | 15-30 分钟脚本、reset proof 模板、逐步 pass/partial/fail 记录位已定义，并已回填真实执行证据 |
| `2026-05-04_v4_0_phase_2_closeout_report.md` | product-engineering | `demo-ready / controlled-beta-ready / blocked` | 仅在真实 fresh-state run 完成后生成，禁止由历史 Phase D/J 证据替代 |

验收：

1. 所有资产路径都在 `docs/plans/v4_0/active/phase_2/` 或 `docs/plans/v4_0/reports/`。
2. 不新增根级临时目录、平行前端、平行后端或运行时产物。
3. 每个资产都能对应一个 workflow step、expected state 或 failure fallback。

## WP2：Demo Dataset

目标：

1. 定义一组可重复 paper set，覆盖 Search -> Import -> KB -> Read -> Chat -> Notes -> Compare -> Review。
2. 每个样本都记录 evidence-quality 检查点和已知 degraded behavior。

输出：

1. `docs/plans/v4_0/active/phase_2/demo_dataset.md`
2. 至少一组 `dataset_id`
3. source query 或 fixed paper IDs
4. expected import mode
5. expected evidence availability
6. known degraded cases

验收：

1. 不能只给营销说明，必须能指导真实 Search/import。
2. 至少包含一个 citation/evidence 检查点。
3. 如果样本依赖外部服务不稳定，必须给 fallback 或标记 blocked。

## WP3：Demo Account and Environment Policy

目标：

1. 明确 Phase 2 第一波使用 local controlled beta。
2. 定义 demo account、reset policy、环境变量、数据隔离和不可清理状态。

输出：

1. `docs/plans/v4_0/active/phase_2/demo_environment_policy.md`
2. local demo account policy
3. reset checklist
4. staging/cloud expansion gate

验收：

1. fresh-state run 前有 reset proof。
2. KB、import jobs、vector/artifact 状态边界清楚。
3. staging/cloud beta 必须被 gate 阻断，直到 local fresh-state pass。

## WP4：Beta Quickstart and Known Limitations

目标：

1. 让受控试用者能按真实产品路径完成一次研究任务。
2. 把 partial、insufficient evidence、prefill-only handoff、AI 输出审查等限制写成用户可见材料。

输出：

1. `docs/plans/v4_0/active/phase_2/beta_quickstart.md`
2. `docs/plans/v4_0/active/phase_2/known_limitations.md`
3. prerequisites、workflow、timing、expected states、recovery、not supported

验收：

1. quickstart 必须覆盖 happy path 和 degraded path。
2. known limitations 必须进入 quickstart，而不是只留在研究文档。
3. 不允许把 `partial / insufficient_evidence` 写成成功完成。

## WP5：Feedback and Triage Loop

目标：

1. 把 beta feedback 从自由文本变成可分诊队列。
2. 明确 severity、owner、decision 和 carry-forward 规则。

输出：

1. `docs/plans/v4_0/active/phase_2/feedback_triage_template.md`
2. severity taxonomy
3. triage decision rules
4. feedback-to-fix/carry-forward policy

验收：

1. feedback template 至少包含 reporter、workflow step、expected behavior、actual behavior、evidence issue、artifact link、severity、owner、decision。
2. 所有 `blocked` 和 `partial` walkthrough 项都能落入该模板。
3. accepted limitation 与 fix-now 必须可区分。

## WP6：Fresh-state Walkthrough Script

目标：

1. 产出 15-30 分钟可执行 walkthrough。
2. 从 reset 后环境跑一次完整主链，并记录证据。

输出：

1. `docs/plans/v4_0/active/phase_2/fresh_state_walkthrough_script.md`
2. run id 和 reset proof
3. step results：Search / Import / KB / Read / Chat / Notes / Compare / Review
4. evidence artifacts
5. observed limitations
6. triage items

验收：

1. 单次 run 必须从 fresh-state 开始。
2. 每一步必须有 pass / partial / fail。
3. walkthrough 失败时，closeout 只能写 `blocked`，不能写 `controlled-beta-ready`。

## WP7：Controlled Beta Closeout

目标：

1. 汇总 asset gate、fresh-state walkthrough gate、controlled release gate。
2. 给出 `blocked / demo-ready / controlled-beta-ready` 之一的结论。

输出：

1. `docs/plans/v4_0/reports/2026-05-03_v4_0_phase_2_closeout_report.md`
2. go/no-go table
3. carried-forward issues
4. downstream handoff to Phase 3/4/5/6/7

验收：

1. closeout 必须引用具体资产路径和 walkthrough evidence。
2. 不能用历史 Phase D/J 证据替代 fresh-state run。
3. public release verdict 必须明确转交 Phase 4.0-7。

## 6. 当前执行顺序

1. 完成 WP1：Beta asset contract。
2. 完成 WP2：demo dataset。
3. 完成 WP3：demo account / environment reset policy。
4. 完成 WP4：quickstart and known limitations。
5. 完成 WP5：feedback triage loop。
6. 完成 WP6：fresh-state walkthrough script and run。
7. 完成 WP7：controlled beta closeout。

不允许跳过 WP1-W5 直接执行 walkthrough。walkthrough 的意义是验证资产与主链，不是临时探索页面。

## 7. 最小验证

文档与治理：

```bash
bash scripts/check-doc-governance.sh
bash scripts/check-plan-governance.sh
bash scripts/check-phase-tracking.sh
bash scripts/check-governance.sh
```

执行 walkthrough 前的建议 smoke：

```bash
cd apps/web && npm run type-check
cd apps/api && pytest -q tests/unit/test_services.py --maxfail=1
```

如果 walkthrough 触发前端或后端代码修复，必须按改动范围追加：

1. 前端改动：`cd apps/web && npm run type-check`
2. 后端改动：`cd apps/api && pytest -q tests/unit/test_services.py --maxfail=1`
3. API 形态变化：同步检查 `docs/specs/architecture/api-contract.md`
4. 资源状态变化：同步检查 `docs/specs/domain/resources.md`

## 8. 完成定义

Phase 4.0-2 完成时，至少满足：

1. demo dataset、environment policy、quickstart、known limitations、feedback template、walkthrough script 均已落地。
2. fresh-state walkthrough 已执行，并记录 pass / partial / fail。
3. closeout report 给出 `blocked / demo-ready / controlled-beta-ready` 之一。
4. 所有 partial/fail 都进入 feedback triage 或 carry-forward。
5. PLAN_STATUS 与 phase-delivery-ledger 已回填。
6. 没有把 controlled beta 写成 public beta 或 release-pass。

## 9. 边界

1. 不新增复杂 RAG 能力。
2. 不做 Graph / global synthesis / corrective retrieval。
3. 不做前端视觉精修；转交 Phase 4.0-4。
4. 不做响应式、可访问性、性能感知全量扫；转交 Phase 4.0-5。
5. 不做 full release/eval gate；转交 Phase 4.0-7。
6. 不新增根级 doc、tmp、legacy、平行实现目录。

## 10. 风险与处理

| risk | handling |
|---|---|
| demo dataset 依赖外部搜索不稳定 | 固定 query / paper IDs，并记录 fallback |
| reset policy 不完整 | walkthrough 不允许开始，状态保持 `blocked` |
| quickstart 变成营销材料 | 每一步必须绑定 expected state、failure fallback 和 evidence |
| fresh-state walkthrough 失败 | closeout 写 `blocked`，问题进入 feedback triage |
| Phase 2 被扩大成技术升级 | RAG 优化全部转交 Phase 4.0-6 |

## 11. Open Questions

1. demo account 是否使用现有本地测试账号，还是创建 Phase 2 专用账号。
2. demo dataset 是否优先选当前已有 KB 中稳定 paper set，还是重新从 Search 入口构造。
3. walkthrough evidence 是否需要浏览器截图作为硬要求，还是第一波允许手工记录加日志路径。
