# Upload Entry Audit

审计范围：

- `apps/api/app/api/papers/paper_upload.py`
- `apps/api/app/api/kb/kb_import.py`
- `apps/api/app/api/uploads.py`
- `apps/api/app/api/imports/upload_sessions.py`
- `apps/api/app/services/upload_session_service.py`
- `apps/api/app/workers/import_worker.py`
- `apps/api/app/tasks/pdf_tasks.py`

当前结论：

- 正式链路中仍存在绕过 ImportJob 的入口：`POST /api/v1/papers/upload`、`POST /api/v1/papers/webhook`、`POST /api/v1/uploads`、`POST /api/v1/uploads/batch/{batch_id}/files`。
- `POST /api/v1/papers/upload/local/{storage_key}` 只是文件写盘入口，但它服务于旧的 `papers -> webhook` 两段式流程，实际仍在帮助旧 pipeline 存活。
- KB 相关入口和 upload session completion 已经基本是 ImportJob-first。
- `apps/api/app/tasks/pdf_tasks.py` 仍通过模拟阶段推进 `ProcessingTask.status`，不是以 PDFCoordinator 真实阶段为准。
- 本地存储路径仍有多处直接使用 `os.getenv("LOCAL_STORAGE_PATH")`，和 `settings.LOCAL_STORAGE_PATH` 并存。

重点风险文件：

- `apps/api/app/api/papers/paper_upload.py`
- `apps/api/app/api/uploads.py`
- `apps/api/app/tasks/pdf_tasks.py`
- `apps/api/app/workers/import_worker.py`
- `apps/api/app/services/upload_session_service.py`

