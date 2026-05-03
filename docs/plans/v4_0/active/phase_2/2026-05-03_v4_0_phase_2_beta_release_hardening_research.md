---
owner: product-engineering
status: research
depends_on:
  - 20_v4_0_phase_1_execution_plan
  - 19_v4_0_phase_0_execution_plan
last_verified_at: 2026-05-03
evidence_commits:
  - working-tree-v4-0-phase-2-research
---

# v4.0-2 研究文档：Beta Release Hardening

> 日期：2026-05-03  
> 状态：research  
> 上游总览：`docs/plans/v4_0/active/overview/18_v4_0_overview_plan.md`  
> 上游 Phase 0 gate：`docs/plans/v4_0/reports/2026-05-02_v4_0_phase_0_closeout_report.md`  
> 上游 Phase 1 closeout：`docs/plans/v4_0/reports/2026-05-02_v4_0_phase_1_closeout_report.md`

## 1. 研究问题

Phase 4.0-2 的目标是把当前已有主链包装成可演示、可试用、可反馈的 controlled beta。它不是公开发布，也不是新增复杂 RAG 能力。

本阶段需要回答：

1. ScholarAI 当前离 controlled beta 还缺哪些最小资产。
2. Demo dataset、demo account、quickstart、known limitations、feedback channel 和 walkthrough script 应如何定义，才不会虚假放大当前完成度。
3. 哪些 release hardening gate 必须先过，才能允许写成 `beta-ready`。
4. 哪些内容应转交 Phase 4.0-7 测试评测 gate，而不是在 Phase 2 里一次性做完。

## 2. 外部研究依据

| source | 采用结论 | 对 ScholarAI Phase 2 的约束 |
|---|---|---|
| Google SRE Launch Coordination Checklist: https://sre.google/sre-book/launch-checklist/ | launch 前需要覆盖架构、容量、端到端测试、故障处理、监控、访问控制、可重复发布、canary / staged rollout | Beta hardening 不能只写 quickstart；必须同时定义 full-chain walkthrough、失败处理、监控/日志、回滚或暂停口径 |
| Google SRE Production Readiness Review: https://sre.google/sre-book/evolving-sre-engagement-model/ | readiness review 应针对服务自身建立 checklist，并在进入正式 launch 前暴露生产短板 | Phase 2 的 gate 必须 repo-local、ScholarAI-specific，不能套通用发布清单 |
| NIST AI RMF / Generative AI Profile: https://doi.org/10.6028/NIST.AI.600-1 | GAI release 需要 pre-deployment testing、known limits、post-deployment monitoring、外部反馈、incident / change management | Beta materials 必须诚实写出 confabulation、unsupported citation、partial review、evidence quality 和反馈闭环 |
| LaunchDarkly beta testing with feature flags: https://launchdarkly.com/blog/beta-testing-using-feature-flags/ | beta 应支持受控人群、逐步放量、快速关闭、收集用户与性能反馈 | 如果进入云端 beta，必须有 beta access policy、opt-in/out 或等价开关；本地 beta 也必须有 reset / disable 方案 |
| Atlassian product launch guide: https://www.atlassian.com/agile/product-management/product-launch | launch 是 pre-launch、launch、post-launch 的连续过程，需要目标、受众、支持准备、监控和反馈后的快速调整 | Phase 2 需要把 demo 目标、目标用户、support/feedback response owner 和 post-beta triage 写清 |

## 3. Repo 真实输入

Phase 2 不是从空白开始。当前 repo 已有以下上游输入：

1. Phase 0 已定义 Beta minimal asset inventory：
   - demo dataset
   - demo account
   - beta quickstart
   - known limitations
   - feedback channel
   - 15-30 min walkthrough script
2. Phase 0 已诚实保留阻断：
   - 缺一条 fresh-state 单次 `Search -> Import -> KB -> Read -> Chat -> Notes -> Compare -> Review` full-chain walkthrough。
   - 不能把已有 Phase D/J 历史证据写成 full-chain release-pass。
3. Phase 1 已完成第一波 workflow continuity：
   - durable handoff
   - Chat prefill recovery
   - WorkflowHydration waiting-state
   - Dashboard command center handoff command
4. 当前 v3.0 strict closeout 仍保留：
   - review 可能 `partial / insufficient_evidence`
   - compare 有 partial workflow 证据，但不是单次 fresh-state 全链证据
   - Beta / demo release 资产未完成

## 4. Phase 2 定位

Phase 4.0-2 应定义为 controlled beta hardening：

