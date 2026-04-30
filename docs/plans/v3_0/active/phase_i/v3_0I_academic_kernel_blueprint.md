# v3.0I Academic Kernel Blueprint

> 日期：2026-04-30  
> 状态：blueprint-draft  
> 上游：`docs/plans/v3_0/active/phase_i/v3_0I_framework_decision_matrix.md`  
> 目的：冻结 ScholarAI 自有 academic-custom RAG kernel 的对象、模块、双核结构与层级边界。

## 1. 蓝图结论

ScholarAI 的 academic-custom RAG framework 不应围绕某个外部框架的对象建模，而应围绕 ScholarAI 自己的领域对象建模。

核心原则：

```txt
thin adapters
+ strong domain kernel
+ local/global dual retrieval kernel
+ claim-centered truthfulness layer
+ orchestration and optimization as subordinate layers
```

## 2. 顶层模块图

建议的顶层模块关系：

```txt
Input / Workflow Entry
-> Task Taxonomy Router
-> Academic Kernel
   -> Local Evidence Retrieval Kernel
   -> Global Synthesis Kernel
   -> Claim Truthfulness Layer
-> Synthesis Interface
-> Output Contracts
-> Trace / Validation / Benchmark Hooks
```

## 3. 核心对象冻结

## 3.1 Domain Objects

以下对象属于 ScholarAI 自有领域核心，不允许被外部框架抽象替代：

1. `Paper`
   - 论文实体
   - 负责 paper identity、metadata、parse lineage
2. `EvidenceCandidate`
   - retrieval 阶段候选证据
3. `EvidenceBlock`
   - UI / synthesis / review 使用的显式证据块
4. `AnswerClaim`
   - claim truthfulness 的核心对象
5. `AnswerCitation`
   - citation jump、quote、offset、source identity
6. `CompareMatrix`
   - multi-paper compare 真源
7. `ReviewRun`
   - review orchestration 与结果跟踪真源
8. `ValidationRun`
   - benchmark / Phase D / release consumption 真源

## 3.2 Object Lifecycle

建议对象生命周期冻结为：

```txt
Paper
-> parse artifacts / section summaries / relation artifacts
-> EvidenceCandidate
-> EvidenceBlock
-> AnswerClaim
-> CompareMatrix / ReviewDraft / AnswerContract
-> ValidationRun
```

## 4. Task Taxonomy Router

在任何 retrieval 或 generation 之前，先做任务分类。

最低冻结任务族：

1. `single_paper_fact`
2. `single_paper_method`
3. `single_paper_table_figure`
4. `compare`
5. `cross_paper`
6. `survey / related_work`
7. `conflicting_evidence`
8. `hard`

路由职责：

1. 决定走 `local kernel` 还是 `global kernel`
2. 决定是否启用 `claim truthfulness`
3. 决定是否进入 `heavy synthesis`
4. 决定使用 `flash` 还是 `pro` retrieval policy

## 5. Local Evidence Retrieval Kernel

## 5.1 目标

服务局部、高精度、可回证据位置的问题。

典型任务：

1. 单篇论文问答
2. compare cell filling
3. citation jump support
4. claim repair evidence retrieval

## 5.2 输入

1. `query`
2. `query_family`
3. `paper_scope`
4. `section constraints`
5. `content_type constraints`

## 5.3 输出

1. `EvidenceCandidate[]`
2. `EvidencePack`
3. diagnostics

## 5.4 设计原则

1. 先证据，再生成
2. 先局部精确，再考虑全局总结
3. retrieval 结果必须天然可映射到 `EvidenceBlock`

## 6. Global Synthesis Kernel

## 6.1 目标

服务综述、趋势、taxonomy、evolution、gap finding 等全局任务。

典型任务：

1. review draft
2. related work
3. method evolution
4. contradiction / gap synthesis

## 6.2 输入

1. `research_question`
2. `paper_scope`
3. `theme hints`
4. `outline plan`

## 6.3 输出

1. `OutlineDoc`
2. section-wise evidence bundles
3. synthesized sections / review draft
4. coverage report

## 6.4 设计原则

1. 先 outline，再 section retrieval，再 synthesis
2. 不直接依赖重型 graph-first 实现
3. 第一版允许：
   - `STORM-lite`
   - hierarchical retrieval
   - evidence coverage checks
4. `GraphRAG / OpenScholar` 只作为增强实验支线

## 7. Claim-centered Truthfulness Layer

## 7.1 目标

让 `claim` 成为 academic kernel 的第一等对象，而不是 review 的附属字段。

## 7.2 子模块

1. `ClaimExtractor`
2. `ClaimLinker`
3. `ClaimVerifier`
4. `ClaimRepairer`
5. `TruthfulnessReportBuilder`

## 7.3 输入输出

输入：

1. `text / draft / answer`
2. `EvidenceBlock[]`

输出：

1. `AnswerClaim[]`
2. `support_status`
3. `support_score`
4. `repair_hint`
5. `supporting_source_chunk_ids`

## 7.4 原则

1. compare / review / chat 都共享同一层 truthfulness substrate
2. verifier baseline 可以简单，但 contract 不能简单
3. unsupported claim 必须显式 surfacing

## 8. Synthesis Interface

academic kernel 不直接绑定具体 generation LLM，而是通过统一 synthesis interface 输出。

接口职责：

1. answer synthesis
2. review paragraph synthesis
3. repair rewrite

要求：

1. 能消费 `EvidenceBlock`
2. 能消费 `AnswerClaim`
3. 不能绕过 evidence contract
4. 可以替换底层 generation LLM，而不改 kernel

## 9. Orchestration Layer

这是从属层，不是领域真源。

职责：

1. step ordering
2. checkpoint / resume
3. retries
4. HITL
5. long-running workflow state

不负责：

1. evidence semantics
2. claim truth
3. compare/review core object definitions

## 10. Optimization Layer

这也是从属层。

职责：

1. prompt / program optimization
2. route selection tuning
3. synthesis quality tuning

不负责：

1. 重定义 academic task taxonomy
2. 重定义 evidence ontology
3. 侵入 runtime truth contract

## 11. Benchmark Hooks

kernel 设计必须天然可被 benchmark。

至少要暴露：

1. `task_family`
2. `retrieval_mode`
3. `generation_mode`
4. `claim_support_metrics`
5. `citation_fidelity_metrics`
6. `coverage metrics`
7. `cost / latency`

## 12. 实施顺序冻结

按当前方案，kernel 落地顺序应为：

1. `Paper / Evidence / Claim / Compare / Review` 对象冻结
2. `local retrieval kernel`
3. `claim truthfulness layer`
4. `STORM-lite global kernel`
5. `hierarchical retrieval`
6. `adaptive routing`
7. `graph/global enhancement experiments`

## 13. 禁止事项

1. 不允许把外部框架对象直接当成 ScholarAI 核心对象。
2. 不允许把 generation LLM 写死进 academic kernel。
3. 不允许让 orchestration 层反向定义领域语义。
4. 不允许在没有 benchmark hook 的情况下把实验路线升为主线。
