---
标题：ScholarAI v3.0-I 学术化定制 RAG 框架研究文档
日期：2026-04-30
状态：research
范围：前沿 RAG 技术研究、优秀开源框架拆解、academic-custom framework blueprint、adopt/extend/experiment/reject 决策矩阵
前提：本文件按“Phase H 已完成、RAG 主链已具备 online-first runtime truth”来组织研究；不代表当前仓库已经拥有完整的学术化框架
---

# 1. 研究目标

本文件定义 ScholarAI `v3.0-I: Academic-custom RAG Framework` 的研究方案。

它回答的核心问题不是：

```txt
要不要换成某个热门 RAG 框架。
```

而是：

```txt
在 Phase H 已把运行时主链收口为 online-first 之后，
ScholarAI 应该如何吸收前沿 RAG 技术与优秀开源框架，
形成真正服务学术阅读、比较、综述、claim verification 的自有框架。
```

本文件只定义：

1. 当前 ScholarAI 学术任务的结构性需求
2. 关键外部框架和技术路线的真实能力边界
3. ScholarAI 应吸收、扩展、实验或拒绝的部分
4. academic-custom framework 的蓝图与阶段性 adoption 顺序

本文件不直接展开到逐文件改造、最终模型选型或一次性大重构。

## 1.1 当前已知模型栈约束

`Phase I` 默认继承 `Phase H` 已冻结的当前线上模型栈约束：

1. retrieval plane：
   - `Qwen flash/pro`
   - `Qwen rerank`
   - `Milvus`
2. generation plane：
   - `glm-4.5-air`

这意味着 `Phase I` 研究的重点不是“重新决定主模型供应商”，而是：

1. 如何在这套已知线上栈之上构建 academic-custom framework
2. 如何让框架支持未来替换 generation plane，而不重写 retrieval / evidence kernel

# 2. 执行摘要

`Phase I` 的研究结论先放前面：

```txt
ScholarAI 不适合直接“选择一个通用框架全盘接管”。

更合理的方向是：
以 ScholarAI 自研 academic RAG kernel 为主，
吸收 LangGraph 的状态编排，
LlamaIndex / Haystack 的数据与组件化思路，
PaperQA 的学术证据工作流，
DSPy 的优化编译方法，
GraphRAG / LightRAG 的局部图增强检索，
最终形成一个以 Paper / Evidence / Claim / ReviewRun 为核心对象的
academic-custom framework。
```

原因很直接：

1. ScholarAI 不是单一 “chat with docs” 产品。
2. 它至少同时包含：
   - single-paper reading
   - evidence-grounded chat
   - multi-paper compare
   - related-work / review draft
   - citation jump
   - claim verification
3. 通用框架擅长的通常是：
   - pipeline orchestration
   - retrieval component assembly
   - agent state graph
   - prompt/program optimization
4. 但它们普遍不直接提供 ScholarAI 需要的：
   - academic evidence ontology
   - claim-level support semantics
   - compare matrix truthfulness
   - review synthesis with explicit evidence coverage
   - product-grade workspace continuity

因此，`Phase I` 的真正目标不是“迁移框架”，而是：

```txt
建立 ScholarAI 自己的 academic RAG framework，
并把外部框架降级为 adapter、pattern source 和 experiment substrate。
```

额外收口结论：

1. `retrieval / evidence kernel` 要尽量围绕 Qwen 在线检索栈稳定下来。
2. `generation plane` 暂时使用 `glm-4.5-air`，所以框架设计必须天然支持“生成器可替换、证据核不重写”。

# 3. 当前仓库基线盘点

## 3.1 当前已有的学术 RAG 结构信号

当前仓库已经不是一个空白的通用聊天系统，而是已经出现了若干学术化结构信号：

1. `compare_service.py`
   - 明确构造 `CompareMatrix`
   - 每个 cell 都要求 evidence-backed
   - 缺失证据时明确写 `not_enough_evidence`
2. `review_draft_service.py`
   - 已拆成 `outline_planner -> evidence_retriever -> review_writer -> citation_validator -> draft_finalizer`
3. `rag_v3/schemas.py`
   - 已有 `EvidencePack`、`EvidenceCandidate`、`AnswerClaim`、`AnswerCitation`、`EvidenceBlock`
4. `claim_verifier.py`
   - 已存在 claim verification 路径，但当前仍是 lexical overlap 级别的弱实现

