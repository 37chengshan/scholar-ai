#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

echo "=== Phase 1 验收开始 ==="

echo "[1/5] 检查 README 主路径说明..."
grep -Eq "apps/web|apps/api|真实代码主路径" README.md
echo "✓ README 包含主路径说明"

echo "[2/5] 检查 AGENTS scope mapping..."
grep -q "apps/web" AGENTS.md
grep -q "apps/api" AGENTS.md
grep -q "前端真实代码主路径" AGENTS.md
grep -q "后端真实代码主路径" AGENTS.md
echo "✓ AGENTS scope mapping 存在"

echo "[3/5] 检查 apps README 约束..."
test -d apps/web/src
test -d apps/api/app
echo "✓ apps 真实代码路径存在"

echo "[4/5] 检查 structure 脚本包含 apps 限制逻辑..."
grep -q "legacy root implementation path forbidden" scripts/check-structure-boundaries.sh
grep -q "apps/web" scripts/check-structure-boundaries.sh
grep -q "apps/api" scripts/check-structure-boundaries.sh
echo "✓ structure 脚本包含物理主路径限制"

echo "[5/5] 运行治理总脚本..."
bash scripts/check-governance.sh
echo "✓ 治理总脚本通过"

echo "=== Phase 1 验收完成 ✓ ==="
