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

- 系统边界：docs/specs/architecture/system-overview.md
- API 契约：docs/specs/architecture/api-contract.md
- 前端设计系统与规范：docs/specs/design/frontend/DESIGN_SYSTEM.md
- 资源模型：docs/specs/domain/resources.md
- 编码规范：docs/specs/development/coding-standards.md
- 文档校验：docs/specs/development/documentation-validation.md
- PR 流程：docs/specs/development/pr-process.md
- 测试策略：docs/specs/development/testing-strategy.md
- 代码边界基线：docs/specs/governance/code-boundary-baseline.md
- Harness 治理：docs/specs/governance/harness-engineering-playbook.md
- Phase 台账：docs/specs/governance/phase-delivery-ledger.md
- 分支生命周期：docs/specs/governance/branch-lifecycle-policy.md
- 治理 KPI：docs/specs/governance/governance-kpi-spec.md
- E2E 失败手册：docs/specs/governance/e2e-failure-handbook.md
- 架构导航：architecture.md

## Rules

- 禁止新增根级 doc、tmp、legacy、_new、平行实现目录。
- 禁止在根目录提交 *.pid、cookies.txt、临时日志、测试产物。
- `docs/` 根层只允许保留 `README.md`、`specs/`、`plans/`。
- agent 可读的规范、架构、设计、治理、参考资料统一放在 `docs/specs/`。
- 计划、研究、评测、归档统一放在 `docs/plans/`。
- 版本化执行材料统一进入 `docs/plans/<version>/{active,complete,search,reports}`。
- 当前阶段前端真实代码只允许落在 apps/web，不允许在根级新增平行前端实现路径。
- 当前阶段后端真实代码只允许落在 apps/api，不允许在根级新增平行后端实现路径。
- 禁止提交运行时产物与本地环境目录：
  - logs/archive、test-results、uploads
  - apps/web/test-results、apps/web/*.log、apps/web/.github、apps/web/packages
  - apps/api/venv、apps/api/htmlcov*、apps/api/**/__pycache__
- 禁止提交嵌套旧仓库快照目录（例如 scholar-ai/**）。
- 改接口必须同时检查并必要时更新：
  - docs/specs/architecture/api-contract.md
  - docs/specs/domain/resources.md
- 改前端前必须检查：
  - docs/specs/design/frontend/DESIGN_SYSTEM.md
  - docs/specs/architecture/api-contract.md
  - apps/web/src/services
  - apps/web/src/app
- 改后端前必须检查：
  - apps/api/app/api
  - apps/api/app/services
  - apps/api/app/models
  - docs/specs/architecture/api-contract.md
- 新功能必须落到既定目录，不允许再开第二套实现路径。
- agent 创建 PR 时必须按 `.github/pull_request_template.md` 完整填写描述，并优先使用 `scripts/pr_create_with_template_check.sh`；未通过模板校验的 PR 不允许提交。

## Required Updates

- 架构边界变化：更新 docs/specs/architecture/system-overview.md 与 architecture.md。
- 前端设计变化：更新 docs/specs/design/frontend/DESIGN_SYSTEM.md。
- API 形态变化：更新 docs/specs/architecture/api-contract.md。
- 资源状态变化：更新 docs/specs/domain/resources.md。
- 流程变化：更新 docs/specs/development/pr-process.md。
- 规范变化：更新 docs/specs/development/coding-standards.md。
- 文档根层结构变化：同步更新 docs/README.md、docs/specs/README.md、docs/plans/README.md。

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

## 项目实现偏好

1. 只要涉及文字排版、文本绕排、动态重排、多栏流动、基于障碍物的文本布局等前端实现，默认优先使用 `pretext` 技术路径。
2. 不默认先用纯 CSS 浮动、`shape-outside` 或普通 DOM 覆盖方案做近似效果，除非明确只是静态展示且我特别说明可以简化。
3. 相关实现优先按“先测量、再排版、最后渲染”的思路组织，而不是先写视觉层再补文字联动。
