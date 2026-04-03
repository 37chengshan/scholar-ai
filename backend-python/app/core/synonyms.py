"""Synonym expansion service for query understanding.

Expands queries with academic synonyms to improve recall:
- Academic synonym dictionary (English + Chinese)
- jieba tokenization for Chinese text
- OR prefix for expanded terms
- Limit to top 2 synonyms per word (per D-06)

Zero-latency, zero-cost approach.
"""

import jieba
from typing import Dict, List


SYNONYMS: Dict[str, List[str]] = {
    # 目标检测 (Object Detection)
    "YOLO": ["object detection", "real-time detection", "You Only Look Once"],
    "目标检测": ["object detection", "目标识别"],
    "目标识别": ["object recognition", "目标检测"],

    # 网络架构 (Network Architecture)
    "CNN": ["convolutional neural network", "卷积神经网络"],
    "RNN": ["recurrent neural network", "循环神经网络"],
    "Transformer": ["注意力机制", "attention mechanism"],
    "attention": ["注意力机制", "attention mechanism"],
    "ResNet": ["residual network", "残差网络"],
    "VGG": ["visual geometry group", "VGGNet"],
    "BERT": ["bidirectional encoder", "BERT model"],
    "GPT": ["generative pre-trained transformer", "GPT model"],

    # 任务 (Tasks)
    "NLP": ["natural language processing", "自然语言处理"],
    "CV": ["computer vision", "计算机视觉"],
    "深度学习": ["deep learning", "神经网络"],
    "机器学习": ["machine learning", "ML"],
    "强化学习": ["reinforcement learning", "RL"],
    "迁移学习": ["transfer learning", "迁移"],
    "监督学习": ["supervised learning", "有监督"],
    "无监督学习": ["unsupervised learning", "自监督"],
    "目标检测": ["object detection", "目标识别"],
    "图像分类": ["image classification", "分类任务"],
    "语义分割": ["semantic segmentation", "分割"],
    "实例分割": ["instance segmentation", "分割"],
    "文本分类": ["text classification", "情感分析"],
    "命名实体识别": ["named entity recognition", "NER"],
    "机器翻译": ["machine translation", "翻译"],
    "问答系统": ["question answering", "QA"],
    "信息检索": ["information retrieval", "检索"],
    "推荐系统": ["recommendation system", "推荐"],

    # 模型与方法 (Models & Methods)
    "卷积": ["convolution", "卷积操作"],
    "池化": ["pooling", "pooling layer"],
    "激活函数": ["activation function", "activation"],
    "损失函数": ["loss function", "loss"],
    "优化器": ["optimizer", "optimization"],
    "梯度下降": ["gradient descent", "SGD"],
    "反向传播": ["backpropagation", "BP"],
    "过拟合": ["overfitting", "overfit"],
    "欠拟合": ["underfitting", "underfit"],
    "正则化": ["regularization", "regularize"],
    "dropout": ["dropout regularization", "随机失活"],
    "批归一化": ["batch normalization", "BN"],
    "数据增强": ["data augmentation", "augmentation"],
    "预训练": ["pre-training", "pretrain"],
    "微调": ["fine-tuning", "finetune"],
    "特征提取": ["feature extraction", "特征"],
    "嵌入": ["embedding", "embeddings"],
    "编码器": ["encoder", "编码"],
    "解码器": ["decoder", "解码"],
    "注意力": ["attention", "注意力机制"],
    "自注意力": ["self-attention", "self attention"],
    "多头注意力": ["multi-head attention", "多头"],
    "位置编码": ["position encoding", "position embedding"],
    "残差连接": ["residual connection", "skip connection"],
    "层归一化": ["layer normalization", "LN"],
    "词向量": ["word embedding", "word vector"],
    "句向量": ["sentence embedding", "sentence vector"],
    "图神经网络": ["graph neural network", "GNN"],
    "生成模型": ["generative model", "GAN"],
    "判别模型": ["discriminative model", "判别器"],
    "变分自编码器": ["variational autoencoder", "VAE"],
    "自编码器": ["autoencoder", "AE"],
    "对抗生成网络": ["generative adversarial network", "GAN"],

    # 数据与评估 (Data & Evaluation)
    "训练集": ["training set", "train data"],
    "测试集": ["test set", "test data"],
    "验证集": ["validation set", "val data"],
    "交叉验证": ["cross validation", "CV"],
    "准确率": ["accuracy", "acc"],
    "精确率": ["precision", "精确"],
    "召回率": ["recall", "召回"],
    "F1分数": ["F1 score", "F1"],
    "ROC曲线": ["ROC curve", "AUC"],
    "混淆矩阵": ["confusion matrix", "CM"],
    "均方误差": ["mean squared error", "MSE"],
    "交叉熵": ["cross entropy", "交叉熵损失"],
    "BLEU": ["BLEU score", "BLEU metric"],
    "困惑度": ["perplexity", "PPL"],
    "吞吐量": ["throughput", "吞吐"],
    "延迟": ["latency", "延时"],
    "推理速度": ["inference speed", "推理时间"],
    "参数量": ["parameter count", "参数数量"],
    "计算量": ["computation", "FLOPs"],
    "GPU": ["graphics processing unit", "显卡"],
    "CPU": ["central processing unit", "处理器"],
    "并行计算": ["parallel computing", "并行"],
    "分布式训练": ["distributed training", "分布式"],
}


def expand_query(query: str) -> str:
    """Expand query with academic synonyms using jieba tokenization.

    Args:
        query: User query string (Chinese or English)

    Returns:
        Expanded query with "OR {synonym}" for each synonym found

    Examples:
        >>> expand_query("YOLO目标检测")
        'YOLO OR object detection OR real-time detection 目标 检测 OR object detection'
        >>> expand_query("CNN架构")
        'CNN OR convolutional neural network 架构'

    Note:
        Limits to top 2 synonyms per word (per D-06).
    """
    # Tokenize query using jieba (handles Chinese + English)
    words = jieba.lcut(query)

    expanded_parts = []

    for word in words:
        # Add the original word
        expanded_parts.append(word)

        # Add synonyms if word is in dictionary
        if word in SYNONYMS:
            # Limit to top 2 synonyms (per D-06)
            for syn in SYNONYMS[word][:2]:
                expanded_parts.append(f"OR {syn}")

    return " ".join(expanded_parts)