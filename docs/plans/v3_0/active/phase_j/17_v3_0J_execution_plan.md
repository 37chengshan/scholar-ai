# 17 v3.0-J 执行计划：RAG Benchmark 与 Comparative Gate

> 日期：2026-04-30  
> 状态：execution-plan  
> 上游研究：`docs/plans/v3_0/active/phase_j/2026-04-30_v3_0J_RAG_Benchmark_研究文档.md`  
> 文档前提：按当前仓库真实脚本与 `Phase H/I` 已冻结 hook 来组织执行，默认 comparative gate 先服务线上基线、Truth + Route 候选和 release consume

## 1. 目标

`Phase J` 的执行目标是把 `RAG benchmark + comparative gate` 从研究结论推进成可实施的评测主链，形成：

```txt
benchmark taxonomy freeze
-> comparative run schema
-> baseline / candidate / diff runbook
-> real-world workflow suite integration
-> gate threshold proposal
-> release / phase consumption
```

## 2. 执行前先读什么

执行者开始前，按以下顺序读取：

1. `docs/plans/v3_0/active/overview/06_v3_0_overview_plan.md`
2. `docs/plans/v3_0/active/phase_a/07_v3_0A_execution_plan.md`
3. `docs/plans/v3_0/active/phase_d/10_v3_0D_execution_plan.md`
4. `docs/plans/v3_0/active/phase_h/15_v3_0H_execution_plan.md`
5. `docs/plans/v3_0/active/phase_i/16_v3_0I_execution_plan.md`
6. `docs/plans/v3_0/active/phase_j/2026-04-30_v3_0J_RAG_Benchmark_研究文档.md`
7. `scripts/evals/run_phase_j_comparative_gate.py`
8. `apps/api/tests/unit/test_phase_j_comparative_gate.py`
9. `apps/api/app/rag_v3/main_path_service.py`
10. `apps/api/app/services/compare_service.py`
11. `apps/api/app/services/review_draft_service.py`

执行规则：

1. 先冻结 benchmark consume contract，再接真实 run。
2. 先比较 baseline / candidate 的 mode parity，再讨论候选收益。
3. 不允许只跑 offline retrieval 指标就宣称候选可替代主链。
4. 不允许 candidate 缺少 `Phase H/I` hook 仍参与 comparative verdict。
5. `Phase A` 提供 academic benchmark 资产，`Phase D` 提供真实 workflow 验证，`Phase J` 负责把两者收成统一对比门禁。
6. comparative verdict 必须区分 `experiment-only` 与 `release-pass`，避免研究信号和上线信号混用。

## 3. 范围

### 包含

```txt
1. comparative benchmark taxonomy
2. baseline / candidate / diff payload schema
3. hook completeness gate
4. real-world workflow success 接入 comparative suite
5. threshold proposal 与 verdict policy
6. Phase H / Phase I / release gate 的统一 consume 规则
7. experiment-only / release-pass verdict split
```

### 不包含

```txt
1. 新 academic corpus 采集与 blind set 扩容
2. 新模型供应商或新框架默认接入
3. STORM / GraphRAG / 强 verifier 的实现本身
4. 替代 Phase D 的真实工作流执行职责
```

## 4. Work Packages

## WP0：Benchmark Taxonomy Freeze

目标：

1. 冻结 `Phase J` 要比较的维度和 case bucket。
2. 明确哪些结果来自 academic benchmark，哪些来自 real-world workflow。

输出：

1. benchmark taxonomy
2. case bucket map
3. suite ownership map

验收：

1. 每条 comparative run 都能映射到固定 taxonomy，而不是自由拼 case。

执行方式：

1. 以 `Phase A` family / modality / answerability 切片为 academic benchmark 真源。
2. 以 `Phase D` workflow run 结果为 real-world suite 真源。
3. 把 `retrieval / truthfulness / review / runtime / workflow success` 明确拆成固定 compare 维度。

## WP1：Comparative Run Contract Freeze

目标：

1. 冻结 baseline / candidate / diff payload 字段。
2. 把 `Phase H/I` 输出 hook 正式变成 gate 输入契约。

输出：

1. comparative run schema extension
2. required hook checklist
3. normalization rules
4. verdict class definitions

验收：

1. `scripts/evals/run_phase_j_comparative_gate.py` 不再依赖隐式字段猜测。
2. 缺 hook、mode parity 不一致、case set 不一致时有明确 verdict class，而不是只输出模糊失败。

执行方式：

1. 把 `task_family / execution_mode / truthfulness_report_summary / retrieval_plane_policy / degraded_conditions` 固定为 required。
2. 同时固定 `citation_coverage / unsupported_claim_rate / total_latency_ms / cost_estimate` 的提取优先级。
3. baseline 与 candidate 若 case set 不一致，直接 fail，不做“尽量比较”。
4. mode parity 不一致时，只允许输出 `experiment-only`，不允许输出 release pass。

## WP2：Baseline / Candidate / Diff Runbook

目标：

1. 定义如何产出 baseline run、candidate run 和 diff verdict。
2. 让研发能用同一 runbook 比较线上基线与候选框架。

输出：

1. comparative runbook
2. baseline naming rule
3. candidate naming rule
4. diff verdict flow
5. parity declaration rule

验收：

