# PR18 Celery Upload/Import Pipeline 稳定性重构计划

## 1. 背景与目标

本计划用于修复上传-导入-解析-入库链路在 Celery worker 下的关键稳定性问题，重点覆盖：

- 任务回调丢失导致 ImportJob 卡死
- `process_import_job` 长时间阻塞 worker
- dedupe 决策后无法稳定续跑
- 重试缺少指数退避，失败风暴风险
- 批量导入对 local_file 缺少“一次提交、多文件上传”闭环

目标是通过一个中等范围 PR 完成可落地且低风险的架构收敛，不做跨存储系统的大迁移。

## 2. 现状调用链（真实代码）

1. 前端创建 ImportJob：`POST /api/v1/knowledge-bases/{kb_id}/imports`
2. 前端上传文件：`PUT /api/v1/import-jobs/{job_id}/file`
3. API 触发 `process_import_job.delay(job_id)`
4. `process_import_job` 创建 `ProcessingTask` 并触发 `process_single_pdf_task.delay(paper_id)`
5. `process_single_pdf_task` 调用 `PDFProcessor.process_pdf_task(task_id)`
6. 成功后调用 `on_processing_task_complete.delay(task_id, paper_id)`
7. 回调更新 ImportJob 为 completed

现有风险点：步骤 6 和 7 通过独立队列任务串联，任一环节失败会导致 ImportJob 与 ProcessingTask 脱节。

## 3. 范围与非范围

### 3.1 本 PR 范围

- Import worker 去阻塞化：移除长轮询等待，快速释放 worker
- Completion 双保险：在 `pdf_tasks` 内直接同步 ImportJob 状态，同时保留回调任务并增强重试
- 重试策略增强：为关键 Celery task 增加指数退避
- Dedupe 决策续跑闭环：`import_as_new_version/force_new_paper` 决策后自动重新入队
- Dedupe 续跑防二次命中：worker 识别已做决策并跳过再次 dedupe
- 批量本地文件上传闭环：新增批量上传 API（按 batch + job 关联文件），后端统一校验并入队
- 最小测试覆盖：新增/更新单测验证关键路径

### 3.2 非范围（后续 PR）

- Celery 全面迁移为原生 async worker 模式
- Postgres/Milvus/Neo4j 的 Saga 补偿事务框架
- Broker 更换（Redis -> RabbitMQ/Kafka）
- 前端完整上传体验重做（断点续传、秒传、断网恢复）

## 4. 设计决策

### D1. 导入 worker 不再等待解析完成

- 现状：`process_import_job` 调用 `track_processing_stages` 轮询最长 1 小时
- 方案：在触发 `process_single_pdf_task` 后立即返回
- 理由：worker_concurrency=1 时，长任务会阻塞后续 job

### D2. ImportJob 完成状态改为“同任务内直写 + 回调兜底”

- 在 `process_single_pdf_async` 成功分支内直接按 `processing_task_id` 更新 ImportJob `completed`
- 在失败分支内同步更新 ImportJob 为 `failed`
- 保留 `on_processing_task_complete` 作为兼容与兜底，但加重试/退避

### D3. Dedupe 决策后自动续跑

- `submit_dedupe_decision` 对 `import_as_new_version` 与 `force_new_paper`：
  - 将 job 置为 `queued/materializing_paper`
  - 清理 `next_action`
  - 触发 `process_import_job.delay(job_id)`
- `reuse_existing`：保持直接完成路径
- `cancel`：保持取消路径

### D4. Dedupe 决策续跑防重复命中

- worker 执行 dedupe 前判断：
  - 若 `job.dedupe_decision in {import_as_new_version, force_new_paper}`
  - 直接标记 dedupe 已解析并跳过 dedupe 检查

### D5. 批量 local_file 上传闭环

新增端点：

- `POST /api/v1/import-batches/{batch_id}/files`

请求采用 multipart：

- `manifest`：JSON，结构为 `[{"importJobId":"...","filename":"..."}, ...]`
- `files`：多个 PDF 文件

处理逻辑：

- 校验 batch 归属用户
- 仅允许 `local_file` 且 `status=created` 的 job
- filename 与 manifest 关联，逐个执行与单文件上传一致的校验
- 写入存储、计算 sha256、调用 `set_file_info`
- 逐个触发 `process_import_job.delay(job_id)`

## 5. 详细任务拆分

### Task A: Worker 去阻塞与回调可靠性增强

涉及文件：

