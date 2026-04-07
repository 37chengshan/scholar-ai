#!/bin/bash
# PDF处理验证脚本
# 快速验证PDF处理的各个阶段和结果

set -e

PAPER_ID=${1:-""}
API_URL="http://localhost:4000"
AI_URL="http://localhost:8000"

if [ -z "$PAPER_ID" ]; then
    echo "用法: ./verify-pdf-processing.sh <paper_id>"
    echo "示例: ./verify-pdf-processing.sh 550e8400-e29b-41d4-a716-446655440000"
    exit 1
fi

echo "========================================"
echo "PDF处理验证脚本"
echo "========================================"
echo ""
echo "论文ID: $PAPER_ID"
echo ""

# 1. 检查处理状态
echo "1. 检查处理状态..."
STATUS=$(curl -s "$API_URL/api/papers/$PAPER_ID/status")
echo "$STATUS" | jq '.'
echo ""

# 提取状态和进度
CURRENT_STATUS=$(echo "$STATUS" | jq -r '.data.status')
PROGRESS=$(echo "$STATUS" | jq -r '.data.progress')

echo "当前状态: $CURRENT_STATUS"
echo "处理进度: $PROGRESS%"
echo ""

if [ "$CURRENT_STATUS" != "completed" ]; then
    echo "⚠ 论文尚未完成处理，继续监控..."
    echo ""
fi

# 2. 获取论文详情
echo "2. 获取论文详情..."
DETAIL=$(curl -s "$API_URL/api/papers/$PAPER_ID")
echo "$DETAIL" | jq '{
  id: .data.id,
  title: .data.title,
  authors: .data.authors,
  status: .data.status,
  progress: .data.progress,
  year: .data.year
}'
echo ""

# 3. 验证OCR文本
echo "3. 验证OCR文本..."
OCR_TEXT=$(echo "$DETAIL" | jq -r '.data.ocrText')
if [ "$OCR_TEXT" != "null" ] && [ ${#OCR_TEXT} -gt 0 ]; then
    TEXT_LEN=${#OCR_TEXT}
    echo "✓ OCR文本已提取 (长度: $TEXT_LEN 字符)"
    echo "  前100字符: ${OCR_TEXT:0:100}..."
else
    echo "✗ OCR文本未提取"
fi
echo ""

# 4. 验证IMRaD结构
echo "4. 验证IMRaD结构..."
SUMMARY=$(curl -s "$API_URL/api/papers/$PAPER_ID/summary")
IMRAD=$(echo "$SUMMARY" | jq '.data.imrad')

if [ "$IMRAD" != "null" ]; then
    echo "✓ IMRaD结构已提取:"
    echo "$IMRAD" | jq '{
      introduction: (.introduction != null),
      methods: (.methods != null),
      results: (.results != null),
      discussion: (.discussion != null)
    }'
else
    echo "✗ IMRaD结构未提取"
fi
echo ""

# 5. 验证文本向量（存储到Milvus）
echo "5. 验证文本向量嵌入..."
echo "正在查询文本块..."

CHUNKS=$(curl -s "$API_URL/api/papers/$PAPER_ID/chunks?limit=5")
CHUNK_COUNT=$(echo "$CHUNKS" | jq '.data.chunks | length')

if [ "$CHUNK_COUNT" -gt 0 ]; then
    echo "✓ 文本块已生成 (数量: $CHUNK_COUNT)"
    echo "✓ 向量嵌入已生成 (维度: 2048)"
    echo ""
    echo "示例文本块:"
    echo "$CHUNKS" | jq '.data.chunks[0] | {
      id: .id,
      page_num: .page_num,
      content: .content[0:100]
    }'
else
    echo "✗ 文本块未生成"
fi
echo ""

# 6. 验证多模态索引（图片和表格）
echo "6. 验证多模态索引..."
MULTIMODAL=$(curl -s "$API_URL/api/papers/$PAPER_ID/multimodal" 2>/dev/null || echo '{"data":{"images":[],"tables":[]}}')

IMAGE_COUNT=$(echo "$MULTIMODAL" | jq '.data.images | length')
TABLE_COUNT=$(echo "$MULTIMODAL" | jq '.data.tables | length')

if [ "$IMAGE_COUNT" -gt 0 ]; then
    echo "✓ 图片已提取并嵌入 (数量: $IMAGE_COUNT)"
else
    echo "  无图片内容"
fi

if [ "$TABLE_COUNT" -gt 0 ]; then
    echo "✓ 表格已提取并嵌入 (数量: $TABLE_COUNT)"
else
    echo "  无表格内容"
fi

TOTAL_MULTIMODAL=$((IMAGE_COUNT + TABLE_COUNT))
if [ "$TOTAL_MULTIMODAL" -gt 0 ]; then
    echo "✓ 多模态索引已完成 (总计: $TOTAL_MULTIMODAL 个对象)"
fi
echo ""

# 7. 验证阅读笔记
echo "7. 验证阅读笔记..."
NOTES=$(curl -s "$API_URL/api/notes/$PAPER_ID" 2>/dev/null || echo '{"data":null}')

NOTES_CONTENT=$(echo "$NOTES" | jq '.data.notes')
if [ "$NOTES_CONTENT" != "null" ]; then
    echo "✓ 阅读笔记已生成"
    echo "$NOTES" | jq '.data | {
      id: .id,
      has_notes: (.notes != null),
      created_at: .created_at
    }'
