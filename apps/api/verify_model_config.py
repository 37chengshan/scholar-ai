#!/usr/bin/env python3
"""验证当前使用的模型配置"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.config import settings
from app.core.embedding.factory import EmbeddingServiceFactory
from app.core.reranker.factory import RerankerServiceFactory


def main():
    print("=" * 60)
    print("ScholarAI 模型配置检查")
    print("=" * 60)
    
    # 1. 检查环境变量
    print("\n📋 环境变量配置:")
    print(f"  EMBEDDING_MODEL      = {settings.EMBEDDING_MODEL}")
    print(f"  EMBEDDING_QUANTIZATION = {settings.EMBEDDING_QUANTIZATION}")
    print(f"  EMBEDDING_DIMENSION  = {settings.EMBEDDING_DIMENSION}")
    print(f"  RERANKER_MODEL       = {settings.RERANKER_MODEL}")
    print(f"  RERANKER_QUANTIZATION = {settings.RERANKER_QUANTIZATION}")
    
    # 2. 检查模型路径
    print("\n📁 模型路径:")
    emb_path = settings.QWEN3VL_EMBEDDING_MODEL_PATH
    rerank_path = settings.QWEN3VL_RERANKER_MODEL_PATH
    
    print(f"  Embedding: {emb_path}")
    if os.path.exists(emb_path):
        print(f"    ✅ 路径存在")
    else:
        print(f"    ❌ 路径不存在")
    
    print(f"  Reranker: {rerank_path}")
    if os.path.exists(rerank_path):
        print(f"    ✅ 路径存在")
    else:
        print(f"    ❌ 路径不存在")
    
    # 3. 检查 Factory 会创建的服务类型
    print("\n🏭 Factory 将创建的服务:")
    
    # Embedding
    try:
        EmbeddingServiceFactory._instances = {}  # 清除缓存
        emb_service = EmbeddingServiceFactory.create()
        service_type = type(emb_service).__name__
        supports_multimodal = emb_service.supports_multimodal()
        
        print(f"  Embedding Service: {service_type}")
        print(f"    - 支持多模态: {'✅ 是' if supports_multimodal else '❌ 否'}")
        
        # 尝试获取维度（如果属性存在）
        if hasattr(emb_service, 'dimension'):
            print(f"    - 向量维度: {emb_service.dimension}")
        
        if "Qwen3VL" in service_type:
            print(f"    ✅ 使用新的 Qwen3-VL 模型")
        else:
            print(f"    ⚠️  使用旧的 BGE 模型")
    except Exception as e:
        print(f"    ❌ 创建失败: {e}")
    
    # Reranker
    try:
        RerankerServiceFactory._instances = {}  # 清除缓存
        rerank_service = RerankerServiceFactory.create()
        service_type = type(rerank_service).__name__
        supports_multimodal = rerank_service.supports_multimodal()
        
        print(f"  Reranker Service: {service_type}")
        print(f"    - 支持多模态: {'✅ 是' if supports_multimodal else '❌ 否'}")
        
        if "Qwen3VL" in service_type:
            print(f"    ✅ 使用新的 Qwen3-VL 模型")
        else:
            print(f"    ⚠️  使用旧的 BGE 模型")
    except Exception as e:
        print(f"    ❌ 创建失败: {e}")
    
    print("\n" + "=" * 60)
    print("✅ 检查完成")
    print("=" * 60)


if __name__ == "__main__":
    main()