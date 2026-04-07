# PDF处理快速参考卡片

## 📋 处理状态流

```
pending (0%)
    ↓
processing_ocr (10%)
    ↓
parsing (25%)
    ↓
extracting_imrad (40%)
    ↓
generating_notes (55%)
    ↓
storing_vectors (75%) ⭐ 向量嵌入
    ↓
indexing_multimodal (90%) ⭐ 多模态索引
    ↓
completed (100%)
```

## 🎯 关键验证点

### 1. 向量嵌入 (storing_vectors - 75%)

**验证项**:
- ✅ 文本分块完成
- ✅ 2048维向量生成
- ✅ Milvus存储成功

**命令**:
```bash
# 查看文本块
curl http://localhost:4000/api/papers/{paperId}/chunks

# 查询Milvus
curl http://localhost:8000/internal/milvus/stats
```

### 2. 多模态索引 (indexing_multimodal - 90%)

**验证项**:
- ✅ 图片嵌入生成
- ✅ 表格嵌入生成
- ✅ 统一2048维向量空间

**命令**:
```bash
# 查看多模态内容
curl http://localhost:4000/api/papers/{paperId}/multimodal

# 多模态搜索测试
curl -X POST http://localhost:8000/api/search/multimodal \
  -H "Content-Type: application/json" \
  -d '{
    "query": "experimental results",
    "paper_ids": ["{paperId}"]
  }'
```

## 🔧 快速命令

### 查询处理状态
```bash
curl http://localhost:4000/api/papers/{paperId}/status | jq
```

### 获取论文详情
```bash
curl http://localhost:4000/api/papers/{paperId} | jq
```

### 验证向量嵌入
```bash
# 文本向量
curl http://localhost:4000/api/papers/{paperId}/chunks?limit=5 | jq

# 多模态向量
curl http://localhost:4000/api/papers/{paperId}/multimodal | jq
```

### 检查Milvus
```bash
# 集合统计
curl http://localhost:8000/internal/milvus/stats | jq

# 查询向量
curl -X POST http://localhost:8000/internal/milvus/query \
  -H "Content-Type: application/json" \
  -d '{"paper_id": "{paperId}", "limit": 10}' | jq
```

### 运行完整验证
```bash
./tests/e2e/verify-pdf-processing.sh {paperId}
```

## 📊 性能基准

| PDF大小 | OCR | 解析 | 向量 | 多模态 | 总时间 |
|---------|-----|------|------|--------|--------|
| 270KB   | 3s  | 5s   | 5s   | 8s     | 21s    |
| 1MB     | 5s  | 8s   | 8s   | 12s    | 33s    |
| 5MB     | 10s | 15s  | 15s  | 20s    | 60s    |

## 🐛 故障排查

### 问题1: 向量生成失败
```bash
# 检查Qwen3-VL服务
python -c "from app.core.qwen3vl_service import get_qwen3vl_service; print('OK')"

# 检查Milvus连接
curl http://localhost:19530/v1/vector/collections
```

### 问题2: 多模态索引失败
```bash
# 查看错误日志
grep "indexing_multimodal" backend-python/logs/app.log

# 检查图片提取
grep "image_extractor" backend-python/logs/app.log
```

### 问题3: 处理超时
```bash
# 增加超时（测试配置）
testConfig.maxPollAttempts = 200

# 检查系统资源
docker stats
```

## 📚 相关文档

- [PDF处理流程详解](./PDF-PROCESSING-STAGES.md) - 完整文档
- [综合测试指南](./COMPREHENSIVE-TEST-README.md) - 测试说明
- [PDF并行流水线](../../../doc/PDF_PARALLEL_PIPELINE.md) - 架构设计

## ✅ 完整验证清单

使用 `verify-pdf-processing.sh` 脚本自动验证以下内容：

- [ ] OCR文本提取
- [ ] IMRaD结构识别
- [ ] 文本向量嵌入 (2048维)
- [ ] 图片嵌入 (Qwen3-VL)
- [ ] 表格嵌入 (Qwen3-VL)
- [ ] Milvus向量存储
- [ ] 多模态索引完整性
- [ ] 阅读笔记生成
- [ ] 知识图谱构建
- [ ] 最终状态completed

## 🚀 快速开始

```bash
# 1. 运行综合测试
npm run test:comprehensive

# 2. 获取测试论文ID
# 从测试输出中复制paperId

# 3. 验证处理结果
./tests/e2e/verify-pdf-processing.sh {paperId}

# 4. 检查所有阶段
# 查看验证脚本的输出报告
```

---

**打印此卡片作为快速参考！**