- `apps/api/app/workers/import_worker.py`
- `apps/api/app/tasks/pdf_tasks.py`

改动：

- 移除 `track_processing_stages` 调用链
- `process_import_job` 增加 retry backoff 配置
- `on_processing_task_complete` 增加 bind/retry/backoff
- `pdf_tasks` 新增 `sync_import_job_from_processing_task(...)` helper
- 在成功/失败分支写 ImportJob 终态

验收：

- 即使 callback 失败，ImportJob 也可被标记完成/失败
- Import worker 不再长轮询

### Task B: Dedupe 决策闭环修复

涉及文件：

- `apps/api/app/api/imports/dedupe.py`
- `apps/api/app/workers/import_worker.py`

改动：

- 决策后自动重入队
- worker 在决策续跑场景跳过二次 dedupe

验收：

- `awaiting_dedupe_decision -> queued -> running` 可自动推进

### Task C: 批量 local_file 上传端点

涉及文件：

- `apps/api/app/api/imports/batches.py`
- 可选：`apps/web/src/services/importApi.ts`（补充客户端方法）

改动：

- 新增 batch 文件上传端点
- 复用单文件校验规则（PDF 魔数、大小、扩展名）
- 返回每项处理结果（accepted/rejected + reason）

验收：

- 一次请求上传多个文件并触发多个 job 入队

### Task D: 测试与回归

新增测试：

- dedupe 决策续跑测试
- 回调失败时 ImportJob 仍由 `pdf_tasks` 完成同步测试（mock）
- 批量上传端点校验与入队测试

回归命令：

- `cd apps/api && pytest -q tests/unit/test_services.py --maxfail=1`
- `cd apps/api && pytest -q tests/unit/test_kb_upload_api.py --maxfail=1`
- `cd apps/api && pytest -q tests/unit/test_import_pipeline_reliability.py --maxfail=1`（新增）

## 6. 风险矩阵与缓解

1. 风险：ImportJob 与 ProcessingTask 状态不一致

- 缓解：双保险写状态（任务内直写 + 回调兜底）

2. 风险：批量上传 manifest 与文件映射错误

- 缓解：强校验（filename 唯一、job 归属、文件数一致）

3. 风险：重试导致重复处理

- 缓解：按 job 状态做幂等门禁（completed/cancelled 不再处理）

4. 风险：现网行为变化影响前端

- 缓解：保持原响应结构，新增字段仅追加

## 7. 回滚策略

- 单 PR 原子回滚：`git revert <PR18 commit>`
- 回滚后恢复原有 callback-only 语义
- 批量上传新端点可保留但不在前端调用

## 8. Plan 审查结论（预审）

- 可行性：高（不改核心 schema，不引入新基础设施）
- 复杂度：中（3 个后端模块 + 1 组测试）
- 边界清晰：是（仅上传导入链路）
- 建议执行顺序：A -> B -> C -> D

## 9. 审查补充与修订

根据计划评审，补充以下强约束，避免执行期歧义：

1. 并发一致性策略

- 不新增 schema 字段。
- 通过状态门禁实现幂等：`completed/cancelled` 视为终态，不允许被回调或重试覆盖。
- `sync_import_job_from_processing_task` 与 `on_processing_task_complete` 均遵守同一门禁。

2. 任务依赖 DAG

- Wave 1：Task A + 单测（A1）
- Wave 2：Task B + 单测（B1），依赖 Wave 1
- Wave 3：Task C + 单测（C1），依赖 Wave 2
- Wave 4：回归与集成验证（D2），依赖 Wave 3

3. 验收标准细化

- A-AC1：`process_import_job` 不再执行长轮询，任务在触发 PDF 任务后快速返回。
- A-AC2：即使 `on_processing_task_complete` 未执行，ImportJob 仍可由 `pdf_tasks` 同步到终态。
- B-AC1：`import_as_new_version/force_new_paper` 决策后会自动重新入队。
- B-AC2：续跑场景不会再次进入 `awaiting_dedupe_decision`。
- C-AC1：批量上传支持部分成功，返回 `accepted/rejected` 明细。
- C-AC2：manifest 与文件映射错误时给出明确错误，不静默失败。

4. 范围澄清

- 本 PR 不改前端页面流程，仅新增后端批量上传能力与可选 SDK/服务方法。
- 前端批量上传交互增强（如断点续传、拖拽批处理进度面板）留在后续 PR。

5. 部署与回滚

- 该 PR 不引入 DB migration。
- 部署前要求消费队列处于低水位；如异常可整 PR 回滚。
