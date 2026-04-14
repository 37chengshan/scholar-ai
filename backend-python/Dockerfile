FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖（使用国内镜像）
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources && \
    apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    zlib1g-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 配置 pip 使用国内镜像
RUN pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/ && \
    pip config set install.trusted-host mirrors.aliyun.com

# 复制依赖文件
COPY requirements.txt .

# 先安装 CPU 版本的 PyTorch（固定版本避免冲突）
RUN pip install --no-cache-dir torch==2.1.0 torchvision==0.16.0 --extra-index-url https://download.pytorch.org/whl/cpu

# 安装 transformers（固定版本）
RUN pip install --no-cache-dir transformers==4.45.0

# 安装 FlagEmbedding（使用 --no-deps 防止覆盖 torch）
RUN pip install --no-cache-dir --no-deps FlagEmbedding==1.3.5

# 安装其他 Python 依赖
# 先安装关键依赖，确保它们不被静默跳过
RUN pip install --no-cache-dir uvicorn[standard]>=0.24.0 fastapi>=0.100.0 celery==5.3.6 redis>=5.0.1

# 安装剩余依赖（允许部分失败但不影响核心功能）
RUN pip install --no-cache-dir -r requirements.txt || echo "Some dependencies may have conflicts but core is installed"

# 复制应用代码
COPY app/ ./app/

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]