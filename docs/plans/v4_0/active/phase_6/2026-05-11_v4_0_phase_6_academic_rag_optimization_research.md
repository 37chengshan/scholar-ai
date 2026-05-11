---
owner: ai-runtime
status: research
depends_on:
  - 22_v4_0_phase_3_execution_plan
  - 18_v4_0_overview_plan
last_verified_at: 2026-05-11
evidence_commits:
  - working-tree-v4-0-phase-6-research
---

# v4.0 Phase 4.0-6 研究文档：Academic RAG Optimization

> 日期：2026-05-11  
> 状态：research  
> 上游总览：[docs/plans/v4_0/active/overview/18_v4_0_overview_plan.md](docs/plans/v4_0/active/overview/18_v4_0_overview_plan.md)  
> 上游决策记录：[docs/plans/v4_0/search/2026-05-02_v4_0_research_decision_note.md](docs/plans/v4_0/search/2026-05-02_v4_0_research_decision_note.md)  
> 上游框架冻结：[docs/plans/v3_0/active/phase_i/v3_0I_framework_decision_matrix.md](docs/plans/v3_0/active/phase_i/v3_0I_framework_decision_matrix.md)  
> 上游 kernel 蓝图：[docs/plans/v3_0/active/phase_i/v3_0I_academic_kernel_blueprint.md](docs/plans/v3_0/active/phase_i/v3_0I_academic_kernel_blueprint.md)

## 1. 研究问题

Phase 4.0-6 的目标不是“换一个更强的 RAG 框架”，而是在 ScholarAI 已稳定的研究工作流主链之上，增加可解释、可回滚、可评测的学术 RAG 优化能力。

本阶段需要回答：

1. 在不新增第二套 agent runtime 的前提下，哪些 academic RAG 优化最值得接入现有主链。
2. corrective retrieval、claim repair、hierarchical retrieval、graph/global synthesis 分别应该落在哪些路径，哪些路径明确不能进入。
3. 哪些外部方案适合 adopt，哪些只适合 extend 或 experiment，哪些应明确 reject。
4. Phase 6 的优化怎样与 Phase 7 的 baseline/candidate/diff/verdict 测试门禁直接对接。

## 2. 阶段边界

本阶段继承 v4.0 总览中已冻结的硬边界：

1. 只优化稳定主链，不替代产品主链。
2. 不训练 Self-RAG 同款模型。
3. 不整仓迁移外部框架。
4. 不新增第二套 agent runtime。
5. Graph / global synthesis 只允许进入 Review / Survey / Related Work 支线，不替代 fact-level RAG。
6. 所有新增能力必须同时暴露用户可见状态、内部 run artifact、fallback 语义与可恢复动作。

因此，Phase 6 的执行口径必须是：

```txt
extend the current kernel
+ expose explicit evidence actions
+ make retrieval correction observable
+ keep graph/global as review-only experiment
- do not hand runtime control to an external framework
```

## 3. Repo 真实基线

ScholarAI 不是从零开始做 academic RAG。当前仓库已有可复用基线：

1. v3.0 Phase I 已冻结 adopt / extend / experiment / reject 矩阵，并明确保留 domain kernel 真源，不允许外部框架吞掉 `Paper`、`EvidenceBlock`、`AnswerClaim`、`ReviewRun` 等对象。
2. v3.0 Phase I 已冻结 `local retrieval`、`global synthesis`、`claim-centered truthfulness` 的三层结构，但 GraphRAG、STORM full stack、training-centric Self-RAG 都被后置。
3. v3.0 Phase J 已把 comparative benchmark、verdict JSON、diff JSON 和 markdown report 变成现有 gate 结构。
4. 当前后端已有关键挂点可扩展：
   - [apps/api/app/core/retrieval_evaluator.py](apps/api/app/core/retrieval_evaluator.py)
   - [apps/api/app/core/retrieval_trace.py](apps/api/app/core/retrieval_trace.py)
   - [apps/api/app/core/claim_verifier.py](apps/api/app/core/claim_verifier.py)
   - [apps/api/app/services/truthfulness_service.py](apps/api/app/services/truthfulness_service.py)
   - [apps/api/app/core/graph_retrieval_service.py](apps/api/app/core/graph_retrieval_service.py)
   - [apps/api/app/rag_v3/retrieval/hierarchical_retriever.py](apps/api/app/rag_v3/retrieval/hierarchical_retriever.py)