这说明：

1. ScholarAI 已经在产品语义上走向 academic RAG。
2. 真正缺的是统一框架，而不是“是否有这些功能”。

## 3.2 当前仍缺什么

当前最明显的缺口有五类：

1. `query-family aware orchestration`
   - fact / method / compare / survey / related_work / conflicting_evidence 仍未被真正统一为不同执行策略
2. `global vs local retrieval split`
   - compare / review / survey 场景需要 global synthesis，但当前主链更多仍偏 local evidence retrieval
3. `claim-level truthfulness kernel`
   - claim verifier 仍偏简化，无法承担学术级 claim support 真源
4. `framework-level trace and recovery`
   - review 里已有 step 概念，但还不是统一 runtime kernel
5. `optimization loop`
   - benchmark / eval 已存在，但还没有把“框架设计 -> 运行结果 -> 自动优化”打通

## 3.3 为什么不能只靠现有 patch 继续堆

如果不成立 `Phase I`，继续 patch 的结果通常会是：

1. compare 越来越像一套专用逻辑
2. review 越来越像另一套专用逻辑
3. chat 再长出第三套 retrieval / grounding 路径
4. Phase J benchmark 只能评估结果，无法反推框架缺陷

所以 `Phase I` 的职责是把这些产品能力往同一 academic kernel 上收口。

# 4. ScholarAI 的任务本体是什么

研究框架之前，必须先冻结任务本体。

ScholarAI 的主要任务不是泛化的 “RAG with tools”，而是以下五类：

## 4.1 Evidence-grounded single-paper understanding

包括：

1. 读一篇论文
2. 问某个 method / table / figure / result
3. 跳回证据位置

这要求：

1. local retrieval 准确
2. section / page / span 对齐可解释
3. evidence block 可直达 UI

## 4.2 Multi-paper comparison

包括：

1. 比较方法
2. 比较数据集与指标
3. 比较 limitations / innovation

这要求：

1. per-paper evidence cell
2. dimension-aware retrieval
3. unsupported / not_enough_evidence honesty

## 4.3 Literature review / related work synthesis

包括：

1. related work 草稿
2. trend / taxonomy / evolution
3. agreement / contradiction / gap finding

这要求：

1. global retrieval and synthesis
2. topic/claim clustering
3. evidence coverage tracking

## 4.4 Claim verification and repair

包括：

1. 对回答或草稿中的 claim 做逐条 support 检查
2. 暴露 unsupported / weakly_supported
3. 支持 repair

这要求：

1. claim object 成为一等公民
2. claim -> evidence 映射稳定
3. verifier 不能只停留在 lexical overlap

## 4.5 Long-running academic workflows

包括：

1. 导入 -> 解析 -> 索引 -> 阅读 -> 比较 -> 综述
2. 用户中断、恢复、重跑
3. 失败后的人类修正与继续执行

这要求：

1. durable state
2. trace
3. resume / HITL
4. cost-aware orchestration

# 5. 外部框架与技术路线拆解

本节只保留对 ScholarAI 直接有价值的外部路线。

## 5.1 PaperQA：学术证据工作流信号最强

### 它真正擅长什么

1. scientific document QA
2. citations-first answer
3. evidence gathering around paper corpora
4. metadata enrichment for literature workflows

### 为什么对 ScholarAI 有价值

因为它离 ScholarAI 的“论文证据型工作流”最近，而不是 generic agent。

### 不适合直接接管的原因

1. 边界太窄
2. 更像强任务 agent，而不是全产品 academic kernel
3. 很难直接覆盖 ScholarAI 的 compare / notes / workspace continuity

### ScholarAI 应吸收什么

1. evidence-first answer contract
2. citation-grounded output
3. paper metadata enrichment
4. LitQA 风格任务意识

### ScholarAI 应拒绝什么

1. 把整个产品收缩成单一 paper QA agent

## 5.2 LlamaIndex：文档与 workflow 组件化信号最强

### 它真正擅长什么

1. ingestion / index / query workflow
2. citation query engine
3. event-driven workflow
4. observability / evaluation hooks

### 为什么对 ScholarAI 有价值

因为 ScholarAI 需要的不是只会“检索+回答”，而是：

1. 解析后产物组织
2. workflow step instrumentation
3. citation-aware query path

