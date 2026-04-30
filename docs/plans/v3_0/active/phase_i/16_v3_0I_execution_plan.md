# 16 v3.0-I 执行计划：学术化定制 RAG 框架

> 日期：2026-04-30  
> 状态：execution-plan  
> 上游研究：`docs/plans/v3_0/active/phase_i/2026-04-30_v3_0I_Academic_Custom_RAG_Framework_研究文档.md`  
> 文档前提：按“Phase H 已完成、RAG 主链已具备 online-first runtime truth”来组织执行

## 1. 目标

`Phase I` 的执行目标是把 `Academic-custom RAG Framework` 从研究结论推进成可实施的框架演进计划，形成：

```txt
task taxonomy freeze
-> framework decision matrix
-> academic kernel blueprint
-> local/global retrieval split
-> claim truthfulness layer
-> orchestration / optimization adoption
-> benchmark-facing experiment harness
```

## 2. 执行前先读什么

执行者开始前，按以下顺序读取：

1. `docs/plans/v3_0/active/overview/06_v3_0_overview_plan.md`
2. `docs/plans/v3_0/active/phase_h/2026-04-30_v3_0H_RAG_Online_Transition_研究文档.md`
3. `docs/plans/v3_0/active/phase_i/2026-04-30_v3_0I_Academic_Custom_RAG_Framework_研究文档.md`
4. `apps/api/app/services/compare_service.py`
5. `apps/api/app/services/review_draft_service.py`
6. `apps/api/app/rag_v3/schemas.py`
7. `apps/api/app/core/claim_verifier.py`
8. `docs/plans/v3_0/active/phase_j/2026-04-30_v3_0J_RAG_Benchmark_研究文档.md`

执行规则：

1. 先冻结学术任务 taxonomy，再设计框架。
2. 先定义 ScholarAI 自有 kernel，再决定外部框架的吸收方式。
3. 任何外部技术只允许以 `adopt / extend / experiment / reject` 进入主计划。
4. 不允许先写大重构，再补理论边界和 benchmark 口径。
5. 默认继承 `Phase H` 已冻结模型栈：
   - retrieval plane: `Qwen flash/pro + Qwen rerank + Milvus`
   - generation plane: `glm-4.5-air`
6. academic kernel 不得把 `glm-4.5-air` 写死为不可替换核心依赖。

## 3. 范围

### 包含

```txt
1. academic task taxonomy
2. domain kernel blueprint
3. local/global retrieval split design
4. claim-centered truthfulness layer
5. orchestration / optimization layer adoption plan
6. framework decision matrix
7. Phase J-facing experiment harness contract
```

### 不包含

```txt
1. 单一外部框架整仓迁移
2. 向量库主线切换
3. 完整 provider 迁移
4. 最终 benchmark 阈值定版
5. 一次性替换全部 compare / review / chat 实现
```

## 4. Work Packages

## WP0：Academic Task Taxonomy Freeze

目标：

1. 冻结 ScholarAI 的学术任务分类
2. 明确哪些任务共用 kernel，哪些任务必须分流

输出：

1. task taxonomy
2. query-family to execution-mode map
3. query-family to retrieval plane / generation plane consumption map

验收：

1. `fact / method / compare / survey / related_work / conflicting_evidence` 不再被混成同一种 RAG。

执行方式：

1. 以 `compare_service`、`review_draft_service`、`rag_v3/schemas.py` 为当前真实能力基线。
2. 先定义任务，再定义框架。
3. taxonomy 一旦冻结，后续组件设计必须显式映射回任务族。

## WP1：Framework Decision Matrix Freeze

目标：

1. 把外部框架与技术路线固定到 `adopt / extend / experiment / reject`
2. 避免后续实现阶段反复“重新讨论选哪个框架”

输出：

1. framework decision matrix
2. rationale per candidate

验收：

1. 后续实现团队能明确知道哪些是主线，哪些只是实验支线。

执行方式：

1. `PaperQA`、`LlamaIndex`、`Haystack`、`LangGraph`、`DSPy`、`GraphRAG`、`LightRAG`、`STORM`、`OpenScholar`、`IRCoT`、`RAPTOR`、`Adaptive-RAG`、`RARR/CoVe` 全部入表。
2. 必须写明“吸收什么、不吸收什么”。
3. 不允许只写推荐，不写拒绝项。

## WP2：Academic Kernel Blueprint

目标：

1. 定义 ScholarAI 自有 academic RAG kernel
2. 冻结核心领域对象与模块边界

输出：

1. kernel blueprint
2. domain object map
3. module boundary map

验收：

1. 外部框架不会吞掉 ScholarAI 的核心对象。

执行方式：

1. 以 `Paper`、`EvidenceCandidate`、`EvidenceBlock`、`AnswerClaim`、`CompareMatrix`、`ReviewRun` 为第一批核心对象。
2. 采用 `thin adapters + thick domain kernel` 原则。
3. orchestration / optimization / retrieval enhancement 均不得反客为主。

## WP3：Local vs Global Dual Kernel Design

目标：

1. 明确 local evidence retrieval 与 global synthesis 的双核结构
2. 让 compare / review / survey 不再被迫共用单一路径

输出：

1. local kernel spec
2. global kernel spec
3. routing rules

验收：

