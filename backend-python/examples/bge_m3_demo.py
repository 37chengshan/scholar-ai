#!/usr/bin/env python3
"""
BGE-M3 快速入门示例
完全免费的开源嵌入模型，替代 Voyage AI
"""

import numpy as np
from app.core.bge_embedding_service import BGEM3EmbeddingService


def cosine_similarity(a, b):
    """计算余弦相似度"""
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))


def main():
    print("=" * 60)
    print("🚀 BGE-M3 开源嵌入模型 - 快速入门")
    print("=" * 60)

    # 初始化服务（首次会自动下载模型，约9GB）
    print("\n📥 正在加载 BGE-M3 模型...")
    print("   模型: BAAI/bge-m3 (智源研究院)")
    print("   许可证: MIT (免费商用)")

    service = BGEM3EmbeddingService()

    print(f"✅ 模型加载完成！")
    print(f"   维度: {service.dimension}")
    print(f"   最大上下文: 8192 tokens")
    print(f"   语言支持: 100+ 种语言")

    # 示例1: 单条文本嵌入
    print("\n" + "=" * 60)
    print("示例 1: 单条文本嵌入")
    print("=" * 60)

    paper_abstract = """
    Transformer architecture has become the dominant model for natural language processing
    since its introduction in 2017. The key innovation is the self-attention mechanism,
    which allows the model to weigh the importance of different words in the input sequence.
    This has led to significant improvements in machine translation, text summarization,
    and question answering tasks.
    """

    embedding = service.generate_embedding(paper_abstract)
    print(f"\n输入文本长度: {len(paper_abstract)} 字符")
    print(f"输出嵌入维度: {len(embedding)}")
    print(f"前10个值: {[round(x, 4) for x in embedding[:10]]}")

    # 示例2: 批量处理（效率更高）
    print("\n" + "=" * 60)
    print("示例 2: 批量文本嵌入")
    print("=" * 60)

    papers = [
        "BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding",
        "GPT-3: Language Models are Few-Shot Learners",
        "Attention Is All You Need: The Transformer Architecture",
        "Deep Residual Learning for Image Recognition (ResNet)",
        "ImageNet Classification with Deep Convolutional Neural Networks (AlexNet)",
    ]

    print(f"\n处理 {len(papers)} 篇论文标题...")
    embeddings = service.generate_embeddings_batch(papers)
    print(f"✅ 生成了 {len(embeddings)} 个嵌入向量")

    # 示例3: 语义相似度搜索
    print("\n" + "=" * 60)
    print("示例 3: 语义相似度搜索")
    print("=" * 60)

    query = "natural language processing with transformers"
    query_embedding = service.generate_embedding(query)

    print(f"\n查询: '{query}'")
    print("\n相关度排名:")

    # 计算与所有论文的相似度
    similarities = []
    for i, paper in enumerate(papers):
        sim = cosine_similarity(query_embedding, embeddings[i])
        similarities.append((paper, sim))

    # 按相似度排序
    similarities.sort(key=lambda x: x[1], reverse=True)

    for i, (paper, sim) in enumerate(similarities, 1):
        bar = "█" * int(sim * 20) + "░" * (20 - int(sim * 20))
        print(f"{i}. [{bar}] {sim:.4f} - {paper[:50]}...")

    # 示例4: 中文支持
    print("\n" + "=" * 60)
    print("示例 4: 中文论文嵌入")
    print("=" * 60)

    chinese_papers = [
        "基于Transformer的文本分类方法研究",
        "深度学习在计算机视觉中的应用",
        "自然语言处理的最新进展",
    ]

    chinese_embeddings = service.generate_embeddings_batch(chinese_papers)

    chinese_query = "文本分类与深度学习"
    chinese_query_emb = service.generate_embedding(chinese_query)

    print(f"\n中文查询: '{chinese_query}'")
    print("\n相关度:")

    for paper, emb in zip(chinese_papers, chinese_embeddings):
        sim = cosine_similarity(chinese_query_emb, emb)
        print(f"   {sim:.4f} - {paper}")

    # 示例5: 长文档处理
    print("\n" + "=" * 60)
    print("示例 5: 长文档处理")
    print("=" * 60)

    long_text = """
    Introduction

    Machine learning has revolutionized numerous fields including computer vision,
    natural language processing, and robotics. Deep learning, a subset of machine
    learning based on artificial neural networks, has achieved remarkable success
    in various tasks such as image classification, speech recognition, and machine
    translation.

    Methodology

    We propose a novel architecture that combines the strengths of convolutional
    neural networks and transformer models. Our approach uses a multi-scale feature
    extraction mechanism followed by self-attention layers to capture both local
    and global patterns in the data.

    Results

    Experimental results on benchmark datasets demonstrate that our method
    outperforms existing approaches by a significant margin. On the ImageNet
    dataset, we achieve 95.2% top-5 accuracy, surpassing the previous state-of-the-art
    by 1.5 percentage points.

    Conclusion

    In this paper, we presented a new deep learning architecture that advances
    the state of the art in visual recognition. Future work will explore extending
    this approach to other domains such as video analysis and 3D object detection.
    """ * 5  # 模拟长文档

    print(f"\n文档长度: {len(long_text)} 字符 (~{len(long_text)//4} tokens)")
    long_embedding = service.generate_embedding(long_text)
    print(f"✅ 成功处理长文档！嵌入维度: {len(long_embedding)}")

    print("\n" + "=" * 60)
    print("✅ 所有示例运行完成！")
    print("=" * 60)
    print("\n💡 提示:")
    print("   - BGE-M3 完全免费，无需 API Key")
    print("   - 支持 100+ 种语言")
    print("   - 最大上下文 8192 tokens")
    print("   - 输出维度 1024")
    print("   - 可离线使用，保护数据隐私")


if __name__ == "__main__":
    main()
