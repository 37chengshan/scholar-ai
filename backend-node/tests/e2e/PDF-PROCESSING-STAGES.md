# PDF处理流程详解

## 完整处理状态流

PDF上传后，系统会依次经过以下处理阶段：

```
pending (等待处理)
    ↓
processing_ocr (OCR识别)
    ↓
parsing (PDF结构解析)
    ↓
extracting_imrad (提取IMRaD结构)
    ↓
generating_notes (生成阅读笔记)
    ↓
storing_vectors (存储向量嵌入) ← 关键阶段
    ↓
indexing_multimodal (多模态索引) ← 关键阶段
    ↓
completed (完成)
```

## 各阶段详解

### 1. pending (等待处理)
- **进度**: 0%
- **描述**: PDF已上传，等待Worker拾取任务
- **耗时**: 通常 < 1秒
- **验证方法**: 
  ```bash
  curl http://localhost:4000/api/papers/{paperId}/status
  # 返回: {"status": "pending", "progress": 0}
  ```

### 2. processing_ocr (OCR识别)
- **进度**: 10%
- **描述**: 使用Docling进行OCR识别，提取文本内容
- **耗时**: 2-10秒（取决于PDF页数）
- **技术栈**: Docling OCR引擎
- **输出**: 文本层、布局信息
- **验证方法**:
  ```bash
  # 检查是否有OCR文本
  curl http://localhost:4000/api/papers/{paperId}
  # 查看ocrText字段
  ```

### 3. parsing (PDF结构解析)
- **进度**: 25%
- **描述**: 解析PDF结构，提取段落、标题、图片、表格
- **耗时**: 5-15秒
- **技术栈**: Docling Parser
- **输出**: 
  - 段落 (paragraphs)
  - 标题 (headings)
  - 图片信息 (images)
  - 表格信息 (tables)
- **验证方法**:
  ```bash
  # 查看解析结果
  curl http://localhost:4000/api/papers/{paperId}
  # 检查parseResult字段
  ```

### 4. extracting_imrad (提取IMRaD结构)
- **进度**: 40%
- **描述**: 识别论文的IMRaD结构（Introduction, Methods, Results, Discussion）
- **耗时**: 2-5秒
- **技术栈**: 自定义IMRaD提取器
- **输出**:
  - introduction (引言)
  - methods (方法)
  - results (结果)
  - discussion (讨论)
- **验证方法**:
  ```bash
  curl http://localhost:4000/api/papers/{paperId}/summary
  # 查看imrad字段
  ```

### 5. generating_notes (生成阅读笔记)
- **进度**: 55%
- **描述**: 基于解析内容自动生成阅读笔记
- **耗时**: 5-15秒（调用LLM）
- **技术栈**: LiteLLM + 智普GLM-4
- **输出**:
  - 核心观点
  - 研究方法
  - 主要发现
  - 阅读建议
- **验证方法**:
  ```bash
  curl http://localhost:4000/api/notes/{paperId}
  # 查看notes字段
  ```

### 6. storing_vectors (存储向量嵌入) ⭐ 关键阶段
- **进度**: 75%
- **描述**: 将文本分块并生成向量嵌入，存储到Milvus
- **耗时**: 5-20秒
- **技术栈**: 
  - 文本分块: 语义分块 (Semantic Chunking)
  - 向量生成: Qwen3-VL-Embedding-2B (2048维)
  - 向量存储: Milvus 2.3
- **处理内容**:
  1. **文本分块**: 将论文按语义切分为chunks
     - 每块大小: 256-512 tokens
     - 分块策略: 语义边界检测
  
  2. **向量生成**: 为每个文本块生成2048维向量
     - 模型: Qwen3-VL-Embedding-2B
     - 维度: 2048
     - 距离度量: COSINE
  
  3. **存储到Milvus**:
     - Collection: `paper_contents`
     - 字段: paper_id, user_id, chunk_id, content, embedding, page_num
     - 索引: IVF_FLAT (nlist=1024)

- **验证方法**:
  ```bash
  # 1. 查看文本块数量
  curl http://localhost:4000/api/papers/{paperId}/chunks
  
  # 2. 直接查询Milvus
  curl http://localhost:8000/internal/milvus/stats
  
  # 3. 检查向量维度
  curl -X POST http://localhost:8000/internal/milvus/query \
    -H "Content-Type: application/json" \
    -d '{"paper_id": "{paperId}", "limit": 1}'
  ```