5. 当前依赖也表明仓库已经接受“吸收局部能力、不交出主控权”的策略：
   - [apps/api/requirements.txt](apps/api/requirements.txt) 已包含 `paper-qa`。
   - [apps/api/requirements.txt](apps/api/requirements.txt) 已包含 `llama-index-core`。

结论是：Phase 6 不需要重新选一个总框架，而是要把现有 kernel、trace、truthfulness 与 review pipeline 再向前推一层。

## 4. 外部研究依据

| source | 核心结论 | 对 ScholarAI 的直接含义 |
|---|---|---|
| CRAG: https://arxiv.org/abs/2401.15884 | 检索质量应先被 evaluator 评估，再决定 rewrite、retry、扩展检索或过滤重组 | 适合做 CRAG-lite，只吸收 evaluator + action policy，不照搬其 web search 假设 |
| Self-RAG: https://arxiv.org/abs/2310.11511 | retrieval 是否必要、证据是否足够、生成是否可靠，应被显式反思与控制 | 只吸收 need-retrieval、abstain、critique policy，不走训练与 reflection token 路线 |
| GraphRAG: https://arxiv.org/abs/2404.16130 | graph-based global summarization 更适合回答整个 corpus 的全局问题，而非局部事实问题 | 只允许进入 Review / Survey / Related Work，不能替代 fact / method / numeric 主链 |
| Ragas docs: https://docs.ragas.io/ | eval 应以 experiments、metrics、datasets 和工作流闭环为中心，而不是 vibe check | 更适合接 Phase 7 评测层，不适合接入 Phase 6 在线主链 |
| PaperQA2 repo: https://github.com/Future-House/paper-qa | evidence-first scientific QA、metadata-aware 检索、上下文摘要、citation-backed answer 已形成成熟模式 | 适合继续吸收模式和局部实现经验，但不能让其 Docs/agent 模型接管 ScholarAI domain kernel |

补充判断：

1. 外部研究的共同结论不是“统一迁移到单一框架”，而是“把 evidence gathering、retrieval correction、claim verification 和 review synthesis 这些动作拆明白”。
2. 对 ScholarAI 来说，最有价值的不是新建一个 agent 系统，而是让当前 `Search -> Import -> KB -> Read -> Chat -> Notes -> Compare -> Review` 的每一跳都拥有更清楚的证据动作与降级语义。

## 5. 候选技术决策矩阵

| candidate | category | fit | integration_cost | observability | lock_in_risk | decision | notes |
|---|---|---:|---:|---:|---:|---|---|
| CRAG-style retrieval evaluator | retrieval correction | 高 | 中 | 高 | 低 | extend | 最适合优先接入。把 retrieval confidence、rewrite、retry、filter/recompose 接到现有 evaluator 和 trace。 |
| Self-RAG policy | runtime policy | 中高 | 低 | 高 | 低 | extend | 只吸收 need-retrieval、abstain、critique 的策略层，不做模型训练。 |
| claim verification + repair loop | truthfulness layer | 高 | 中 | 高 | 低 | adopt-pattern | 与现有 truthfulness substrate 连续性最高，应成为 Chat / Compare / Review 共用能力。 |
| citation-backed rewrite | answer repair | 高 | 中 | 高 | 低 | extend | 适合把 unsupported claim 从静态诊断升级为可执行修复动作。 |
| RAPTOR-lite hierarchical retrieval | long-doc retrieval | 高 | 中 | 中 | 低 | extend | 适合学术长文、跨论文 compare 和 review draft，但不应强制所有 query 走分层索引。 |
| PaperQA2 pattern | scientific evidence workflow | 高 | 中 | 中 | 中 | extend | 吸收 evidence-first、metadata-aware、contextual summarization；不让其 agent runtime 接管主链。 |
| Ragas | evaluation | 中高 | 低 | 高 | 低 | adopt | 放到 Phase 7 测试评测门禁，不进入在线回答路径。 |
| LlamaIndex pattern | orchestration/index pattern | 中 | 中 | 高 | 中 | extend | 可借鉴 query path、workflow instrumentation、解析与索引经验，不做全量切换。 |
| Haystack pattern | pipeline pattern | 中 | 高 | 高 | 中 | extend-pattern | 更适合吸收显式 pipeline 与 serialization 思路，不适合在本阶段新引入主 runtime。 |
| DSPy | offline optimization | 中 | 中高 | 中 | 中 | experiment | 只适合离线优化 prompt、阈值或 route，不得进入 serving path。 |
| LangGraph | durable orchestration | 中 | 高 | 高 | 高 | reject-for-runtime | 可以借鉴模式，但不能在当前仓库里形成第二套 agent runtime。 |
| GraphRAG | global synthesis | 中 | 高 | 中 | 高 | experiment | 只允许在 Review / Survey / Related Work 做受控实验。 |
| LightRAG | graph-enhanced RAG server | 低到中 | 很高 | 中 | 高 | reject | 更像独立服务与栈，不适合接管 ScholarAI 稳定主链。 |