1. 单 claim 问答与 literature review 有不同 execution mode，但共用同一 evidence ontology。

执行方式：

1. local kernel 优先服务 read/chat/cell-level compare。
2. global kernel 优先服务 review/trend/taxonomy/evolution。
3. Graph-enhanced retrieval 仅进入 global kernel 或高价值特例。
4. 第一版 global kernel 不强制绑定 GraphRAG；先允许 `STORM-lite + hierarchical retrieval` 轻实现。

## WP4：Claim-centered Truthfulness Layer

目标：

1. 把 claim verification 从功能点升级为框架层能力
2. 为 review / compare / chat 提供统一 truthfulness substrate

输出：

1. claim object lifecycle
2. claim-to-evidence linking contract
3. verifier / repair loop design

验收：

1. `ClaimVerifier` 不再被视为孤立工具，而是 framework core component。

执行方式：

1. claim extraction、support grading、repair、unsupported surfacing 必须一起设计。
2. 当前 lexical overlap verifier 仅作为 baseline，不作为最终框架结论。
3. 结果必须能被 Phase J benchmark 消费。

## WP5：Orchestration and Optimization Adoption

目标：

1. 吸收 LangGraph / DSPy 等外部路线，但保持从属地位
2. 把它们放到正确层次

输出：

1. orchestration adoption note
2. optimization adoption note

验收：

1. LangGraph 只影响状态编排层，DSPy 只影响优化层，不侵入领域真源。

执行方式：

1. 把 checkpoint / resume / HITL 设计映射到 review / long-running workflows。
2. 把 optimizer-driven tuning 设计映射到 synthesis / critique / route selection。
3. 把 `STORM-lite` 映射到 outline planner / section-wise evidence retrieval。
4. 把 `Adaptive-RAG` 映射到 complexity-based routing 和 cost-aware depth control。
5. 两者都必须通过 Phase J 的 comparative gate 来证明价值。
6. `glm-4.5-air` 只在 generation plane 生效，不得侵入 claim/evidence/domain kernel 设计。

## WP6：Experiment Harness and Adoption Order

目标：

1. 定义哪些创新先做实验，哪些可以进入主线
2. 把 Phase I 与 Phase J benchmark 真正接起来

输出：

1. experiment backlog
2. adoption order
3. benchmark contract hooks

验收：

1. 所有实验项都知道自己如何被 benchmark，而不是凭感觉推进。

执行方式：

1. `GraphRAG / LightRAG / corrective retrieval loops / stronger claim verifier / IRCoT / OpenScholar-style long-form synthesis` 先进入实验 backlog。
2. 每个实验都要定义：
   - target task family
   - expected gain
   - added cost
   - rollback condition
3. `PaperQA-style workflow`、`claim repair loop`、`RAPTOR-style hierarchical retrieval`、`STORM-lite` 作为第一批主线候选。
4. 只有通过 comparative gate 的实验才能申请主链 adoption。
5. `GraphRAG / OpenScholar` 即使实验表现好，也必须先证明成本和 trace 可控，才能申请进入主线。

## 5. 实际执行顺序

执行者按以下顺序推进：

1. `WP0 Academic Task Taxonomy Freeze`
2. `WP1 Framework Decision Matrix Freeze`
3. `WP2 Academic Kernel Blueprint`
4. `WP3 Local vs Global Dual Kernel Design`
5. `WP4 Claim-centered Truthfulness Layer`
6. `WP5 Orchestration and Optimization Adoption`
7. `WP6 Experiment Harness and Adoption Order`

原因：

1. 任务不先冻，框架设计一定漂。
2. 框架决策不先冻，后续实现会反复摇摆。
3. kernel blueprint 不先立，外部框架会抢走主导权。
4. benchmark hooks 不最后接上，创新无法形成可审计闭环。

## 6. 下层文档

当前 Phase I 已有：

1. `docs/plans/v3_0/active/phase_i/2026-04-30_v3_0I_Academic_Custom_RAG_Framework_研究文档.md`

后续建议补齐：

1. `v3_0I_framework_decision_matrix.md`
2. `v3_0I_academic_kernel_blueprint.md`
3. `v3_0I_claim_truthfulness_spec.md`
4. `v3_0I_execution_plan_review.md`

## 7. 验收标准

Phase I P0 可视为完成，当且仅当：

1. ScholarAI 学术任务 taxonomy 已冻结。
2. 外部框架与技术路线进入正式 decision matrix。
3. academic RAG kernel 的核心对象与模块边界已冻结。
4. local retrieval 与 global synthesis 的双核结构已定义。
5. claim-centered truthfulness layer 已被定义为 framework core，而不是零散功能。
6. `STORM-lite`、`Adaptive-RAG`、`RAPTOR`、`RARR/CoVe` 等第一批产品化技术已有明确归属层。
7. orchestration / optimization / graph enhancement 都有明确从属位置和 benchmark 消费方式。

## 8. 风险

1. 若先选框架再定任务，ScholarAI 会被外部框架反向塑形。
2. 若不冻结 domain kernel，对 compare / review / chat 的收口会继续分裂。
3. 若 GraphRAG 类路线过早进入主线，会显著放大成本和复杂度。
4. 若不把 claim truthfulness 定义为框架层能力，学术可信性会长期停留在功能拼接态。
