# Core Boundary Baseline

## Purpose

定义 backend-python/app/core 的职责边界，阻止 core 演化为通用业务杂物箱。

## Scope

适用于 backend-python/app/core 全目录与新增文件准入审查。

## Allowed Responsibilities

- config
- database bootstrap and connection glue
- logging and observability plumbing
- security primitives
- base exceptions
- infra client wrappers

## Disallowed Responsibilities

- 业务域编排逻辑（papers/kb/chat/session 等）
- API 路由相关逻辑
- 资源域 service/repository 逻辑
- 页面或前端语义相关逻辑
- 新的查询流程 orchestration（应进入 app/services）

## Required Updates

- 新增 core 文件时，PR 必须说明为何不适合放入 app/services 或 app/repositories。
- 若边界有变更，需同步更新 docs/development/coding-standards.md。

## Verification

- 代码评审检查新增 core 文件职责。
- 抽样检查 import 方向保持 api -> services -> repositories/models/schemas。