## 6. Phase 6 推荐实施顺序

### 6.1 第一优先级：统一 evidence action contract

先统一 Chat、Compare、Review 共享的“下一步动作”结构，而不是先接入新框架。建议 contract 至少能表达：

1. 继续检索。
2. 改写 query 后重检。
3. 进入 claim verification。
4. 进入 citation repair。
5. 因证据不足而降级答复。
6. 引导用户回到 Read / Compare / Review 的具体恢复入口。

这一步是所有优化的前置，因为没有统一 action contract，后续 corrective retrieval 和 repair loop 只能变成散落在各端点里的特例逻辑。

### 6.2 第二优先级：接入 CRAG-lite corrective retrieval

在现有 retrieval plane 上新增受控纠偏，而不是把所有请求都升级成 agentic loop。建议只对高价值 query family 开启：

1. `compare`
2. `cross_paper`
3. `survey / related_work`
4. `conflicting_evidence`
5. `single_paper_table_figure` 或 `numeric` 等高风险定位类问题

建议行为：

1. 先产出 retrieval confidence。
2. confidence 低时只允许一次额外 corrective round。
3. corrective round 只能在 rewrite、filter/recompose、扩 scope、降级答复之间选择，不允许无上限递归。
4. 每次 corrective 行为都必须进入 retrieval trace。

### 6.3 第三优先级：把 unsupported claim 升级为 repair loop

现有 truthfulness layer 已有基础，Phase 6 应该把它从“报告字段”升级成“可执行修复流程”：

1. 先做 claim extraction 与 support judgment。
2. 再针对 unsupported / weakly supported claim 触发 citation repair 或 rewrite。
3. 若修复失败，最终输出应保留 abstain / insufficient evidence，而不是继续生成看似完整但不可支撑的段落。

### 6.4 第四优先级：引入 RAPTOR-lite hierarchical retrieval

对长文和跨论文综述，单层 chunk 检索很容易在 recall、section hit 和长程结构上失真。Phase 6 应优先尝试 paper / section / chunk 三层摘要与检索，而不是一次性引入重型全局图谱。

建议范围：

1. review draft
2. survey / related work
3. compare matrix 的长段落填充
4. 单篇长论文的 method / ablation / appendix 追踪

### 6.5 第五优先级：Review-only global synthesis experiment

Graph / global synthesis 可以进入 Review / Survey / Related Work，但必须满足：

1. graph 不参与单点事实问答默认路径。
2. graph 不可用时能显式 fallback 到 local-only。
3. fallback 与 degraded state 必须进入 trace 和质量字段。
4. 若 Phase 7 不能证明收益，则只能保留 experiment-only，不进入 release-pass。

## 7. 明确不做的事项

Phase 6 明确不做以下内容：

1. 不训练 Self-RAG 同款模型，不引入 reflection token 路线。
2. 不把 GraphRAG 或 LightRAG 变成默认检索主链。
3. 不引入 LangGraph 作为新的运行时真源。
4. 不把 PaperQA2、LlamaIndex、Haystack 任一外部框架升级为产品主框架。
5. 不让 DSPy 直接进入 serving path。
6. 不做 default-all-query 的 multi-hop / IRCoT 式循环。
7. 不把 graph/global synthesis 扩大到 fact、table、figure、numeric 等局部证据路径。

## 8. 对接 Phase 7 的评测假设

