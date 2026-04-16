# Coding Standards

## Purpose

定义前后端分层边界、命名规范、文件组织规则与禁止事项，避免平行实现和层级越权。

## Scope

适用于 frontend、backend-python 以及跨层契约相关代码。

## Source of Truth

- API 契约：docs/architecture/api-contract.md
- 资源模型：docs/domain/resources.md
- 系统总览：docs/architecture/system-overview.md

## Rules

命名规范：

- 前端组件/页面/store/service：camelCase。
- 后端模型、schema、DTO、内部字段：snake_case。
- 同一层内禁止混用两种命名风格。

文件组织规范：

- 前端页面与路由代码集中在 frontend/src/app。
- 前端 API 访问统一走 frontend/src/services 与 hooks。
- 后端入口在 backend-python/app/api，业务编排在 backend-python/app/services。
- schema/DTO 优先集中管理，不得在多个目录重复定义。

边界规则：

- 前端组件不得直接请求后端 API。
- frontend/src/app/pages 与 frontend/src/app/components 禁止直接使用 apiClient、fetch、EventSource。
- 组件不持有跨页面业务状态，跨页状态放 store。
- router 不写业务逻辑，service 不拼 UI 文案。
- repository/schema 不依赖 UI 层。
- backend-python/app/api 禁止新增直接数据库操作语句（见 docs/governance/code-boundary-baseline.md）。

禁止项：

- 禁止新增 _new、legacy、平行实现目录。
- 禁止为同一资源新增第二套路由命名。
- 禁止复制实现而不做替换与下线计划。

## Required Updates

- 新分层规则：同步更新 docs/architecture/system-overview.md。
- 新接口字段规范：同步更新 docs/architecture/api-contract.md。
- 目录约束变化：同步更新 AGENTS.md。

## Verification

- 抽样检查页面调用链是否经由 service/hooks。
- 抽样检查 router 文件是否无业务编排代码。
- 抽样检查 schema/DTO 是否未在多个目录重复定义。
- 运行 bash scripts/check-code-boundaries.sh 验证代码层边界。

## Open Questions

- 是否在 frontend 引入统一领域目录规范替代历史分散路径。
- 是否在 backend 引入 repository 抽象层模板并逐步收敛旧实现。
