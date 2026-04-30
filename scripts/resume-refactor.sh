#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

echo "=== 迁移后稳定期恢复 ==="

for phase in 0 1 2 3 4 5; do
  script="scripts/verify-phase${phase}.sh"
  if [[ ! -f "$script" ]]; then
    echo "⚠ 缺少 $script，无法自动恢复到该阶段"
    continue
  fi

  echo "验证 Phase $phase ..."
  if bash "$script"; then
    echo "✓ Phase $phase 已完成"
  else
    echo "✗ Phase $phase 未完成或验收失败"
    echo "请从 docs/plans/v2_0/reports/release/post-migration-stabilization-checklist.md 对应阶段继续执行。"
    exit 0
  fi
done

echo "✓ 所有阶段均已通过，可直接执行 scripts/verify-all-phases.sh 复核。"
