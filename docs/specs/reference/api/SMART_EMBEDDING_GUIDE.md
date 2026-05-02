# Smart Embedding Service - 使用指南

## 功能概述

自动根据论文语言和长度选择最佳嵌入模型：

| 场景 | 自动选择 | 原因 |
|------|---------|------|
| 英文论文 (<512 tokens) | SPECTER 2 | 学术专用，引用关系训练 |
| 中文/其他语言 | BGE-M3 | 多语言支持 |
| 长文档 (>512 tokens) | BGE-M3 | 8192 token 上下文 |

## 快速开始

### 1. 配置环境变量

```bash
# 添加到 .env
EMBEDDING_BACKEND=auto
EMBEDDING_MODEL=BAAI/bge-m3
SPECTER2_ADAPTER=proximity
```

### 2. 安装依赖

```bash
pip install adapters structlog
```

### 3. 使用代码

```python
from app.core.specter2_embedding_service import SmartEmbeddingService

# 创建智能服务
service = SmartEmbeddingService(backend="auto")

# 自动选择最佳模型生成嵌入
embedding = service.generate_embedding("你的论文文本")

# 查看选择的模型
info = service.get_backend_info("你的论文文本")
print(f"使用模型: {info['backend']}")
print(f"原因: {info['recommendation']}")
```

## 模型对比

| 特性 | BGE-M3 | SPECTER 2 |
|------|--------|-----------|
| **维度** | 1024 | 768 |
| **上下文** | 8192 tokens | 512 tokens |
| **语言** | 100+ | 英文为主 |
| **训练数据** | 通用多语言 | 600万+论文引用 |
| **速度** | 中等 | 快 |
| **显存** | ~6GB | ~2GB |

## 手动指定模型

```python
# 强制使用 BGE-M3
service = SmartEmbeddingService(backend="bge-m3")

# 强制使用 SPECTER 2
service = SmartEmbeddingService(backend="specter2")

# 使用其他适配器
service = SmartEmbeddingService(
    backend="specter2",
    specter_adapter="adhoc_query"  # proximity, classification, regression
)
```

## 批量处理

```python
papers = [
    "BERT: Pre-training of Deep Bidirectional Transformers",  # EN -> SPECTER2
    "基于Transformer的文本分类方法研究",  # ZH -> BGE-M3
    "GPT-3: Language Models are Few-Shot Learners",  # EN -> SPECTER2
]

# 自动为每篇论文选择最佳模型
embeddings = service.generate_embeddings_batch(papers)
```

## 文件结构

```
apps/api/app/core/
├── embedding_service.py              # 原始 Sentence Transformers
├── bge_embedding_service.py          # BGE-M3 (多语言)
├── specter2_embedding_service.py     # SPECTER 2 (英文) + Smart
```

## 依赖

```
# requirements.txt 已更新
transformers>=4.30.0
torch>=2.0.0
adapters>=0.2.0  # SPECTER 2 必需
structlog>=23.0.0
```

## 注意事项

1. **首次使用**会自动下载模型:
   - BGE-M3: ~9GB
   - SPECTER 2: ~500MB

2. **SPECTER 2 限制**:
   - 仅优化英文论文
   - 最大 512 tokens
   - 需要 `adapters` 库

3. **自动切换依据**:
   - 中文字符 → BGE-M3
   - 日/韩/俄/阿/希腊文 → BGE-M3
   - 英文且长度<512 → SPECTER 2
   - 英文但长度>512 → BGE-M3
