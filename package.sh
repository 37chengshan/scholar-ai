#!/bin/bash
# ScholarAI 项目打包脚本
# 排除虚拟环境、依赖、模型文件、测试覆盖率等

set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
PACKAGE_NAME="scholar-ai-$(date +%Y%m%d-%H%M%S)"
OUTPUT_DIR="${PROJECT_DIR}/../packages"

mkdir -p "$OUTPUT_DIR"

echo "=== ScholarAI 项目打包 ==="
echo "项目目录: $PROJECT_DIR"
echo "输出文件: $OUTPUT_DIR/${PACKAGE_NAME}.tar.gz"

echo ""
echo "排除目录大小统计:"
echo "- Qwen 模型: $(du -sh "$PROJECT_DIR/../Qwen" 2>/dev/null | cut -f1 || echo 'N/A')"
echo "- apps/api/venv: $(du -sh "$PROJECT_DIR/apps/api/venv" 2>/dev/null | cut -f1 || echo 'N/A')"
echo "- apps/api/venv_new: $(du -sh "$PROJECT_DIR/apps/api/venv_new" 2>/dev/null | cut -f1 || echo 'N/A')"
echo "- apps/web/node_modules: $(du -sh "$PROJECT_DIR/apps/web/node_modules" 2>/dev/null | cut -f1 || echo 'N/A')"
echo "- uploads: $(du -sh "$PROJECT_DIR/../uploads" 2>/dev/null | cut -f1 || echo 'N/A')"
echo "- .git: $(du -sh "$PROJECT_DIR/.git" 2>/dev/null | cut -f1)"
echo "- 覆盖率报告: $(du -sh "$PROJECT_DIR/apps/api/htmlcov" 2>/dev/null | cut -f1 || echo 'N/A')"
echo ""

cd "$PROJECT_DIR"

tar -czf "$OUTPUT_DIR/${PACKAGE_NAME}.tar.gz" \
    --exclude='.git' \
    --exclude='.github' \
    --exclude='.planning' \
    --exclude='.DS_Store' \
    --exclude='*.log' \
    --exclude='*.pid' \
    --exclude='*.pyc' \
    --exclude='__pycache__' \
    --exclude='.pytest_cache' \
    --exclude='.ruff_cache' \
    --exclude='.coverage' \
    --exclude='coverage-report.txt' \
    --exclude='htmlcov' \
    --exclude='htmlcov_*' \
    --exclude='node_modules' \
    --exclude='venv' \
    --exclude='venv_new' \
    --exclude='.venv' \
    --exclude='env' \
    --exclude='.env' \
    --exclude='test-results' \
    --exclude='test-papers' \
    --exclude='uploads' \
    --exclude='apps/api/venv' \
    --exclude='apps/api/venv_new' \
    --exclude='apps/api/__pycache__' \
    --exclude='apps/api/.pytest_cache' \
    --exclude='apps/api/.coverage' \
    --exclude='apps/api/coverage-report.txt' \
    --exclude='apps/api/htmlcov' \
    --exclude='apps/api/htmlcov_*' \
    --exclude='apps/api/*.log' \
    --exclude='apps/api/tests/integration/workflow_fixtures' \
    --exclude='apps/web/node_modules' \
    --exclude='apps/web/dist' \
    --exclude='apps/web/.vite' \
    --exclude='apps/web/coverage' \
    --exclude='nginx/ssl' \
    --exclude='cookies.txt' \
    --exclude='package.sh' \
    .

echo ""
echo "=== 打包完成 ==="
echo "文件: $OUTPUT_DIR/${PACKAGE_NAME}.tar.gz"
echo "大小: $(du -sh "$OUTPUT_DIR/${PACKAGE_NAME}.tar.gz" | cut -f1)"

echo ""
echo "包含的主要文件/目录:"
tar -tzf "$OUTPUT_DIR/${PACKAGE_NAME}.tar.gz" | head -30

echo ""
echo "文件统计:"
TOTAL_FILES=$(tar -tzf "$OUTPUT_DIR/${PACKAGE_NAME}.tar.gz" | wc -l | tr -d ' ')
echo "总文件数: $TOTAL_FILES"

echo ""
echo "验证排除:"
EXCLUDED=$(tar -tzf "$OUTPUT_DIR/${PACKAGE_NAME}.tar.gz" | grep -E "venv|node_modules|htmlcov|\.coverage|\.pyc" | wc -l | tr -d ' ')
if [ "$EXCLUDED" -eq 0 ]; then
    echo "✓ 已排除所有虚拟环境、依赖和覆盖率文件"
else
    echo "⚠ 还有 $EXCLUDED 个文件应该被排除"
fi

echo ""
echo "建议部署步骤:"
echo "1. 解压: tar -xzf ${PACKAGE_NAME}.tar.gz"
echo "2. 安装前端依赖: cd apps/web && npm install"
echo "3. 安装后端依赖: cd apps/api && pip install -r requirements.txt"
echo "4. 配置环境变量: cp .env.example .env 并编辑"
