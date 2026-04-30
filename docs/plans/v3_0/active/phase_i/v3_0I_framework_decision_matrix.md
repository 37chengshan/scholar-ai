# v3.0I Framework Decision Matrix

> 日期：2026-04-30  
> 状态：freeze-draft  
> 上游：`docs/plans/v3_0/active/phase_i/2026-04-30_v3_0I_Academic_Custom_RAG_Framework_研究文档.md`  
> 目的：把 `Phase I` 的框架与技术路线正式冻结到 `adopt / extend / experiment / reject`。

## 1. 冻结原则

所有候选路线只能落到四类之一：

1. `adopt`
   - 直接吸收设计模式或作为正式实现基线
2. `extend`
   - 吸收其核心思想，但必须包裹在 ScholarAI 自有 domain kernel 内
3. `experiment`
   - 只进入 benchmark 支线，不进入默认主链
4. `reject`
   - 明确不作为当前主线方向

额外规则：

1. 任何候选如果会吞掉 ScholarAI 的 `Paper / Evidence / Claim / ReviewRun` 核心对象，一律不能进 `adopt`
2. 任何候选如果缺少 trace / cost / rollback 解释能力，一律不能直进主线
3. 任何候选进入主线前，必须先经过 `Phase J` comparative gate

## 2. 决策矩阵

| candidate | decision | ScholarAI absorb point | do_not_absorb | target_scope | benchmark_required | notes |
|---|---|---|---|---|---|---|
| PaperQA / PaperQA2 | extend | evidence-first academic QA, citation-grounded synthesis, metadata enrichment | whole-product takeover | chat / read / review evidence workflow | yes | 当前最接近产品主链 |
| LlamaIndex | extend | workflow instrumentation, citation query path, observability mindset | node/index abstraction takeover | ingestion / citation-aware query orchestration | yes | 适合作为 pattern，不适合作为内核 |
| Haystack | adopt-pattern | pipeline boundaries, serialization, metadata filtering, evaluation separation | enterprise FAQ simplification | retrieval/review/compare pipeline structuring | yes | 适合生产模块化信号 |
| LangGraph | adopt-pattern | durable execution, checkpoint, resume, HITL | orchestration takeover of domain truth | long-running workflows / review orchestration | yes | 只吸收编排模式 |
| DSPy | extend | optimization layer, signature-driven tuning, benchmark-first improvement | runtime kernel takeover | synthesis / critique / route optimization | yes | 明确放优化层 |
| STORM | adopt-pattern | outline-first planning, perspective expansion, section-wise evidence retrieval | full heavy multi-agent stack | review generation | yes | 先做 STORM-lite |
| OpenScholar | experiment | citation-first long-form synthesis target architecture | full replication | long-form scientific synthesis | yes | 目标架构参考，不直进主线 |
| IRCoT | experiment | complex-query escalation, interleaved retrieval | default all-query multi-hop loop | hard academic query / review sub-questions | yes | 成本高，先实验 |
| RAPTOR | extend | hierarchical retrieval, section/document-level summaries | full corpus tree-first default | long paper / long review retrieval | yes | 可作为第一批主线候选 |
| GraphRAG | experiment | local vs global split, concept graph as secondary layer | graph-first default | survey / related_work / method evolution | yes | 只走 global synthesis 支线 |
| LightRAG | experiment | lighter graph-enhanced retrieval | production backbone | graph-enhanced retrieval experiments | yes | 比 GraphRAG 更轻，但仍非主线 |
| Self-RAG | extend-policy | retrieval adequacy, need-retrieval / abstain policy | training-heavy full self-rag route | runtime retrieval policy | yes | 吸收 runtime policy，不走训练主线 |
| CRAG / Corrective RAG | extend-policy | rewrite / retry / corrective retrieval | opaque autonomous loop | retrieval correction | yes | 可融入 high-value query family |
| RARR / Chain-of-Verification | extend | post-answer verification, repair loop, citation-grounded rewrite | offline-only judge pattern | claim repair / answer repair / review repair | yes | 第一批主线候选 |
| SciFact-style claim verification | adopt-contract | claim+rationale truthfulness contract | benchmark-only isolation | claim-centered truthfulness layer | yes | 应进入 framework core |
| Adaptive-RAG | adopt-pattern | complexity routing, cost-aware depth selection | unconstrained model-only self-routing | runtime routing policy | yes | 第一批主线候选 |

## 3. 第一批主线候选

按当前方案，第一批最值得进入主线候选的是：

1. `PaperQA-style workflow`
2. `RARR / CoVe / SciFact-style truthfulness + repair`
3. `Adaptive-RAG runtime policy`
4. `STORM-lite`
5. `RAPTOR-style hierarchical retrieval`

原因：

1. 与当前 ScholarAI 主链最连续
2. 对 read / chat / compare / review 直接有产品价值
3. 不要求先引入重型 graph/global stack
4. 最容易被 `Phase J` benchmark 做硬裁决

## 4. 明确不提前主线化的路线

以下路线当前不允许直接主线化：

1. `GraphRAG`
2. `LightRAG`
3. `OpenScholar full replication`
4. `IRCoT default-all-query`
5. `training-centric Self-RAG`

理由不是“它们不好”，而是：

1. 太重
2. 太贵
3. 太难解释
4. 太容易让 runtime trace 与 rollback 失控

## 5. 与当前模型栈的兼容口径

本矩阵默认继承当前已知模型栈：

1. retrieval plane：
   - `Qwen flash/pro`
   - `Qwen rerank`
   - `Milvus`
2. generation plane：
   - `glm-4.5-air`

因此：

1. 所有 `adopt / extend` 候选都必须能在这套模型栈上工作
2. 不能默认要求先切换 generation LLM
3. 不能默认要求先切换向量库

## 6. Benchmark 前必须回答的问题

每个候选进入 benchmark 前都必须明确：

1. 它优化哪个 task family
2. 它提升哪类指标
3. 它增加多少 latency
4. 它增加多少 cost
5. 它失败时如何回滚
6. 它是否改变 retrieval plane / generation plane 的口径

## 7. 进入主线的硬条件

任一候选路线想从 `experiment` 或 `extend` 进入正式主线，至少满足：

1. `Phase J` comparative benchmark 有明确正收益
2. 成本与延迟增长在可接受区间
3. trace / rollback / degraded condition 可解释
4. 不破坏 `Paper / Evidence / Claim / ReviewRun` 领域内核
5. 不要求引入平行产品系统
