# ScholarAI 后端数据库配置指南

## 🚀 快速开始

### 1. 安装依赖

```bash
cd backend-python
pip install -r requirements.txt
```

### 2. 配置环境变量

编辑 `.env.local` 文件，修改数据库密码：

```bash
vim .env.local

# 修改以下字段为你的实际密码：
POSTGRES_PASSWORD=<YOUR_PASSWORD>
NEO4J_PASSWORD=<YOUR_PASSWORD>
```

### 3. 测试连接

```bash
# 测试数据库连接
python -m scripts.test_db_connection
```

### 4. 初始化数据库

```bash
# 创建必要的表结构和约束
python -m scripts.init_database
```

### 5. 启动服务

```bash
uvicorn app.main:app --reload --port 8000
```

访问文档：`http://localhost:8000/docs`

---

## 📁 配置文件说明

### `.env.local`
本地开发环境配置。⚠️ **不要提交到 Git！**

```
# PostgreSQL (使用环境变量或安全配置)
DATABASE_URL=postgresql://${DB_USER}:${DB_PASSWORD}@${DB_HOST}:${DB_PORT}/${DB_NAME}

# Redis (使用环境变量或安全配置)
REDIS_URL=redis://${REDIS_HOST}:${REDIS_PORT}/${REDIS_DB}

# Neo4j (使用环境变量或安全配置)
NEO4J_URI=bolt://${NEO4J_HOST}:${NEO4J_PORT}
NEO4J_USER=${NEO4J_USER}
NEO4J_PASSWORD=${NEO4J_PASSWORD}
```

### `app/core/config.py`
Pydantic 配置类，自动从 `.env.local` 加载环境变量。

### `app/core/database.py`
数据库连接管理模块：
- `PostgresDB`: PostgreSQL 异步连接池
- `Neo4jDB`: Neo4j 图数据库驱动
- `RedisDB`: Redis 缓存客户端

---

## 🔌 数据库架构

### PostgreSQL (关系型数据)

| 表名 | 用途 |
|-----|------|
| `papers` | 论文基础信息 |
| `citations` | 引用关系 |
| `paper_metadata` | PaperQA2 解析结果 |
| `paper_embeddings` | 向量嵌入 (pgvector) |

### Neo4j (图数据库)

| 节点/关系 | 用途 |
|----------|------|
| `(p:Paper)` | 论文节点 |
| `(a:Author)` | 作者节点 |
| `(p)-[:CITES]->(p)` | 引用关系 |

### Redis (缓存)

| Key | 用途 |
|-----|------|
| `papers:hot` | 热门论文缓存 |
| `paper:{id}` | 单篇论文缓存 |

---

## 🧪 测试脚本

### `scripts/test_db_connection.py`
测试所有数据库连接的脚本：
- 测试 PostgreSQL 读写
- 测试 Neo4j 节点创建
- 测试 Redis 缓存

### `scripts/init_database.py`
初始化数据库结构的脚本：
- 创建 PostgreSQL 表
- 启用 pgvector 扩展
- 创建 Neo4j 约束和索引

---

## 📚 API 示例

### `app/api/papers.py`
论文数据管理 API 示例：

```python
# 创建论文 (PostgreSQL + Neo4j)
POST /papers/

# 获取论文详情 (PostgreSQL + Neo4j 引用)
GET /papers/{paper_id}

# 获取热门论文 (Redis 缓存)
GET /papers/hot

# 创建引用关系 (Neo4j 图关系)
POST /papers/citations

# 获取相关论文 (Neo4j 图遍历)
GET /papers/{paper_id}/related
```

---

## 🔧 故障排查

### 连接超时

```bash
# 检查网络连通性
ping <YOUR_HOST_IP>

# 检查端口开放
telnet <YOUR_HOST_IP> 5432  # PostgreSQL
telnet <YOUR_HOST_IP> 7687  # Neo4j
telnet <YOUR_HOST_IP> 6379  # Redis
```

### 认证失败

1. 检查 `.env.local` 密码是否正确
2. 检查服务器数据库密码

### 表不存在

```bash
# 运行初始化脚本
python -m scripts.init_database
```

---

## 📊 数据库连接状态

| 服务 | 配置方式 | 状态 |
|-----|------|------|
| PostgreSQL | ${DB_HOST}:${DB_PORT} | 环境变量配置 |
| Neo4j | ${NEO4J_HOST}:${NEO4J_PORT} | 环境变量配置 |
| Redis | ${REDIS_HOST}:${REDIS_PORT} | 环境变量配置 |

---

## 📝 注意事项

1. **`.env.local` 不要提交到 Git**，已添加到 `.gitignore`
2. 本地开发时自动使用 `.env.local` 配置
3. 生产环境使用 Docker 环境变量或 Kubernetes Secrets
4. ⚠️ **数据库密码定期更换，使用环境变量模板**