1. 不同执行者能按同一顺序产出可比较结果。
2. baseline / candidate 的研究试验结果与 release 判定结果不会混在一份 verdict 里。

执行方式：

1. baseline 必须先声明 dataset_version、runtime mode、provider identity。
2. candidate 必须声明与 baseline 的 mode parity。
3. diff verdict 必须同时输出 metric delta、missing hook 状态和 degraded rate。
4. baseline / candidate 若只具研究可比性但不具 release 可比性，必须落到 `experiment-only`。

## WP3：Real-world Workflow Suite Integration

目标：

1. 把 `Phase D` 的真实 workflow 结果纳入 comparative gate。
2. 避免 benchmark 只看离线 academic case。

输出：

1. workflow success consume rule
2. workflow artifact adapter
3. failure bucket alignment

验收：

1. comparative verdict 可同时反映学术离线指标和真实工作流成功率。

执行方式：

1. 复用 `Phase D` 已有 workflow run / failure bucket 结构。
2. 明确 `Search -> Import -> KB -> Read -> Chat`、`KB -> Review`、`Compare` 至少进入首批 suite。
3. 若 workflow artifact 缺少 `Phase H/I` hook，视为未达 comparative consume 条件。

## WP4：Gate Threshold Proposal

目标：

1. 冻结首批 comparative gate 的回退阈值和通过条件。
2. 避免后续每次比较都临时讨论“多少算退化”。

输出：

1. threshold proposal
2. fail / warn / pass policy
3. release-consume rule
4. calibration hook backlog

验收：

1. 候选是否通过 comparative gate 有明确规则，而不是人工口头判断。
2. 首批阈值虽保守，但后续可接入人工标注或更强 judge 做 calibration，而不破坏主 contract。

执行方式：

1. `unsupported_claim_rate` 默认不得显著回退。
2. `citation_coverage` 默认不得回退。
3. `latency / cost / degraded_rate` 允许预算内回归，但必须固定阈值来源。
4. 若 mode parity 不一致，仅允许生成 experiment verdict，不允许生成 release pass verdict。
5. 首批不把大规模人工标注设为前置阻塞，但要保留 calibration hook 给后续 verifier / judge 升级。

## WP5：Phase Consume and Reporting

目标：

1. 让 `Phase H`、`Phase I` 和 release gate 能稳定消费 `Phase J` verdict。
2. 让报告产物不只停留在 JSON。

输出：

1. gate summary artifact
2. markdown summary
3. phase consume mapping
4. verdict class annotation

验收：

1. `Phase H` 可用它判断 online baseline 是否稳定。
2. `Phase I` 可用它判断候选 truth / route 改动是否值得升级。
3. release gate 可用它判断候选是否具备替代资格。
4. research trial 与 release-qualified candidate 有明确区分。

执行方式：

1. summary 同时输出 overall verdict 和 per-bucket diff。
2. 明确哪些 verdict 只属于 research signal，哪些属于 release signal。
3. 任何 pass 结论都必须附带 baseline / candidate case set 一致性声明。
4. release-consume summary 必须显式说明是否存在 `experiment-only` case。

## 5. 实际执行顺序

执行者按以下顺序推进，不按周数推进：

1. `WP0 Benchmark Taxonomy Freeze`
2. `WP1 Comparative Run Contract Freeze`
3. `WP2 Baseline / Candidate / Diff Runbook`
4. `WP3 Real-world Workflow Suite Integration`
5. `WP4 Gate Threshold Proposal`
6. `WP5 Phase Consume and Reporting`

原因：

1. taxonomy 不冻，suite 会持续漂移。
2. contract 不冻，脚本只能做脆弱兼容。
3. runbook 不定，baseline / candidate 无法稳定比较。
4. workflow 不接入，comparative gate 仍然只是一半真相。
5. 若不先拆开 `experiment-only` 与 `release-pass`，后续 PR / release 审核会继续混淆研究收益与上线资格。

## 6. 下层文档

1. `docs/plans/v3_0/active/phase_j/2026-04-30_v3_0J_RAG_Benchmark_研究文档.md`
2. `docs/plans/v3_0/active/phase_j/v3_0J_execution_plan_review.md`
3. `scripts/evals/run_phase_j_comparative_gate.py`
4. `apps/api/tests/unit/test_phase_j_comparative_gate.py`

## 7. 验收标准

Phase J P0 可视为完成，当且仅当：

1. comparative gate taxonomy 冻结。
2. baseline / candidate / diff 的字段与 case set 规则冻结。
3. academic benchmark 与 real-world workflow 都有明确 consume 入口。
4. threshold proposal 已写成正式规则，而不是口头约定。
5. `Phase H`、`Phase I`、release gate 都知道自己如何消费 `Phase J` verdict。
6. `experiment-only` 与 `release-pass` 已形成正式区分规则。

## 8. 风险

1. 若 `Phase A` artifact 结构继续变化，`Phase J` consume contract 会反复返工。
2. 若 `Phase D` workflow artifact 仍缺关键 hook，真实工作流会继续游离在 comparative gate 之外。
3. 若 `Phase H` mode truth 不稳定，baseline / candidate 的 parity 结论会失真。
4. 若阈值提议没有明确来源，gate 很容易退化成主观判断。
5. 若 calibration hook 没有预留，首批阈值会难以升级。
