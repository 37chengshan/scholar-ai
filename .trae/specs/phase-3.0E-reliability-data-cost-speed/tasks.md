# Tasks

## Task 1: Unified Async Task Base & Registry

建立统一异步任务基类与注册机制，使所有长任务走统一路径。

- [ ] SubTask 1.1: 创建 `apps/api/app/core/task_framework/base.py`，定义 `BaseAsyncTask` 抽象基类
  - 统一生命周期钩子：`on_start`、`on_stage_change`、`on_progress`、`on_complete`、`on_fail`、`on_cancel`
  - 统一 checkpoint 持久化接口：`save_checkpoint(stage, data)`、`load_checkpoint()`
  - 统一成本记录接口：`record_cost(category, amount, model)`
  - 统一取消检查接口：`is_cancelled()`、`check_cancellation()`
- [ ] SubTask 1.2: 创建 `apps/api/app/core/task_framework/registry.py`，定义任务类型注册表
  - `task_type` 枚举：`import_job`、`review`、`compare`、`reading_card`、`notes_generation`
  - 每个 task_type 映射到对应的 BaseAsyncTask 实现类与 Celery 任务函数
- [ ] SubTask 1.3: 创建 `apps/api/app/core/task_framework/__init__.py`，导出公共接口
- [ ] SubTask 1.4: 重构 `import_worker.py` 的 `process_import_job`，使其继承 BaseAsyncTask 生命周期
- [ ] SubTask 1.5: 重构 `pdf_tasks.py` 的 `process_single_pdf_task`，使其继承 BaseAsyncTask 生命周期
- [ ] SubTask 1.6: 验证：现有导入流程功能不回归

## Task 2: Task Cancellation Propagation

实现任务取消信号传播机制，使用户可取消运行中的长任务。

- [ ] SubTask 2.1: 在 Redis 中建立取消信号存储
  - Key: `task:cancel:{task_id}`，Value: `{"reason": "user_request", "requested_at": timestamp}`
  - TTL: 1 小时（防止信号残留）
- [ ] SubTask 2.2: 在 `BaseAsyncTask` 中实现 `is_cancelled()` 与 `check_cancellation()`
  - `is_cancelled()` 检查 Redis 取消信号
  - `check_cancellation()` 在每个阶段转换前调用，若已取消则抛出 `TaskCancelledError`
- [ ] SubTask 2.3: 在 `ProcessingTask` 模型中新增 `cancelled_at`、`cancellation_reason` 字段
- [ ] SubTask 2.4: 在 `ImportJob` 状态机中新增 `cancelling` 中间状态
  - 取消请求 → `cancelling` → worker 确认 → `cancelled`
- [ ] SubTask 2.5: 实现取消传播：ImportJob 取消时传播到关联 ProcessingTask
  - 在 `import_worker.py` 的 `process_import_job` 中检查父任务取消信号
- [ ] SubTask 2.6: 实现 `POST /api/v1/tasks/{task_id}/cancel` 端点
  - 运行中/排队中任务可取消
  - 终态任务返回 409 Conflict
- [ ] SubTask 2.7: 实现取消后资源清理
  - 释放并发槽位（`ConcurrentControl.decrement_pending`）
  - 保留已完成子阶段结果
  - 未开始子阶段标记为 `skipped`
- [ ] SubTask 2.8: 验证：取消导入任务后 worker 正确停止、资源正确释放

## Task 3: Task Recovery from Checkpoint

实现任务从 checkpoint 恢复执行的能力。

- [ ] SubTask 3.1: 扩展 `ProcessingTask` 的 checkpoint 字段使用
  - `checkpoint_stage`：记录最近完成的阶段
  - `checkpoint_data`：JSON，存储恢复所需上下文（storage_key、paper_id 等）
  - `checkpoint_version`：checkpoint 格式版本
- [ ] SubTask 3.2: 在 `BaseAsyncTask` 中实现 `save_checkpoint()` 与 `load_checkpoint()`
  - 每个阶段完成后自动保存 checkpoint
  - 恢复时从 checkpoint 阶段开始，跳过已完成阶段
- [ ] SubTask 3.3: 在 `ImportJob` 状态机中新增 `recovering` 中间状态
  - 重试请求 → `recovering`（加载 checkpoint）→ `running`（从 checkpoint 阶段继续）
- [ ] SubTask 3.4: 重构 `process_import_job` 支持恢复执行
  - 检查 `checkpoint_stage`，若存在则跳过已完成阶段
  - 恢复时追加 `retry_trace_id`
