# Checklist

## Task 1: Unified Async Task Base & Registry

- [ ] `BaseAsyncTask` 抽象基类已创建，包含统一生命周期钩子（on_start/on_stage_change/on_progress/on_complete/on_fail/on_cancel）
- [ ] `BaseAsyncTask` 包含 checkpoint 持久化接口（save_checkpoint/load_checkpoint）
- [ ] `BaseAsyncTask` 包含成本记录接口（record_cost）
- [ ] `BaseAsyncTask` 包含取消检查接口（is_cancelled/check_cancellation）
- [ ] 任务类型注册表已创建，task_type 枚举覆盖 import_job/review/compare/reading_card/notes_generation
- [ ] `process_import_job` 已重构为继承 BaseAsyncTask 生命周期
- [ ] `process_single_pdf_task` 已重构为继承 BaseAsyncTask 生命周期
- [ ] 现有导入流程功能无回归（手动验证或自动化测试通过）

## Task 2: Task Cancellation Propagation

- [ ] Redis 取消信号存储已实现（task:cancel:{task_id}）
- [ ] `BaseAsyncTask.is_cancelled()` 正确检查 Redis 取消信号
- [ ] `BaseAsyncTask.check_cancellation()` 在阶段转换前调用，取消时抛出 TaskCancelledError
- [ ] ProcessingTask 模型新增 cancelled_at、cancellation_reason 字段
- [ ] ImportJob 状态机新增 cancelling 中间状态
- [ ] 取消传播：ImportJob 取消时传播到关联 ProcessingTask
- [ ] `POST /api/v1/tasks/{task_id}/cancel` 端点已实现，终态任务返回 409
- [ ] 取消后资源清理正确：并发槽位释放、已完成子阶段保留、未开始子阶段标记 skipped
- [ ] 取消导入任务后 worker 正确停止、资源正确释放

## Task 3: Task Recovery from Checkpoint

- [ ] ProcessingTask 的 checkpoint 字段（checkpoint_stage/checkpoint_data/checkpoint_version）已扩展使用
- [ ] `BaseAsyncTask.save_checkpoint()` 每阶段完成后自动保存
- [ ] `BaseAsyncTask.load_checkpoint()` 恢复时正确加载
- [ ] ImportJob 状态机新增 recovering 中间状态
- [ ] `process_import_job` 支持从 checkpoint 恢复执行，跳过已完成阶段
- [ ] `process_single_pdf_task` 支持从 checkpoint 恢复执行
- [ ] 恢复时追加 retry_trace_id
- [ ] 模拟 worker 崩溃后重试任务从 checkpoint 恢复而非从头开始

## Task 4: Multi-Layer Cache Implementation

- [ ] 统一缓存管理器 CacheManager 已创建，包含 CacheLayer 抽象接口
- [ ] 外部搜索缓存已实现，整合现有 ImportCache
- [ ] PDF 下载缓存已实现，在 pdf_download_worker 中集成
- [ ] Embedding 缓存已实现，在 embedding 服务层集成
- [ ] Rerank 缓存已实现，在 reranker 服务层集成
- [ ] RAG 查询响应包含 cache_hit/cache_type/cache_age_seconds 字段
- [ ] 缓存键包含 model_version，模型切换后旧缓存自动失效
- [ ] 相同请求第二次命中缓存、模型切换后缓存正确失效

## Task 5: Task Observability API

- [ ] ProcessingTask 模型新增 cost_breakdown、cache_stats 字段，迁移脚本已执行
- [ ] `GET /api/v1/tasks` 端点已实现，支持 status/task_type 过滤与分页
- [ ] `GET /api/v1/tasks/{task_id}` 端点已实现，返回完整任务详情含 stage_timings/cost_breakdown/cache_stats
- [ ] `POST /api/v1/tasks/{task_id}/retry` 端点已实现，检查 is_retryable 并重置入队
- [ ] SSE 新增 cancelled/recovering/cost_update 事件
- [ ] API 返回正确的任务状态、阶段耗时、失败分类

## Task 6: Cost and Latency Observability

- [ ] TokenTracker 已扩展为通用 CostTracker，支持 embedding/rerank/PDF 下载成本记录
- [ ] BaseAsyncTask 生命周期钩子中集成成本记录
- [ ] 延迟指标记录：stage_timings 各阶段耗时、queue_wait_ms
- [ ] 错误分类枚举已扩展（network_error/timeout/rate_limit/model_error/storage_error/validation_error/unknown）
- [ ] 缓存命中率统计已实现，聚合到 cache_stats
- [ ] Analytics 页面新增成本趋势图、延迟分布图、错误分类图、缓存命中率面板
- [ ] 执行任务后成本/延迟/错误/缓存指标正确记录并可查询

## Task 7: Frontend Task Observability UI

- [ ] TaskListPanel 组件已创建，按状态分组展示任务列表
- [ ] TaskDetailDrawer 组件已创建，展示阶段时间线、成本分项、缓存统计、错误详情
- [ ] 取消交互已增强：运行中任务显示取消按钮、确认对话框、状态即时更新
- [ ] 重试交互已增强：失败可重试任务显示重试按钮、checkpoint 恢复提示
- [ ] Analytics 页面扩展：成本趋势图、延迟分布图、错误分类图、缓存命中率组件
- [ ] 前端正确展示任务状态、可取消/重试、观测面板数据正确

## Task 8: Spec & Contract Updates

- [ ] system-overview.md 已更新（统一异步任务框架、缓存策略、可观测性）
- [ ] api-contract.md 已更新（任务查询/取消/重试接口、缓存命中字段、SSE 事件）
- [ ] resources.md 已更新（Task 资源模型扩展、缓存资源定义、状态机更新）
- [ ] import_processing_state_machine.md 已更新（cancelling/recovering 状态、取消传播、恢复协议）
- [ ] phase-delivery-ledger.md 已更新（Phase 3.0-E 交付单元记录）