### 7. indexing_multimodal (多模态索引) ⭐ 关键阶段
- **进度**: 90%
- **描述**: 为图片和表格生成多模态嵌入，支持跨模态检索
- **耗时**: 10-30秒（取决于图片和表格数量）
- **技术栈**: Qwen3-VL-Embedding-2B
- **处理内容**:
  1. **图片嵌入**:
     - 直接编码图片像素
     - 生成2048维向量
     - 存储到Milvus `multimodal_contents` collection
     - 支持以图搜图、以文搜图
  
  2. **表格嵌入**:
     - 将表格序列化为Markdown/JSON
     - 生成2048维向量
     - 支持表格语义检索
  
  3. **多模态索引**:
     - 文本、图片、表格统一在2048维向量空间
     - 支持跨模态检索（文本搜图片、图片搜表格等）

- **验证方法**:
  ```bash
  # 1. 查看多模态内容
  curl http://localhost:4000/api/papers/{paperId}/multimodal
  
  # 2. 查询Milvus多模态collection
  curl http://localhost:8000/internal/milvus/multimodal/stats
  
  # 3. 测试多模态搜索
  curl -X POST http://localhost:8000/api/search/multimodal \
    -H "Content-Type: application/json" \
    -d '{
      "query": "experimental results chart",
      "paper_ids": ["{paperId}"],
      "content_types": ["image", "table"]
    }'
  ```

### 8. completed (完成)
- **进度**: 100%
- **描述**: 所有处理阶段完成，论文可用于检索和问答
- **验证方法**:
  ```bash
  curl http://localhost:4000/api/papers/{paperId}/status
  # 返回: {"status": "completed", "progress": 100}
  ```

## 向量嵌入详解

### 文本向量嵌入流程

```
论文PDF
    ↓ (OCR)
文本内容
    ↓ (语义分块)
文本块 [chunk1, chunk2, ..., chunkN]
    ↓ (Qwen3-VL-Embedding)
向量列表 [vector1, vector2, ..., vectorN]
    ↓ (Milvus存储)
向量数据库索引
```

### 多模态向量嵌入流程

```
论文PDF
    ↓ (解析)
┌─────────┬─────────┬─────────┐
│ 文本    │ 图片    │ 表格    │
└────┬────┴────┬────┴────┬────┘
     │         │         │
     │         │         └─→ 序列化为Markdown
     │         │              ↓
     │         └─→ Qwen3-VL  ↓
     │              ↓        ↓
     └─→ Qwen3-VL  ↓        ↓
          ↓        ↓        ↓
       2048维向量 (统一向量空间)
          ↓        ↓        ↓
       Milvus `multimodal_contents` collection
```

### 向量存储结构

#### 文本向量表 (paper_contents)
```json
{
  "id": "uuid",
  "paper_id": "string",
  "user_id": "string",
  "chunk_id": "int",
  "content": "string (文本内容)",
  "embedding": "float[2048] (向量)",
  "page_num": "int",
  "chunk_type": "string (paragraph|heading|caption)",
  "created_at": "timestamp"
}
```

#### 多模态向量表 (multimodal_contents)
```json
{
  "id": "uuid",
  "paper_id": "string",
  "user_id": "string",
  "content_type": "string (image|table)",
  "content_data": "string (描述/序列化数据)",
  "embedding": "float[2048] (向量)",
  "page_num": "int",
  "bbox": "json (图片位置)",
  "raw_data": "json (表格原始数据)",
  "created_at": "timestamp"
}
```

## 失败状态处理

### 状态: failed
- **进度**: 当前阶段进度
- **原因**: 处理过程中出现错误
- **常见错误**:
  1. PDF下载失败
  2. OCR识别失败
  3. 文件格式不支持
  4. 向量生成失败
  5. Milvus连接失败

### 错误排查步骤

```bash
# 1. 查看错误详情
curl http://localhost:4000/api/papers/{paperId}/status
# 查看error字段

# 2. 检查Python服务日志
tail -f backend-python/logs/app.log

# 3. 检查Milvus连接
curl http://localhost:19530/v1/vector/collections

# 4. 检查数据库连接
psql -U scholarai -d scholarai -c "SELECT * FROM processing_tasks WHERE paper_id = '{paperId}'"

# 5. 重新处理
curl -X POST http://localhost:4000/api/papers/{paperId}/retry
```

