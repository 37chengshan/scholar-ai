#!/bin/bash

# 综合集成测试运行脚本
# 用于快速运行完整的E2E测试

set -e

echo "======================================"
echo "ScholarAI 综合集成测试"
echo "======================================"
echo ""

# 检查Node.js环境
if ! command -v node &> /dev/null; then
    echo "✗ Node.js 未安装"
    exit 1
fi

echo "✓ Node.js版本: $(node -v)"

# 检查npm
if ! command -v npm &> /dev/null; then
    echo "✗ npm 未安装"
    exit 1
fi

echo "✓ npm版本: $(npm -v)"

# 检查Jest
if ! npm list jest &> /dev/null; then
    echo "✗ Jest 未安装，正在安装..."
    npm install --save-dev jest ts-jest @types/jest supertest @types/supertest
fi

echo "✓ Jest 已安装"

# 检查测试PDF文件
TEST_PDF_DIR="/Users/cc/scholar-ai-deploy/schlar ai/doc/测试论文"
if [ ! -d "$TEST_PDF_DIR" ]; then
    echo "⚠ 测试PDF目录不存在: $TEST_PDF_DIR"
    echo "  请确保测试PDF文件存在"
fi

echo "✓ 测试PDF目录: $TEST_PDF_DIR"
echo ""

# 检查后端服务
echo "检查后端服务状态..."

# Node.js API Gateway
if curl -s http://localhost:4000/health > /dev/null 2>&1; then
    echo "✓ Node.js API Gateway (Port 4000) - 运行中"
else
    echo "✗ Node.js API Gateway (Port 4000) - 未运行"
    echo "  请先启动: cd backend-node && npm run dev"
    exit 1
fi

# Python AI Service
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "✓ Python AI Service (Port 8000) - 运行中"
else
    echo "✗ Python AI Service (Port 8000) - 未运行"
    echo "  请先启动: cd backend-python && python -m uvicorn app.main:app --reload --port 8000"
    exit 1
fi

echo ""
echo "======================================"
echo "开始运行综合集成测试..."
echo "======================================"
echo ""

# 运行测试
cd backend-node

echo "测试配置:"
echo "  测试账户: integration-test@example.com"
echo "  测试PDF: 2604.01245v1.pdf (270KB), 2604.01226v1.pdf (5.5MB)"
echo "  最大轮询: 120次 (每5秒一次)"
echo "  超时时间: 600秒 (10分钟)"
echo ""

# 运行Jest测试
npm test tests/e2e/comprehensive-integration.e2e.test.ts --verbose --detectOpenHandles --runInBand

echo ""
echo "======================================"
echo "测试完成！"
echo "======================================"
echo ""

# 显示测试结果摘要
echo "测试涵盖的功能模块:"
echo "  ✓ 用户注册与登录（智能检测已存在账户）"
echo "  ✓ PDF上传与解析（实时监控进度）"
echo "  ✓ 文献库管理（列表、详情、删除）"
echo "  ✓ 笔记生成与编辑"
echo "  ✓ Chat对话（阻塞式、流式、多论文）"
echo "  ✓ 外部搜索（arXiv、Semantic Scholar）"
echo ""
echo "查看详细日志: backend-node/logs/test-comprehensive.log"
echo ""