```txt
controlled beta =
repeatable demo dataset
+ resettable demo account/environment
+ truthful quickstart
+ known limitations
+ feedback and triage loop
+ fresh-state walkthrough evidence
+ release/rollback decision rules
```

它不能定义为：

1. public beta launch。
2. full production release。
3. RAG 技术升级 phase。
4. 前端视觉重做 phase。
5. 用文档宣称替代真实 walkthrough 的 phase。

## 4.1 术语边界

Phase 2 后续文档和 closeout 只能使用以下术语：

| term | allowed meaning | forbidden meaning |
|---|---|---|
| `controlled-beta-ready` | 内部或受控试用者可按 quickstart 跑一条明确脚本，并能反馈问题 | 公开 beta、生产可用、无需人工陪跑 |
| `demo-ready` | 指定 dataset / account / walkthrough 可复现 | 任意用户任意数据都能稳定跑通 |
| `fresh-state-pass` | 从重置后的账号/环境执行单次全链并留下证据 | 复用历史 Phase D/J 或局部测试结果 |
| `known-limitation` | 用户可见、可解释、可反馈的当前能力边界 | 隐藏失败或把 partial 说成成功 |
| `release-pass` | 仅由 Phase 4.0-7 或后续 release gate 给出 | Phase 2 自行宣布发布完成 |

这组术语的目的不是降低标准，而是避免 Phase 2 把资产补齐误写成正式发布完成。

## 5. 最小 Beta Asset 研究结论

### 5.1 Demo Dataset

目标是可重复，而不是样本数量大。

最小要求：

1. 至少 1 组 paper set，覆盖 Search / Import / KB / Read / Chat / Notes / Compare / Review。
2. 每个样本记录：
   - source query 或 fixed paper IDs
   - expected import mode
   - expected evidence availability
   - known failure / degraded behavior
   - expected demo talking point
3. 必须包含至少 1 个 evidence-quality 检查点，避免 demo 只验证页面跳转。

建议路径：

1. `docs/plans/v4_0/active/phase_2/demo_dataset.md`
2. 后续如果要机器可读，再补 `artifacts/demo/v4_0_beta_dataset.json`，但研究阶段不强制创建 artifact。

建议字段：

| field | purpose |
|---|---|
| `dataset_id` | 固定样本组标识，避免每次 demo 临时换数据 |
| `source_query_or_ids` | Search/import 的可复现入口 |
| `expected_workflow_steps` | 本样本必须覆盖的页面和动作 |
| `expected_evidence` | 至少一处 citation / evidence 检查点 |
| `known_degraded_cases` | 允许出现 partial 的地方与解释口径 |
| `reset_requirements` | 运行前必须清理或隔离的状态 |

### 5.2 Demo Account / Environment

目标是 resettable。

最小要求：

1. 明确本地 demo、staging demo、或二者的优先级。
2. 明确 fresh-state reset 策略：
   - user id / account
   - KB 清理方式
   - import jobs 清理或隔离方式
   - vector store / artifact 清理边界
3. 明确不能清理的状态，避免把污染状态误认为 fresh demo。

当前建议：

1. Phase 2 第一波先做 local controlled beta。
2. staging/cloud beta 只在 local full-chain walkthrough pass 后进入。

环境策略：

| environment | Phase 2 first-wave status | condition to expand |
|---|---|---|
| local controlled beta | allowed | demo dataset、reset policy、quickstart 和 fresh-state script 齐全 |
| staging controlled beta | gated | local fresh-state run pass，且账号/数据清理策略可重复 |
| public beta | out of scope | 需要 Phase 4.0-7 release/eval gate 或后续 release plan |

### 5.3 Beta Quickstart

目标是让试用者能按真实产品路径完成任务。

最小结构：

1. prerequisites：服务启动、账号、环境变量、demo data。
2. workflow：Search -> Import -> KB -> Read -> Chat -> Notes -> Compare -> Review。
3. timing：哪些步骤应秒级，哪些可能分钟级。
4. expected states：成功、partial、recoverable、blocked。
5. recovery：失败后从哪里恢复、重试、查看日志或回报。
6. not supported：当前不承诺的能力。

### 5.4 Known Limitations

Known limitations 必须显式写，不得只在 closeout 里隐含。

第一批必须包含：

1. Review 可能 partial / insufficient evidence。
2. 首轮 import / indexing 可能较慢。
3. Compare 已接入 workflow 语义，但仍缺单次 fresh-state 全链 release-pass。
4. Chat handoff 是 prefill-only，不自动发送。
5. AI 输出必须看 citation / evidence，不得当作无审查事实。
6. 当前 workflow truth 仍以前端 store + persistence 为主，未升级为后端资源真源。

