# ScholarAI / 智读

> **智能学术阅读平台**
>
> **英文名**: ScholarAI
> **中文名**: 智读 (Zhì Dú)
>
> 基于 Agentic RAG 的 AI 论文精读助手

![ScholarAI](https://img.shields.io/badge/ScholarAI-AI%20Powered%20Research%20Assistant-00f5ff)
![React](https://img.shields.io/badge/React-18-61DAFB?logo=react)
![Tailwind](https://img.shields.io/badge/Tailwind-3-06B6D4?logo=tailwindcss)
![Vite](https://img.shields.io/badge/Vite-5-646CFF?logo=vite)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-4169E1?logo=postgresql)
![Neo4j](https://img.shields.io/badge/Neo4j-5-008CC1?logo=neo4j)

---

## 项目介绍

ScholarAI（智读）是一个基于开源生态整合的智能学术阅读平台，通过 Agentic RAG + 混合搜索 + IMRaD 感知分块技术，让科研人员从"读完一篇论文需要 3 小时"缩短到"掌握核心内容只需 10 分钟"。

### 核心创新

- 🔍 **文献库智能检索引擎** - 突破上下文限制，秒级精准检索数百篇论文
- 🧠 **Agentic RAG** - 多轮推理，自动发现跨文档关联
- 📊 **IMRaD 感知分块** - 针对学术论文结构的智能分块策略
- 🌐 **引用网络分析** - PageRank 算法识别领域关键论文

---

## 开发状态

### 已完成功能 ✅

- [x] **云端数据库部署** - PostgreSQL + PGVector + Neo4j + Redis
- [x] **数据库连接配置** - 本地开发环境可连接云端数据库

### 进行中 ⏳

- [ ] Node.js API Gateway 搭建
- [ ] Python AI Service 搭建
- [ ] 用户认证系统
- [ ] PDF 上传与解析

### 待开始 📋

- [ ] 文献库管理
- [ ] Agentic RAG 检索
- [ ] 知识图谱可视化
- [ ] 前端页面开发

---

## 快速开始

### 1. 安装依赖

```bash
cd scholar-ai
npm install
```

### 2. 开发模式

```bash
npm run dev
```

访问 http://localhost:5176

### 3. 构建生产版本

```bash
npm run build
```

构建输出在 `dist/` 目录

---

## 项目结构

```
scholar-ai/
├── src/                          # 前端源码
│   ├── components/
│   │   ├── ui/                   # UI组件
│   │   │   └── Button.tsx
│   │   ├── effects/              # 特效组件
│   │   │   └── ParticleBackground.tsx
│   │   └── sections/             # 页面区块
│   │       ├── Hero.tsx          # 首屏
│   │       ├── PainPoints.tsx
│   │       ├── Features.tsx
│   │       ├── Demo.tsx          # 演示区
│   │       └── Footer.tsx
│   ├── styles/
│   │   └── globals.css           # 全局样式
│   ├── App.tsx                   # 主应用
│   └── main.tsx                  # 入口
├── backend-node/                 # Node.js API Gateway (待创建)
│   └── ...
├── backend-python/               # Python AI Service (待创建)
│   └── ...
├── index.html
├── tailwind.config.js            # Tailwind配置
└── package.json
```

## 云端服务

### 数据库服务（已部署）

| 服务 | 地址 | 端口 | 用途 |
|------|------|------|------|
| PostgreSQL + PGVector | `223.6.249.253` | 5432 | 主数据库 + 向量存储 |
| Neo4j HTTP | `http://223.6.249.253` | 7474 | 图数据库 Web 界面 |
| Neo4j Bolt | `bolt://223.6.249.253` | 7687 | 图数据库连接协议 |
| Redis | `223.6.249.253` | 6379 | 缓存服务 |

**服务器配置**: 阿里云 ECS 4核8G (华东1)

### 本地开发连接

#### 1. 复制配置文件

```bash
# 复制本地开发配置到后端项目
cp /Users/cc/scholar-ai-deploy/local-config/.env.local /path/to/your/backend/.env.local
```

#### 2. 获取数据库密码

请联系项目管理员获取数据库密码，或查看：
- 服务器配置文件: `/www/scholar-ai/.env`
- 本地配置文件: `/Users/cc/scholar-ai-deploy/.env`

#### 3. 连接字符串示例

```bash
# PostgreSQL
DATABASE_URL="postgresql://scholarai:密码@223.6.249.253:5432/scholarai"

# Neo4j
NEO4J_URI="bolt://223.6.249.253:7687"
NEO4J_USER="neo4j"

# Redis
REDIS_URL="redis://223.6.249.253:6379"
```

#### 4. 测试连接

```bash
# 测试 PostgreSQL
psql "postgresql://scholarai:密码@223.6.249.253:5432/scholarai" -c "SELECT 1;"

# 测试 Redis
redis-cli -h 223.6.249.253 -p 6379 ping

# 测试 Neo4j（浏览器）
open http://223.6.249.253:7474
```

---

---

## 设计系统

### 颜色方案

| 变量 | 值 | 用途 |
|------|-----|------|
| `--bg-primary` | `#050508` | 主背景 |
| `--neon-cyan` | `#00f5ff` | 霓虹青（主色） |
| `--neon-blue` | `#0080ff` | 霓虹蓝 |
| `--neon-purple` | `#b829dd` | 霓虹紫 |

### 字体

- **标题**：Chakra Petch（科技感）
- **正文**：Sora（现代简洁）

### 动画

- 入场动画：stagger 延迟淡入
- 悬停效果：发光 + 上浮
- 持续动画：粒子连接、脉冲光效
- 鼠标交互：粒子被鼠标吸引

---

## 技术栈

- ⚡ **Vite** - 极速开发体验
- ⚛️ **React 18** - UI框架
- 🎨 **Tailwind CSS** - 原子化样式
- ✨ **Framer Motion** - 流畅动画
- 🌐 **Canvas API** - 粒子系统
- 📘 **TypeScript** - 类型安全

---

## 开源协议

Apache 2.0 License

---

*ScholarAI - 让科研更高效*
