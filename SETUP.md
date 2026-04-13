# ScholarAI 智读 - 开发环境配置指南

## 🚀 快速开始

### 方式一：Docker Compose（推荐）

```bash
# 1. 克隆项目并进入目录
cd scholar-ai

# 2. 启动所有服务
docker-compose up -d

# 3. 查看服务状态
docker-compose ps
```

服务启动后：
- 前端: http://localhost:3000
- Python AI API: http://localhost:8000
- PostgreSQL: localhost:5432
- Redis: localhost:6379
- Neo4j: http://localhost:7474

### 方式二：本地开发

#### 1. 启动基础设施

```bash
# 只启动数据库服务
docker-compose up -d postgres redis neo4j
```

#### 2. 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件，添加你的 API 密钥
```

#### 3. 启动 Python AI 服务

```bash
cd backend-python

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 启动服务
uvicorn app.main:app --reload --port 8000
```

#### 4. 启动前端

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

## 📁 项目结构

```
scholar-ai/
├── docker-compose.yml       # Docker 编排配置
├── .env                     # 环境变量
├── papers/                  # PDF 文件存储目录
│
├── frontend/                # React + Vite 前端
│   ├── src/
│   └── ...
│
└── backend-python/          # Python AI 服务 (FastAPI)
    ├── app/
    │   ├── api/            # API 路由
    │   ├── core/           # 核心配置
    │   ├── services/       # 业务逻辑
    │   └── utils/          # 工具函数
    └── ...
```

## 🔧 常用命令

### Docker 命令

```bash
# 启动所有服务
docker-compose up -d

# 停止所有服务
docker-compose down

# 查看日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs -f ai-service

# 重建服务
docker-compose up -d --build

# 进入容器
docker-compose exec postgres psql -U scholarai
```

### 数据库命令

```bash
cd backend-node

# 生成迁移文件
npx prisma migrate dev --name <migration-name>

# 应用迁移
npx prisma migrate deploy

# 查看数据库
npx prisma studio

# 重置数据库
npx prisma migrate reset
```

## 🔑 API 密钥配置

1. **OpenAI API Key**: https://platform.openai.com/api-keys
2. **Anthropic API Key**: https://console.anthropic.com/settings/keys

获取后填入 `.env` 文件：
```
OPENAI_API_KEY=sk-your-key-here
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

## 📚 API 文档

- Python AI Service: http://localhost:8000/docs (Swagger UI)
- API Health: http://localhost:8000/api/v1/health

## 🐛 故障排查

### 端口被占用
```bash
# 查看端口占用
lsof -i :5432  # PostgreSQL
lsof -i :6379  # Redis
lsof -i :8000  # Python AI
lsof -i :3000  # Frontend
```

### 数据库连接失败
```bash
# 检查数据库是否运行
docker-compose ps postgres

# 检查数据库日志
docker-compose logs postgres

# 手动连接测试
docker-compose exec postgres psql -U scholarai -d scholarai
```

### Python AI 服务启动失败
```bash
# 检查依赖是否安装
pip list | grep paper-qa
pip list | grep docling

# 查看日志
docker-compose logs ai-service
```

## 📖 下一步

1. [ ] 配置 API 密钥
2. [ ] 启动开发环境
3. [ ] 测试 PDF 上传和解析
4. [ ] 集成 PaperQA2 RAG 功能
5. [ ] 开发前端界面

---

*环境配置完成时间: 2026-03-13*
