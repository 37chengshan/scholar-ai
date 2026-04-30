---
标题：ScholarAI v3.0-B External Search + Import to KB 研究文档
日期：2026-04-28
状态：research
范围：外部论文发现、统一搜索、导入知识库、异步入库闭环
前提：文档层假设 Phase A 的结构性产物已完成并可复用；不等同于仓库当前代码状态已全部完成
---

# 1. 研究目标

本文件定义 ScholarAI `v3.0-B: External Search + Import to KB` 的研究方案。

它回答的核心问题是：

```txt
怎样把 ScholarAI 从“能处理用户手头已有 PDF”，
升级成“能主动发现外部论文、拉入 KB、再进入 Read / Chat / Notes / Compare 主链”的产品。
```

本文件只定义产品闭环、系统边界、后端抽象、前端入口、状态语义和风险控制；不展开到逐文件 patch 级实施。

# 2. 执行摘要

`Phase B` 是 `v3.0` 最直接提升用户价值的阶段，因为它决定 ScholarAI 是否只是一个“上传后问答工具”，还是一个“外部文献发现 + 学术工作流入口”。

当前仓库已经具备三类可复用基础：

1. 前端搜索工作区入口已存在：
   - `apps/web/src/features/search/components/SearchWorkspace.tsx`
   - `apps/web/src/features/search/hooks/useUnifiedSearch.ts`
   - `apps/web/src/features/search/hooks/useSearchImportFlow.ts`
2. 后端外部搜索与统一搜索主链已存在：
   - `apps/api/app/api/search/external.py`
   - `apps/api/app/api/search/library.py`
   - `apps/api/app/api/search/shared.py`
3. ImportJob-first 导入与异步处理链已存在：
   - `apps/api/app/services/import_job_service.py`
   - `apps/api/app/services/import_dedupe_service.py`
   - `apps/api/app/workers/import_worker.py`
   - `docs/specs/contracts/import_processing_state_machine.md`

因此，`Phase B` 的正确方向不是“新造一个外部搜索页面”，而是：

```txt
复用 SearchWorkspace 作为统一发现入口，
复用 ImportJob 作为统一导入真源，
把外部发现接进现有 KB / Read / Chat 主链。
```

# 3. 前提假设

本文件写作时采用以下前提：

1. `Phase A` 在文档层面已提供可复用的 benchmark / schema / gate 方向。
2. 这不表示当前仓库真实代码里 `Phase A` 已经完全交付。
3. `Phase B` 设计可先于 `Phase A` 实现结束而成文，但默认后续实现时可消费 `Phase A` 的结构性产物与质量约束。

换句话说：

```txt
Phase B 文档把 Phase A 当成“已定义好的质量基线”，
不是把当前代码状态误判成“已经交付完成”。
```

# 4. 当前基线盘点

## 4.1 前端基线

当前前端已经有外部搜索与导入 KB 的入口骨架：

1. `SearchWorkspace.tsx`
   - 已有外部 source 概念
   - 已展示 arXiv / Semantic Scholar 结果计数
2. `searchApi.ts`
   - 已有 unified search、external source 调用、author search
3. `useSearchImportFlow.ts`
   - 已能从搜索结果发起导入
   - 已通过 SSE + fallback polling 跟踪 ImportJob

这意味着：

1. 不需要再新增一套平行页面
2. 正确做法是增强现有 Search / Import / KB 交互

## 4.2 后端基线

当前后端已经有：

1. `search/external.py`
   - `GET /search/arxiv`
   - `GET /search/semantic-scholar`
2. `search/library.py`
   - `GET /search/unified`
3. `source_adapters`
   - `arxiv_adapter.py`
   - `s2_adapter.py`
   - `doi_adapter.py`
4. `ImportJob` 状态机与 worker
5. `dedupe` 逻辑
   - DOI / arXiv / S2 / hash / title fuzzy

这说明：

1. Phase B 的难点不是“从零接 API”
2. 难点是把搜索、下载、去重、metadata-only、fulltext-ready、UI 状态表达全部收口成统一闭环

## 4.3 已有研究基线

仓库中已存在与 Phase B 高相关的研究文档：

1. `docs/plans/v3_0/search/2026-04-20_SemanticScholar_arXiv_一键下载解析入库_研究报告.md`
2. `docs/specs/contracts/import_processing_state_machine.md`
3. `docs/specs/reference/api/前端接口列表.md`

本文件在此基础上前进一步，重点收口：

1. `Search -> Import -> KB` 主链
2. external paper 统一数据模型
3. metadata-only 与 fulltext-indexed 的严格区分
4. 前端状态与后端真源的对齐方式

# 5. 为什么 Phase B 是 v3.0 第一优先级

## 5.1 用户价值最大

它直接把 ScholarAI 从“处理你已经有的论文”升级成“帮你找到还没在库里的论文并纳入工作流”。

## 5.2 代码基础最接近可收口状态

Search 工作区、ImportJob 状态机、source adapters、dedupe 和 KB 入口都已经存在，不需要另起一套新系统。

