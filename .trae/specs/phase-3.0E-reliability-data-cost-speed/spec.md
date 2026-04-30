# Phase 3.0-E: Reliability / Data / Cost / Speed Spec

## Why

v3.0 当前功能已基本就位，但批量导入时任务容易卡死或失败不可恢复，PDF 下载/解析/embedding/rerank 成本高且存在大量重复计算，长任务对用户不可见、不可取消、不可重试。需要把系统从"功能存在"推进到"可以长期稳定跑"。

## What Changes

- 引入统一异步任务框架，将 import job、review、compare、reading card 等长任务纳入统一 async 路径
- 新增外部搜索缓存、PDF 下载缓存、embedding 缓存、rerank 缓存，消除重复计算
- 新增任务可观测性层：用户可查看任务阶段、耗时、失败原因与重试入口
- 新增任务取消控制：用户可取消运行中的长任务
- 新增成本/延迟/错误态观测：进入 analytics 或内部观测面板

## Impact

- Affected specs:
  - docs/specs/architecture/system-overview.md（统一异步路径、缓存策略、可观测性）
  - docs/specs/architecture/api-contract.md（任务查询/取消/重试接口、缓存命中响应字段）
  - docs/specs/domain/resources.md（Task 资源模型扩展、缓存资源定义）
  - docs/specs/contracts/import_processing_state_machine.md（恢复协议、取消传播）
- Affected code:
  - apps/api/app/tasks/（统一任务基类与注册）
  - apps/api/app/workers/（恢复能力、取消传播、阶段耗时记录）
  - apps/api/app/core/cache/（缓存策略抽象层）
  - apps/api/app/services/（缓存集成、成本记录）
  - apps/api/app/api/（任务查询/取消/重试端点）
  - apps/api/app/models/（Task 模型扩展、成本记录模型）
  - apps/web/src/features/（任务可观测性 UI、取消/重试交互）
  - apps/web/src/services/（任务 API 客户端）

## ADDED Requirements

### Requirement: Unified Async Task Framework

系统 SHALL 提供统一异步任务框架，使 import job、review、compare、reading card 等长任务走统一 async 路径。

#### Scenario: 任务提交与状态追踪

- **WHEN** 用户触发任何长任务（导入、综述生成、比较分析、阅读卡片生成）
- **THEN** 系统创建统一 Task 记录，包含 `task_type`、`status`、`stage`、`progress`、`created_at`、`trace_id`
- **AND** 任务通过统一队列路由执行

#### Scenario: 任务阶段推进

- **WHEN** 任务执行中从一个阶段推进到下一阶段
- **THEN** 系统更新 Task 的 `stage`、`progress`、`stage_timings`，并记录阶段开始时间与耗时

#### Scenario: 任务恢复

- **WHEN** 任务因 worker 崩溃或外部错误而中断
- **THEN** 系统支持从最近完成的 checkpoint 阶段恢复执行，而非从头开始
- **AND** 恢复时 `attempts` 递增，`is_retryable` 标记保持有效

### Requirement: Multi-Layer Cache Strategy

系统 SHALL 提供多层缓存策略，覆盖外部搜索、PDF 下载、embedding 计算、rerank 计算四个关键路径。

#### Scenario: 外部搜索缓存命中

- **WHEN** 用户发起外部搜索请求（arXiv/S2/DOI）
- **THEN** 系统首先检查缓存，若命中则直接返回缓存结果
- **AND** 响应中包含 `cache_hit=true` 标记与 `cache_age` 字段

#### Scenario: PDF 下载缓存命中

- **WHEN** 系统需要下载 PDF 文件（导入、外部论文获取）
- **THEN** 系统首先检查 PDF 下载缓存（基于 URL SHA256），若命中则跳过下载
- **AND** 缓存条目包含 `url_hash`、`storage_key`、`content_hash`、`cached_at`

#### Scenario: Embedding 缓存命中

- **WHEN** 系统需要计算文本 embedding
- **THEN** 系统首先检查 embedding 缓存（基于文本内容 hash + 模型标识），若命中则直接返回向量
- **AND** 缓存键包含 `model_type`、`content_hash`，确保模型切换时缓存正确失效

#### Scenario: Rerank 缓存命中

- **WHEN** 系统需要执行 rerank 操作
- **THEN** 系统首先检查 rerank 缓存（基于 query + candidate_ids hash + 模型标识），若命中则直接返回排序结果
- **AND** 缓存键包含 `model_type`、`query_hash`、`candidates_hash`

#### Scenario: 缓存失效

- **WHEN** 缓存条目超过 TTL 或底层数据变更（如索引版本升级）
- **THEN** 系统自动失效过期缓存条目
- **AND** 缓存失效不影响业务正确性，仅导致重新计算

### Requirement: Task Observability

系统 SHALL 提供任务可观测性，使用户可查看任务阶段、耗时、失败原因与重试入口。

#### Scenario: 任务列表查询

