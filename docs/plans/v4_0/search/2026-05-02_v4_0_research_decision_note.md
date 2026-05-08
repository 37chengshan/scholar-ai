# v4.0 研究决策记录：从功能型 RAG 到可审计研究工作流

> 日期：2026-05-02  
> 状态：research-note  
> 用途：为 v4.0 大版本主线提供外部研究依据与仓库内落地边界，不替代后续各 phase 的详细研究文档。

## 1. 研究问题

v3.0 已经把 ScholarAI 推到 academic RAG、外部论文导入、online-first runtime、Truth + Route、comparative gate 的组合阶段。v4.0 的问题不是“再堆一个 RAG 框架”，而是：

1. 如何把单轮 Search / Chat / Review 能力升级为连续研究工作流。
2. 如何让系统在检索不足、证据冲突、长文综述、跨论文综合时能自我评估并触发下一步动作。
3. 如何把 citation / claim / benchmark / runtime truth 变成用户可理解、团队可审计、发布可门禁的统一产品内核。

## 2. 外部信号

### 2.1 RAG 评测必须覆盖多维质量

RAGAS 明确把 RAG 评估拆成检索上下文质量、LLM 是否忠实利用上下文、生成质量等维度，并强调不依赖人工 gold answer 的快速评估循环价值。对 ScholarAI 的含义是：v4.0 不能只看“答案是否像样”，必须让 retrieval、faithfulness、citation、latency、cost、degraded runtime 分开进入报告。

来源：<https://arxiv.org/abs/2309.15217>

### 2.2 Agentic / reflective RAG 是方向，但不能整仓迁移

Self-RAG 的关键价值不是训练同款模型，而是把“是否需要检索、检索是否有用、生成是否被证据支撑”的反思动作显式化。CRAG 进一步强调 retrieval evaluator：当检索质量不足时，系统应触发重检索、扩展检索或过滤重组，而不是直接生成。

来源：

- <https://arxiv.org/abs/2310.11511>
- <https://arxiv.org/abs/2401.15884>

### 2.3 Graph / global synthesis 适合综述类任务，不应替代所有 RAG

GraphRAG 的优势在全局语料主题、社区结构和 query-focused summarization；它解决的是“整个 corpus 的主要主题/关系”而非每个事实问答都需要图谱。对 ScholarAI 的含义是：v4.0 应把 graph/global synthesis 放到 Review / Survey / Related Work 的路径，而不是替代 fact / method / numeric 等局部证据路径。

来源：<https://arxiv.org/abs/2404.16130>

### 2.4 学术文献合成需要专门产品约束

OpenScholar 说明科学文献综合需要高召回科学语料、citation-backed synthesis、专门 benchmark 与长文答案质量评估。对 ScholarAI 的含义是：v4.0 的目标应是“研究过程产品化”，而不是只做一个更强 chat box。

来源：<https://arxiv.org/abs/2411.14199>

### 2.5 公开评测正在把 RAG 变成可比较赛道

NIST TREC 已把 Retrieval Augmented Generation 作为正式 track，并在 2025 proceedings 中列出 RAG 相关 overview 与参赛系统。这意味着 v4.0 的 benchmark/gate 不能只是内部脚本，应逐步向公开评测口径靠拢：case set、run artifact、diff、release verdict 必须可复现。

来源：

- <https://trec.nist.gov/data/rag.html>
- <https://trec.nist.gov/pubs/trec34/index.html>

## 3. v4.0 主线判断

用户已确认 v4.0 采用 A+C 优先，新增两个前端精细打磨 phase，B 后置拆分。因此 v4.0 应定义为：

```txt
ScholarAI v4.0 =
Productized Research Workflow
+ Beta-ready Research Workspace
+ Reliable Full-chain Execution
+ Citation-backed Review Artifacts
+ Frontend Experience Craft
+ Frontend Interaction Quality
+ Targeted Academic RAG Optimization
+ Evidence-based Release Testing
```

这不是一次技术栈重写，而是把 v3.0 已经形成的 Search -> Import -> KB -> Read -> Chat -> Notes -> Compare -> Review 主链升级成：

```txt
goal
-> plan
-> search / import
-> read / extract
-> retrieve
-> verify claims
-> synthesize
-> produce artifact
-> benchmark / audit
-> resume next step
```

其中：

1. A 主线负责产品化连续研究工作流。
2. C 主线负责 Beta release、稳定性、演示资产和反馈闭环。
3. 前端非常细致打磨拆成视觉体验和交互质量两个 phase。
4. B 技术升级只保留为一个优化 phase，不在开场阶段替换主链。
5. B 的效果验证单独进入一个测试评测 phase。

## 4. 采纳 / 扩展 / 实验 / 拒绝

| 技术信号 | v4.0 决策 | 仓库内边界 |
|---|---|---|
| RAGAS-style multi-metric evaluation | adopt in testing phase | 扩展 Phase J gate，不替换已有 eval service |
| Self-RAG reflective control | defer to optimization phase | 只做 verifier/action pattern，不训练同款 LM |
| CRAG retrieval evaluator | defer to optimization phase | 先评估 retrieval confidence 和 corrective action，不抢 Phase 1/2 主线 |
| GraphRAG global synthesis | experiment in optimization phase | 只进入 Review / Survey / Related Work，不替代 fact path |
| OpenScholar scientific synthesis | extend in artifact phase | 吸收 citation-backed synthesis 和 corpus strategy，服务 Review artifact |
| TREC RAG public benchmark practices | adopt in testing phase | 用 artifact/run/diff/verdict 结构靠拢公开评测 |
| 单一外部 RAG 框架整仓迁移 | reject | 与现有 apps/api 主链、runtime truth、Phase J gate 冲突 |

## 5. 对 v4.0 Phase 的约束

1. Phase 0 作为候选启动 gate，优先关闭 v3.0 遗留验证、后端 smoke、frontend test runner、full-chain walkthrough 与 beta material 缺口。
2. Phase 1 优先产品化连续研究工作流，不开第二套 agent runtime。
3. Phase 2 优先 Beta release hardening，不新增复杂 RAG 能力。
4. Phase 3 聚焦 citation-backed review artifacts，让已有能力形成可交付研究材料。
5. Phase 4 和 Phase 5 专门做前端精细打磨，分别处理视觉体验和交互质量。
6. Phase 6 才进入 B 类 academic RAG optimization。
7. Phase 7 单独做 testing and evaluation gate，验证产品主线、前端打磨和技术优化收益。
8. 所有新能力必须同时有用户可见状态、内部 run artifact、Phase ledger 证据。

## 6. 后续必补研究

1. v4.0 Phase 1：Productized Research Workflow 研究文档
2. v4.0 Phase 2：Beta Release Hardening 研究文档
3. v4.0 Phase 3：Citation-backed Review Artifacts 研究文档
4. v4.0 Phase 4：Frontend Experience Craft 研究文档
5. v4.0 Phase 5：Frontend Interaction Quality 研究文档
6. v4.0 Phase 6：Academic RAG Optimization 研究文档
7. v4.0 Phase 7：Testing and Evaluation Gate 研究文档