## 5.3 能为后续 Phase 提供真实输入

1. `Phase C` 的 citation / verification 需要更多真实外部论文场景。
2. `Phase D` 的 real-world validation 需要外部导入论文进入完整闭环。
3. `Phase E` 的 reliability / cost / speed 会直接暴露在批量外部导入场景里。

# 6. Phase B 的正式目标

`Phase B` 需要同时满足以下六个目标：

1. `统一发现`
   - 在 Search 中统一展示本地与外部来源
2. `统一导入`
   - 外部论文统一走 ImportJob-first 真源
3. `统一状态`
   - metadata-only、downloaded、parsed、indexed、failed 状态严格区分
4. `统一去重`
   - DOI / arXiv / S2 / hash / title 层层收口
5. `统一异步`
   - 下载、解析、索引都走真实 async job
6. `统一消费`
   - 导入完成后进入 KB / Read / Chat / Notes / Compare

# 7. 产品主链定义

建议将 `Phase B` 的主链固定为：

```txt
Search query
-> source selection
-> external results
-> preview metadata / abstract / availability
-> import to KB
-> ImportJob orchestration
-> dedupe / resolve / download / parse / index
-> paper available in KB
-> Read / Chat / Notes / Compare / Review
```

关键点：

1. 外部搜索本身不是终点
2. `Import to KB` 之后的状态透明度与恢复能力同样是产品核心

# 8. 推荐的系统边界

## 8.1 前端边界

前端负责：

1. query 输入
2. source 选择
3. 结果列表与 preview
4. KB 选择与导入动作
5. 导入状态展示
6. 已入库 / 重复 / metadata-only 提示

前端不负责：

1. 第三方 API key 调用
2. 下载候选决策
3. PDF 可用性真实性判断
4. dedupe 最终真源判定

## 8.2 后端边界

后端负责：

1. 外部 provider 调用
2. normalized paper metadata
3. PDF candidate 选择
4. dedupe 判定
5. ImportJob 状态推进
6. metadata-only / fulltext-ready 的资源状态表达

## 8.3 真源边界

统一真源：

1. 发现真源：`search/*` 路由与 provider 适配层
2. 导入真源：`ImportJob`
3. 文件与解析真源：worker / processing pipeline
4. 资源消费真源：KB / Paper / Chunk / IndexArtifact

# 9. External Paper 数据模型建议

建议引入统一 `ExternalPaper` 概念，作为 Search 结果与导入前 preview 的 canonical 结构。

最小字段建议：

1. `external_id`
2. `source`
   - `arxiv`
   - `semantic_scholar`
3. `title`
4. `authors[]`
5. `abstract`
6. `year`
7. `venue`
8. `doi`
9. `arxiv_id`
10. `s2_paper_id`
11. `url`
12. `pdf_url`
13. `open_access`
14. `citation_count`
15. `references_count`
16. `fields_of_study[]`
17. `availability`
   - `metadata_only`
   - `pdf_available`
   - `pdf_unavailable`
18. `library_status`
   - `not_imported`
   - `importing`
   - `imported_metadata_only`
   - `imported_fulltext_ready`

设计原则：

1. Search 展示层与 ImportJob 输入层共享同一个 canonical shape
2. 不允许前端自己拼 source-specific 字段逻辑

# 10. Provider 抽象建议

建议正式抽象：

1. `ExternalPaperProvider`
   - `search(query, filters)`
   - `get_paper(id)`
   - `resolve_pdf(paper)`
   - `normalize_metadata(raw)`

一期 provider：

1. `ArxivProvider`
2. `SemanticScholarProvider`

二期前不建议引入更多源。

原因：

1. 当前产品目标是先把 `arXiv + Semantic Scholar` 做深做稳
2. 多源过早扩张只会把 dedupe、availability、download planner 复杂度拉高

# 11. Search 体验建议

## 11.1 不新造页面

必须继续以：

1. `SearchWorkspace.tsx`
2. `useUnifiedSearch.ts`
3. `useSearchImportFlow.ts`

作为正式入口。

## 11.2 Source 模型

建议 Search source 固定为：

1. `local_kb`
2. `arxiv`
3. `semantic_scholar`
4. `all`

不要同时把 source 模型和 author search 混在同一个抽象层里扩张得过于复杂。

## 11.3 搜索结果卡片最小信息

每条 external result 至少展示：

1. title
2. authors
3. year
4. source
5. abstract preview
6. citation count
7. PDF availability
8. import button
9. already in library / importing / duplicate badge

# 12. 导入状态语义建议

当前 Phase B 最大的产品风险之一，是把“记录了 metadata”误当作“已全文可问答”。

因此必须严格区分：

1. `discovered`
2. `queued`
3. `resolving`
4. `downloading`
5. `downloaded`
6. `parsing`
7. `indexing`
8. `completed_metadata_only`
9. `completed_fulltext_ready`
10. `failed`
11. `cancelled`

关键约束：

