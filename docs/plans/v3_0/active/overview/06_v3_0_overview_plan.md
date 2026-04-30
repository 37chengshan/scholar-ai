# 06 v3.0 纵览计划：学术严谨性升级 + 外部论文发现入库 + 前端产品化打磨

> 日期：2026-04-28  
> 状态：overview  
> 用途：定义 ScholarAI v3.0 的主线、Phase 拆分与优先级。  
> 说明：本文件只描述每个 phase 的方向、目标与边界，不展开到接口级、表结构级、任务拆分级实施方案；各 phase 的细化研究与执行文档后续单独建立。

## 1. v3.0 定位

v3.0 不应再延续单线推进思路，而应明确为双主线推进：

```txt
主线一：学术严谨性升级
主线二：外部论文发现入库 + 前端产品化打磨
```

统一表达为：

```txt
ScholarAI v3.0 =
Academic-grade RAG Evaluation
+ External Literature Discovery
+ Production UX Release
```

这意味着 v3.0 的目标不是重写系统，而是在现有真实代码主链上，把 ScholarAI 从“能跑通若干能力”推进到“可对外演示、可持续迭代、可被真实研究者使用”的产品阶段。

## 2. 项目基线判断

本计划基于当前仓库现状，而不是从零假设重新设计：

1. 前端已存在真实搜索工作区入口：
   - `apps/web/src/features/search/components/SearchWorkspace.tsx`
   - `apps/web/src/features/search/hooks/useUnifiedSearch.ts`
   - `apps/web/src/features/search/hooks/useSearchImportFlow.ts`
2. 后端已存在外部搜索与统一搜索能力：
   - `apps/api/app/api/search/external.py`
   - `apps/api/app/api/search/library.py`
   - `apps/api/app/api/search/shared.py`
3. 后端已存在 ImportJob、去重、异步导入与 worker 骨架：
   - `apps/api/app/api/kb/kb_import.py`
   - `apps/api/app/services/import_job_service.py`
   - `apps/api/app/services/import_dedupe_service.py`
   - `apps/api/app/workers/import_worker.py`
4. 文档层已有前端接口列表与外部入库研究基线：
   - `docs/specs/reference/api/前端接口列表.md`
   - `docs/plans/archive/reports/2026-04-20_SemanticScholar_arXiv_一键下载解析入库_研究报告.md`
5. 评测与 v3.0 质量报告已有早期基础：
   - `docs/plans/v3_0/reports/official_rag_evaluation/v3_0_phase1_report.md`
   - `docs/plans/v3_0/reports/official_rag_evaluation/v3_0_phase5_6_report.md`

因此，v3.0 的正确路径不是新造平行页面或平行导入系统，而是在既有 Search -> Import -> KB -> Read/Chat/Notes 主链上扩展。

## 3. v3.0 规划原则

1. 不重写整个前端，只扩展 `SearchWorkspace`、KB workspace、Read/Chat/Notes 主链。
2. 不重写整个 RAG，只把评测、citation、verification 做成更严格、更可观测。
3. 外部搜索必须复用现有后端代理，不允许前端直接持有第三方 API key。
4. metadata 入库与全文可检索必须明确区分，不能把“已记录论文”伪装成“已全文索引”。
5. 每个 phase 先定义结果形态与验收目标，再单独做技术研究和实施拆解。

## 4. v3.0 Phase 总览

## Phase 3.0-A：Academic Benchmark 3.0

### 核心思路

把当前 benchmark 从“内部基线验证”升级成真正支撑学术严谨性的评测体系，重点不再只是检索命中率，而是 evidence 质量、claim 支撑质量、跨学科泛化能力和 blind set 稳定性。

### 这一阶段解决什么

1. 解决当前 benchmark 规模偏小、覆盖面偏窄的问题。
2. 解决固定题集容易被定向优化的问题。
3. 解决图表、表格、公式、多论文综合等学术问答难题缺少专门评测的问题。

### 结果形态

1. benchmark 扩容到更接近真实学术使用场景的规模。
2. 每题带人工 gold answer / gold evidence。
3. 引入 public set + blind set 双层结构。
4. 所有 RAG 迭代都能产出 baseline / candidate / diff。

### 本阶段边界

本阶段只定义评测体系升级方向，不在本文件中展开题目构建、标注流程、脚本结构和门禁阈值。

## Phase 3.0-B：External Search + Import to KB

### 核心思路

把外部论文发现正式纳入 v3.0 主线，并接到现有 Search / KB 导入链路中，形成从“发现外部论文”到“进入本地知识库并可问答”的闭环。

### 为什么是 v3.0 第一优先级

1. 项目已经有 `SearchWorkspace` 和 unified search 结构，具备承接入口。
2. 项目已经有 `ImportJob`、dedupe、worker、KB 导入流程，具备承接后链。
3. 这是最直接提升用户价值的一步，能把“上传本地 PDF”扩成“主动发现并吸收外部论文”。

### 结果形态

