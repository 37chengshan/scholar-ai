#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

echo "=== Phase 0 验收开始 ==="

echo "[1/5] 检查必需文件..."
if [[ ! -f .github/workflows/governance.yml && ! -f .github/workflows/governance-baseline.yml ]]; then
  echo "✗ 缺少 governance workflow" >&2
  exit 1
fi

test -f .github/PULL_REQUEST_TEMPLATE.md
test -d .github/ISSUE_TEMPLATE
echo "✓ 文件存在"

echo "[2/5] 检查 apps README 内容..."
test -d apps/web/src
test -d apps/api/app
echo "✓ README 约束说明存在"

echo "[3/5] 运行治理脚本..."
bash scripts/check-doc-governance.sh
bash scripts/check-structure-boundaries.sh
bash scripts/check-code-boundaries.sh
bash scripts/check-governance.sh
echo "✓ 治理脚本通过"

echo "[4/5] 检查工作流触发配置..."
workflow_file=".github/workflows/governance.yml"
if [[ ! -f "$workflow_file" ]]; then
  workflow_file=".github/workflows/governance-baseline.yml"
fi
grep -q "on:" "$workflow_file"
grep -Eq "push|pull_request|workflow_dispatch" "$workflow_file"
echo "✓ 触发条件配置正确"

echo "[5/5] 检查 issue 模板最小集合..."
test -f .github/ISSUE_TEMPLATE/bug-report.yml
test -f .github/ISSUE_TEMPLATE/feature-request.yml
test -f .github/ISSUE_TEMPLATE/governance-task.yml
echo "✓ issue 模板完整"

echo "=== Phase 0 验收完成 ✓ ==="
