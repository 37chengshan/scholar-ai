#!/bin/bash
# ScholarAI Python Worker 一键部署脚本
# 适用于阿里云 ECS (CentOS/Ubuntu)
# 无需 Git，直接部署

set -e  # 遇到错误立即退出

echo "═══════════════════════════════════════════════════════════════"
echo "  ScholarAI Python Worker 部署脚本"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# 配置
INSTALL_DIR="/opt/scholarai"
BACKEND_DIR="${INSTALL_DIR}/backend-python"
UPLOADS_DIR="${INSTALL_DIR}/uploads"
LOGS_DIR="${INSTALL_DIR}/logs"

# 数据库配置（请根据实际情况修改）
# ⚠️ SECURITY: Set these via environment variables before running
# Run: export DB_HOST=xxx DB_PASSWORD=xxx REDIS_PASSWORD=xxx NEO4J_PASSWORD=xxx
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-scholarai}"
DB_USER="${DB_USER:-scholarai}"
DB_PASS="${DB_PASSWORD}"

REDIS_HOST="${REDIS_HOST:-localhost}"
REDIS_PORT="${REDIS_PORT:-6379}"
REDIS_PASS="${REDIS_PASSWORD}"

NEO4J_HOST="${NEO4J_HOST:-localhost}"
NEO4J_PORT="${NEO4J_PORT:-7687}"
NEO4J_USER="${NEO4J_USER:-neo4j}"
NEO4J_PASS="${NEO4J_PASSWORD}"

echo "Step 1: 安装系统依赖"
echo "─────────────────────────────────────────────────────────────"

# 检测系统类型
if [ -f /etc/redhat-release ]; then
    # CentOS/RHEL
    yum update -y
    yum install -y python3 python3-pip python3-devel gcc curl wget unzip
elif [ -f /etc/lsb-release ]; then
    # Ubuntu/Debian
    apt-get update
    apt-get install -y python3 python3-pip python3-dev gcc curl wget unzip
else
    echo "不支持的操作系统"
    exit 1
fi

echo "✅ 系统依赖安装完成"
echo ""

echo "Step 2: 创建目录结构"
echo "─────────────────────────────────────────────────────────────"

mkdir -p ${INSTALL_DIR}
mkdir -p ${BACKEND_DIR}
mkdir -p ${UPLOADS_DIR}
mkdir -p ${LOGS_DIR}
mkdir -p ${INSTALL_DIR}/models

echo "✅ 目录结构创建完成"
echo ""

echo "Step 3: 创建 Python 虚拟环境"
echo "─────────────────────────────────────────────────────────────"

cd ${BACKEND_DIR}
python3 -m venv venv
source venv/bin/activate

echo "✅ 虚拟环境创建完成"
echo ""

echo "Step 4: 安装 Python 依赖"
echo "─────────────────────────────────────────────────────────────"

# 创建 requirements.txt
cat > ${BACKEND_DIR}/requirements.txt << 'REQEOF'
# FastAPI
fastapi==0.128.8
uvicorn[standard]==0.34.0
python-multipart==0.0.20

# Database
asyncpg==0.31.0
redis==5.2.1

# Docling
docling==2.69.1
docling-core==2.60.1
docling-parse==4.7.3

# AI/ML
accelerate==1.10.1
transformers==4.57.6
torch==2.8.0
torchvision==0.23.0

# Utils
pydantic==2.12.5
pydantic-settings==2.11.0
python-dotenv==1.0.0
httpx==0.28.1
aiohttp==3.11.16
structlog==25.2.0

# Neo4j
neo4j==5.28.1

# RAG/LangChain
langchain==0.3.23
langchain-openai==0.3.12

# LiteLLM
litellm==1.63.2
REQEOF

# 安装依赖
pip install --upgrade pip
pip install -r requirements.txt

echo "✅ Python 依赖安装完成"
echo ""

echo "Step 5: 创建应用代码"
echo "─────────────────────────────────────────────────────────────"

# 创建 app 目录结构
mkdir -p ${BACKEND_DIR}/app/{core,services,utils,workers}
mkdir -p ${BACKEND_DIR}/app/api

echo "✅ 应用目录结构创建完成"
echo ""

echo "Step 6: 创建环境配置文件"
echo "─────────────────────────────────────────────────────────────"