1. 用户可在 Search 中选择 `Local KB / arXiv / Semantic Scholar / All`。
2. 用户可查看外部结果的 metadata、abstract、citation、PDF 可用性。
3. 用户可将 1 篇或多篇论文导入指定 KB。
4. 导入后任务异步完成下载、解析、embedding、索引。
5. 导入完成的论文进入 KB，并可用于 Read / Chat / Notes / Compare / Review。

### 项目约束

1. Semantic Scholar 已有 API key，统一放在后端环境变量，仅经后端代理调用。
2. arXiv 继续走无 key 路径，但必须维持缓存与节流约束。
3. 去重以 `doi / arxiv_id / s2_paper_id / title hash` 为核心。
4. 没有 PDF 的外部论文允许 metadata 入库，但状态必须与全文索引区分。

### 本阶段边界

本阶段只定义产品闭环与架构方向，不在本文件中展开 provider 抽象、导入状态机、批量策略和失败恢复细节。

## Phase 3.0-C：Span-level Citation + Claim Verification

### 核心思路

把当前以 page-level 为主的 citation 能力升级到 span-level / claim-level，让回答和综述草稿中的关键论断都能回溯到更细粒度证据，而不是停留在“引用了哪篇论文哪一页”。

### 这一阶段解决什么

1. 解决 citation 粒度过粗、用户难以判断 claim 是否真的被支撑的问题。
2. 解决 Review Draft 中关键段落无法逐 claim 审核的问题。
3. 解决 evidence 可视性不足，unsupported claims 不易暴露的问题。

### 结果形态

1. claim 成为可显式验证的对象。
2. citation 从 page 跳转升级为 span / quote / offset / bbox 级定位。
3. UI 能区分 supported、weakly supported、unsupported。
4. 用户可针对单个 claim 触发重检索、重验证或修复 citation。

### 本阶段边界

本阶段只定义 citation 与 verification 的产品方向，不在本文件中展开 claim segmentation、verifier pipeline、PDF span 对齐或 bbox 抽取策略。

## Phase 3.0-D：Real-world Validation

### 核心思路

让 v3.0 不只在 benchmark 上看起来更强，而是在真实论文、真实工作流、真实失败模式下仍然成立。

### 这一阶段解决什么

1. 解决 benchmark 与真实使用场景脱节的问题。
2. 解决扫描版 PDF、图表密集论文、公式密集论文、跨学科 KB 等场景验证不足的问题。
3. 解决“外部导入论文能否进入完整研究流程”缺少系统性验证的问题。

### 结果形态

1. 建立真实论文验证集。
2. 将 external search import 也纳入验证链路。
3. 验证流程覆盖 Search -> Import -> KB -> Read -> Chat -> Notes -> Compare -> Review。
4. 形成正式验证报告。

### 本阶段边界

本阶段只定义真实验证的对象与范围，不在本文件中展开样本抽样、标注规范、成功判据和报告模板。

## Phase 3.0-E：Reliability / Data / Cost / Speed

### 核心思路

把 v3.0 从“功能存在”推进到“可以长期稳定跑”，重点落在恢复能力、缓存策略、异步任务可观测性、取消控制以及成本/延迟透明化。

### 这一阶段解决什么

1. 解决批量导入时任务容易卡死或失败不可恢复的问题。
2. 解决 PDF 下载、解析、embedding、rerank 成本高且重复计算的问题。
3. 解决长任务对用户不可见、不可取消、不可复试的问题。

### 结果形态

1. import job、review、compare、reading card 等长任务走统一 async 路径。
2. 外部搜索缓存、PDF 下载缓存、embedding 缓存、rerank 缓存进入主设计。
3. 用户可查看任务阶段、耗时、失败原因与重试入口。
4. 成本、延迟、错误态进入 analytics 或内部观测面板。

### 本阶段边界

本阶段只定义运行可靠性的目标形态，不在本文件中展开缓存键设计、任务恢复协议、取消传播和指标模型。

## Phase 3.0-F：Frontend Productization Polish

### 核心思路

v3.0 的前端目标不是再做一轮孤立的视觉美化，而是把复杂能力压缩成顺手、连续、可自解释的研究工作流。

### 这一阶段解决什么

1. 解决 Search、KB、Read、Chat、Notes、Compare、Review 之间仍有割裂感的问题。
2. 解决导入状态、去重状态、索引状态、citation 状态对用户不透明的问题。
3. 解决新用户需要看文档才能跑通主流程的问题。

### 结果形态

1. Dashboard 明确展示下一步动作。
2. Search 统一本地检索与外部发现体验。
3. KB 清楚表达导入状态、去重状态、索引状态。
4. Read / Chat / Notes 统一围绕 evidence 工作，而不是分散在多套交互里。
5. Compare / Review / Analytics 具备对外演示可读性。

### 本阶段边界

本阶段只定义产品化体验方向，不在本文件中展开页面 IA、组件拆分、排版规范和交互动效方案。

