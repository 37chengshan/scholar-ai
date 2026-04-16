#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

echo "=== Phase 2 验收开始 ==="

echo "[1/7] 检查 useKnowledgeBases 仅一份实现..."
count=$(find apps/web/src -name "useKnowledgeBases.ts" | wc -l | tr -d ' ')
if [[ "$count" -ne 1 ]]; then
  echo "✗ 发现 $count 份 useKnowledgeBases 实现，应为 1" >&2
  exit 1
fi
echo "✓ useKnowledgeBases 仅一份实现"

echo "[2/7] 检查无 app/hooks/useKnowledgeBases 引用..."
refs=$( (rg -n "app/hooks/useKnowledgeBases" apps/web/src -S || true) | wc -l | tr -d ' ')
if [[ "$refs" -ne 0 ]]; then
  echo "✗ 仍存在 $refs 处 app/hooks/useKnowledgeBases 引用" >&2
  exit 1
fi
echo "✓ 无 app/hooks/useKnowledgeBases 引用"

echo "[3/7] 检查无同名 hook 冲突..."
conflicts=$(comm -12 <(ls apps/web/src/hooks 2>/dev/null | sort) <(ls apps/web/src/app/hooks 2>/dev/null | sort) || true)
if [[ -n "$conflicts" ]]; then
  echo "✗ 检测到同名 hook 冲突: $conflicts" >&2
  exit 1
fi
echo "✓ 无同名 hook 冲突"

echo "[4/7] 运行 TypeScript 类型检查..."
(
  cd apps/web
  npm run type-check
)
echo "✓ TypeScript 类型检查通过"

echo "[5/7] 运行前端测试..."
(
  cd apps/web
  npm run test:run
)
echo "✓ 前端测试通过"

echo "[6/7] 检查边界规则文档..."
test -f docs/development/coding-standards.md
grep -q "app/hooks" docs/development/coding-standards.md
echo "✓ 文档已覆盖 app/hooks 边界"

echo "[7/7] 检查 kbApi 返回 DTO 约束..."
if rg -n "return \{ success: true, data:" apps/web/src/services/kbApi.ts -S >/dev/null; then
  echo "✗ kbApi 仍返回 { success, data } 包装" >&2
  exit 1
fi
echo "✓ kbApi 返回纯 DTO"

echo "=== Phase 2 验收完成 ✓ ==="
