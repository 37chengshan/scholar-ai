# ScholarAI Agent Map

## Purpose

为 AI 协作提供仓库地图级规则，确保改动落在正确边界、同步正确文档、执行最小验证。

## Scope

本文件适用于 scholar-ai 根目录下全部内容。

代码边界映射：

- apps/web -> 前端真实代码主路径
- apps/api -> 后端真实代码主路径
- infra -> docker-compose、nginx、部署脚本
- tools -> 工具与脚本

## Source of Truth

- 系统边界：docs/architecture/system-overview.md
- API 契约：docs/architecture/api-contract.md
- 资源模型：docs/domain/resources.md
- 编码规范：docs/development/coding-standards.md
- 文档校验：docs/development/documentation-validation.md
- PR 流程：docs/development/pr-process.md
- 测试策略：docs/development/testing-strategy.md
- 代码边界基线：docs/governance/code-boundary-baseline.md
- Harness 治理：docs/governance/harness-engineering-playbook.md
- 架构导航：architecture.md

## Rules

- 禁止新增根级 doc、tmp、legacy、_new、平行实现目录。
- 禁止在根目录提交 *.pid、cookies.txt、临时日志、测试产物。
- 当前阶段前端真实代码只允许落在 apps/web，不允许在根级新增平行前端实现路径。
- 当前阶段后端真实代码只允许落在 apps/api，不允许在根级新增平行后端实现路径。
- 禁止提交运行时产物与本地环境目录：
  - logs/archive、test-results、uploads
  - apps/web/test-results、apps/web/*.log、apps/web/.github、apps/web/packages
  - apps/api/venv、apps/api/htmlcov*、apps/api/**/__pycache__
- 禁止提交嵌套旧仓库快照目录（例如 scholar-ai/**）。
- 改接口必须同时检查并必要时更新：
  - docs/architecture/api-contract.md
  - docs/domain/resources.md
- 改前端前必须检查：
  - docs/architecture/api-contract.md
  - apps/web/src/services
  - apps/web/src/app
- 改后端前必须检查：
  - apps/api/app/api
  - apps/api/app/services
  - apps/api/app/models
  - docs/architecture/api-contract.md
- 新功能必须落到既定目录，不允许再开第二套实现路径。

## Required Updates

- 架构边界变化：更新 docs/architecture/system-overview.md 与 architecture.md。
- API 形态变化：更新 docs/architecture/api-contract.md。
- 资源状态变化：更新 docs/domain/resources.md。
- 流程变化：更新 docs/development/pr-process.md。
- 规范变化：更新 docs/development/coding-standards.md。

## Verification

- 前端改动：cd apps/web && npm run type-check
- 后端改动：cd apps/api && pytest -q tests/unit/test_services.py --maxfail=1
- 结构或流程改动：
  - bash scripts/check-runtime-hygiene.sh tracked
  - bash scripts/check-doc-governance.sh
  - bash scripts/check-structure-boundaries.sh
  - bash scripts/check-code-boundaries.sh
  - bash scripts/check-governance.sh
  - 检查核心文档是否齐全
  - 检查 .gitignore 是否覆盖运行时产物
  - 检查 .github 模板与工作流是否可用

## Open Questions

- apps 与 packages 何时开始实质承接新代码，而非仅边界预留。
- 是否引入统一 SDK 层承接 apps/web 与 apps/api 的共享契约。