## Phase 3.0-FR：Frontend Reliability Refactor

### 核心思路

在 `Phase F` 的产品化目标之前，先对当前最重、最脆弱的生产力页面执行一轮结构性收口，优先解决 giant page、legacy bridge、hover-only 核心操作和本地偏好状态散落的问题。

### 这一阶段解决什么

1. 解决 `Chat / Knowledge Base / Read / Notes` 页面仍存在的遗留桥接与重复实现问题。
2. 解决知识库大列表在高数据量下缺乏虚拟化导致的前端阻塞风险。
3. 解决 `Read / Notes` 偏好状态仍锁在页面 `useState` 中、刷新和跨会话恢复不一致的问题。
4. 解决核心删除与主路径操作被隐藏在 Hover 中的触屏可用性缺陷。

### 结果形态

1. `Chat` 与 `Knowledge Base` 的 legacy bridge 被清理。
2. KB 论文列表具备可扩展的虚拟化渲染能力。
3. `Read / Notes` 偏好状态进入持久化 store。
4. 前端重构边界、冻结条款与执行顺序被文档化，作为后续 `Phase F` 的实施前置。

### 本阶段边界

本阶段只做第一轮可靠性重构与结构清障，不在本文件中展开整套 Chat 工作台深拆、完整 Compare/Review IA 重做或全站视觉重绘。

## Phase 3.0-G：Public Beta / Demo Release

### 核心思路

在 v3.0 主链路可用后，补足面向陌生用户的体验封装、说明材料、部署文档和演示脚本，使产品具备公开演示和小范围内测条件。

### 这一阶段解决什么

1. 解决系统“内部可运行但外部难理解、难上手”的问题。
2. 解决 demo 时需要大量口头解释、流程不够稳定的问题。
3. 解决部署、反馈、已知限制说明不完整的问题。

### 结果形态

1. demo dataset 与 demo account。
2. README / Quickstart / 本地与云部署指南。
3. 演示脚本、known limitations、feedback 入口。
4. 基于 v3.0 主流程的 15-30 分钟上手体验。

### 本阶段边界

本阶段只定义公开演示与 beta 释放方向，不在本文件中展开素材组织、运维细节和发布节奏。

## 5. 推荐优先级

建议执行顺序：

```txt
1. Phase 3.0-B External Search + Import to KB
2. Phase 3.0-A Academic Benchmark 3.0
3. Phase 3.0-C Span-level Citation + Claim Verification
4. Phase 3.0-D Real-world Validation
5. Phase 3.0-FR Frontend Reliability Refactor
6. Phase 3.0-E Reliability / Data / Cost / Speed
7. Phase 3.0-F Frontend Productization Polish
8. Phase 3.0-G Public Beta / Demo Release
```

并行视角：

```txt
技术线：Benchmark / Citation / Verification
产品线：External Search / Import / UX Polish
工程线：Reliability / Cost / Deployment
```

## 6. v3.0 不建议做的事

1. 不重写整个 RAG。
2. 不重写整个前端。
3. 不把 GraphRAG 升级为 v3.0 主线。
4. 不一次接太多外部源，先聚焦 arXiv + Semantic Scholar。
5. 不让前端直接调第三方外部 API。
6. 不把 metadata-only 导入标记成已全文索引。
7. 不只围绕固定 benchmark 做优化而缺少 blind 验证。

## 7. 后续文档拆分建议

本文件之后，建议按以下顺序补独立研究/执行文档：

1. `Phase 3.0-B external search / import` 详细研究与实施方案
2. `Phase 3.0-A benchmark 3.0` 题库、标注、门禁方案
3. `Phase 3.0-C citation / verification` 数据结构与 UI 方案
4. `Phase 3.0-E reliability / async jobs / observability` 工程方案
5. `Phase 3.0-F frontend productization` 页面与交互方案

## 8. 参考信号

仓库内参考：

1. `docs/plans/archive/reports/2026-04-20_下一大迭代研究报告.md`
2. `docs/plans/archive/reports/2026-04-20_SemanticScholar_arXiv_一键下载解析入库_研究报告.md`
3. `docs/specs/architecture/system-overview.md`
4. `docs/specs/architecture/api-contract.md`
5. `docs/specs/domain/resources.md`

外部参考信号：

1. Semantic Scholar API Overview: https://www.semanticscholar.org/product/api
2. Semantic Scholar Academic Graph API Docs: https://api.semanticscholar.org/api-docs/graph
3. arXiv API User's Manual: https://info.arxiv.org/help/api/user-manual.html
4. RAGAs: https://aclanthology.org/2024.eacl-demo.16/
5. FaithfulRAG: https://aclanthology.org/2025.acl-long.1062/

一句话结论：

```txt
ScholarAI v3.0 的主战场，不是再开一套新系统，
而是把外部论文发现、学术严谨性升级和前端产品化，
压到现有 Search / Import / KB / Read / Chat 主链上做成闭环。
```
