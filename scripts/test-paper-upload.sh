#!/bin/bash
# 论文上传和解析测试脚本

set -e

BASE_URL="http://localhost:8000"
UPLOAD_DIR="scholar-ai/uploads"
PDF_DIR="doc/测试论文"

echo "=========================================="
echo "  ScholarAI 论文上传和解析测试"
echo "=========================================="
echo ""

# 1. 登录获取 Cookie
echo "🔐 登录..."
LOGIN_RESPONSE=$(curl -s -c cookies.txt -X POST "$BASE_URL/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"Test123456"}')

if echo "$LOGIN_RESPONSE" | grep -q '"success":true'; then
  echo "✅ 登录成功"
else
  echo "❌ 登录失败"
  echo "$LOGIN_RESPONSE"
  exit 1
fi

echo ""

# 2. 获取第一个 PDF 文件
PDF_DIR="../doc/测试论文"
PDF_FILE=$(ls "$PDF_DIR"/*.pdf 2>/dev/null | head -1)
PDF_NAME=$(basename "$PDF_FILE")
echo "📄 使用测试论文: $PDF_NAME"
echo ""

# 3. 创建论文记录
echo "📤 创建论文记录..."
CREATE_RESPONSE=$(curl -s -b cookies.txt -X POST "$BASE_URL/api/papers" \
  -H "Content-Type: application/json" \
  -d "{\"filename\":\"$PDF_NAME\"}")

PAPER_ID=$(echo "$CREATE_RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin).get('data',{}).get('paperId',''))" 2>/dev/null)
STORAGE_KEY=$(echo "$CREATE_RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin).get('data',{}).get('storageKey',''))" 2>/dev/null)

if [ -z "$PAPER_ID" ]; then
  echo "❌ 创建论文记录失败"
  echo "$CREATE_RESPONSE"
  exit 1
fi

echo "✅ 论文记录创建成功"
echo "   Paper ID: $PAPER_ID"
echo "   Storage Key: $STORAGE_KEY"
echo ""

# 4. 上传 PDF 文件
echo "📤 上传 PDF 文件..."
mkdir -p "$UPLOAD_DIR"
cp "$PDF_FILE" "$UPLOAD_DIR/$STORAGE_KEY"

if [ -f "$UPLOAD_DIR/$STORAGE_KEY" ]; then
  FILE_SIZE=$(ls -lh "$UPLOAD_DIR/$STORAGE_KEY" | awk '{print $5}')
  echo "✅ 文件上传成功 (大小: $FILE_SIZE)"
else
  echo "❌ 文件上传失败"
  exit 1
fi
echo ""

# 5. 调用 Webhook 触发解析
echo "🔄 触发论文解析..."
WEBHOOK_RESPONSE=$(curl -s -b cookies.txt -X POST "$BASE_URL/api/papers/webhook" \
  -H "Content-Type: application/json" \
  -d "{\"paperId\":\"$PAPER_ID\",\"storageKey\":\"$STORAGE_KEY\"}")

if echo "$WEBHOOK_RESPONSE" | grep -q '"success":true'; then
  echo "✅ 解析任务已触发"
else
  echo "⚠️  Webhook 响应:"
  echo "$WEBHOOK_RESPONSE"
fi
echo ""

# 6. 检查论文状态
echo "📊 检查论文状态..."
sleep 2
STATUS_RESPONSE=$(curl -s -b cookies.txt "$BASE_URL/api/papers/$PAPER_ID")
echo "$STATUS_RESPONSE" | python3 -m json.tool 2>/dev/null | head -20

echo ""
echo "=========================================="
echo "  测试完成"
echo "=========================================="
echo ""
echo "💡 提示:"
echo "  - 论文 ID: $PAPER_ID"
echo "  - 查看解析进度: curl -b cookies.txt $BASE_URL/api/papers/$PAPER_ID"
echo "  - 启动 Celery Worker 进行异步解析"
echo ""

# 清理
rm -f cookies.txt