### 5.5 Feedback Channel

目标不是收集一堆自由文本，而是能转成修复队列。

最小字段：

1. reporter / role
2. workflow step
3. expected behavior
4. actual behavior
5. evidence quality issue
6. screenshot/log/artifact link
7. severity
8. triage owner
9. decision：fix now / carry forward / accepted limitation / duplicate

Phase 2 应先提供 repo-local feedback template；如果进入真实外部 beta，再接入 GitHub issue form、表单或应用内入口。

### 5.6 Walkthrough Script

Phase 2 的 walkthrough script 必须是硬门槛。

最小要求：

1. 15-30 分钟可执行。
2. 包含 happy path 和 degraded path。
3. 每一步记录：
   - page / endpoint
   - action
   - expected state
   - failure fallback
   - evidence artifact
4. 执行后必须产出 closeout report，不能只保留口头结论。

建议证据字段：

| field | requirement |
|---|---|
| `run_id` | 一次 walkthrough 一个唯一编号 |
| `environment` | local / staging / cloud，禁止混用 |
| `reset_proof` | 运行前账号、KB、import job、artifact 状态说明 |
| `step_results` | 每个 workflow step 的 pass / partial / fail |
| `evidence_artifacts` | 截图、日志、测试输出、生成物路径 |
| `limitations_observed` | 本次真实触发的 limitation |
| `triage_items` | 进入反馈/修复队列的问题 |
| `verdict` | `demo-ready` / `controlled-beta-ready` / `blocked` |

## 6. Release Hardening Gate

Phase 2 应采用三层 gate：

| gate | purpose | pass condition | fail action |
|---|---|---|---|
| Asset gate | Beta materials 是否齐全 | demo dataset/account/quickstart/limitations/feedback/walkthrough script 全部存在 | 不允许开始 beta run |
| Fresh-state walkthrough gate | 产品主链是否可演示 | 单次 fresh-state run 覆盖 Search -> Import -> KB -> Read -> Chat -> Notes -> Compare -> Review，并记录 partial / fail | 不允许写 beta-ready |
| Controlled release gate | 是否可给 beta 用户试用 | 访问控制、reset、known limitations、feedback triage、rollback/pause 明确 | 只允许内部 demo，不允许外部 beta |

Phase 2 的 `beta-ready` 只允许表示 controlled beta ready，不等于 public release ready。

## 6.1 Gate 责任边界

| gate item | Phase 2 responsibility | Phase 4.0-7 responsibility |
|---|---|---|
| asset completeness | 定义并补齐 demo dataset/account/quickstart/limitations/feedback/script | 复核资产是否仍匹配 release gate |
| fresh-state walkthrough | 跑通一条受控全链并记录 partial/fail | 扩展成可重复测试矩阵和 release verdict |
| evidence quality | 至少检查一个 citation/evidence 点，记录 unsupported 风险 | 量化 citation coverage、unsupported claim rate、degraded runtime |
| frontend quality | 只检查 walkthrough 是否可执行 | 视觉一致性、响应式、可访问性、性能感知 gate |
| RAG quality | 不做新技术升级，只诚实记录 limitations | 对 Phase 4.0-6 的优化做 baseline/candidate/diff |

## 6.2 Phase 2 产物目录建议

Phase 2 后续执行不应把材料散落到根目录或临时目录。建议固定为：

| artifact | proposed path | owner |
|---|---|---|
| research doc | `docs/plans/v4_0/active/phase_2/2026-05-03_v4_0_phase_2_beta_release_hardening_research.md` | product-engineering |
| execution plan | `docs/plans/v4_0/active/phase_2/21_v4_0_phase_2_execution_plan.md` | product-engineering |
| demo dataset | `docs/plans/v4_0/active/phase_2/demo_dataset.md` | product-engineering |
| demo environment policy | `docs/plans/v4_0/active/phase_2/demo_environment_policy.md` | product-engineering |
| beta quickstart | `docs/plans/v4_0/active/phase_2/beta_quickstart.md` | product-engineering |
| known limitations | `docs/plans/v4_0/active/phase_2/known_limitations.md` | product-engineering |
| feedback template | `docs/plans/v4_0/active/phase_2/feedback_triage_template.md` | product-engineering |
| walkthrough script | `docs/plans/v4_0/active/phase_2/fresh_state_walkthrough_script.md` | product-engineering |
| closeout report | `docs/plans/v4_0/reports/2026-05-03_v4_0_phase_2_closeout_report.md` | product-engineering |