cat > ${BACKEND_DIR}/.env << 'ENVEOF'
# Database
DATABASE_URL=postgresql://${DB_USER}:${DB_PASS}@${DB_HOST}:${DB_PORT}/${DB_NAME}

# Redis
REDIS_URL=redis://${REDIS_PASS}@${REDIS_HOST}:${REDIS_PORT}/0

# Neo4j
NEO4J_URI=bolt://${NEO4J_HOST}:${NEO4J_PORT}
NEO4J_USER=${NEO4J_USER}
NEO4J_PASSWORD=${NEO4J_PASSWORD}

# Storage
OSS_ENDPOINT=local
LOCAL_STORAGE_PATH=/opt/scholarai/uploads

# HuggingFace Cache
HF_HOME=/opt/scholarai/models

# Logging
LOG_LEVEL=info
ENVEOF

echo "✅ 环境配置文件创建完成"
echo ""

echo "Step 7: 下载 Docling 模型"
echo "─────────────────────────────────────────────────────────────"

# 使用 Python 下载模型
python3 << 'PYEOF'
import os
os.environ['HF_HOME'] = '/opt/scholarai/models'

from huggingface_hub import snapshot_download
import sys

models_to_download = [
    ('ds4sd/docling-models', 'docling'),
    ('docling-project/docling-layout-heron', 'layout-heron'),
]

for repo_id, name in models_to_download:
    try:
        print(f"Downloading {name}...")
        snapshot_download(repo_id=repo_id, cache_dir='/opt/scholarai/models')
        print(f"✅ {name} downloaded")
    except Exception as e:
        print(f"⚠️ {name} failed: {e}", file=sys.stderr)
PYEOF

echo "✅ 模型下载完成"
echo ""

echo "Step 8: 创建启动脚本"
echo "─────────────────────────────────────────────────────────────"

cat > ${INSTALL_DIR}/start-worker.sh << 'STARTEOF'
#!/bin/bash
# 启动 ScholarAI Python Worker

cd /opt/scholarai/backend-python
source venv/bin/activate

export PYTHONPATH=/opt/scholarai/backend-python
export OSS_ENDPOINT=local
export LOCAL_STORAGE_PATH=/opt/scholarai/uploads
export HF_HOME=/opt/scholarai/models

# 加载环境变量
export $(cat /opt/scholarai/backend-python/.env | xargs)

echo "Starting PDF Worker..."
python3 -m app.workers.pdf_worker 2>&1 | tee /opt/scholarai/logs/worker.log
STARTEOF

chmod +x ${INSTALL_DIR}/start-worker.sh

echo "✅ 启动脚本创建完成"
echo ""

echo "Step 9: 创建 Systemd 服务"
echo "─────────────────────────────────────────────────────────────"

cat > /etc/systemd/system/scholarai-worker.service << 'SERVICEEOF'
[Unit]
Description=ScholarAI PDF Worker
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/scholarai/backend-python
Environment=PYTHONPATH=/opt/scholarai/backend-python
Environment=OSS_ENDPOINT=local
Environment=LOCAL_STORAGE_PATH=/opt/scholarai/uploads
Environment=HF_HOME=/opt/scholarai/models
ExecStart=/opt/scholarai/backend-python/venv/bin/python -m app.workers.pdf_worker
Restart=always
RestartSec=5
StandardOutput=append:/opt/scholarai/logs/worker.log
StandardError=append:/opt/scholarai/logs/worker-error.log

[Install]
WantedBy=multi-user.target
SERVICEEOF

systemctl daemon-reload

echo "✅ Systemd 服务创建完成"
echo ""

echo "═══════════════════════════════════════════════════════════════"
echo "  部署完成！"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "安装目录: ${INSTALL_DIR}"
echo "日志目录: ${LOGS_DIR}"
echo "模型目录: ${INSTALL_DIR}/models"
echo ""
echo "启动命令:"
echo "  手动启动: ${INSTALL_DIR}/start-worker.sh"
echo "  服务启动: systemctl start scholarai-worker"
echo "  开机自启: systemctl enable scholarai-worker"
echo ""
echo "查看日志:"
echo "  tail -f ${LOGS_DIR}/worker.log"
echo ""
echo "═══════════════════════════════════════════════════════════════"