## 性能基准

### 处理时间参考（不同大小PDF）

| PDF大小 | 页数 | OCR | 解析 | 向量 | 多模态 | 总时间 |
|---------|------|-----|------|------|--------|--------|
| 270KB   | 10页 | 3s  | 5s   | 5s   | 8s     | 21s    |
| 1MB     | 20页 | 5s  | 8s   | 8s   | 12s    | 33s    |
| 5MB     | 50页 | 10s | 15s  | 15s  | 20s    | 60s    |
| 10MB    | 100页| 15s | 25s  | 25s  | 30s    | 95s    |

### 资源使用

| 资源 | 峰值使用 | 说明 |
|------|----------|------|
| CPU | 75% | OCR和解析阶段 |
| 内存 | 3GB | 大PDF处理时 |
| GPU | 80% | 向量生成（如果有GPU） |
| 磁盘 | 临时2xPDF大小 | 处理完成后清理 |

## API端点汇总

### 状态查询
```bash
GET /api/papers/{paperId}/status
```

### 获取论文详情
```bash
GET /api/papers/{paperId}
```

### 获取摘要和IMRaD
```bash
GET /api/papers/{paperId}/summary
```

### 获取文本块（向量）
```bash
GET /api/papers/{paperId}/chunks?limit=10
```

### 获取多模态内容
```bash
GET /api/papers/{paperId}/multimodal
```

### 获取阅读笔记
```bash
GET /api/notes/{paperId}
```

### 多模态搜索
```bash
POST /api/search/multimodal
{
  "query": "experimental results",
  "paper_ids": ["{paperId}"],
  "content_types": ["image", "table"]
}
```

### 知识图谱
```bash
GET /api/graph/paper/{paperId}
```

## 测试验证清单

使用综合测试脚本时，确保以下内容都已验证：

- [ ] ✅ 状态监控覆盖所有8个阶段
- [ ] ✅ OCR文本成功提取
- [ ] ✅ IMRaD结构正确识别
- [ ] ✅ 阅读笔记成功生成
- [ ] ✅ 文本向量成功生成（2048维）
- [ ] ✅ 向量成功存储到Milvus
- [ ] ✅ 图片嵌入成功生成
- [ ] ✅ 表格嵌入成功生成
- [ ] ✅ 多模态索引完整
- [ ] ✅ 知识图谱节点和关系正确
- [ ] ✅ 最终状态为completed
- [ ] ✅ 进度达到100%

## 故障排查指南

### 问题1: 向量生成失败
**症状**: 在storing_vectors阶段失败

**可能原因**:
1. Qwen3-VL模型加载失败
2. Milvus连接失败
3. 内存不足

**解决方案**:
```bash
# 检查模型
python -c "from app.core.qwen3vl_service import get_qwen3vl_service; s = get_qwen3vl_service(); print(s)"

# 检查Milvus
curl http://localhost:19530/v1/vector/collections

# 增加内存限制（Docker）
docker-compose.yml:
  python:
    mem_limit: 4g
```

### 问题2: 多模态索引失败
**症状**: 在indexing_multimodal阶段失败

**可能原因**:
1. 图片提取失败
2. 表格解析失败
3. 嵌入生成超时

**解决方案**:
```bash
# 查看图片提取日志
grep "image_extractor" backend-python/logs/app.log

# 查看表格提取日志
grep "table_extractor" backend-python/logs/app.log

# 检查Qwen3-VL服务
curl http://localhost:8000/health
```

### 问题3: 处理超时
**症状**: 达到最大轮询次数仍未完成

**可能原因**:
1. PDF过大
2. 系统资源不足
3. Worker并发过高

**解决方案**:
```bash
# 增加超时时间
# 修改测试配置
testConfig.maxPollAttempts = 200

# 检查系统资源
docker stats

# 降低并发
# 修改 python worker 配置
MAX_CONCURRENT_TASKS=2
```

## 相关文档

- [PDF并行流水线架构](../../../doc/PDF_PARALLEL_PIPELINE.md)
- [多模态搜索文档](../../../doc/多模态搜索.md)
- [向量嵌入服务](../../../doc/Qwen3-VL-Embedding.md)
- [Milvus配置](../../../doc/Milvus配置.md)

---

**最后更新**: 2026-04-05  
**维护者**: ScholarAI Team