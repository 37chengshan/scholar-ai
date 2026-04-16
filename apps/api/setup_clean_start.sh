#!/bin/bash
# 清理旧数据并启动服务

echo "=========================================="
echo "ScholarAI 服务启动脚本"
echo "=========================================="
echo ""

# 切换到项目根目录
cd "$(dirname "$0")/.."

echo "📋 步骤 1: 启动 Docker 服务（包括 Milvus）"
echo "----------------------------------------"
docker-compose up -d

echo ""
echo "⏳ 等待服务就绪..."
sleep 10

echo ""
echo "📋 步骤 2: 检查服务状态"
echo "----------------------------------------"
docker-compose ps

echo ""
echo "📋 步骤 3: 清理旧 Collection"
echo "----------------------------------------"
cd apps/api
python cleanup_old_collections.py 2>&1 | grep -E "(删除|清理完成|不存在)"

echo ""
echo "📋 步骤 4: 验证配置"
echo "----------------------------------------"
python verify_model_config.py 2>&1 | grep -E "(✅|❌|Embedding|Reranker|环境变量)"

echo ""
echo "=========================================="
echo "✅ 准备完成！"
echo "=========================================="
echo ""
echo "🎯 下一步操作:"
echo "  1. 启动后端服务:"
echo "     cd apps/api"
echo "     uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
echo ""
echo "  2. 上传论文进行索引"
echo ""
echo "📁 模型信息:"
echo "  - Embedding: Qwen3-VL-Embedding-2B (2048维)"
echo "  - Reranker:  Qwen3-VL-Reranker-2B"
echo "  - 量化: INT4"
echo ""