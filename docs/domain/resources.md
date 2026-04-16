# Resources Model

## Purpose

统一定义 ScholarAI 核心资源、资源关系、状态机与生命周期事件，支撑 API 设计和异步任务治理。

## Scope

覆盖论文、会话、消息、知识片段、任务与索引等核心资源。

## Source of Truth

- API 契约：docs/architecture/api-contract.md
- 系统总览：docs/architecture/system-overview.md
- 后端模型：apps/api/app/models
- 后端服务：apps/api/app/services

## Rules

核心资源清单：

- Paper：论文与元数据
- Collection：文献集合与组织单元
- Chunk：文本切片与向量化单元
- ChatSession：会话上下文
- ChatMessage：会话消息
- Task：异步任务
- IndexArtifact：索引或检索产物

资源关系：

- Paper 属于零个或多个 Collection。
- Paper 产生多个 Chunk。
- ChatSession 包含多个 ChatMessage。
- Task 作用于 Paper、Collection 或 IndexArtifact。

状态机：

- Paper：uploaded -> parsing -> parsed -> indexed -> archived | failed
- Task：queued -> running -> succeeded | failed | canceled
- ChatSession：active -> closed | archived
- IndexArtifact：building -> ready | failed -> rebuilding

关键生命周期事件：

- paper.uploaded
- paper.parsed
- paper.indexed
- task.started
- task.finished
- task.failed
- session.closed

可被异步任务修改的资源：

- Paper（解析与索引状态）
- Chunk（生成、重算、清理）
- Task（执行状态）
- IndexArtifact（构建状态）

## Required Updates

- 新增资源类型：同步更新本文件与 docs/architecture/api-contract.md。
- 资源状态迁移变化：同步更新 apps/api/app/models 与本文件。
- 新增异步任务：同步补充可修改资源列表。

## Verification

- 抽样检查 API 响应中的资源状态是否在状态机集合内。
- 抽样检查任务完成后资源状态迁移是否可追踪。
- 抽样检查同一资源无重复命名或平行模型定义。

## Open Questions

- IndexArtifact 是否需要拆分为向量索引与图索引两类资源。
- ChatSession 的归档策略是否需要时间窗口自动化。