| endpoint/function | current flow | target flow | risk | action |
|---|---|---|---|---|
| `POST /api/v1/papers/upload` | validate PDF -> save file -> create `Paper` -> create `ProcessingTask` -> return task/paper | validate PDF -> `create_import_job_from_uploaded_file(...)` -> `ImportJob` queued -> `process_import_job.delay(job.id)` -> compat response | 直接绕过 ImportJob；`storage_key` 规则不统一；无 `UploadHistory` 同步；重试幂等性弱 | 改为兼容转发到统一 helper，禁止直接创建 `Paper`/`ProcessingTask` |
| `POST /api/v1/papers/webhook` | accept `paperId` + `storageKey` -> create `ProcessingTask` for existing `Paper` | 兼容入口仅查找/复用 `ImportJob`，不得再直接建 `ProcessingTask`；必要时转发到 ImportJob resume/complete helper | 旧两段式流程继续绕过 ImportJob；会制造额外任务 | 保留 endpoint，但内部改为 ImportJob-first compatibility shim |
| `POST /api/v1/papers/upload/local/{storage_key}` | validate ownership/path -> write file to disk -> return `storageKey` | 仅作为受控文件写入 helper，被 ImportJob upload session/legacy shim 调用 | 单独存在会继续服务旧 `paper + webhook` 流程；未绑定 ImportJob | 限定只服务 ImportJob 链路，避免独立业务语义 |
| `POST /api/v1/knowledge-bases/{kb_id}/upload` | validate PDF -> `ImportJobService.create_job(local_file)` -> save file -> `set_file_info` -> `process_import_job.delay` | 保持 ImportJob-first，内部抽到统一 helper | 路径实现仍用 `os.getenv("LOCAL_STORAGE_PATH")`；helper 逻辑重复 | 抽到统一 `create_import_job_from_uploaded_file(...)` |
| `POST /api/v1/knowledge-bases/{kb_id}/batch-upload` | per file: validate -> local-file `ImportJob` -> save file -> `set_file_info` -> queue worker | per file 继续走统一 helper | helper 重复；批量结果与统一状态机文档未绑定 | 复用统一 helper，批量仅负责编排结果 |
| `POST /api/v1/knowledge-bases/{kb_id}/import-url` | create `ImportJob(source_type=pdf_url)` -> queue worker | 保持 ImportJob-first | 最终状态依赖 `pdf_tasks.py` 真实化之前仍不可靠 | 保持入口，收口状态同步 |
| `POST /api/v1/knowledge-bases/{kb_id}/import-arxiv` | create `ImportJob(source_type=arxiv)` -> queue worker | 保持 ImportJob-first | 同上；状态同步和失败显式化仍要补强 | 保持入口，接入统一状态机 |
| `POST /api/v1/import-jobs/{job_id}/upload-sessions` | verify existing local-file `ImportJob` -> create/resume `UploadSession` | 保持 ImportJob-first | 本地路径仍用 `os.getenv(...)`；只允许 `created/failed` job 进入 | 路径改用 settings；保持单一正式本地上传入口 |
| `PUT /api/v1/upload-sessions/{session_id}/parts/{part_number}` | persist chunk part to local storage | 保持 ImportJob upload session protocol | 本地路径仍用 `os.getenv(...)` | 改用统一 storage path helper |
| `POST /api/v1/upload-sessions/{session_id}/complete` | assemble file -> compute sha256 -> `ImportJobService.set_file_info` -> mark session completed -> `process_import_job.delay(job.id)` | 保持 ImportJob-first | 本地路径仍用 `os.getenv(...)`；`storage_key` 规则少了 `uploads/` 前缀 | 统一到权威 `storage_key` 规则和 settings |
| `POST /api/v1/uploads` | validate PDF -> save file -> create `Paper` -> create `UploadHistory` -> create `ProcessingTask` | validate PDF -> unified helper -> queued `ImportJob` -> compat response + UploadHistory sync | 直接绕过 ImportJob；状态与新链路割裂；旧进度模型 | 改为兼容转发 ImportJob-first |
| `POST /api/v1/uploads/batch` | create `PaperBatch` + placeholder `Paper` records + upload URLs | 兼容入口应改为创建 batch-level import orchestration 或逐文件 ImportJob 准备态；至少不能以 `Paper` 作为上传前主实体 | 上传前就 materialize `Paper`，与权威链路冲突 | 本阶段先标记兼容入口，避免新增并行 pipeline；后续改为 ImportJob batch orchestration |
| `POST /api/v1/uploads/batch/{batch_id}/files` | save file -> update/create `Paper` -> when batch full create `ProcessingTask` for papers | 逐文件走 ImportJob-first，禁止批量直接创建 `ProcessingTask` | 直接绕过 ImportJob；批量重试会重复造 task | 本阶段至少改成兼容转发/阻断独立 task 创建 |
| `GET /api/v1/uploads/history` / `GET /api/v1/knowledge-bases/{kb_id}/upload-history` | read `UploadHistory` + `ProcessingTask.status`, using legacy progress map | read unified ImportJob/ProcessingTask real stage projection | 仍依赖旧假阶段名：`processing_ocr`, `extracting_imrad`, `storing_vectors` 等 | 改成从真实状态机映射展示进度 |
| `POST /api/v1/uploads/history` | create standalone `UploadHistory` record for external URL | 不应作为正式 import pipeline；若保留仅作历史记录兼容 | 容易被误用成“外部 URL 导入入口”，但不创建 ImportJob | 保留为 history-only endpoint，并在报告中明确非正式导入入口 |
| `process_import_job(job_id)` | resolve/download/hash/dedupe/materialize paper -> create/reuse `ProcessingTask` -> queue `process_single_pdf_task` | 保持为唯一 ImportJob orchestration worker | 本地路径仍用 `os.getenv(...)`；已有 completed task 时会直接完成 job，需要和正式终态同步测试一起验证 | 改用 settings 和统一状态同步测试覆盖 |
| `process_single_pdf_async(...)` / `process_single_pdf_task` path | create/reuse `ProcessingTask` -> simulate stage loop -> call `PDFProcessor.process_pdf_task` -> set terminal state | `ProcessingTask` stage 只由真实 pipeline 更新；`PDFCoordinator` 作为唯一正式来源 | 当前为假阶段；ImportJob/UploadHistory 读取到的是模拟进度 | 删除模拟阶段循环，引入 coordinator stage callback |
| `PDFProcessor.process_pdf_task(task_id)` | adapter -> `PDFCoordinator.process(task_id)` | 保持 adapter-only | 旧类内仍保留大量 legacy methods，正式路径和过时实现边界不清 | 标记 legacy methods deprecated，测试正式路径只走 coordinator |

需要统一替换的 `LOCAL_STORAGE_PATH` 读取点：

- `apps/api/app/api/kb/kb_import.py`
- `apps/api/app/api/uploads.py`
- `apps/api/app/services/upload_session_service.py`
- `apps/api/app/workers/import_worker.py`
- `apps/api/app/workers/import_worker_helpers.py`
- `apps/api/app/core/storage.py`
- `apps/api/app/api/imports/jobs.py`
- `apps/api/app/api/imports/batches.py`
