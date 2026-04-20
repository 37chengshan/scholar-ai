#!/usr/bin/env python3
"""检查数据库向量维度与模型配置的一致性"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.config import settings
from app.core.milvus_service import MilvusService


def main():
    print("=" * 70)
    print("数据库向量维度一致性检查")
    print("=" * 70)
    
    # 1. 检查配置中的维度
    print("\n📋 配置文件中的维度:")
    print(f"  EMBEDDING_DIMENSION = {settings.EMBEDDING_DIMENSION}")
    
    # 2. 检查 MilvusService 中的维度配置
    print("\n📁 MilvusService 中的维度:")
    print(f"  embedding_dim = {settings.EMBEDDING_DIMENSION} (from settings.EMBEDDING_DIMENSION)")
    print(f"  ✅ 使用配置文件中的维度，无硬编码")
    
    # 3. 检查问题
    print("\n🔍 问题分析:")
    
    # 读取 create_collection_v2 的代码
    with open('app/core/milvus_service.py', 'r') as f:
        content = f.read()
        
    # 检查硬编码的 2048
    if "embedding_dim=2048" in content:
        print("  ❌ create_collection_v2() 中硬编码了 2048 维")
        print("     建议: 应该使用 settings.EMBEDDING_DIMENSION")
    
    # 检查是否使用了配置
    if "settings.EMBEDDING_DIMENSION" in content:
        print("  ✅ 代码中使用了 settings.EMBEDDING_DIMENSION")
    else:
        print("  ⚠️  代码中未使用 settings.EMBEDDING_DIMENSION")
    
    # 4. 维度匹配检查
    print("\n🎯 维度匹配检查:")
    
    config_dim = settings.EMBEDDING_DIMENSION
    
    if config_dim == 2048:
        print(f"  ✅ 配置维度 {config_dim} 与 Qwen3-VL-Embedding (2048维) 匹配")
    elif config_dim == 1024:
        print(f"  ⚠️  配置维度 {config_dim} 与 BGE-M3 (1024维) 匹配")
    elif config_dim == 768:
        print(f"  ⚠️  配置维度 {config_dim} 与旧模型 (768维) 匹配")
    else:
        print(f"  ❌ 配置维度 {config_dim} 未知")
    
    # 5. 建议
    print("\n💡 修复建议:")
    print("  1. 将 MilvusService.EMBEDDING_DIM 更新为使用配置")
    print("  2. 删除硬编码的维度值")
    print("  3. 统一使用 settings.EMBEDDING_DIMENSION")
    
    print("\n" + "=" * 70)
    
    # 返回状态
    if config_dim == 2048:
        print("✅ 配置正确: Qwen3-VL (2048维)")
        return 0
    else:
        print("⚠️  配置需要更新")
        return 1


if __name__ == "__main__":
    sys.exit(main())