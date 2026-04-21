---
标题：ScholarAI Semantic Scholar/arXiv 一键下载解析入库研究报告
作者：glm5.1+37chengshan
日期：2026-04-20
状态：v1.1-final
范围：外部论文检索、下载、解析、入库自动化链路
---

> 更新：本报告已完成六维复审并修订，当前版本为 v1.1-final。

# 1. 研究目标

围绕以下核心问题建立可落地方案：

如何让用户输入 DOI / arXiv / Semantic Scholar / URL 后，系统自动完成“检索 -> 下载 -> 解析 -> 去重 -> 入库 -> 可问答”全流程，并且在失败时可恢复、可解释。

# 2. 当前实现能力评估

## 2.1 现有实现优势

1. 已有统一 source resolver 与多适配器体系。
2. 已有 ImportJob 状态机与 worker 执行链。
3. 已有导入分片上传会话，支持手动接力。
4. 已有去重策略（外部ID + hash + 模糊标题）。

## 2.2 关键不足

1. DOI 下载成功路径过度依赖 Semantic Scholar `openAccessPdf`。
2. 缺少 Open Access 多源聚合策略（Unpaywall/OpenAlex 未实装到核心下载回退）。
3. 外部 API 调度策略以单源直连为主，缺少 source routing 与质量评分。
4. 导入前的“是否可下载”判断粒度不足（license、host、格式稳定性）。
5. 前端一键导入流程仍以短轮询为主，长任务反馈不稳定。

# 3. 外部 API 事实基线（用于设计约束）

## 3.1 Semantic Scholar

可用事实：

1. Graph API 支持多种 paper_id 表达（SHA、DOI、ARXIV、CorpusId 等）。
2. `openAccessPdf` 字段可直接指向可下载 PDF。
3. API key 通过 `x-api-key` 传递。
4. 搜索接口存在返回规模限制（relevance search 不适合超大规模全量拉取）。

对设计的约束：

- 作为“高质量元数据 + 候选 PDF 来源”的强源，但不能作为唯一下载源。

## 3.2 arXiv

可用事实：

1. 官方用户手册建议连续调用需加入约 3 秒间隔。
2. 支持 `start/max_results` 分页，且单次返回与总量有上限约束。
3. 同一查询日内变化有限，官方建议缓存，避免重复请求。

对设计的约束：

- 必须显式做节流和缓存；批量导入时不能并发猛拉。

## 3.3 Crossref

可用事实：

1. 强项是 DOI 元数据检索，不保证直接 PDF 可得。
2. 官方建议优先 filter/select/cursor、避免低效逐条查询。
3. 大结果集建议分片拉取并本地缓存。

对设计的约束：

- Crossref 应定位为“元数据权威源”，而非 PDF 最终源。

## 3.4 Unpaywall / OpenAlex

可用事实：

1. Unpaywall 响应中包含 `best_oa_location`、`oa_locations`、`url_for_pdf`、`oa_status` 等关键字段。
2. OpenAlex 支持通过 DOI 等外部 ID 查询 works，并提供 OA 相关字段与分页能力。

对设计的约束：

- 二者非常适合补齐 DOI 场景下的 OA PDF 回退链路。

# 4. 目标架构：一键入库编排器

建议新增统一编排层：Ingestion Orchestrator。

职责：

1. 输入归一化（DOI/arXiv/S2/URL）
2. 元数据聚合（S2 + Crossref + OpenAlex）
3. 下载候选排序（arXiv -> S2 openAccessPdf -> Unpaywall/OpenAlex OA -> Direct URL）
4. 许可与可用性判定（license/status/content-type）
5. 下载执行与重试
6. 解析路由（轻量解析 or 增强解析）
7. 去重决策与入库

可选流程（文本时序）：

