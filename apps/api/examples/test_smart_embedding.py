#!/usr/bin/env python3
"""
测试 Smart Embedding Service 自动切换功能
验证 BGE-M3 和 SPECTER 2 的智能选择
"""

import sys
sys.path.insert(0, '/Users/cc/scholar-ai-deploy/schlar ai/scholar-ai/backend-python')

from app.core.specter2_embedding_service import SmartEmbeddingService, Specter2EmbeddingService
from app.core.bge_embedding_service import BGEM3EmbeddingService


def test_smart_selection():
    """测试智能选择逻辑"""
    print("=" * 70)
    print("🧪 测试 Smart Embedding Service 自动切换")
    print("=" * 70)

    service = SmartEmbeddingService(backend="auto")

    test_cases = [
        # (文本, 期望后端, 原因)
        (
            "Transformer architecture has revolutionized NLP.",
            "specter2",
            "英文短论文"
        ),
        (
            "基于Transformer的文本分类方法研究",
            "bge-m3",
            "中文论文"
        ),
        (
            "This is a very long document " * 100,  # >512 tokens
            "bge-m3",
            "超长文档"
        ),
        (
            "Attention Is All You Need: The Transformer Architecture",
            "specter2",
            "英文论文标题"
        ),
        (
            "自然语言处理的最新进展",
            "bge-m3",
            "中文短文本"
        ),
    ]

    print("\n📋 自动选择测试:\n")
    for text, expected, reason in test_cases:
        info = service.get_backend_info(text)
        status = "✅" if info["backend"] == expected else "❌"
        print(f"{status} {reason}")
        print(f"   文本: {text[:50]}...")
        print(f"   选择: {info['backend']} (期望: {expected})")
        print(f"   语言: {info['language']}, Tokens: ~{info['estimated_tokens']}")
        print(f"   建议: {info['recommendation']}\n")


def test_embedding_generation():
    """测试嵌入生成"""
    print("=" * 70)
    print("🧪 测试嵌入生成")
    print("=" * 70)

    # 测试 BGE-M3
    print("\n📦 BGE-M3:")
    try:
        bge = BGEM3EmbeddingService()
        text = "基于深度学习的自然语言处理"
        embedding = bge.generate_embedding(text)
        print(f"   ✅ 维度: {len(embedding)}")
        print(f"   ✅ 前5值: {[round(x, 4) for x in embedding[:5]]}")
    except Exception as e:
        print(f"   ❌ 错误: {e}")

    # 测试 SPECTER 2
    print("\n📦 SPECTER 2:")
    try:
        specter = Specter2EmbeddingService(adapter="proximity")
        text = "Attention Is All You Need: The Transformer Architecture"
        embedding = specter.generate_embedding(text)
        print(f"   ✅ 维度: {len(embedding)}")
        print(f"   ✅ 前5值: {[round(x, 4) for x in embedding[:5]]}")
    except ImportError as e:
        print(f"   ⚠️  跳过: {e}")
    except Exception as e:
        print(f"   ❌ 错误: {e}")


def test_smart_service():
    """测试智能服务自动切换"""
    print("=" * 70)
    print("🧪 测试 Smart Service 自动切换")
    print("=" * 70)

    service = SmartEmbeddingService(backend="auto")

    # 英文论文 -> SPECTER 2
    print("\n📝 英文论文 (应使用 SPECTER 2):")
    en_text = "BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding"
    info = service.get_backend_info(en_text)
    print(f"   选择后端: {info['backend']}")
    print(f"   原因: {info['reason']}")

    try:
        embedding = service.generate_embedding(en_text)
        print(f"   ✅ 成功生成，维度: {len(embedding)}")
    except Exception as e:
        print(f"   ❌ 错误: {e}")

    # 中文论文 -> BGE-M3
    print("\n📝 中文论文 (应使用 BGE-M3):")
    zh_text = "基于Transformer的文本分类方法研究"
    info = service.get_backend_info(zh_text)
    print(f"   选择后端: {info['backend']}")
    print(f"   原因: {info['reason']}")

    try:
        embedding = service.generate_embedding(zh_text)
        print(f"   ✅ 成功生成，维度: {len(embedding)}")
    except Exception as e:
        print(f"   ❌ 错误: {e}")


