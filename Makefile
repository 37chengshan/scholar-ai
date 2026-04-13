# ScholarAI 开发环境 Makefile

.PHONY: help install dev build up down logs ps clean reset

# 默认显示帮助
help:
	@echo "ScholarAI 开发环境命令"
	@echo ""
	@echo "安装和启动:"
	@echo "  make install    - 安装所有依赖"
	@echo "  make dev        - 启动本地开发环境 (只启动数据库)"
	@echo "  make up         - 使用 Docker Compose 启动所有服务"
	@echo ""
	@echo "Docker 操作:"
	@echo "  make down       - 停止所有 Docker 服务"
	@echo "  make logs       - 查看所有服务日志"
	@echo "  make logs-api   - 查看 API 服务日志"
	@echo "  make logs-ai    - 查看 AI 服务日志"
	@echo "  make ps         - 查看服务状态"
	@echo "  make build      - 重建 Docker 镜像"
	@echo ""
	@echo "数据库操作:"
	@echo "  make db-migrate - 运行数据库迁移 (Python backend)"
	@echo "  make db-reset   - 重置数据库"
	@echo ""
	@echo "清理:"
	@echo "  make clean      - 清理构建文件和容器"
	@echo "  make reset      - 完全重置环境 (⚠️ 会删除数据)"

# 安装依赖
install:
	@echo "📦 安装前端依赖..."
	cd frontend && npm install
	@echo "📦 安装 Python 后端依赖..."
	cd backend-python && pip install -r requirements.txt
	@echo "✅ 依赖安装完成"

# 启动开发环境 (只启动数据库)
dev:
	@echo "🐳 启动数据库服务..."
	docker-compose up -d postgres redis neo4j milvus-etcd milvus-minio milvus-standalone
	@echo "✅ 数据库已启动"
	@echo ""
	@echo "请手动启动其他服务:"
	@echo "  1. cd backend-python && uvicorn app.main:app --reload --port 8000"
	@echo "  2. cd frontend && npm run dev"

# Docker Compose 操作
up:
	@echo "🚀 启动所有服务..."
	docker-compose up -d

down:
	@echo "🛑 停止所有服务..."
	docker-compose down

logs:
	docker-compose logs -f

logs-api:
	docker-compose logs -f api

logs-ai:
	docker-compose logs -f ai-service

ps:
	docker-compose ps

build:
	docker-compose up -d --build

# 数据库操作 (Python backend uses SQLAlchemy)
db-migrate:
	@echo "⚠️ Python backend uses SQLAlchemy auto-migration"
	@echo "Run: cd backend-python && python -c 'from app.db.base import init_db; init_db()'"

db-reset:
	@echo "⚠️ 重置数据库..."
	docker-compose down -v postgres redis neo4j milvus-etcd milvus-minio milvus-standalone
	docker volume rm scholar-ai_postgres_data scholar-ai_redis_data scholar-ai_neo4j_data 2>/dev/null || true
	docker-compose up -d postgres redis neo4j milvus-etcd milvus-minio milvus-standalone
	@echo "✅ 数据库已重置"

# 清理
clean:
	@echo "🧹 清理构建文件..."
	docker-compose down -v
	rm -rf frontend/dist
	rm -rf frontend/node_modules
	rm -rf node_modules
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".venv" -exec rm -rf {} + 2>/dev/null || true
	@echo "✅ 清理完成"

reset: clean
	@echo "⚠️  正在完全重置环境..."
	docker volume rm scholar-ai_postgres_data scholar-ai_redis_data scholar-ai_neo4j_data 2>/dev/null || true
	@echo "✅ 环境已重置"