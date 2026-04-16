#!/bin/bash
# ScholarAI Python Worker 部署脚本 - 兼容 Python 3.6
set -e

echo "═══════════════════════════════════════════════════════════════"
echo "  ScholarAI Python Worker 部署脚本 (Python 3.6 兼容版)"
echo "═══════════════════════════════════════════════════════════════"

INSTALL_DIR="/opt/scholarai"
mkdir -p ${INSTALL_DIR}/{uploads,logs,models}

echo "Step 1: 安装 Python 3.9"
echo "─────────────────────────────────────────────────────────────"

# 安装 Python 3.9
if [ -f /etc/redhat-release ]; then
    yum install -y centos-release-scl-rh
    yum install -y rh-python39-python rh-python39-python-devel
    source /opt/rh/rh-python39/enable
    echo "source /opt/rh/rh-python39/enable" >> ~/.bashrc
else
    apt-get update
    apt-get install -y python3.9 python3.9-dev python3.9-venv
fi

echo "✅ Python 3.9 安装完成"

echo ""
echo "Step 2: 创建虚拟环境"
cd ${INSTALL_DIR}
python3.9 -m venv venv 2>/dev/null || /opt/rh/rh-python39/root/usr/bin/python3 -m venv venv
source venv/bin/activate

echo "✅ 虚拟环境创建完成"

echo ""
echo "Step 3: 安装依赖"
pip install --upgrade pip

# 安装兼容版本的包
pip install \
    fastapi==0.104.1 \
    uvicorn[standard]==0.24.0 \
    asyncpg==0.29.0 \
    redis==5.0.1 \
    python-multipart==0.0.6 \
    pydantic==2.5.0 \
    httpx==0.25.0 \
    aiohttp==3.9.0 \
    python-dotenv==1.0.0 \
    structlog==23.2.0 \
    pillow==10.1.0 \
    pypdfium2==4.25.0 \
    filetype==1.2.0

echo "✅ 依赖安装完成"

echo ""
echo "Step 4: 创建启动脚本"
cat > ${INSTALL_DIR}/start.sh << 'STARTEOF'
#!/bin/bash
cd /opt/scholarai
source venv/bin/activate
export PYTHONPATH=/opt/scholarai
export HF_HOME=/opt/scholarai/models
echo "环境就绪，等待上传应用代码..."
STARTEOF

chmod +x ${INSTALL_DIR}/start.sh

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "  基础环境部署完成！"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "下一步："
echo "  1. 上传 apps/api 代码到 ${INSTALL_DIR}/"
echo "  2. 运行 ${INSTALL_DIR}/start.sh"
echo ""