def test_batch_processing():
    """测试批量处理"""
    print("=" * 70)
    print("🧪 测试批量处理")
    print("=" * 70)

    service = SmartEmbeddingService(backend="auto")

    papers = [
        "BERT: Pre-training of Deep Bidirectional Transformers",  # EN
        "基于Transformer的文本分类方法研究",  # ZH
        "GPT-3: Language Models are Few-Shot Learners",  # EN
    ]

    print(f"\n处理 {len(papers)} 篇论文...")
    try:
        embeddings = service.generate_embeddings_batch(papers)
        print(f"   ✅ 成功生成 {len(embeddings)} 个嵌入")
        for i, emb in enumerate(embeddings):
            print(f"   Paper {i+1}: {len(emb)} 维")
    except Exception as e:
        print(f"   ❌ 错误: {e}")


def test_similarity():
    """测试相似度计算"""
    print("=" * 70)
    print("🧪 测试相似度计算")
    print("=" * 70)

    import numpy as np

    def cosine_sim(a, b):
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

    service = SmartEmbeddingService(backend="auto")

    # 测试语义相似度
    papers = [
        "BERT: Pre-training of Deep Bidirectional Transformers",
        "RoBERTa: A Robustly Optimized BERT Pretraining Approach",
        "ResNet: Deep Residual Learning for Image Recognition",
    ]

    query = "自然语言处理预训练模型"

    print(f"\n查询: {query}")
    print("\n论文相似度:")

    try:
        query_emb = service.generate_embedding(query)
        paper_embs = service.generate_embeddings_batch(papers)

        similarities = []
        for paper, emb in zip(papers, paper_embs):
            sim = cosine_sim(query_emb, emb)
            similarities.append((paper, sim))

        # 排序
        similarities.sort(key=lambda x: x[1], reverse=True)

        for paper, sim in similarities:
            bar = "█" * int(sim * 20) + "░" * (20 - int(sim * 20))
            print(f"   [{bar}] {sim:.4f} - {paper[:40]}...")

    except Exception as e:
        print(f"   ❌ 错误: {e}")


def main():
    print("\n" + "=" * 70)
    print("🚀 Smart Embedding Service 测试套件")
    print("=" * 70)
    print("\n功能:")
    print("  1. BGE-M3: 多语言 + 长文档支持")
    print("  2. SPECTER 2: 英文论文专用，引用关系训练")
    print("  3. Smart: 自动根据语言/长度选择最佳模型")
    print()

    try:
        test_smart_selection()
    except Exception as e:
        print(f"\n❌ 自动选择测试失败: {e}")

    try:
        test_embedding_generation()
    except Exception as e:
        print(f"\n❌ 嵌入生成测试失败: {e}")

    try:
        test_smart_service()
    except Exception as e:
        print(f"\n❌ 智能服务测试失败: {e}")

    try:
        test_batch_processing()
    except Exception as e:
        print(f"\n❌ 批量处理测试失败: {e}")

    try:
        test_similarity()
    except Exception as e:
        print(f"\n❌ 相似度测试失败: {e}")

    print("\n" + "=" * 70)
    print("✅ 测试完成")
    print("=" * 70)
    print("\n💡 使用建议:")
    print("   export EMBEDDING_BACKEND=auto")
    print("   from app.core.specter2_embedding_service import SmartEmbeddingService")
    print("   service = SmartEmbeddingService()")
    print("   embedding = service.generate_embedding(text)  # 自动选择最佳模型")


if __name__ == "__main__":
    main()
