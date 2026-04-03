# 开源嵌入模型推荐 - 替代 Voyage AI

如果你希望**完全免费**且**本地运行**嵌入模型，以下是最佳开源选择。

## 🏆 推荐方案

### 1. BGE-M3（首推）

```python
# 安装
pip install transformers torch

# 使用
from app.core.bge_embedding_service import BGEM3EmbeddingService

service = BGEM3EmbeddingService()
embedding = service.generate_embedding("Your paper abstract here...")
print(f"Dimension: {len(embedding)}")  # 1024
```

**优势：**
- ✅ 完全免费（MIT 许可证）
- ✅ 8192 token 上下文（适合长论文）
- ✅ 100+ 语言支持
- ✅ 1024 维度（与 Voyage-3 相同）
- ✅ 本地运行，无需网络
- ✅ MTEB 分数 66.36（接近商业模型）

**硬件要求：**
- GPU: 推荐（但 CPU 也可运行）
- 显存: ~6GB
- 内存: ~8GB
- 存储: ~9GB 模型文件

---

### 2. GTE-Qwen2-7B（阿里巴巴）

```python
from app.core.bge_embedding_service import OpenSourceEmbeddingService

# 超大规模上下文（131072 tokens）
service = OpenSourceEmbeddingService(
    model_name="Alibaba-NLP/gte-Qwen2-7B-instruct"
)
```

**优势：**
- 3584 维度
- 131K 上下文（整本书都能嵌入）
- 指令微调，适合问答

**劣势：**
- 需要 ~14GB 显存
- 推理较慢

---

### 3. E5-Mistral-7B（Microsoft）

```python
service = OpenSourceEmbeddingService(
    model_name="intfloat/e5-mistral-7b-instruct"
)
```

**优势：**
- 4096 维度
- 32K 上下文
- 指令微调强

---

## 📊 性能对比

| 模型 | MTEB | 维度 | 上下文 | 显存 | 速度 |
|------|------|------|--------|------|------|
| **Voyage-3** | ~68* | 1024 | 32K | N/A | API依赖 |
| **BGE-M3** | 66.36 | 1024 | 8K | 6GB | 中等 |
| **SFR-Embedding-2_R** | 70.31 | 4096 | 32K | 14GB | 慢 |
| **GTE-Qwen2-7B** | 70.24 | 3584 | 131K | 14GB | 慢 |
| **E5-Mistral-7B** | 66.63 | 4096 | 32K | 14GB | 慢 |
| **GTE-large** | 66.06 | 1024 | 8K | 2GB | 快 |
| **BGE-large** | 64.53 | 1024 | 512 | 1.5GB | 快 |

*Voyage 未公开 MTEB，根据论文估计

---

## 💰 成本对比（1000篇论文）

| 方案 | 成本 | 速度 | 隐私 |
|------|------|------|------|
| **Voyage-3** | $0.23 | 中等 | 数据外传 |
| **BGE-M3 (GPU)** | $0 | 快 | ✅ 本地 |
| **BGE-M3 (CPU)** | $0 | 较慢 | ✅ 本地 |
| **OpenAI** | $1.30 | 快 | 数据外传 |

---

## 🔧 快速切换

修改 `.env` 即可切换：

```bash
# 商业 API（付费）
EMBEDDING_BACKEND=voyage
VOYAGE_API_KEY=pa-...
VOYAGE_MODEL=voyage-3

# 开源本地（免费）
EMBEDDING_BACKEND=bge-m3
# 无需 API Key！
```

或在代码中切换：

```python
# Voyage（付费，高质量）
from app.core.voyage_embedding_service import VoyageEmbeddingService
voyage = VoyageEmbeddingService(model="voyage-3")

# BGE-M3（免费，本地运行）
from app.core.bge_embedding_service import BGEM3EmbeddingService
bge = BGEM3EmbeddingService()  # 自动下载模型

# 两者 API 完全相同
embedding = service.generate_embedding(text)
```

---

## 🚀 部署建议

### 场景1: 个人研究（推荐 BGE-M3）

```bash
# 1. 安装依赖
pip install transformers torch

# 2. 模型自动下载（首次 ~9GB）
python -c "from app.core.bge_embedding_service import BGEM3EmbeddingService; BGEM3EmbeddingService()"

# 3. 开始使用
export EMBEDDING_BACKEND=bge-m3
```

### 场景2: 服务器部署

```python
# 预加载模型到内存
from app.core.bge_embedding_service import BGEM3EmbeddingService

# 启动时加载
service = BGEM3EmbeddingService(device="cuda")

# FastAPI 中使用
@app.post("/embed")
async def embed(text: str):
    embedding = service.generate_embedding(text)
    return {"embedding": embedding}
```

### 场景3: 无 GPU 环境

```python
# CPU 模式（较慢但可用）
service = BGEM3EmbeddingService(device="cpu")

# 或使用更小的模型
from app.core.bge_embedding_service import OpenSourceEmbeddingService

service = OpenSourceEmbeddingService(
    model_name="BAAI/bge-small-en-v1.5"  # 384维，更快
)
```

---

## 📥 模型下载

模型会自动从 HuggingFace 下载：

```python
# 手动下载（如果网络问题）
from huggingface_hub import snapshot_download

# 设置镜像（国内用户）
export HF_ENDPOINT=https://hf-mirror.com

# 下载模型
snapshot_download(repo_id="BAAI/bge-m3", local_dir="./models/bge-m3")
```

国内镜像：
- https://hf-mirror.com
- https://modelscope.cn

---

## 🎯 选择建议

| 你的情况 | 推荐方案 |
|---------|----------|
| 追求免费 + 隐私 | ✅ BGE-M3 |
| 追求最高质量 | Voyage-3 或 SFR-Embedding |
| 追求速度 | GTE-large 或 BGE-small |
| 长文档（>8K tokens） | GTE-Qwen2-7B |
| 无 GPU | BGE-small 或 Voyage API |
| 多语言论文 | BGE-M3 |

---

## 🔬 学术研究特别推荐

### 针对学术论文优化的模型

1. **BGE-M3** - 智源研究院专门针对学术文本训练
2. **SFR-Embedding-2_R** - Salesforce 在科学文献上微调
3. **GTE-Qwen2-7B** - 阿里巴巴的长文档优化

### 混合策略

```python
# 新论文使用 BGE-M3（免费）
# 重要论文同时使用 Voyage（高质量）做双重验证

bge_service = BGEM3EmbeddingService()
voyage_service = VoyageEmbeddingService(model="voyage-3")

# 对比两种嵌入的检索结果
bge_results = search_with_embedding(bge_embedding)
voyage_results = search_with_embedding(voyage_embedding)

# 取交集或加权融合
final_results = reciprocal_rank_fusion(bge_results, voyage_results)
```

---

## 📚 相关链接

- **BGE-M3**: https://huggingface.co/BAAI/bge-m3
- **GTE**: https://huggingface.co/Alibaba-NLP/gte-large-en-v1.5
- **E5**: https://huggingface.co/intfloat/e5-large-v2
- **SFR**: https://huggingface.co/Salesforce/SFR-Embedding-2_R
- **MTEB 排行榜**: https://huggingface.co/spaces/mteb/leaderboard
