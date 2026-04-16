# ScholarAI

ScholarAI 是面向学术阅读与知识工作流的全栈 AI 工程仓库，目标是形成可长期迭代维护的稳定架构。

## Purpose

- 固定仓库边界，减少目录漂移和重复实现。
- 用统一契约连接前端、后端、异步任务与测试流程。
- 让文档、流程、CI 与代码结构一起演进。

## Scope

- 本仓库当前采用逻辑对齐，不做 frontend 与 backend-python 的物理迁移。
- 逻辑映射如下：
	- apps/web -> frontend
	- apps/api -> backend-python
	- infra -> docker-compose、nginx、部署脚本
	- tools -> 打包与开发辅助工具

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
- 仓库协同地图：AGENTS.md
- 架构导航入口：architecture.md

## Rules

- 根目录只保留长期核心文件与核心目录，不放 *.pid、cookies.txt、临时日志和测试产物。
- 新文档统一写入 docs，不再新增 doc、tmp、legacy、_new 平行目录。
- 前端页面不直接请求 API，必须通过 service 或 hooks。
- 后端 router 不写业务编排，业务逻辑集中在 service 层。
- 新接口必须符合统一响应格式与命名规范。

## Required Updates

- 变更系统边界：同时更新 docs/architecture/system-overview.md 与 architecture.md。
- 变更 API 形态：同时更新 docs/architecture/api-contract.md。
- 变更资源生命周期：同时更新 docs/domain/resources.md。
- 变更流程与规范：同时更新 docs/development 下对应文档。

## Verification

前置依赖：

- Node.js 20+
- Python 3.11+
- Docker / Docker Compose

本地启动：

```bash
make dev
cd backend-python && pip install -r requirements.txt && uvicorn app.main:app --reload --port 8000
cd frontend && npm install && npm run dev
```

常用命令：

```bash
bash scripts/check-doc-governance.sh
bash scripts/check-structure-boundaries.sh
bash scripts/check-code-boundaries.sh
bash scripts/check-governance.sh
cd frontend && npm run type-check
cd frontend && npm run test:run
cd backend-python && pytest
```

开发/测试/部署入口：

- 开发入口：frontend 与 backend-python
- 测试入口：tests 与 frontend/e2e
- 部署入口：deploy-cloud.sh、deploy-cloud-fixed.sh、docker-compose.yml

目录说明：

- frontend: Web 前端应用
- backend-python: API 与异步任务后端
- docs: 唯一文档系统
- scripts: 运维与开发脚本
- tests: 跨模块测试与评估
- infra: 基础设施逻辑聚合入口

## Open Questions

- frontend、backend-python 的物理迁移时机是否绑定下一个里程碑。
- packages/ui、packages/types 的首批公共资产拆分边界是否先从新功能开始。
