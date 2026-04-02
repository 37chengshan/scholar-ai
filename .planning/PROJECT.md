# ScholarAI / 智读

## What This Is

ScholarAI（智读）是一个基于开源生态整合的智能学术阅读平台，通过 Agentic RAG + 混合搜索 + IMRaD 感知分块技术，让科研人员从"读完一篇论文需要 3 小时"缩短到"掌握核心内容只需 10 分钟"。

产品面向科研人员、研究生、学者，解决学术文献阅读效率低下的痛点。

## Core Value

科研人员能在 10 分钟内掌握一篇论文的核心内容，而不是花费 3 小时通读全文。

## Requirements

### Validated

- ✓ **云端数据库部署** — 数据库连接配置完成 (v0.1)
- ✓ **PostgreSQL + PGVector** — 向量数据存储就绪 (v0.1)
- ✓ **Neo4j 图数据库** — 知识图谱存储就绪 (v0.1)
- ✓ **Redis 缓存服务** — 缓存层就绪 (v0.1)

### Active

- [ ] **Node.js API Gateway 搭建** — 核心 API 路由和认证
- [ ] **Python AI Service 搭建** — PDF 处理和 RAG 引擎
- [ ] **用户认证系统** — JWT 登录/注册
- [ ] **PDF 上传与解析** — 支持 Docling 解析
- [ ] **文献库管理** — 论文 CRUD、分类、标签
- [ ] **Agentic RAG 检索** — 多轮推理问答
- [ ] **知识图谱可视化** — 引用网络展示
- [ ] **前端页面开发** — React + Tailwind 界面

### Out of Scope

- 移动端 App — 优先 Web 端，移动端后续迭代
- 付费订阅系统 — MVP 阶段免费使用
- 多语言支持 — 中文优先，英文后续
- 协作功能（共享笔记）— 个人使用优先
- 离线模式 — 云端优先架构

## Context

**技术环境：**
- 双后端架构：Node.js API Gateway + Python AI Service
- 微服务设计，JWT 服务间认证
- 多数据库策略：PostgreSQL + PGVector + Neo4j + Redis

**当前代码状态：**
- backend-node/ — Express + Prisma + TypeScript，部分路由已实现
- backend-python/ — FastAPI + PaperQA2 + Docling，基础服务搭建中
- 前端 — React + Vite + Tailwind，基础结构存在

**已知问题：**
- 部分 API 接口待完善
- 前端页面待开发
- PDF 处理流程待端到端测试

## Constraints

- **Tech Stack**: Node.js 20 + Python 3.11 — 双语言后端已选定
- **Database**: PostgreSQL + Neo4j + Redis — 云端已部署
- **AI Model**: 支持 OpenAI / Anthropic — 通过环境变量配置
- **Timeline**: 优先完成核心功能，再优化体验
- **Security**: JWT 认证，API 密钥管理

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Dual-backend (Node.js + Python) | Node.js 适合 API Gateway，Python 适合 AI/ML | — Pending |
| PostgreSQL + PGVector | 关系数据 + 向量搜索一体化 | — Pending |
| Neo4j for knowledge graph | 原生图数据库，适合引用网络 | — Pending |
| PaperQA2 for RAG | 学术场景优化，支持引用溯源 | — Pending |
| Docling for PDF parsing | 支持 IMRaD 结构识别 | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd:transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-02 after initialization*