1. 没有 PDF 或没有成功解析的论文，只能是 `metadata_only`
2. 只有 chunk / embedding / index 完成后，才允许进入 `fulltext_ready`

## 12.1 三层状态分工

Phase B 必须把以下三层状态分开定义，不能混写成一个字段：

1. `availability`
   - 归属：`ExternalPaper`
   - 取值：`metadata_only | pdf_available | pdf_unavailable`
   - 含义：只表达外部来源是否可提供 PDF / 全文候选
2. `library_status`
   - 归属：`ExternalPaper` / Search result 的文库投影
   - 取值：`not_imported | importing | imported_metadata_only | imported_fulltext_ready`
   - 含义：只表达该论文在当前 KB 中是否已入库、是否可消费
3. `ImportJob.stage`
   - 归属：导入任务
   - 取值：`queued | resolving | downloading | parsing | indexing | completed_metadata_only | completed_fulltext_ready | failed | cancelled`
   - 含义：只表达当前这次导入任务进行到哪一步

执行规则：

1. `availability` 不能代替导入进度
2. `library_status` 不能代替任务进度
3. `ImportJob.stage` 不能直接拿来当论文最终消费态

# 13. 去重与资源合并策略

建议 dedupe 顺序继续保持：

1. DOI
2. arXiv ID
3. S2 paper ID
4. file SHA256
5. title fuzzy

但在 `Phase B` 中要把 dedupe 从“导入内部细节”升级成用户可见反馈：

1. `already imported`
2. `same paper, different source`
3. `metadata exists, fulltext missing`
4. `possible duplicate, needs decision`

目标不是把 dedupe 暴露得很技术，而是让用户知道为什么不能直接重复导入。

# 14. metadata-only 与 fulltext-ready 的正式区分

这是 `Phase B` 最重要的资源语义之一。

## 14.1 metadata-only

表示：

1. 论文信息已存在
2. 但 PDF 不可得，或解析/索引未完成

允许：

1. 在 KB 列表中可见
2. 在 Search 中被标记为已入库
3. 显示 abstract / metadata

不允许：

1. 假装已全文检索
2. 假装可稳定用于 Read / Chat 证据级问答

## 14.2 fulltext-ready

表示：

1. PDF 已成功获取
2. 已解析
3. 已 chunk
4. 已 embedding / index

只有这一状态，才算真正进入 ScholarAI 主工作流。

# 15. 下载与解析编排建议

下载与解析必须统一挂在 ImportJob 主链上。

建议子阶段：

1. `resolving_source`
2. `federating_metadata`
3. `planning_download_candidates`
4. `downloading_pdf`
5. `validating_pdf`
6. `parsing`
7. `indexing`
8. `completed_metadata_only`
9. `completed_fulltext_ready`

这与现有 `ImportJob` 状态机可以兼容演进，不需要重造第二套任务系统。

# 16. Semantic Scholar / arXiv 的设计约束

## 16.1 Semantic Scholar

当前前提：

1. API key 已具备
2. 必须只保留在后端环境变量
3. 所有请求经后端代理

Phase B 的正式定位：

1. 强元数据源
2. 候选 PDF 源
3. citation / field / author 丰富度补充源

不是：

1. 唯一下载源

## 16.2 arXiv

当前前提：

1. 无 key 路径
2. 继续保持缓存与 3 秒级节流约束

Phase B 的正式定位：

1. 高可信 canonical PDF 源
2. 低 friction 外部发现源

# 17. UX 设计要求

`Phase B` 不是单纯后端集成，它必须同时满足以下交互要求：

1. 用户一眼看懂来源与可用性
2. 用户一键导入后能看到真实进度
3. 用户能区分“已入 metadata”与“已可全文问答”
4. 用户导入后能顺滑跳转到 KB / Read
5. 批量导入时不会丢失状态

# 18. 风险与反模式

最需要避免的 7 个错误：

1. 新造一个平行的 external search 页面
2. 让前端直接拿 API key 调第三方
3. 把 metadata-only 标成 imported/fulltext-ready
4. 在 ImportJob 之外再造第二套导入状态机
5. 批量导入时忽略 arXiv / S2 限流
6. 去重命中后不向用户解释
7. 让导入完成后的资源仍然无法进入 KB / Read / Chat 主链

# 19. 正式建议

基于现有代码和研究基线，`Phase B` 的正式建议是：

1. 继续以 `SearchWorkspace` 为唯一外部发现入口。
2. 继续以 `ImportJob` 为唯一导入真源。
3. 抽象 `ExternalPaper` 作为前后端共享 canonical search result。
4. 强化 metadata-only / fulltext-ready 的资源边界。
5. 先只做 `arXiv + Semantic Scholar`，不引入更多外部源。
6. 外部搜索不是终点，导入后能进入 KB / Read / Chat 主链才算 Phase B 完成。

# 20. 结论

一句话总结：

```txt
Phase B 的本质，不是“接两个外部 API”，
而是把 ScholarAI 从被动处理 PDF 的工具，
升级成能主动发现论文、拉入知识库、并进入完整学术工作流的系统。
```
