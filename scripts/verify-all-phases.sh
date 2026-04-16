#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

echo "========================================"
echo "  ScholarAI 结构整改整体验收"
echo "========================================"

echo "【1/4】仓库治理验收..."
bash scripts/verify-phase0.sh
bash scripts/verify-phase1.sh

echo "【2/4】前端验收..."
bash scripts/verify-phase2.sh

echo "【3/4】后端验收..."
bash scripts/verify-phase3.sh

echo "【4/4】契约与迁移准备验收..."
bash scripts/verify-phase4.sh
bash scripts/verify-phase5.sh

echo "========================================"
echo "  ✓ 整改完成！所有验收通过"
echo "========================================"
