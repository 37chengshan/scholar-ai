#!/usr/bin/env python3
"""清理所有旧的 Milvus collection（旧数据不需要了）"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.milvus_service import MilvusService
from app.core.config import settings
from app.utils.logger import logger


def main():
    print("=" * 70)
    print("清理旧 Milvus Collection")
    print("=" * 70)
    
    service = MilvusService()
    service.connect()
    
    # 需要删除的旧 collection
    old_collections = [
        ("paper_images", "768维，旧模型"),
        ("paper_tables", "768维，旧模型"),
        ("paper_contents", "1024维，BGE-M3"),
        ("paper_contents_v2", "2048维，但可能需要重建"),
    ]
    
    print("\n🗑️  检查并删除旧 collection:")
    
    deleted_count = 0
    
    for collection_name, description in old_collections:
        if service.has_collection(collection_name):
            print(f"\n  删除: {collection_name} ({description})")
            try:
                service.drop_collection(collection_name)
                print(f"    ✅ 已删除")
                deleted_count += 1
            except Exception as e:
                print(f"    ❌ 删除失败: {e}")
        else:
            print(f"\n  {collection_name} - 不存在，跳过")
    
    print("\n" + "=" * 70)
    print(f"✅ 清理完成: 删除了 {deleted_count} 个旧 collection")
    print("=" * 70)
    
    print("\n📋 下一步:")
    print("  1. 重启服务，会自动创建新的 collection (2048维)")
    print("  2. 上传新的论文进行索引")
    
    service.disconnect()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())