### 风险

1. abstraction-heavy
2. 容易让业务问题变成框架抽象问题
3. 容易把核心领域对象退化成 node/index abstraction

### ScholarAI 应吸收什么

1. workflow instrumentation
2. citation query path
3. evaluation / observability separation
4. 解析后多层索引视图

### ScholarAI 应拒绝什么

1. 用框架抽象覆盖自己的领域模型

## 5.3 Haystack：生产型 pipeline 信号最强

### 它真正擅长什么

1. component contract
2. controllable pipelines
3. metadata filtering
4. evaluation modules
5. serialization / visualization

### 为什么对 ScholarAI 有价值

ScholarAI 后续一定需要：

1. 把 compare / review / chat 的 pipeline 拆开但同构
2. 把 evaluation 与 runtime 分层
3. 让 pipeline 可序列化、可观测

### 风险

1. 学术证据语义不够深
2. 容易滑向企业搜索/FAQ pipeline

### ScholarAI 应吸收什么

1. pipeline serialization
2. module boundaries
3. metadata filters
4. retrieval/evaluation decoupling

### ScholarAI 应拒绝什么

1. 把 academic workflow 简化成通用企业问答

## 5.4 LangGraph：状态编排信号最强

### 它真正擅长什么

1. durable execution
2. state graph
3. checkpoint / resume
4. interrupt / human-in-the-loop
5. long-running agent orchestration

### 为什么对 ScholarAI 有价值

因为 review、deep compare、long-running literature tasks 不是一次性同步函数。

### 风险

1. 它不定义 academic evidence semantics
2. 它不解决 retrieval / citation truth
3. 直接套用会得到“状态机很强、学术语义很弱”的系统

### ScholarAI 应吸收什么

1. run state
2. checkpoint / resume
3. HITL
4. failure recovery

### ScholarAI 应拒绝什么

1. 让 orchestration 层侵入领域对象与 retrieval kernel

## 5.5 DSPy：优化编译信号最强

### 它真正擅长什么

1. LM program signatures
2. optimizer-driven prompt/program tuning
3. metric-first compilation

### 为什么对 ScholarAI 有价值

ScholarAI 一定会遇到：

1. review synthesis 质量优化
2. critique / repair loop 质量优化
3. benchmark 驱动的 program evolution

### 风险

1. 不负责完整产品 runtime
2. 不负责 ingestion / evidence UI / workspace continuity

### ScholarAI 应吸收什么

1. signature-based module interfaces
2. benchmark-first optimization
3. evaluator-driven prompt/program tuning

### ScholarAI 应拒绝什么

1. 把产品主架构建立在 prompt 编译之上

## 5.6 GraphRAG / LightRAG：全局综述增强信号

### 它们真正擅长什么

1. community/global search
2. relationship-centric retrieval
3. theme synthesis
4. cross-document concept linking

### 为什么对 ScholarAI 有价值

它们解决的是：

1. literature review
2. cross-paper theme discovery
3. method evolution
4. contradiction / gap finding

而不是普通 fact lookup。

### 风险

1. 索引重
2. 成本高
3. 解释链更长
4. 不适合做默认主链

### ScholarAI 应吸收什么

1. local vs global retrieval split
2. concept graph as secondary retrieval layer
3. community reports 作为综述辅助信号

### ScholarAI 应拒绝什么

1. graph-first default
2. 让所有 query 都先走图增强

# 6. 前沿技术研究结论

除了框架，技术层还有若干对 ScholarAI 极重要的信号。

## 6.1 Self-RAG / Corrective RAG：自我反思和检索修正有价值，但不能黑箱

它们真正给出的信号不是“把模型弄得更 agentic”，而是：

1. 检索不足时应允许 retry / critique / repair
2. answer 生成不能与 evidence adequacy 脱钩

ScholarAI 可吸收：

1. retrieval adequacy checks
2. answerability gating
3. corrective retry steps

ScholarAI 不应照搬：

1. 黑箱式自反思 loop
2. 牺牲可解释性换取表面效果

## 6.2 STORM / OpenScholar：综述生成必须是 outline-first，而不是直接长回答

这一路线给 ScholarAI 的最强信号不是“多 agent 很酷”，而是：

1. literature review 需要先规划结构
2. 不同 section 需要不同 perspective expansion
3. synthesis 必须带 evidence coverage checks

