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
if [[ -f docs/specs/governance/migration-conditions.md ]]; then
  echo "✓ docs/specs/governance/migration-conditions.md 存在"
else
  echo "✗ 缺少 docs/specs/governance/migration-conditions.md" >&2
  exit 1
fi

echo "[3/6] 检查 stabilization 报告模板..."
test -f docs/plans/v2_0/reports/release/post-migration-stabilization-checklist.md
echo "✓ stabilization 报告模板存在"

echo "[4/6] 检查共享包落地状态..."

types_code_files=$( (find packages/types/src -type f \( -name "*.ts" -o -name "*.tsx" \) 2>/dev/null) || true )
types_code_count=$(echo "$types_code_files" | sed '/^$/d' | wc -l | tr -d ' ')
if [[ "$types_code_count" -eq 0 ]]; then
  echo "✗ packages/types 尚未落地共享契约代码" >&2
  exit 1
fi

sdk_code_files=$( (find packages/sdk/src -type f \( -name "*.ts" -o -name "*.tsx" \) 2>/dev/null) || true )
sdk_code_count=$(echo "$sdk_code_files" | sed '/^$/d' | wc -l | tr -d ' ')
if [[ "$sdk_code_count" -eq 0 ]]; then
  echo "✗ packages/sdk 尚未落地 typed client 代码" >&2
  exit 1
fi

ui_code_files=$( (find packages/ui -type f \( -name "*.ts" -o -name "*.tsx" -o -name "*.js" -o -name "*.jsx" -o -name "*.py" \) | grep -v "README" | grep -v ".gitkeep") || true )
ui_code_count=$(echo "$ui_code_files" | sed '/^$/d' | wc -l | tr -d ' ')
if [[ "$ui_code_count" -gt 0 ]]; then
  echo "✗ packages/ui 仍应保持占位，不应落地业务代码（检测到 $ui_code_count 个文件）" >&2
  exit 1
fi

config_code_files=$( (find packages/config -type f \( -name "*.ts" -o -name "*.tsx" -o -name "*.js" -o -name "*.jsx" -o -name "*.py" \) | grep -v "README" | grep -v ".gitkeep") || true )
config_code_count=$(echo "$config_code_files" | sed '/^$/d' | wc -l | tr -d ' ')
if [[ "$config_code_count" -gt 0 ]]; then
  echo "✗ packages/config 仍应保持占位，不应落地业务代码（检测到 $config_code_count 个文件）" >&2
  exit 1
fi

echo "✓ packages/types 与 packages/sdk 已落地，ui/config 仍保持占位"

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
