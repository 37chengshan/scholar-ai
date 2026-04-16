#!/bin/bash
# BGE-M3 一键配置脚本

echo "🚀 BGE-M3 开源嵌入模型 - 快速配置"
echo "=================================="
echo ""

# 检查 Python 环境
echo "📋 检查环境..."
python3 --version || { echo "❌ Python 3 未安装"; exit 1; }

# 检查依赖
echo "📦 检查依赖..."
python3 -c "import transformers; import torch; print(f'✅ Transformers {transformers.__version__}'); print(f'✅ PyTorch {torch.__version__}')" 2>/dev/null || {
    echo "⚠️  缺少依赖，正在安装..."
    pip install transformers torch -q
}

# 创建环境变量配置
echo ""
echo "📝 配置环境变量..."
ENV_FILE=".env.bge"

cat > "$ENV_FILE" << 'EOF'
# BGE-M3 开源嵌入模型配置
# 完全免费，本地运行

# 切换为 BGE-M3
EMBEDDING_BACKEND=bge-m3
EMBEDDING_MODEL=BAAI/bge-m3

# 可选：其他开源模型
# EMBEDDING_MODEL=BAAI/bge-large-en-v1.5  # 更快
# EMBEDDING_MODEL=BAAI/bge-small-en-v1.5  # 最轻量
# EMBEDDING_MODEL=Alibaba-NLP/gte-large-en-v1.5  # 阿里巴巴
# EMBEDDING_MODEL=intfloat/e5-large-v2  # Microsoft

# Voyage AI（商业）- 注释掉以使用 BGE-M3
# VOYAGE_API_KEY=your-key-here
# VOYAGE_MODEL=voyage-3
EOF

echo "✅ 配置文件已创建: $ENV_FILE"
echo ""

# 下载模型（可选，首次使用会自动下载）
echo "💾 预下载 BGE-M3 模型（约9GB）..."
echo "   按回车开始下载，或 Ctrl+C 跳过（首次使用时会自动下载）"
read -r

python3 << 'PYTHON'
from huggingface_hub import snapshot_download
import os

# 设置国内镜像（可选）
# os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'

print("📥 正在下载 BGE-M3 模型...")
print("   这可能需要几分钟，取决于网络速度...")
print()

try:
    snapshot_download(
        repo_id="BAAI/bge-m3",
        local_dir="./models/bge-m3",
        local_dir_use_symlinks=False
    )
    print("\n✅ 模型下载完成！")
except Exception as e:
    print(f"\n⚠️  下载失败: {e}")
    print("   首次使用时会自动下载，无需担心")
PYTHON

echo ""
echo "=================================="
echo "✅ BGE-M3 配置完成！"
echo "=================================="
echo ""
echo "📖 使用方法:"
echo ""
echo "   1. 加载环境变量:"
echo "      export \$(cat $ENV_FILE | xargs)"
echo ""
echo "   2. Python 代码:"
echo "      from app.core.bge_embedding_service import BGEM3EmbeddingService"
echo "      service = BGEM3EmbeddingService()"
echo "      embedding = service.generate_embedding('你的文本')"
echo ""
echo "   3. 运行示例:"
echo "      python3 examples/bge_m3_demo.py"
echo ""
echo "💡 提示:"
echo "   - 完全免费，无需 API Key"
echo "   - 1024 维度，8192 tokens 上下文"
echo "   - 支持 100+ 种语言"
echo "   - 可离线使用，保护隐私"
echo ""