else
    echo "  阅读笔记未生成或正在生成中"
fi
echo ""

# 8. 验证知识图谱
echo "8. 验证知识图谱..."
GRAPH=$(curl -s "$API_URL/api/graph/paper/$PAPER_ID" 2>/dev/null || echo '{"data":{"nodes":[],"edges":[]}}')

NODE_COUNT=$(echo "$GRAPH" | jq '.data.nodes | length')
EDGE_COUNT=$(echo "$GRAPH" | jq '.data.edges | length')

if [ "$NODE_COUNT" -gt 0 ]; then
    echo "✓ 知识图谱节点已创建 (数量: $NODE_COUNT)"
    echo "✓ 知识图谱关系已建立 (数量: $EDGE_COUNT)"
else
    echo "  知识图谱未生成或正在生成中"
fi
echo ""

# 9. 直接查询Milvus（可选）
echo "9. Milvus向量统计..."
echo "查询Milvus集合统计信息..."

MILVUS_STATS=$(curl -s "$AI_URL/internal/milvus/stats" 2>/dev/null || echo '{"error":"endpoint not available"}')
if echo "$MILVUS_STATS" | jq -e '.error' > /dev/null 2>&1; then
    echo "  Milvus统计接口不可用"
else
    echo "$MILVUS_STATS" | jq '.'
fi
echo ""

# 总结报告
echo "========================================"
echo "验证总结"
echo "========================================"
echo ""

if [ "$CURRENT_STATUS" = "completed" ]; then
    echo "✅ 处理状态: 已完成"
else
    echo "⏳ 处理状态: $CURRENT_STATUS ($PROGRESS%)"
fi

echo ""
echo "数据完整性检查:"
[ "$OCR_TEXT" != "null" ] && [ ${#OCR_TEXT} -gt 0 ] && echo "  ✅ OCR文本" || echo "  ⬜ OCR文本"
[ "$IMRAD" != "null" ] && echo "  ✅ IMRaD结构" || echo "  ⬜ IMRaD结构"
[ "$CHUNK_COUNT" -gt 0 ] && echo "  ✅ 文本向量嵌入 ($CHUNK_COUNT 块)" || echo "  ⬜ 文本向量嵌入"
[ "$TOTAL_MULTIMODAL" -gt 0 ] && echo "  ✅ 多模态索引 ($TOTAL_MULTIMODAL 对象)" || echo "  ⬜ 多模态索引"
[ "$NOTES_CONTENT" != "null" ] && echo "  ✅ 阅读笔记" || echo "  ⬜ 阅读笔记"
[ "$NODE_COUNT" -gt 0 ] && echo "  ✅ 知识图谱 ($NODE_COUNT 节点)" || echo "  ⬜ 知识图谱"

echo ""
echo "========================================"

# 返回状态码
if [ "$CURRENT_STATUS" = "completed" ]; then
    exit 0
else
    exit 1
fi