- [ ] SubTask 3.5: 重构 `process_single_pdf_task` 支持恢复执行
  - PDFCoordinator 各阶段完成后保存 checkpoint
  - 恢复时从 checkpoint 阶段继续
- [ ] SubTask 3.6: 验证：模拟 worker 崩溃后，重试任务从 checkpoint 恢复而非从头开始

## Task 4: Multi-Layer Cache Implementation

实现外部搜索缓存、PDF 下载缓存、embedding 缓存、rerank 缓存。

- [ ] SubTask 4.1: 创建 `apps/api/app/core/cache/cache_manager.py`，统一缓存管理器
  - 抽象 `CacheLayer` 接口：`get(key)`、`set(key, value, ttl)`、`delete(key)`、`invalidate(pattern)`
  - 支持多层缓存策略（Redis + 内存 LRU）
  - 缓存命中/未命中事件发布
- [ ] SubTask 4.2: 实现外部搜索缓存
  - Key: `cache:search:{source}:{query_hash}`
  - TTL: arXiv 1 天、S2 7 天、DOI 7 天
  - 整合现有 `ImportCache`（`import_rate_limiter.py`）到统一缓存管理器
  - 响应中附加 `cache_hit`、`cache_age_seconds` 字段
- [ ] SubTask 4.3: 实现 PDF 下载缓存
  - Key: `cache:pdf_download:{url_hash}`
  - Value: `{"storage_key": "...", "content_hash": "...", "size_bytes": ..., "cached_at": "..."}`
  - TTL: 30 天
  - 在 `pdf_download_worker.py` 的 `download_external_pdf` 中集成
- [ ] SubTask 4.4: 实现 Embedding 缓存
  - Key: `cache:embedding:{model_type}:{content_hash}`
  - Value: 向量数组（压缩存储）
  - TTL: 7 天
  - 在 `embedding/factory.py` 的服务层集成
- [ ] SubTask 4.5: 实现 Rerank 缓存
  - Key: `cache:rerank:{model_type}:{query_hash}:{candidates_hash}`
  - Value: 排序结果与分数
  - TTL: 1 小时
  - 在 `reranker/factory.py` 的服务层集成
- [ ] SubTask 4.6: 在 RAG 查询响应中附加缓存命中字段
  - `cache_hit`、`cache_type`（`exact` | `semantic` | `none`）、`cache_age_seconds`
- [ ] SubTask 4.7: 实现缓存版本追踪
  - embedding 缓存键包含 `model_version`，模型切换时旧缓存自动失效
  - rerank 缓存键包含 `model_version`
- [ ] SubTask 4.8: 验证：相同请求第二次命中缓存、模型切换后缓存正确失效

## Task 5: Task Observability API

实现任务可观测性 API，使用户可查看任务阶段、耗时、失败原因与重试入口。

- [ ] SubTask 5.1: 扩展 `ProcessingTask` 模型字段
  - `cost_breakdown`：JSON（`embedding_cost`、`rerank_cost`、`llm_cost`、`storage_cost`）
  - `cache_stats`：JSON（`search_hits`、`pdf_download_hits`、`embedding_hits`、`rerank_hits`）
  - 数据库迁移脚本
- [ ] SubTask 5.2: 实现 `GET /api/v1/tasks` 统一任务列表端点
  - 支持按 `status`、`task_type` 过滤
  - 支持分页（`limit`、`offset`）
  - 返回 `task_type`、`status`、`stage`、`progress`、`created_at`、`updated_at`
- [ ] SubTask 5.3: 实现 `GET /api/v1/tasks/{task_id}` 任务详情端点
  - 返回完整任务信息：`stage_timings`、`error_code`、`error_message`、`trace_id`、`attempts`
  - 失败任务包含 `failure_stage`、`failure_code`、`is_retryable`
  - 包含 `cost_breakdown`、`cache_stats`
- [ ] SubTask 5.4: 实现 `POST /api/v1/tasks/{task_id}/retry` 重试端点
  - 检查 `is_retryable`，允许则重置状态并重新入队
  - 保留原 `trace_id`，追加 `retry_trace_id`
- [ ] SubTask 5.5: 扩展 SSE 任务事件
  - 新增 `cancelled` 事件
  - 新增 `recovering` 事件
  - 新增 `cost_update` 事件（可选）
- [ ] SubTask 5.6: 验证：API 返回正确的任务状态、阶段耗时、失败分类

## Task 6: Cost and Latency Observability

实现成本、延迟、错误态的观测能力。

- [ ] SubTask 6.1: 扩展 `TokenTracker` 为通用 `CostTracker`
  - 支持记录 embedding 成本（按 token 数或请求数计费）
  - 支持记录 rerank 成本
  - 支持记录 PDF 下载成本（带宽/外部 API 调用）
  - 保留现有 LLM token 追踪能力
