# Testing Strategy

## Purpose

定义 ScholarAI 的测试分层、覆盖范围与最小回归要求，保证重构和新功能可验证。

## Scope

覆盖单元测试、集成测试、E2E 测试、冒烟测试与回归触发条件。

## Source of Truth

- PR 流程：docs/development/pr-process.md
- 文档校验：docs/development/documentation-validation.md
- API 契约：docs/architecture/api-contract.md
- 系统总览：docs/architecture/system-overview.md

## Rules

单元测试覆盖范围：

- 纯函数、数据转换、核心业务规则
- service 层关键分支
- 前端 hooks 与 store 的状态转换

集成测试覆盖范围：

- API 路由到 service 的主链路
- 数据库读写与任务状态变更
- SSE 关键事件序列

E2E 覆盖范围：

- 上传论文 -> 解析 -> 检索/对话
- 创建会话 -> 发送消息 -> 流式返回
- 核心失败路径（鉴权失败、解析失败、超时）

必测核心链路：

- API 统一响应格式
- 异步任务状态机迁移
- SSE done/error 收敛行为

冒烟测试清单：

- runtime hygiene 校验
- 文档结构与链接校验
- 结构边界校验
- 代码层边界校验
- 前端 type-check
- 后端 pytest 最小子集
- 核心文档存在性与路径正确性

测试产物不入库规则：

- 禁止提交 `test-results/`、`apps/web/test-results/`、`playwright-report/`
- 禁止提交 `.coverage`、`apps/api/.coverage`、`htmlcov/`、`apps/api/htmlcov*/`
- 禁止提交 `.pytest_cache/`、`apps/api/**/__pycache__/`、`apps/api/venv/`

必须补回归测试的变更：

- API 响应结构变更
- 资源状态机变更
- 鉴权与权限控制变更
- SSE 事件语义变更
- 路由命名或参数协议变更

## Required Updates

- 新增测试层级或框架：同步更新本文件与 docs/development/pr-process.md。
- 新增关键链路：同步更新必测链路与冒烟清单。

## Verification

- 本地最小验证：
	- bash scripts/check-runtime-hygiene.sh tracked
	- bash scripts/check-doc-governance.sh
	- bash scripts/check-structure-boundaries.sh
	- bash scripts/check-code-boundaries.sh
	- bash scripts/check-governance.sh
	- cd apps/web && npm run type-check
	- cd apps/api && pytest -q tests/unit/test_services.py --maxfail=1

- CI 最小验证：
	- 核心文档存在性检查
	- frontend type-check
	- backend pytest 冒烟

## Open Questions

- 是否在 CI 强制 E2E 冒烟，还是先保留手动触发。
- 是否对 SSE 增加专门的契约测试快照。
