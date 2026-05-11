# 🎓 ScholarAI

[![React](https://img.shields.io/badge/React-18-blue.svg)](https://reactjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)
[![Milvus](https://img.shields.io/badge/Milvus-Vector_DB-blueviolet)](https://milvus.io/)

**ScholarAI** 是一个开源的、基于 AI 驱动的学术阅读、知识管理与 **Academic-Grade RAG（检索增强生成）** 平台。

无论您是研究人员、学生还是知识工作者，ScholarAI 致力于改变传统的文献阅读方式，通过强大的大模型能力与精密的 RAG 检索管线，让您与海量学术论文进行更深入的交互。我们希望通过工程化与 AI 的深度结合，打造一个高可用、可扩展的私人学术外脑。

---

## ✨ 核心特性

- 🧠 **学术级 RAG 引擎**: 深度解析 PDF 文献，智能分块与向量化。借助强大的 RAG V3 架构，精准找回学术证据，实现“无幻觉”的深度文献问答。
- 📚 **全能知识图谱与管理**: 支持文献库的精细化管理（收藏、标签、来源追踪），并构建专属的学术知识网。
- ⚡️ **极速流畅的交互体验**: Web 客户端基于 React + Vite 构建，支持流式 (SSE) 交互响应，全响应式适配，体验媲美原生应用。
- 🤖 **多 Agent 智能协作**: 预置多种 AI 工作流代理，支持提取关键结论、总结文献摘要、横向文献对比乃至自动起草综述。
- 🛡️ **生产级可扩展架构**: 后端严选 FastAPI 构建，整合 PostgreSQL (关系型核心数据) 与 Milvus (高维向量)，原生支持完备的异步任务调度处理体系。

## 🏗️ 技术架构

**ScholarAI** 秉持严格的模块化与清晰的系统边界设计：

*   **Web 前端 (`apps/web`)**: React 18, Vite, TailwindCSS, Playwright (E2E 测试)
*   **API 后端 (`apps/api`)**: Python 3.11+, FastAPI, SQLAlchemy, Alembic
*   **数据存储**: PostgreSQL (业务数据引擎), Milvus / BGE-M3 (向量检索)
*   **部署与基建 (`infra`)**: Docker Compose, Nginx

## 🚀 快速开始

想要在本地启动 ScholarAI 探索全功能体验？仅需以下几步：

### 环境前置要求
*   [Node.js 20+](https://nodejs.org/)
*   [Python 3.11+](https://www.python.org/)
*   [Docker & Docker Compose](https://www.docker.com/)

### 步骤 1：拉起公共基础设施
推荐使用 Docker 一键启动 PostgreSQL 和 Milvus 等底层依赖。
```bash
docker-compose -f docker-compose.yml up -d
```

### 步骤 2：启动后端架构 API 服务
```bash
cd apps/api
# 安装依赖
pip install -r requirements.txt
# 配置本地/远程大模型与 Vector 环境
bash setup_bge_m3.sh
# 启动后端服务
uvicorn app.main:app --reload --port 8000
```
*(注意：首次使用需将 `apps/api/.env.example` 复制为 `.env`，并在此处配置您的大模型 API 密钥)*

### 步骤 3：启动前端 Web 服务
```bash
cd apps/web
npm install
npm run dev
```

## 📚 查阅核心文档

我们不仅开源了代码层，更开源了我们的**工程化治理体系与设计哲学**。如果您想深入了解 ScholarAI：

- [🏛️ 系统架构概览](docs/specs/architecture/system-overview.md)
- [📖 API 核心契约](docs/specs/architecture/api-contract.md)
- [🎨 研发规范](docs/specs/development/coding-standards.md)
- [🔒 代码治理与质量门禁](docs/specs/governance/code-boundary-baseline.md)

## 🤝 参与贡献

我们非常欢迎开发者参与共建！无论是修复一个隐蔽 Bug，还是提出一个能大幅提升搜索准确率的新型 RAG Pipeline：

1. 提交流水线前，请知悉我们的 [分支生命周期策略](docs/specs/governance/branch-lifecycle-policy.md)
2. 提交 Pull Request 前，请阅读完整 [PR 处理流程](docs/specs/development/pr-process.md)
3. 为了保持高质量的代码层交付，请始终在提交前运行本地测试套件与安全检测：
```bash
# 执行全量完整验证
bash scripts/verify/run-all.sh
```

## 📄 许可与协议

本项目基于无附加限制的开源协议构建发布。愿每个人拥有私人的强大学术利器。

## Purpose

为 ScholarAI 提供仓库级入口说明，并与 `docs/specs/`、`docs/plans/` 的治理体系保持一致，确保实现、计划、验证和交付证据可追踪。

## Scope

本 README 适用于仓库根目录和跨模块协作的总览说明，具体实现细节以子目录与规范文档为准：

- `apps/web`
- `apps/api`
- `infra`
- `tools`
- `docs/specs`
- `docs/plans`

## Source of Truth

- 系统总览：`docs/specs/architecture/system-overview.md`
- API 契约：`docs/specs/architecture/api-contract.md`
- 资源模型：`docs/specs/domain/resources.md`
- 编码规范：`docs/specs/development/coding-standards.md`
- 文档校验规范：`docs/specs/development/documentation-validation.md`
- PR 流程：`docs/specs/development/pr-process.md`
- 测试策略：`docs/specs/development/testing-strategy.md`
- 代码边界：`docs/specs/governance/code-boundary-baseline.md`
- Harness 治理：`docs/specs/governance/harness-engineering-playbook.md`
- Phase 台账：`docs/specs/governance/phase-delivery-ledger.md`
- 分支生命周期：`docs/specs/governance/branch-lifecycle-policy.md`
- 治理 KPI：`docs/specs/governance/governance-kpi-spec.md`
- E2E 失败手册：`docs/specs/governance/e2e-failure-handbook.md`
- 计划状态真源：`docs/plans/PLAN_STATUS.md`

## Rules

1. 根目录仅承载总览与导航，不放置平行实现和临时产物。
2. 实现变更优先落在 `apps/web` 与 `apps/api`，避免越界实现。
3. 计划与研究类文档写入 `docs/plans`；规范与治理文档写入 `docs/specs`。
4. 接口、资源、流程或治理变化时，必须同步对应规范文档。

## Required Updates

- 架构边界调整：更新 `docs/specs/architecture/system-overview.md`
- 接口形态调整：更新 `docs/specs/architecture/api-contract.md`
- 资源状态语义调整：更新 `docs/specs/domain/resources.md`
- 流程或门禁调整：更新 `docs/specs/development/pr-process.md` 与相关治理文档
- 计划状态变化：更新 `docs/plans/PLAN_STATUS.md` 与 `docs/specs/governance/phase-delivery-ledger.md`

## Verification

- `bash scripts/check-doc-governance.sh`
- `bash scripts/check-plan-governance.sh`
- `bash scripts/check-phase-tracking.sh`
- `bash scripts/check-governance.sh`

## Open Questions

- `apps` 与 `packages` 的共享契约是否引入统一 SDK 层以减少前后端重复定义。
- 在保持主链稳定的前提下，如何把阶段性演示能力平滑升级为长期可维护的发布门禁能力。
