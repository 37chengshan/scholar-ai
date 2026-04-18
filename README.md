# ScholarAI

ScholarAI 是面向学术阅读与知识工作流的全栈 AI 工程仓库，目标是形成可长期迭代维护的稳定架构。

## Purpose

- 固定仓库边界，减少目录漂移和重复实现。
- 用统一契约连接前端、后端、异步任务与测试流程。
- 让文档、流程、CI 与代码结构一起演进。
- 在物理迁移完成后，通过持续门禁维持仓库卫生与可维护性。

## Scope

	- apps/web -> Web 前端实现
	- apps/api -> Python 后端实现
	- infra -> docker-compose、nginx、部署脚本
	- tools -> 打包与开发辅助工具
- 当前阶段唯一真实代码主路径：apps/web 与 apps/api。
- 目录边界如下：
	- apps/web -> 前端真实代码主路径
	- apps/api -> 后端真实代码主路径
	- infra -> docker-compose、nginx、部署脚本
	- tools -> 打包与开发辅助工具
	- packages/* -> 共享资产预留区（当前不承接业务代码）

## Source of Truth

- 架构总览：docs/architecture/system-overview.md
- API 契约：docs/architecture/api-contract.md
- 资源域模型：docs/domain/resources.md
- 开发规范：docs/development/coding-standards.md
- 文档校验：docs/development/documentation-validation.md
- PR 流程：docs/development/pr-process.md
- 测试策略：docs/development/testing-strategy.md
- 代码边界基线：docs/governance/code-boundary-baseline.md
- Harness 治理：docs/governance/harness-engineering-playbook.md
- Phase 台账：docs/governance/phase-delivery-ledger.md
- 分支生命周期：docs/governance/branch-lifecycle-policy.md
- 治理 KPI：docs/governance/governance-kpi-spec.md
- E2E 失败手册：docs/governance/e2e-failure-handbook.md
- 仓库协同地图：AGENTS.md
- 架构导航入口：architecture.md

## Rules

- 根目录只保留长期核心文件与核心目录，不放 *.pid、cookies.txt、临时日志和测试产物。
- 新文档统一写入 docs，不再新增 doc、tmp、legacy、_new 平行目录。
- apps/web 与 apps/api 之外禁止新增平行实现路径。
- 禁止提交运行时产物、覆盖率目录、本地虚拟环境与嵌套旧仓库快照：
	- logs/archive、test-results、uploads
	- apps/web/test-results、apps/web/*.log
	- apps/api/venv、apps/api/htmlcov*、apps/api/**/__pycache__
	- scholar-ai/**
- 前端页面不直接请求 API，必须通过 service 或 hooks。
- 后端 router 不写业务编排，业务逻辑集中在 service 层。
- 新接口必须符合统一响应格式与命名规范。

## Required Updates

- 变更系统边界：同时更新 docs/architecture/system-overview.md 与 architecture.md。
- 变更 API 形态：同时更新 docs/architecture/api-contract.md。
- 变更资源生命周期：同时更新 docs/domain/resources.md。
- 变更流程与规范：同时更新 docs/development 下对应文档。
- 调整治理门禁或稳定化策略：同步更新 docs/governance/migration-conditions.md。
- 调整 phase 追踪、分支生命周期、fallback 或 E2E 策略：同步更新 docs/governance 对应文档。

## Verification

前置依赖：

- Node.js 20+
- Python 3.11+
- Docker / Docker Compose

本地启动：

```bash
make dev
cd apps/api && pip install -r requirements.txt && uvicorn app.main:app --reload --port 8000
cd apps/web && npm install && npm run dev
```

常用命令：

```bash
bash scripts/check-runtime-hygiene.sh tracked
bash scripts/check-doc-governance.sh
bash scripts/check-structure-boundaries.sh
bash scripts/check-code-boundaries.sh
bash scripts/check-governance.sh
bash scripts/check-phase-tracking.sh
bash scripts/check-branch-lifecycle.sh
bash scripts/check-contract-gate.sh
bash scripts/check-fallback-expiry.sh
bash scripts/check-e2e-gate.sh --mode manifest
bash scripts/audit-governance-kpi.sh --window 14d --output docs/reports/governance-kpi/latest.md
bash scripts/verify-all-phases.sh
cd apps/web && npm run type-check
cd apps/web && npm run test:run
cd apps/api && pytest -q tests/unit/test_services.py --maxfail=1
```

需要深度清理本地环境时可执行：

```bash
bash scripts/check-runtime-hygiene.sh strict
```

开发/测试/部署入口：

- 开发入口：apps/web 与 apps/api
- 测试入口：tests 与 apps/web/e2e
- 部署入口：deploy-cloud.sh、deploy-cloud-fixed.sh、docker-compose.yml

目录说明：

- apps/web: Web 前端应用
- apps/api: API 与异步任务后端
- docs: 唯一文档系统
- scripts: 运维与开发脚本
- tests: 跨模块测试与评估
- infra: 基础设施逻辑聚合入口

## Open Questions

- packages/types、packages/sdk 在何时开始承接首批共享契约。
- 是否为 runtime-hygiene 增加 pre-commit 钩子减少误提交概率。
