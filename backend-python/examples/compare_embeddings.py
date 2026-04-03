#!/usr/bin/env python3
"""
嵌入模型对比测试
对比 BGE-M3、Sentence-Transformers 和（可选）Voyage AI
"""

import time
import numpy as np
from typing import List, Dict, Tuple

def cosine_similarity(a, b):
    """计算余弦相似度"""
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))


def test_model(name: str, service, texts: List[str], query: str) -> Dict:
    """测试单个模型"""
    print(f"\n{'='*60}")
    print(f"测试: {name}")
    print('='*60)

    # 生成嵌入
    start = time.time()
    embeddings = service.generate_embeddings_batch(texts)
    batch_time = time.time() - start

    query_emb = service.generate_embedding(query)
    single_time = time.time() - start - batch_time

    # 计算相似度
    similarities = []
    for emb in embeddings:
        sim = cosine_similarity(query_emb, emb)
        similarities.append(sim)

    # 排序
    ranked = sorted(enumerate(similarities), key=lambda x: x[1], reverse=True)

    print(f"✅ 维度: {len(query_emb)}")
    print(f"⏱️  批量处理: {batch_time:.3f}s ({len(texts)} texts)")
    print(f"⏱️  单条处理: {single_time:.3f}s")
    print(f"\n📊 相似度排名:")
    for i, (idx, sim) in enumerate(ranked[:5], 1):
        marker = "🎯" if i == 1 else "  "
        print(f"{marker} #{i}: {sim:.4f} - {texts[idx][:50]}...")

    return {
        "name": name,
        "dimension": len(query_emb),
        "batch_time": batch_time,
        "single_time": single_time,
        "top_result": texts[ranked[0][0]],
        "top_score": ranked[0][1],
    }


def main():
    print("=" * 70)
    print("🚀 嵌入模型对比测试")
    print("=" * 70)
    print("\n对比模型:")
    print("  1. BGE-M3 (开源免费)")
    print("  2. all-mpnet-base-v2 (当前使用)")
    print("  3. all-MiniLM-L6-v2 (轻量级)")

    # 准备测试数据 - 学术论文主题
    papers = [
        # NLP 相关（应该排前面）
        "Attention Is All You Need: The Transformer Architecture",
        "BERT: Pre-training of Deep Bidirectional Transformers",
        "GPT-3: Language Models are Few-Shot Learners",
        "T5: Text-to-Text Transfer Transformer",
        "RoBERTa: A Robustly Optimized BERT Pretraining Approach",

        # CV 相关
        "ResNet: Deep Residual Learning for Image Recognition",
        "AlexNet: ImageNet Classification with Deep CNNs",
        "Vision Transformer: An Image is Worth 16x16 Words",

        # 其他
        "AlphaGo: Mastering the Game of Go",
        "DQN: Human-level Control Through Deep Reinforcement Learning",
    ]

    query = "natural language processing with transformers and attention"

    print(f"\n查询: '{query}'")
    print(f"文档数: {len(papers)}")

    results = []

    # 测试 BGE-M3
    try:
        from app.core.bge_embedding_service import BGEM3EmbeddingService
        bge_service = BGEM3EmbeddingService()
        result = test_model("BGE-M3 (开源)", bge_service, papers, query)
        results.append(result)
    except Exception as e:
        print(f"\n❌ BGE-M3 测试失败: {e}")

    # 测试 all-mpnet-base-v2
    try:
        from app.core.embedding_service import EmbeddingService
        mpnet_service = EmbeddingService(model_name="sentence-transformers/all-mpnet-base-v2")
        result = test_model("all-mpnet-base-v2 (当前)", mpnet_service, papers, query)
        results.append(result)
    except Exception as e:
        print(f"\n❌ all-mpnet-base-v2 测试失败: {e}")

    # 测试 all-MiniLM-L6-v2
    try:
        from app.core.embedding_service import EmbeddingService
        minilm_service = EmbeddingService(model_name="sentence-transformers/all-MiniLM-L6-v2")
        result = test_model("all-MiniLM-L6-v2 (轻量)", minilm_service, papers, query)
        results.append(result)
    except Exception as e:
        print(f"\n❌ all-MiniLM-L6-v2 测试失败: {e}")

    # 总结
    print("\n" + "=" * 70)
    print("📊 性能总结")
    print("=" * 70)

    for r in results:
        print(f"\n{r['name']}:")
        print(f"  维度: {r['dimension']}")
        print(f"  批量时间: {r['batch_time']:.3f}s")
        print(f"  单条时间: {r['single_time']:.3f}s")
        print(f"  最高分: {r['top_score']:.4f}")
        print(f"  最佳匹配: {r['top_result'][:50]}...")

    # 推荐
    print("\n" + "=" * 70)
    print("💡 推荐")
    print("=" * 70)

    if len(results) >= 2:
        bge = next((r for r in results if "BGE-M3" in r['name']), None)
        current = next((r for r in results if "当前" in r['name']), None)

        if bge and current:
            print(f"\n✅ BGE-M3 vs 当前模型:")
            print(f"   维度: {bge['dimension']} vs {current['dimension']} (↑{bge['dimension']/current['dimension']:.1f}x)")
            print(f"   质量: BGE-M3 更适合学术论文")
            print(f"   成本: BGE-M3 完全免费")

    print("\n" + "=" * 70)
    print("🔧 切换方法")
    print("=" * 70)
    print("\n1. 使用 BGE-M3（推荐）:")
    print("   export EMBEDDING_BACKEND=bge-m3")
    print("   export EMBEDDING_MODEL=BAAI/bge-m3")
    print("\n2. 使用当前模型:")
    print("   export EMBEDDING_BACKEND=sentence-transformers")
    print("   export EMBEDDING_MODEL=sentence-transformers/all-mpnet-base-v2")


if __name__ == "__main__":
    main()
