# System Overview

## Purpose

定义 ScholarAI 的子系统边界、前后端职责、数据与任务流以及异步链路，作为架构与协作的统一基线。

## Scope

覆盖 apps/web、apps/api、异步任务、SSE 流式输出及外部运行时依赖。

当前仓库主路径：

- apps/web -> Web 前端实现
- apps/api -> API 后端实现
- infra -> docker-compose、nginx、部署脚本
- tools -> scripts 与开发辅助工具

## Source of Truth

- API 契约：docs/architecture/api-contract.md
- 资源模型：docs/domain/resources.md
- 开发规范：docs/development/coding-standards.md
- 架构入口：architecture.md

## Rules

子系统清单：

- Web 客户端：apps/web（Vite + React）
- API 后端：apps/api（FastAPI）
- 异步任务：apps/api/app/tasks 与 apps/api/app/workers
- 持久化与检索：PostgreSQL/PGVector、Redis、Neo4j、Milvus

前后端边界：

- 前端页面只消费 service/hooks，不直接拼接 API 调用。
- apps/api/app/api 只做协议与编排入口，不写重业务逻辑。
- apps/api/app/services 承担业务编排，数据访问和模型调用在对应基础层完成。

数据流：

1. 前端页面触发用户动作。
2. service/hooks 发起请求到 API。
3. router 完成鉴权与入参校验后转入 service。
4. service 协调数据库、向量检索和外部模型。
5. 返回统一响应格式给前端。

任务流：

1. 用户触发上传/解析/索引任务。
2. API 创建任务并持久化状态。
3. worker 消费任务并更新资源状态。
4. 前端轮询或订阅事件获取进度。

SSE/异步链路：

- SSE 事件命名、载荷与完成信号遵循 docs/architecture/api-contract.md。
- 长任务必须可观测，至少提供 queued/running/succeeded/failed 状态。

外部依赖与运行时组件：

- Docker Compose 作为本地依赖编排入口。
- Nginx 配置位于 nginx。
- 部署脚本位于根目录 deploy-cloud*.sh，后续纳入 infra/deploy 逻辑聚合。

## Required Updates

- 新增/删除子系统：同步更新本文件与 architecture.md。
- 引入新运行时依赖：同步更新 docs/domain/resources.md。
- 改动 SSE 行为：同步更新 docs/architecture/api-contract.md。

## Verification

- 检查目录边界：确认无新增平行实现目录。
- 检查链路一致性：随机抽样前端调用与后端路由是否经由 service。
- 检查异步可观测性：任务状态可从 API 或事件读取。

## Open Questions

- deploy-cloud 系列脚本收敛到 infra/deploy 的分阶段计划。
- 是否需要统一任务编排层以减少 worker 入口分散。
