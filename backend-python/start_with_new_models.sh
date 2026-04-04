#!/bin/bash
# 使用新模型启动 Python AI 服务

echo "=========================================="
echo "启动 ScholarAI AI Service"
echo "使用新模型："
echo "  - Embedding: Qwen3-VL-Embedding-2B"
echo "  - Reranker:  Qwen3-VL-Reranker-2B"
echo "=========================================="
echo ""

# 切换到项目根目录（模型文件所在位置）
cd "$(dirname "$0")/.."

# 验证模型路径
if [ ! -d "Qwen/Qwen3-VL-Embedding-2B" ]; then
    echo "❌ Embedding 模型不存在: Qwen/Qwen3-VL-Embedding-2B"
    exit 1
fi

if [ ! -d "Qwen3-VL-Reranker-2B" ]; then
    echo "❌ Reranker 模型不存在: Qwen3-VL-Reranker-2B"
    exit 1
fi

echo "✅ 模型文件检查通过"
echo ""

# 启动服务
cd backend-python
python verify_model_config.py
echo ""
echo "启动服务..."
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
