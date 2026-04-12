#!/bin/bash
# ScholarAI Python Worker 最小化部署
set -e

echo "═══════════════════════════════════════════════════════════════"
echo "  ScholarAI Python Worker 部署脚本 (Minimal)"
echo "═══════════════════════════════════════════════════════════════"

INSTALL_DIR="/opt/scholarai"
mkdir -p ${INSTALL_DIR}/{uploads,logs,models}

echo "Step 1: 检查 Python 版本"
echo "─────────────────────────────────────────────────────────────"

PYTHON_VERSION=$(python3 --version 2>&1 | grep -oP '\d+\.\d+' | head -1)
echo "当前 Python 版本: $PYTHON_VERSION"

if [[ "$PYTHON_VERSION" < "3.9" ]]; then
    echo "⚠️ Python 版本过低，尝试安装 Python 3.11..."
    
    # 尝试多种方式安装 Python 3.11
    if command -v apt-get &> /dev/null; then
        # Ubuntu/Debian
        apt-get update
        apt-get install -y software-properties-common
        add-apt-repository -y ppa:deadsnakes/ppa
        apt-get update
        apt-get install -y python3.11 python3.11-dev python3.11-venv python3.11-distutils
        ln -sf /usr/bin/python3.11 /usr/bin/python3
    elif command -v yum &> /dev/null; then
        # CentOS/RHEL - 使用 alternatives
        yum install -y python3.11 python3.11-devel
        alternatives --set python3 /usr/bin/python3.11
    fi
fi

echo "✅ Python 检查完成"

echo ""
echo "Step 2: 创建虚拟环境"
cd ${INSTALL_DIR}
python3 -m venv venv || python3.11 -m venv venv
source venv/bin/activate

echo "✅ 虚拟环境创建完成"

echo ""
echo "Step 3: 安装基础依赖"
pip install --upgrade pip setuptools wheel

# 使用较新版本但仍兼容的依赖
cat > ${INSTALL_DIR}/requirements.txt << 'REQEOF'
# Web Framework
fastapi>=0.100.0,<0.110.0
uvicorn[standard]>=0.23.0,<0.25.0
python-multipart>=0.0.6

# Database
asyncpg>=0.28.0,<0.30.0
redis>=4.5.0,<5.0.0

# Docling - 使用简化版
docling>=2.0.0,<3.0.0

# Utils
pydantic>=2.0.0,<2.6.0
httpx>=0.25.0,<0.26.0
aiohttp>=3.8.0,<4.0.0
python-dotenv>=1.0.0
structlog>=23.0.0,<24.0.0
pillow>=10.0.0,<11.0.0
pypdfium2>=4.20.0,<5.0.0
REQEOF

pip install -r requirements.txt

echo "✅ 依赖安装完成"

echo ""
echo "Step 4: 创建环境配置"
cat > ${INSTALL_DIR}/.env << 'ENVEOF'
# ⚠️ SECURITY: All credentials must be set via environment variables
# Run: export DB_PASSWORD=xxx REDIS_PASSWORD=xxx NEO4J_PASSWORD=xxx
# before executing this script

# Database - credentials from environment
DATABASE_URL=postgresql://${DB_USER:-scholarai}:${DB_PASSWORD}@${DB_HOST:-localhost}:${DB_PORT:-5432}/${DB_NAME:-scholarai}

# Redis - credentials from environment
REDIS_URL=redis://${REDIS_HOST:-localhost}:${REDIS_PORT:-6379}/${REDIS_DB:-0}

# Neo4j - credentials from environment
NEO4J_URI=bolt://${NEO4J_HOST:-localhost}:${NEO4J_PORT:-7687}
NEO4J_USER=${NEO4J_USER:-neo4j}
NEO4J_PASSWORD=${NEO4J_PASSWORD}

# Storage
OSS_ENDPOINT=local
LOCAL_STORAGE_PATH=/opt/scholarai/uploads

# HuggingFace Cache
HF_HOME=/opt/scholarai/models
HF_HUB_OFFLINE=0

# Logging
LOG_LEVEL=info
ENVEOF

echo "✅ 环境配置创建完成"

echo ""
echo "Step 5: 创建启动脚本"
cat > ${INSTALL_DIR}/start.sh << 'STARTEOF'
#!/bin/bash
cd /opt/scholarai
source venv/bin/activate

export PYTHONPATH=/opt/scholarai
export HF_HOME=/opt/scholarai/models
export $(cat .env | xargs)

echo "═══════════════════════════════════════════════════════════════"
echo "  ScholarAI Python Worker"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "等待上传应用代码后启动..."
echo ""
echo "使用方法:"
echo "  1. 上传 backend-python/app 代码到 /opt/scholarai/"
echo "  2. 运行: python -m app.workers.pdf_worker"
echo ""
echo "═══════════════════════════════════════════════════════════════"
STARTEOF

chmod +x ${INSTALL_DIR}/start.sh

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "  部署完成！"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "安装目录: ${INSTALL_DIR}"
echo "虚拟环境: ${INSTALL_DIR}/venv"
echo "日志目录: ${INSTALL_DIR}/logs"
echo "模型目录: ${INSTALL_DIR}/models"
echo ""
echo "下一步:"
echo "  1. 上传 backend-python/app 代码"
echo "  2. 运行 ${INSTALL_DIR}/start.sh"
echo ""
echo "═══════════════════════════════════════════════════════════════"
