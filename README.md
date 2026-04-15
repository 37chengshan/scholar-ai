# ScholarAI 智读

> 让研究人员在 5 分钟内掌握一篇论文的精华，在 30 分钟内完成深度理解。

[![Status](https://img.shields.io/badge/状态-开发中-yellow)]()
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)]()
[![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black)]()
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110-009688?logo=fastapi&logoColor=white)]()
[![License](https://img.shields.io/badge/License-MIT-green)]()

ScholarAI 智读是一个学术论文智能阅读系统，帮助研究人员高效阅读、理解和分析学术论文。

## 核心功能

| 功能 | 状态 | 描述 |
|------|:----:|------|
| PDF 智能解析 | ✅ | 上传 PDF 自动提取结构、图表、IMRaD 章节 |
| RAG 问答 | ✅ | 基于论文内容的智能问答，支持引用溯源 |
| 知识图谱 | ✅ | 实体关系提取与 PageRank 分析（Neo4j） |
| 论文对比 | ✅ | 多论文横向对比分析 |
| 智能笔记 | ✅ | 富文本编辑器 + AI 辅助生成 |
| 知识库管理 | ✅ | 论文分组、标签、导入去重 |
| AI 对话 | ✅ | SSE 流式对话，支持多轮上下文 |
| Semantic Scholar | ✅ | 外部论文搜索与元数据抓取 |
| 多模态检索 | 🔄 | 图表/表格联合检索（Milvus 集成中） |
| 阅读进度 | ✅ | 论文阅读位置跟踪与统计 |
| 多 LLM 支持 | ✅ | LiteLLM 路由，支持 OpenAI / Claude / 智谱等 |

## 技术栈

<table>
<tr>
<td width="50%">

**前端**
- React 18 + TypeScript
- Vite + Tailwind CSS v4
- Radix UI + Material UI
- Zustand + React Query
- Tiptap 富文本编辑器
- KaTeX / Mermaid / Recharts

</td>
<td width="50%">

**后端**
- Python FastAPI（统一后端）
- SQLAlchemy + PGVector
- Neo4j 图数据库
- Redis 缓存 + Celery 异步任务
- Milvus 多模态向量存储
- BGE-M3 / SPECTER2 Embedding
- LiteLLM 多模型路由

</td>
</tr>
</table>

## 快速开始

### 前置要求

- Docker & Docker Compose
- Node.js 20+
- Python 3.11+

### 1. 克隆项目

```bash
git clone https://github.com/37chengshan/scholar-ai.git
cd scholar-ai
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env，填入数据库密码、API Key 等
```

### 3. 启动服务

**Docker 一键部署：**

```bash
docker-compose up -d
```

**本地开发：**

```bash
# 启动数据库
docker-compose up -d postgres redis neo4j milvus-standalone

# 启动后端
cd backend-python
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# 启动前端
cd frontend
npm install
npm run dev
```

服务地址：
- 前端：http://localhost:3000
- 后端 API：http://localhost:8000
- API 文档：http://localhost:8000/docs

## 项目结构

```
scholar-ai/
├── backend-python/       # FastAPI 统一后端
│   ├── app/
│   │   ├── api/          # REST API 路由
│   │   ├── core/         # 核心服务（RAG、图谱、嵌入）
│   │   ├── models/       # 数据模型
│   │   ├── services/     # 业务逻辑
│   │   ├── workers/      # Celery 异步任务
│   │   └── middleware/   # 认证、日志、错误处理
│   └── tests/            # 测试
├── frontend/             # React 前端
│   └── src/
│       ├── app/pages/    # 页面组件
│       ├── components/   # 通用组件
│       ├── services/     # API 调用
│       ├── stores/       # Zustand 状态管理
│       └── hooks/        # 自定义 Hooks
├── docker-compose.yml    # 服务编排
└── Makefile              # 开发命令
```

## 项目状态

> **本项目正在积极开发中，尚未发布正式版本。**
>
> 部分功能已可用，部分功能仍在开发中。欢迎 Star 关注进展，但暂不建议用于生产环境。

## License

MIT