ScholarAI 可吸收：

1. `outline-first planning`
2. `perspective expansion`
3. `section-wise evidence retrieval`
4. `citation-first synthesis`

ScholarAI 不应照搬：

1. 全量重型 multi-agent stack
2. 脱离成本约束的长链路 orchestration

对执行层的直接结论：

1. 现有 `review_draft_service.py` 的 `outline_planner -> evidence_retriever -> review_writer -> citation_validator -> draft_finalizer` 路线是对的
2. Phase I 应把它升级成正式 framework primitive，而不是继续当作单一功能实现

## 6.3 IRCoT / multi-hop retrieval：复杂学术问题不能只做一次检索

对 ScholarAI 的信号是：

1. 有些问题需要 retrieval-reasoning 交替进行
2. 特别是：
   - cross-paper compare
   - conflicting evidence
   - method evolution
   - limitation synthesis

ScholarAI 可吸收：

1. complex query escalation
2. interleaved retrieval
3. sub-question decomposition

ScholarAI 不应照搬：

1. 对所有 query 一律启用多跳 loop
2. 不受控的 latency 放大

结论：

1. multi-hop 应成为高价值 query family 的专用 execution mode
2. 不应成为默认主链

## 6.4 RAPTOR：长论文与长综述需要层级检索

对 ScholarAI 的信号是：

1. 长文理解不能只靠平铺 chunks
2. 需要 section / paper / collection 三层视图

ScholarAI 可吸收：

1. hierarchical summaries
2. section-level retrieval before raw chunk retrieval
3. 文档级与章节级的过渡摘要

ScholarAI 不应照搬：

1. 一上来做全库树状重建
2. 把层级索引作为所有 query 的统一入口

结论：

1. 先在 single-paper understanding 与 review context 上产品化层级检索
2. 再考虑扩展到全 KB

## 6.5 RARR / Chain-of-Verification：引用与 claim 修复必须是框架层能力

这条路线给 ScholarAI 的关键结论是：

1. answer 之后还需要 verification
2. verification 之后还需要 repair
3. citation grounding 与 claim truthfulness 必须联动

ScholarAI 可吸收：

1. `claim -> support/refute/insufficient_evidence`
2. post-answer verification
3. rewrite / repair after failed support

ScholarAI 不应照搬：

1. 只做离线 judge，不进入运行时
2. 把 verification 只当成 review 功能，不服务 chat / compare

结论：

1. `claim verification` 应从“功能点”升级为 framework contract
2. 这是 Phase I 最应该优先产品化的部分之一

## 6.6 Adaptive-RAG：成本控制必须进入框架，而不是上线后再补

这条路线的价值在于：

1. 不是每个 academic query 都值得走重链路
2. simple / medium / hard query 应有不同成本路径

ScholarAI 可吸收：

1. route by complexity
2. selective retrieval depth
3. selective verification depth
4. review-only heavy path

ScholarAI 不应照搬：

1. 完全依赖模型自判复杂度而缺少规则约束
2. 让 cost routing 侵入学术真值语义

结论：

1. Adaptive-RAG 应成为 runtime policy 层
2. 它对 `Phase H` 的 online-first 成本控制和 `Phase J` benchmark 都有直接价值

## 6.7 SciFact / claim verification 路线：claim + rationale 必须成为数据真源

对 ScholarAI 的关键信号：

1. claim 不应只是 UI 展示物
2. claim 应成为：
   - retrieval target
   - verifier target
   - repair target
   - benchmark target

这直接指向：

1. `AnswerClaim` 不能停留在轻量字段
2. `ClaimVerifier` 不能长期停留在 lexical overlap

## 6.8 LitQA / PaperQA 任务形态：学术问答与通用问答不同

关键差异在于：

1. 回答必须带 citation
2. 证据不足要明确 abstain
3. metadata 与 paper identity 很重要
4. 问题常跨多篇论文与多段证据

对 ScholarAI 的信号：

1. 任务评估必须有 academic-specific benchmark
2. compare / review / survey 不能共用一套简化问答逻辑

## 6.9 ARES / RAGAs：评估必须拆层

对 ScholarAI 的直接结论：

1. retrieval quality
2. evidence quality
3. citation fidelity
4. claim support
5. final synthesis quality

这五层必须分开评估，而不是只看最终答案评分。