1. 用户提交标识符。
2. Resolver 识别 source type 并规范化 canonical id。
3. Metadata federation 并行请求多源，生成融合元数据。
4. Download planner 生成候选 URL 队列并打分。
5. Downloader 按候选顺序尝试，记录失败原因与已尝试来源。
6. 成功后进入解析管道、索引与 KB 绑定。
7. 回传作业状态与可追溯 provenance。

# 5. 下载候选排序策略（核心）

建议顺序（默认）：

1. arXiv canonical PDF（若 source 为 arXiv）
2. Semantic Scholar `openAccessPdf.url`
3. Unpaywall `best_oa_location.url_for_pdf`
4. Unpaywall `oa_locations[].url_for_pdf` 按 license/host 优先级
5. OpenAlex `best_oa_location` 或 `primary_location` 中可下载地址
6. 用户给定直链 URL（最后尝试，需更严格校验）

评分要素：

- 可下载概率（历史成功率）
- 响应速度（host p95）
- 内容稳定性（PDF magic bytes 通过率）
- 许可可用性（license 白名单）

# 6. 状态机增强建议

在现有状态机基础上新增关键子阶段，便于排障与用户反馈：

1. resolving_source
2. federating_metadata
3. planning_download_candidates
4. downloading_pdf
5. validating_pdf
6. parsing
7. indexing
8. completed / awaiting_user_action / failed

失败分类建议：

- NO_PDF_CANDIDATE
- SOURCE_RATE_LIMITED
- CONTENT_TYPE_MISMATCH
- PDF_MAGIC_INVALID
- LICENSE_RESTRICTED
- PARSE_FAILED

# 7. 解析引擎策略

建议采用双层解析：

1. 默认解析：现有轻量解析链路（低成本、快）
2. 增强解析：复杂版面/表格/图像密集文档触发（Docling 或 GROBID 路径）

触发条件示例：

- 默认解析置信度低
- OCR 需求高
- 表格/图像命中阈值高
- 用户手动要求“高精解析”

收益：

- 避免所有文档都走重链路导致成本飙升。
- 在复杂学术 PDF 上显著提升结构化质量。

# 8. 前端一键导入体验改造建议

1. 从短轮询升级为 SSE 主通道 + 轮询备份。
2. 明确展示“已尝试来源列表”和失败原因。
3. 支持失败后一键接力（上传本地 PDF 并复用当前 ImportJob）。
4. 在导入中页面切换后可恢复同一任务视图。
5. 提供 ETA 与阶段进度文案，避免用户误判卡死。

# 9. 数据与监控指标

建议至少建立以下指标：

1. `ingest_attempt_total`（按 sourceType、result）
2. `ingest_success_rate`（总成功率与分源成功率）
3. `download_source_fallback_depth`（平均回退层数）
4. `download_latency_ms`（按来源 host 聚合）
5. `parse_success_rate`（轻量/增强分层）
6. `time_to_query_ready`（从提交到可问答）

建议门槛：

- 一键入库总成功率 >= 95%
- DOI 场景成功率 >= 90%
- 导入到可问答 p95 <= 180s

# 10. 合规与安全建议

1. 仅允许 HTTPS 下载源。
2. 强制校验 PDF magic bytes 与大小上限。
3. 下载域名白名单与异常域名熔断。
4. 记录来源、license 与抓取时间，保留审计线索。
5. 对失败详情做用户可读与内部可诊断双层错误信息。

# 11. 分阶段落地计划（8 周）

第 1-2 周：

1. 引入 ingestion orchestrator 抽象层。
2. 将 S2/arXiv 现有适配器接入候选下载计划器。
3. 前端接入 SSE 导入进度展示。

第 3-4 周：

1. 接入 Unpaywall + OpenAlex 作为 DOI OA 回退源。
2. 下载失败分型与错误码标准化。
3. 导入可恢复体验（接力上传）收口。

第 5-6 周：

1. 双层解析策略上线（复杂文档触发增强解析）。
2. 建立分源成功率与 fallback 深度看板。