机器可读 artifact 如后续需要，应进入 `artifacts/` 的既有验证/演示命名空间，并确保 `.gitignore` 与治理脚本允许或明确忽略；研究阶段先不创建运行时 artifact。

## 7. 建议 Work Packages

后续执行计划建议拆成六个 WP：

1. WP1：Beta Asset Contract
   - 冻结资产目录、文件命名、必填字段和 pass/fail 口径。
2. WP2：Demo Dataset and Account
   - 产出 demo dataset、demo account/environment policy、reset strategy。
3. WP3：Quickstart and Known Limitations
   - 产出 beta quickstart、known limitations、support / recovery notes。
4. WP4：Fresh-state Walkthrough Script
   - 产出 15-30 分钟脚本和 evidence capture 模板。
5. WP5：Feedback and Triage Loop
   - 产出 feedback template、severity taxonomy、owner SLA。
6. WP6：Controlled Beta Gate
   - 产出 closeout report 模板、go/no-go 规则、rollback/pause 口径。

## 7.1 执行顺序建议

Phase 2 不应先跑 walkthrough，再回头补资产。合理顺序是：

1. 先冻结 asset contract 和术语边界。
2. 再补 demo dataset 与 demo environment reset policy。
3. 然后写 quickstart、known limitations 和 feedback template。
4. 最后写 fresh-state walkthrough script 并执行。
5. 只有 walkthrough 产出证据后，才能写 closeout report。

如果执行中发现主链代码阻断，应按 `blocked` 记录并回到对应模块修复；不得通过修改 quickstart 文案绕过产品缺口。

## 8. 不进入 Phase 2 的内容

1. 不新增第二套 workflow runtime。
2. 不做 Graph / global synthesis / corrective retrieval。
3. 不做 full frontend visual craft；该项转交 Phase 4.0-4。
4. 不做 full responsive / accessibility sweep；该项转交 Phase 4.0-5。
5. 不把 Phase 4.0-7 的完整 release/eval gate 提前吃进 Phase 2。
6. 不承诺 public beta 或 production release。

## 9. 风险

| risk | impact | mitigation |
|---|---|---|
| 用历史 Phase D/J 证据替代 fresh walkthrough | Beta-ready 结论失真 | Phase 2 必须补单次 fresh-state run |
| Beta asset 变成营销文档 | 无法指导试用与问题修复 | 每个资产都必须绑定 workflow step、expected state、failure fallback |
| Known limitations 写得过轻 | 用户误信 AI 输出或误判 partial 成功 | limitations 必须进入 quickstart 和 walkthrough |
| 外部 beta 过早 | support 与 reset 不成熟，反馈无法闭环 | 第一波只允许 local controlled beta，staging 需 gate 通过 |
| Phase 2 扩大成技术升级 | 阶段失焦 | RAG 优化转交 Phase 4.0-6，测试评测转交 Phase 4.0-7 |

## 9.1 Phase 2 到后续阶段的交接

| downstream phase | Phase 2 hands off | not handed off |
|---|---|---|
| Phase 4.0-3 Citation-backed Review Artifacts | known limitations、review partial 证据、citation/evidence 检查点 | Review artifact 产品化实现 |
| Phase 4.0-4 Frontend Experience Craft | walkthrough 中暴露的视觉/状态表达问题 | 全站视觉重做 |
| Phase 4.0-5 Frontend Interaction Quality | walkthrough 中暴露的交互、恢复、响应式问题 | 完整 a11y/performance sweep |
| Phase 4.0-6 Academic RAG Optimization | evidence quality limitation 与 degraded runtime 记录 | 新 RAG 技术实施 |
| Phase 4.0-7 Testing and Evaluation Gate | demo assets、fresh-state evidence、blocked/partial case | public release verdict |

## 10. 研究结论

Phase 4.0-2 可以启动，但必须按 controlled beta hardening 处理。

结论：

1. Phase 2 的首要产物不是代码功能，而是可执行 Beta 资产和 fresh-state walkthrough 证据。
2. Phase 1 已提供 workflow continuity 底座，Phase 2 应消费它来写 demo 和 recovery 路径。
3. 没有单次 fresh-state full-chain walkthrough 之前，不允许写 `beta-ready`。
4. Beta quickstart 必须同时写 happy path、partial path、known limitations 和 feedback path。
5. Phase 2 完成后，应只解锁 controlled beta；public release verdict 仍交给 Phase 4.0-7。
