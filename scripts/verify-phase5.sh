#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

echo "=== Phase 5 验收开始 ==="

echo "[1/6] 检查 packages README 承接边界..."
for pkg in types sdk ui config; do
  file="packages/$pkg/README.md"
  test -f "$file"
  grep -Eq "只放|承接边界|Reserved" "$file"
  echo "✓ $file"
done

echo "[2/6] 检查迁移条件清单文档..."
if [[ -f docs/governance/migration-conditions.md ]]; then
  echo "✓ docs/governance/migration-conditions.md 存在"
else
  echo "✗ 缺少 docs/governance/migration-conditions.md" >&2
  exit 1
fi

echo "[3/6] 检查 stabilization 报告模板..."
test -f docs/reports/post-migration-stabilization-checklist.md
echo "✓ stabilization 报告模板存在"

echo "[4/6] 检查 packages 无业务代码..."
code_files=$( (find packages -type f \( -name "*.ts" -o -name "*.tsx" -o -name "*.js" -o -name "*.jsx" -o -name "*.py" \) | grep -v "README" | grep -v ".gitkeep") || true )
code_files=$(echo "$code_files" | sed '/^$/d' | wc -l | tr -d ' ')
if [[ "$code_files" -gt 0 ]]; then
  echo "✗ packages 中存在业务代码文件数: $code_files" >&2
  exit 1
fi
echo "✓ packages 无业务代码"

echo "[5/6] 检查 runtime hygiene..."
bash scripts/check-runtime-hygiene.sh tracked
echo "✓ runtime hygiene 检查通过"

echo "[6/6] 检查迁移 readiness 脚本（可选）..."
if [[ -f scripts/check-migration-readiness.sh ]]; then
  echo "✓ scripts/check-migration-readiness.sh 存在"
else
  echo "ℹ 未检测到 scripts/check-migration-readiness.sh（可选）"
fi

echo "=== Phase 5 验收完成 ✓ ==="