# 7. ScholarAI 的 academic-custom framework 蓝图

研究结论最终收敛为以下蓝图。

## 7.1 Thin adapters, thick domain kernel

ScholarAI 应保持：

1. 外部框架是 adapter
2. 核心领域对象由 ScholarAI 自己掌握

核心对象至少包括：

1. `Paper`
2. `EvidenceCandidate`
3. `EvidenceBlock`
4. `AnswerClaim`
5. `CompareMatrix`
6. `ReviewRun`
7. `ValidationRun`

## 7.2 Local retrieval vs global synthesis 双核

统一框架不应假设一种检索足够。

应该分成：

1. `Local Evidence Retrieval Kernel`
   - 面向单 claim、单问题、单 paper 或局部 compare cell
2. `Global Synthesis Kernel`
   - 面向 review、trend、taxonomy、method evolution、contradiction mining

两者共用：

1. provider contract
2. evidence ontology
3. trace / cost / benchmark interfaces

优化点：

1. `global synthesis` 不应过早绑定 GraphRAG 或 OpenScholar 某一种实现。
2. 第一版应该先用当前线上检索栈 + outline planning + hierarchical retrieval 做轻量版本，再决定是否引入更重的 graph/global machinery。

## 7.3 Claim-centered truthfulness layer

在 answer / compare / review 之上，必须有统一 truthfulness layer：

1. claim extraction
2. claim-to-evidence linking
3. support grading
4. repair loop
5. unsupported surfacing

## 7.4 Orchestration layer as infrastructure, not product truth

无论后续借鉴 LangGraph 还是自建 state runtime，都必须遵守：

1. orchestration 负责状态、重试、checkpoint
2. academic truth 由 evidence/claim/domain model 决定

## 7.5 Optimization layer as separate concern

DSPy 类思路应放在：

1. prompt/program optimization
2. route selection optimization
3. synthesis quality optimization

但不能直接与 runtime kernel 耦死。

这里还需要强调：

1. `glm-4.5-air` 当前只是 generation plane 的临时主线，不应写死到 academic kernel。
2. kernel 只依赖：
   - claim contract
   - evidence contract
   - retrieval contract
   - synthesis interface
3. 这样后续替换 generation LLM，不会把 compare / review / verification 全部推倒重来。

# 8. ScholarAI 决策矩阵

按 `search-first` 的 adopt / extend / experiment / reject 口径，建议如下：

## 8.1 Adopt

1. `LangGraph-style durable execution patterns`
   - adopt pattern，不一定 adopt whole framework
2. `Haystack-style component boundary and serialization mindset`
3. `LlamaIndex-style workflow instrumentation and observability mindset`
4. `STORM-lite outline planning`
5. `Adaptive-RAG runtime policy`

## 8.2 Extend

1. `PaperQA-style evidence-first academic QA semantics`
2. `DSPy-style optimization loop`
3. `LlamaIndex-style citation workflow`
4. `RAPTOR-style hierarchical retrieval`
5. `RARR / Chain-of-Verification style repair loop`

## 8.3 Experiment

1. `GraphRAG`
   - 只在 survey / related_work / method_evolution 支线实验
2. `LightRAG`
   - 作为更轻图增强实验支线
3. `corrective retrieval loops`
   - 只在高价值 query family 试点
4. `IRCoT-style multi-hop reasoning`
   - 只在 complex academic questions 上试点
5. `OpenScholar-style long-form scientific synthesis`
   - 作为目标架构信号，不做直接重实现

额外优化：

6. `不要过早把 RAPTOR / GraphRAG 合并成主线默认路径`
   - 第一版先让 `hierarchical retrieval` 服务长文和 review
   - `graph/global retrieval` 继续保持实验分支

## 8.4 Reject

1. 框架全盘接管 ScholarAI
2. graph-first default
3. opaque agent loops without trace
4. document/node abstraction 覆盖 ScholarAI 领域模型

# 9. ScholarAI 的优先产品化顺序

如果假设 `Phase H` 已完成，那么 `Phase I` 最值得优先产品化的不是“全部创新一起上”，而是以下顺序：

1. `PaperQA-style evidence-first academic QA workflow`
2. `claim verification + repair loop`
3. `Adaptive-RAG complexity routing`
4. `STORM-lite outline-first review generation`
5. `RAPTOR-style hierarchical retrieval`
6. `IRCoT-style complex-query escalation`
7. `GraphRAG / LightRAG / OpenScholar` 支线实验