Phase 6 的优化必须天然服务 Phase 7 gate。建议 Phase 7 至少验证以下假设：

| hypothesis | target scope | primary metrics | pass direction |
|---|---|---|---|
| H1: CRAG-lite 降低高价值 query family 的 unsupported claim | compare / cross_paper / survey | unsupported_claim_rate, citation_coverage, second_pass_gain | unsupported claim 下降，citation coverage 不下降 |
| H2: claim repair 能提升可支撑段落比例 | chat / compare / review | supported_claim_count, unsupported_claim_count, repair_success_rate | supported claim 上升，repair 成功率可解释 |
| H3: RAPTOR-lite 提升长文与综述检索质量 | long paper / review draft | recall@10, MRR, section_hit_rate, paper_hit_rate | 在长文本族上相对 baseline 正收益 |
| H4: degraded surfacing 提升可恢复性 | all optimized paths | degraded_rate, recovery_action_exposed_rate, silent_fallback_count | silent fallback 必须归零，recovery action 暴露率提升 |
| H5: review-only graph synthesis 在综述任务上有收益 | review / survey / related_work | comprehensiveness, diversity, citation_faithfulness, cost, latency | 仅当综述路径收益明确且成本可控，才可进入 experiment-only 以上结论 |

建议同步跟踪的指标维度：

1. Retrieval 侧：`recall@5`、`recall@10`、`MRR`、`section_hit_rate`、`paper_hit_rate`、`second_pass_gain`
2. Truthfulness 侧：`unsupported_claim_rate`、`supported_claim_count`、`citation_coverage`、`citation_faithfulness`
3. Runtime 侧：`p50/p95 latency`、`cost_estimate`、`degraded_rate`、`silent_fallback_count`
4. Workflow 侧：Search -> Import -> KB -> Read -> Chat、KB -> Review、Compare 三条链路成功率
5. Diagnostics 侧：failure bucket 分布、repair success rate、answer mode 分布

## 9. 关键风险与规避策略

| risk | why it matters | mitigation |
|---|---|---|
| 外部框架接管主链 | 一旦把 runtime 真源交给框架，现有 domain kernel、trace 与 rollback 会失去唯一真源 | 锁定 ScholarAI domain kernel 为唯一真源；外部只做 adapter、pattern source 或离线实验 |
| corrective retrieval 过度重试 | evaluator 阈值不稳会直接放大 latency 和 cost | 只在高价值 family 开启；最多 1 次额外 corrective round；所有动作进 retrieval trace |
| graph/global synthesis 污染事实主链 | graph 路线适合综述，但容易损害局部证据路径的精确性 | graph 只允许 Review / Survey / Related Work 触发，且必须有 local-only fallback |
| 观测字段不完整 | 没有 trigger reason、action taken、fallback、cost/latency，就无法进 comparative gate | 任何新动作都必须同步生成 trace、quality、recovery hooks |
| 离线优化与在线路径耦合过深 | DSPy 或复杂 prompt 优化一旦直连 serving，会降低行为可解释性 | 把优化器限定在离线 benchmark loop；线上只消费冻结后的阈值、模板和策略 |

## 10. 研究结论

Phase 6 最合理的总策略不是“上一个更强框架”，而是：

```txt
主链：extend
综述支线：experiment
评测层：adopt
第二套 runtime 与整仓迁移：reject
```

更具体地说：

1. 主链优先做 `evidence action contract -> CRAG-lite -> claim repair -> RAPTOR-lite`。
2. graph/global synthesis 仅作为 review-only experiment 存在。
3. Phase 6 的每个新增能力都必须先回答：优化哪类 task family、改善哪类指标、增加多少 latency/cost、失败时如何回滚。
4. 没有 baseline/candidate/diff/verdict 的优化，一律不能写成收益成立。

## 11. 下一步

研究完成后，下一步应进入 Phase 6 执行计划，而不是重新做框架选型。执行计划应至少冻结：

1. evidence action contract 的字段与消费方。
2. CRAG-lite 的触发条件、最大 corrective round 与 trace 字段。
3. claim repair 的输入输出契约与失败降级语义。
4. RAPTOR-lite 的索引范围、触发 query family 与 fallback 语义。
5. graph/global synthesis experiment 的唯一入口、回滚条件与 Phase 7 验收门槛。