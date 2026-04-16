# Coding Standards

## Purpose

定义前后端分层边界、命名规范、文件组织规则与禁止事项，避免平行实现和层级越权。

## Scope

适用于 apps/web、apps/api 以及跨层契约相关代码。

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

- 前端页面与路由代码集中在 apps/web/src/app。
- 前端 API 访问统一走 apps/web/src/services 与 hooks。
- apps/web/src/hooks 为共享业务 hook 唯一实现目录；apps/web/src/app/hooks 仅允许页面级局部 hook。
- 禁止在 apps/web/src/hooks 与 apps/web/src/app/hooks 保留同名 hook 文件。
- 后端入口在 apps/api/app/api，业务编排在 apps/api/app/services。
- 后端 schema/DTO 必须统一放在 apps/api/app/schemas。
- apps/api/app/models 仅保留 ORM/持久化模型，不得新增 Pydantic BaseModel。
- 数据访问查询统一收敛到 apps/api/app/repositories，router 不直接写数据库查询。
- schema/DTO 不得在多个目录重复定义。

边界规则：

- 前端组件不得直接请求后端 API。
- apps/web/src/app/pages 与 apps/web/src/app/components 禁止直接使用 apiClient、fetch、EventSource。
- 组件不持有跨页面业务状态，跨页状态放 store。
- router 不写业务逻辑，service 不拼 UI 文案。
- repository/schema 不依赖 UI 层。
- apps/api/app/api 禁止新增直接数据库操作语句（见 docs/governance/code-boundary-baseline.md）。
- apps/api/app/core 仅允许基础设施能力（config/database/logging/security/base exception），禁止新增业务编排逻辑。

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

- 是否在 apps/web 引入统一领域目录规范替代历史分散路径。
- 是否在 apps/api 引入 repository 抽象层模板并逐步收敛旧实现。
