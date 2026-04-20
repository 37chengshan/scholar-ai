# EP-2026-04-20 vNext 冻结版执行计划（PR）

作者：glm5.1+37chengshan
日期：2026-04-20
分支：feat/vnext-freeze-import-rag-20260420
基线：origin/main@94c3c28

## 1. 目标与边界（严格对齐任务单）

本版只做以下冻结目标：
1. 导入任务可视化与实时反馈（SSE 主，轮询 fallback）
2. 本地文件默认导入路径统一为 Upload Session
3. DOI / PDF URL 下载成功率提升（多源回退 + 失败可救）
4. RAG 引用可信度最小闭环（默认带引用 + 低置信提示）

本版不做：
1. 知识图谱重构
2. 重度 Agentic RAG 扩展
3. 更多外部源接入
4. Chat 视觉动画精修
5. 大范围 UI 改版

停止线：
1. 四大目标验收通过即停
2. 非四大目标需求记入 vNext+1
3. 不直接提升主链路成功率/可恢复性/可信度的优化延期

## 2. 代码现状与差距映射

## A. 导入任务实时化

已具备：
1. 后端已有 SSE 端点：apps/api/app/api/imports/events.py
2. 前端 importApi 已有 getStreamUrl：apps/web/src/services/importApi.ts

差距：
1. useSearchImportFlow 仍以固定 30 次轮询为主逻辑
2. 缺少 subscribeImportJob(jobId) 的统一封装
3. 缺少 SSE 断线自动 fallback 到 get(jobId) 轮询
4. 缺少刷新后按 jobId 恢复任务卡片的显式状态恢复
5. 验收要求“导入后 1 秒内可见阶段变化”尚未在前端时序中明确

## B/C. 默认导入路径统一 + 上传性能与恢复收口

已具备：
1. useChunkUpload 已走 create ImportJob + create upload session
2. useUploadRecovery 已支持 needs_file_reselect
3. 服务端 assembled file 后计算 sha256 已存在

差距：
1. useChunkUpload 当前分片串行上传（for 循环）
2. 单分片失败重试无指数退避
3. 前端创建 upload session 仍默认做全文件 arrayBuffer() + SHA256
4. direct upload 接口仍是通用路径，需显式标注 fallback/small-file only
5. 恢复状态需收口为 pending/queued/completed/aborted/needs_file_reselect

## D. DOI / PDF URL 成功率提升

已具备：
1. doi_adapter 有 CrossRef + S2 路径
2. pdf_url_adapter 有 HTTPS/content-type/magic bytes/size 校验

差距：
1. DOI 下载未实现 S2 -> Unpaywall -> OpenAlex 多源回退
2. 未统一记录 tried_sources 与失败原因
3. pdf_url 在 HEAD 失败时未降级 GET 探测
4. DOI 无 PDF 时 nextAction 需明确 upload_local_pdf
5. 外部源调用与限流策略未在实现细节中落地（Unpaywall/OpenAlex）

## E. Import Worker 稳定性

已具备：
1. completed 仅在 processing 完成后回写的主框架已存在

差距：
1. import_worker.py 使用了 uuid.uuid4() 但未导入 uuid（显式 bug）
2. 关键日志字段需要补全（job_id/stage/source_type/processing_task_id/error_code）
3. jobs.py 的 direct upload 路径需明确 fallback 定位

## F. RAG 最小可信度闭环

已具备：
1. 后端已做 citation contract normalize_source_contract
2. 后端已有 confidence 与 confidence_explain

差距：
1. 缺少 answerEvidenceConsistency 指标
2. 缺少低置信原因枚举（evidence_insufficient/evidence_conflict/retrieval_weak）
3. 前端 citation 类型仍是旧字段（page/snippet/content_type），需统一兼容新契约字段
4. 缺少最小 20 条评测集 fixture

## 3. 文件级实施顺序（严格按任务单）

## 第 1 组：统一契约
1. apps/web/src/services/importApi.ts
2. apps/api/app/api/imports/jobs.py
3. apps/api/app/api/imports/events.py

产出：status/stage/error/nextAction 前后端一致；direct upload 标注 fallback。

## 第 2 组：接 SSE 与任务卡片
1. apps/web/src/features/search/hooks/useSearchImportFlow.ts
2. apps/web/src/features/search/hooks/useSearchImportFlow.ts 内新增 ImportProgressCard 状态段（不新建页面）
3. KB 页面导入完成跳转/刷新处理

产出：SSE 主链路 + 轮询 fallback，刷新可恢复。

## 第 3 组：统一上传主路径与恢复
1. apps/web/src/features/uploads/hooks/useChunkUpload.ts
2. apps/web/src/features/uploads/hooks/useUploadRecovery.ts
3. apps/api/app/api/imports/upload_sessions.py
4. apps/api/app/services/upload_session_service.py

产出：并发分片 + 指数退避 + 不强依赖前端全文件 hash。

## 第 4 组：修下载成功率
1. apps/api/app/services/source_adapters/doi_adapter.py
2. apps/api/app/services/source_adapters/pdf_url_adapter.py
3. apps/api/app/services/import_rate_limiter.py

产出：DOI 多源回退、HEAD->GET 探测、失败来源可见。

外部依赖与实现约束：
1. 继续使用现有 httpx，不新增第三方 SDK 依赖。
2. Unpaywall/OpenAlex 通过 HTTP API 调用，失败进入下一个来源。
3. 在 import_rate_limiter.py 增加对应 limiter（unpaywall/openalex）或复用统一 external_import_limiter。