- **WHEN** 用户请求任务列表
- **THEN** 系统返回按时间倒序排列的任务列表，每个条目包含 `task_type`、`status`、`stage`、`progress`、`created_at`、`updated_at`
- **AND** 支持按 `status`、`task_type` 过滤

#### Scenario: 任务详情查询

- **WHEN** 用户请求单个任务详情
- **THEN** 系统返回完整任务信息，包含 `stage_timings`（各阶段耗时）、`error_code`、`error_message`、`trace_id`、`attempts`
- **AND** 失败任务包含 `failure_stage`、`failure_code`、`is_retryable` 标记

#### Scenario: 失败任务重试

- **WHEN** 用户对失败任务发起重试
- **THEN** 系统检查 `is_retryable` 标记，若允许则重置任务状态并重新入队
- **AND** 重试时保留原 `trace_id` 并追加 `retry_trace_id`

### Requirement: Task Cancellation Control

系统 SHALL 提供任务取消控制，使用户可取消运行中的长任务。

#### Scenario: 取消运行中任务

- **WHEN** 用户对运行中任务发起取消
- **THEN** 系统将任务状态置为 `cancelled`，并向执行中的 worker 发送取消信号
- **AND** 取消传播到子任务（如 ImportJob 取消时传播到 ProcessingTask）

#### Scenario: 取消后资源清理

- **WHEN** 任务被取消
- **THEN** 系统释放已占用的并发槽位、清理临时文件、回滚部分写入的资源状态
- **AND** 已完成的子阶段结果保留（不回滚），未开始的子阶段标记为 `skipped`

#### Scenario: 不可取消的任务

- **WHEN** 任务已进入终态（completed/failed/cancelled）
- **THEN** 系统返回 409 Conflict，拒绝取消请求

### Requirement: Cost and Latency Observability

系统 SHALL 提供成本、延迟、错误态的观测能力，进入 analytics 或内部观测面板。

#### Scenario: 单次任务成本记录

- **WHEN** 任务执行完成（成功或失败）
- **THEN** 系统记录该任务的累计成本，包含 `embedding_cost`、`rerank_cost`、`llm_cost`、`total_cost`
- **AND** 成本按模型和操作类型分项记录

#### Scenario: 延迟指标记录

- **WHEN** 任务执行完成
- **THEN** 系统记录该任务的端到端延迟与各阶段延迟
- **AND** 延迟指标包含 `total_duration_ms`、`stage_durations{}`、`queue_wait_ms`

#### Scenario: 错误态分类与统计

- **WHEN** 任务执行失败
- **THEN** 系统记录错误分类（`network_error`、`timeout`、`rate_limit`、`model_error`、`storage_error`、`validation_error`、`unknown`）
- **AND** 错误统计可在内部观测面板按 `failure_code` 聚合查看

#### Scenario: 缓存命中率统计

- **WHEN** 系统执行缓存查询
- **THEN** 系统记录缓存命中/未命中事件
- **AND** 缓存命中率可在内部观测面板按缓存类型（search/pdf_download/embedding/rerank）聚合查看

## MODIFIED Requirements

### Requirement: ImportJob 状态机（扩展恢复与取消）

ImportJob 状态机在现有 `created -> queued -> running -> awaiting_user_action -> completed | failed | cancelled` 基础上，新增：

- `cancelling` 中间状态：收到取消请求后进入，等待 worker 确认取消完成
- `recovering` 中间状态：从 checkpoint 恢复执行时进入，恢复完成后转为 `running`
- 取消传播：ImportJob 取消时必须传播到关联 ProcessingTask
- 恢复协议：失败任务重试时从 `checkpoint_stage` 恢复，而非从头开始

### Requirement: ProcessingTask 模型（扩展可观测性字段）

ProcessingTask 在现有字段基础上新增：

- `cancelled_at`：取消时间戳
- `cancellation_reason`：取消原因（`user_request` / `parent_cancelled` / `timeout`）
- `cost_breakdown`：成本分项 JSON（`embedding_cost`、`rerank_cost`、`llm_cost`、`storage_cost`）
- `cache_stats`：缓存命中统计 JSON（`search_hits`、`pdf_download_hits`、`embedding_hits`、`rerank_hits`）

### Requirement: RAG 查询响应（缓存命中字段）

`POST /api/v1/rag/query` 响应新增可选字段：

- `cache_hit`：布尔值，本次查询是否命中缓存
- `cache_type`：命中类型（`exact` | `semantic` | `none`）
- `cache_age_seconds`：缓存条目年龄
- `cost_breakdown`：成本分项（`embedding_cost`、`rerank_cost`、`llm_cost`）

### Requirement: SSE 任务事件（统一进度推送）

导入任务 SSE 事件集合在现有 `status_update / stage_change / progress / completed / error` 基础上新增：

- `cancelled`：任务被取消事件
- `recovering`：任务从 checkpoint 恢复事件
- `cost_update`：成本实时更新事件（可选）

## REMOVED Requirements

无移除需求。本阶段为纯增量扩展，不破坏现有功能。