第 7-8 周：

1. 全链路压测与回归。
2. 发布稳定版并定义 SLO。

# 12. 对当前代码的直接改造建议清单

后端优先：

1. apps/api/app/services/source_adapters/doi_adapter.py：加入 Unpaywall/OpenAlex 回退。
2. apps/api/app/services/source_adapters/pdf_url_adapter.py：HEAD 失败时允许 GET 探测回退。
3. apps/api/app/workers/import_worker.py：增加 federating/planning 子阶段记录。
4. apps/api/app/services/import_rate_limiter.py：按 source 与 host 维度细化节流计量。

前端优先：

1. apps/web/src/features/search/hooks/useSearchImportFlow.ts：替换短轮询为 SSE 主通道。
2. apps/web/src/features/uploads/hooks/useChunkUpload.ts：并发分片与更细粒度失败恢复。
3. apps/web/src/features/uploads/hooks/useUploadRecovery.ts：增强跨刷新恢复与错误提示。

# 13. 多维度复审（已执行）与修订记录

复审维度：

1. 技术可行性（代码层可接入性）
2. API 约束匹配度（S2/arXiv/Crossref/OA 源）
3. 成本与性能
4. 失败恢复与可观测性
5. 合规与安全
6. 前后端契约一致性

复审发现与已修订项：

1. 发现：初稿中“下载候选排序”与现有适配器边界衔接不够具体。
- 修订：在改造清单中明确落点到 `doi_adapter.py` 与 `pdf_url_adapter.py`，保证可落地。

2. 发现：arXiv 节流约束提到 3 秒，但未强调批量场景风险。
- 修订：补充“批量导入禁用高并发猛拉、需要缓存复用”的执行约束。

3. 发现：S2 价值描述偏理想化，缺少“不是唯一下载源”的工程边界。
- 修订：明确 S2 定位为“强元数据 + 候选 PDF 源”，并与 OA 回退链路并列。

4. 发现：失败分类虽完整，但未与前端体验改造绑定。
- 修订：将“失败分类”与“已尝试来源列表、失败原因可见、一键接力上传”一并绑定。

5. 发现：指标阈值存在可用但不够可运营的问题。
- 修订：保留成功率与 p95 门槛，同时新增 `fallback_depth` 与分源口径，便于持续调优。

最终建议优先级与落地顺序（修订后）：

1. P0（先做）：
	- SSE 主通道接入与失败分类可见化
	- DOI 的 OA 多源回退（Unpaywall/OpenAlex）
	- `pdf_url` 的 HEAD 失败 GET 探测回退

2. P1（随后）：
	- 编排器子阶段埋点（federating/planning/downloading）
	- 导入接力体验与跨刷新恢复
	- 分源成功率与回退深度看板

3. P2（最后）：
	- 双层解析（轻量 + 增强）
	- 基于复杂样本触发增强解析策略

# 14. 参考资料

官方文档：

- Semantic Scholar API Overview: https://www.semanticscholar.org/product/api
- Semantic Scholar Graph API: https://api.semanticscholar.org/api-docs/graph
- arXiv API User Manual: https://info.arxiv.org/help/api/user-manual.html
- Crossref REST API Tips: https://www.crossref.org/documentation/retrieve-metadata/rest-api/tips-for-using-the-crossref-rest-api/
- OpenAlex API Intro: https://developers.openalex.org/api-reference/introduction
- Unpaywall API 示例: https://api.unpaywall.org/v2/10.1038/nature12373?email=demo@unpaywall.org

开源项目：

- RAGFlow: https://github.com/infiniflow/ragflow
- Onyx: https://github.com/onyx-dot-app/onyx
- Dify: https://github.com/langgenius/dify
- AnythingLLM: https://github.com/Mintplex-Labs/anything-llm
- Docling: https://github.com/docling-project/docling
- GROBID: https://github.com/grobidOrg/grobid