## 第 5 组：RAG 可信度收口
1. apps/api/app/api/rag.py
2. apps/web/src/features/chat/components/workspaceTypes.ts
3. apps/web/src/features/chat/workspace/ChatWorkspaceV2.tsx
4. apps/web/src/features/chat/components/citation-panel/CitationPanel.tsx
5. 测试/评测 fixture（apps/api/tests）

产出：默认带 citation，低置信可解释且不伪确定。

## 4. 逐项实施清单（必须完成）

## A. 导入任务实时化
1. 新增 importApi.subscribeImportJob(jobId, handlers)（EventSource 封装）
2. 消费 status_update/stage_change/progress/completed/error/cancelled
3. useSearchImportFlow 状态机只认 status/stage/error/nextAction
4. SSE 异常自动回退 importApi.get(jobId) 轮询
5. 页面刷新从 jobId 恢复任务状态
6. 从创建任务到首次 stage_change/status_update 的前端可见时延控制在 <= 1s（通过立即发起 SSE + 首帧状态注入）

## B. 默认导入路径统一
1. 本地文件入口统一 ImportJob + UploadSession
2. PUT /import-jobs/{job_id}/file 文档和响应中标记 fallback/small-file only
3. 上传工作区持久化 importJobId + uploadSessionId
4. 刷新优先恢复 upload session
5. 本地文件缺失转 needs_file_reselect

## C. 上传性能与恢复收口
1. 分片并发上传 2~4（默认 3）
2. 单分片失败独立重试 + 指数退避
3. 前端不再强制全文件 arrayBuffer() hash
4. 优先服务端 assembled 后计算 sha256
5. 恢复状态显式区分 pending/queued/completed/aborted/needs_file_reselect

实现参数：
1. 并发策略：Promise.allSettled + 固定并发窗口（3）
2. 重试策略：初始 500ms，倍率 2，最大 4000ms，最多 3 次
3. SHA256 策略：默认不传；仅在浏览器空闲时可选计算

## D. DOI / PDF URL 成功率
1. DOI 下载链：S2 openAccessPdf -> Unpaywall -> OpenAlex -> 手动上传接力
2. 记录 tried_sources + source_errors
3. pdf_url HEAD 失败时允许 GET 探测
4. 下载后统一校验 HTTPS/content-type/magic bytes/size
5. awaiting_user_action 返回 nextAction.type=upload_local_pdf

## E. Worker 稳定性
1. 修复 import_worker.py 中 processing_task_id = str(uuid.uuid4()) 对应的 uuid 导入缺失（文件顶部 imports 区域补 `import uuid`）
2. 检查 ProcessingTask 复用与 completed 回写路径
3. direct upload 默认路径退居 fallback
4. 补关键日志字段

## F. RAG 可信度闭环
1. 统一 citation 字段：paper_id/source_id/page_num/section_path/anchor_text/text_preview
2. 增加 answerEvidenceConsistency 指标
3. 低置信原因：evidence_insufficient/evidence_conflict/retrieval_weak
4. 普通 query 与 agentic query 最小边界隔离（策略分流，不改架构）
5. 建立 20 条最小评测集并可回归执行

评测集落点与格式：
1. 文件：apps/api/tests/fixtures/rag/vnext_freeze_eval_set.json
2. 条目字段：query、paper_ids、expected_citation_fields、expected_low_confidence_reason、notes
3. 执行：在 apps/api/tests/unit/test_rag_confidence.py 增加参数化回归入口

## 5. 测试冻结清单

手工场景：
1. 本地 PDF 上传成功到可问答
2. 上传中途刷新可恢复
3. DOI 成功自动下载入库
4. DOI 无 PDF 引导手动上传接力
5. URL HEAD 失败但 GET 探测成功
6. dedupe hit 后可继续决策
7. RAG 回答带引用
8. 低置信回答有提示

自动化最低要求：
1. ImportJob API 契约测试
2. Upload session 状态迁移测试
3. DOI adapter 回退链测试
4. RAG citation contract 测试

质量门槛：
1. 单测/集成/E2E 综合覆盖率 >= 80%
2. 关键链路（A/B/C/D/F）至少各有 1 条自动化断言

映射关系：
1. 场景 1/2 对应 B/C
2. 场景 3/4/5 对应 D
3. 场景 6 对应 A/B/E
4. 场景 7/8 对应 F

## 6. 风险缓解与约束

发现与约束：
1. 任务单中的 useChunkUpload/useUploadRecovery 路径在仓库中实际存在，按真实路径执行。
2. “导入任务展示组件”当前无独立新页面，本次在现有搜索导入流程与跳转逻辑中接入，避免超范围 UI 扩张。

风险与缓解：
1. DOI 多源回退依赖外部服务可用性。缓解：统一 tried_sources 记录并给出 upload_local_pdf nextAction。
2. 并发分片可能放大失败重试。缓解：限制并发=3 + 指数退避 + 每片独立失败。

## 7. 提交与 PR 策略

建议分 4~6 个原子提交：
1. Import SSE 主链路 + fallback
2. Upload session 主路径/并发上传/恢复
3. DOI/PDF URL 回退链
4. Worker 稳定性修补
5. RAG 可信度字段与前端展示
6. 测试与评测集

提交依赖关系：
1. 提交 2 依赖提交 1 的导入状态契约稳定
2. 提交 3 可并行开发，但合并前需通过提交 1/2 的契约测试
3. 提交 5 依赖提交 1 的字段契约与提交 3 的错误原因输出
4. 提交 6 必须在前 1~5 完成后统一回归

PR 组织：
1. 单 PR，多原子提交（本次冻结版）
2. 合并前必过：类型检查、lint、测试、覆盖率门槛、关键链路手工验收

PR 标题建议：
feat: freeze vnext import-recovery-rag trust chain (SSE/session/DOI fallback/citation confidence)