这套顺序在当前模型栈下是合理的，因为：

1. 前四项主要依赖 `Qwen retrieval/rerank + glm generation` 的现有双平面结构就能推进
2. 不需要等待更重的 graph/global stack 成熟

原因：

1. 前四项与当前 ScholarAI 主链最连续
2. 它们对 chat / compare / review 的价值最直接
3. 它们最容易被 `Phase J` benchmark 做对比验证

# 10. Phase I 的正式研究结论

1. ScholarAI 应坚持自研 `academic RAG kernel`，而不是整体迁移到单一通用框架。
2. `LangGraph` 更适合作为编排模式来源，不适合作为学术语义真源。
3. `LlamaIndex / Haystack` 更适合作为组件化与 workflow 设计信号，不适合作为领域内核。
4. `PaperQA` 对 academic evidence workflow 的启发最强，应重点吸收 citations-first 与 literature-task 思路。
5. `DSPy` 应进入优化层，而不是主运行时。
6. `GraphRAG / LightRAG` 应只进入全局综述与关系发现的实验支线。
7. `STORM-lite`、`Adaptive-RAG`、`RAPTOR`、`RARR/CoVe` 比全量重型 agent 框架更适合作为第一批产品化技术。
8. `Claim-centered truthfulness`、`local/global dual kernel`、`thin adapters + thick domain kernel` 应成为 ScholarAI 框架三大不变量。

一句话结论：

```txt
Phase I 的目标不是“换框架”，
而是把 ScholarAI 从一组学术功能，
升级成有统一理论边界和工程边界的 academic-custom RAG framework。
```

# 11. 参考资料

官方文档与主仓库：

1. PaperQA
   - https://github.com/Future-House/paper-qa
2. LlamaIndex
   - https://docs.llamaindex.ai/
   - https://docs.llamaindex.ai/en/stable/module_guides/workflow/
   - https://docs.llamaindex.ai/en/stable/examples/workflow/citation_query_engine/
   - https://docs.llamaindex.ai/en/stable/module_guides/evaluating/
   - https://docs.llamaindex.ai/en/stable/module_guides/observability/
3. Haystack
   - https://github.com/deepset-ai/haystack
   - https://docs.haystack.deepset.ai/docs/evaluation
   - https://docs.haystack.deepset.ai/v2.1/docs/pipelines
   - https://docs.haystack.deepset.ai/v2.3/docs/serialization
   - https://docs.haystack.deepset.ai/v2.0/docs/metadata-filtering
4. LangGraph
   - https://docs.langchain.com/oss/python/langgraph/durable-execution
   - https://docs.langchain.com/oss/python/langgraph/human-in-the-loop
   - https://docs.langchain.com/oss/python/langgraph/graph-api
5. DSPy
   - https://dspy.ai/
   - https://github.com/stanfordnlp/dspy
6. GraphRAG
   - https://github.com/microsoft/graphrag
   - https://microsoft.github.io/graphrag/query/overview/
7. LightRAG
   - https://github.com/HKUDS/LightRAG

论文与研究：

1. PaperQA / LitQA
   - https://arxiv.org/abs/2312.07559
   - https://arxiv.org/abs/2409.13740
2. DSPy
   - https://arxiv.org/abs/2310.03714
3. OpenScholar
   - https://arxiv.org/abs/2411.14199
4. STORM
   - https://arxiv.org/abs/2402.14207
   - https://github.com/stanford-oval/storm
5. IRCoT
   - https://arxiv.org/abs/2212.10509
6. RAPTOR
   - https://arxiv.org/abs/2401.18059
7. SciFact
   - https://aclanthology.org/2020.emnlp-main.609/
8. RARR
   - https://arxiv.org/abs/2210.08726
9. Chain-of-Verification
   - https://arxiv.org/abs/2309.11495
10. Self-RAG
   - https://arxiv.org/abs/2310.11511
11. Corrective RAG
   - https://arxiv.org/abs/2401.15884
12. Adaptive-RAG
   - https://arxiv.org/abs/2403.14403
13. RAGAs
   - https://aclanthology.org/2024.eacl-demo.16/
14. ARES
   - https://aclanthology.org/2024.naacl-long.20/