- [ ] SubTask 6.2: 在 `BaseAsyncTask` 生命周期钩子中集成成本记录
  - 每个阶段完成后记录该阶段的成本分项
  - 任务完成时汇总到 `cost_breakdown`
- [ ] SubTask 6.3: 实现延迟指标记录
  - 在 `stage_timings` 中记录各阶段耗时
  - 新增 `queue_wait_ms` 字段（任务从创建到 worker 开始执行的等待时间）
- [ ] SubTask 6.4: 实现错误分类与统计
  - 扩展 `failure_code` 枚举：`network_error`、`timeout`、`rate_limit`、`model_error`、`storage_error`、`validation_error`、`unknown`
  - 在 `BaseAsyncTask.on_fail` 中自动分类错误
- [ ] SubTask 6.5: 实现缓存命中率统计
  - 在 `CacheManager` 中记录命中/未命中事件
  - 聚合到 `cache_stats` 字段
- [ ] SubTask 6.6: 扩展内部观测面板（Analytics 页面）
  - 新增成本趋势图（按日/周聚合，分 embedding/rerank/llm 三类）
  - 新增延迟分布图（P50/P95/P99，按 task_type 分组）
  - 新增错误分类饼图（按 failure_code 聚合）
  - 新增缓存命中率面板（按缓存类型分组）
- [ ] SubTask 6.7: 验证：执行任务后成本/延迟/错误/缓存指标正确记录并可查询

## Task 7: Frontend Task Observability UI

实现前端任务可观测性、取消/重试交互。

- [ ] SubTask 7.1: 创建统一任务列表组件 `TaskListPanel`
  - 按状态分组（running/queued/completed/failed/cancelled）
  - 每条显示：任务类型图标、标题、阶段标签、进度条、耗时
  - 支持过滤（按 task_type、status）
- [ ] SubTask 7.2: 创建任务详情抽屉 `TaskDetailDrawer`
  - 阶段时间线（各阶段耗时可视化）
  - 成本分项展示
  - 缓存命中统计
  - 错误详情与分类
- [ ] SubTask 7.3: 增强取消交互
  - 运行中/排队中任务显示取消按钮
  - 取消确认对话框
  - 取消后状态即时更新
- [ ] SubTask 7.4: 增强重试交互
  - 失败且 `is_retryable` 的任务显示重试按钮
  - 重试后从 checkpoint 恢复的提示
- [ ] SubTask 7.5: 扩展 Analytics 页面
  - 成本趋势图组件
  - 延迟分布图组件
  - 错误分类图组件
  - 缓存命中率组件
- [ ] SubTask 7.6: 验证：前端正确展示任务状态、可取消/重试、观测面板数据正确

## Task 8: Spec & Contract Updates

更新相关规范与契约文档。

- [ ] SubTask 8.1: 更新 `docs/specs/architecture/system-overview.md`
  - 新增统一异步任务框架描述
  - 新增缓存策略描述
  - 新增可观测性描述
- [ ] SubTask 8.2: 更新 `docs/specs/architecture/api-contract.md`
  - 新增任务查询/取消/重试接口契约
  - 新增缓存命中响应字段
  - 新增 SSE 任务事件
- [ ] SubTask 8.3: 更新 `docs/specs/domain/resources.md`
  - 扩展 Task 资源模型字段
  - 新增缓存资源定义
  - 更新状态机（cancelling/recovering）
- [ ] SubTask 8.4: 更新 `docs/specs/contracts/import_processing_state_machine.md`
  - 新增 cancelling/recovering 状态
  - 新增取消传播协议
  - 新增恢复协议
- [ ] SubTask 8.5: 更新 `docs/specs/governance/phase-delivery-ledger.md`
  - 新增 Phase 3.0-E 交付单元记录

# Task Dependencies

- Task 2 depends on Task 1（取消机制依赖统一任务基类）
- Task 3 depends on Task 1（恢复机制依赖统一任务基类）
- Task 4 独立（缓存实现不依赖任务框架，但集成依赖 Task 1）
- Task 5 depends on Task 1, Task 2, Task 3（可观测性 API 依赖任务框架、取消、恢复）
- Task 6 depends on Task 1, Task 4（成本观测依赖任务框架与缓存统计）
- Task 7 depends on Task 5, Task 6（前端 UI 依赖后端 API）
- Task 8 depends on Task 1-7（文档更新在实现完成后）
- Task 2 与 Task 3 可并行
- Task 4 可与 Task 2/3 并行
