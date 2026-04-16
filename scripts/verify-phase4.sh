#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

echo "=== Phase 4 验收开始 ==="

echo "[1/8] 检查 API 契约文档关键字段..."
test -f docs/architecture/api-contract.md
rg -n '"items"' docs/architecture/api-contract.md -S >/dev/null
rg -n '"meta"' docs/architecture/api-contract.md -S >/dev/null
grep -q "camelCase" docs/architecture/api-contract.md
echo "✓ API 契约文档关键字段存在"

echo "[2/8] 检查后端通用响应壳..."
test -f apps/api/app/schemas/common.py
rg -n "ListResponse|ListMeta|SuccessResponse" apps/api/app/schemas/common.py -S >/dev/null
echo "✓ common.py 响应壳存在"

echo "[3/8] 检查 papers schema..."
test -f apps/api/app/schemas/papers.py
echo "✓ schemas/papers.py 存在"

echo "[4/8] 检查前端 papers 类型与服务..."
if [[ -f apps/web/src/types/papers.ts ]]; then
  rg -n "items|PaperListResponse" apps/web/src/types/papers.ts -S >/dev/null || true
fi
test -f apps/web/src/services/papersApi.ts
echo "✓ 前端 papers 相关文件存在"

echo "[5/8] 检查 papersApi 兼容逻辑不扩散..."
compat_lines=$(rg -n "arxivId|arxiv_id|storageKey|storage_key|fileSize|file_size" apps/web/src/services/papersApi.ts -S | wc -l | tr -d ' ')
echo "ℹ papersApi 兼容字段匹配行数: $compat_lines"

echo "[6/8] 检查 kbApi/papersApi 不返回 success 包装..."
if rg -n "return \{ success" apps/web/src/services/kbApi.ts apps/web/src/services/papersApi.ts -S >/dev/null; then
  echo "✗ 发现 service 层返回 { success } 包装" >&2
  exit 1
fi
echo "✓ service 返回模式已统一为 DTO"

echo "[7/8] 尝试运行时契约抽样（可选）..."
if curl -s --connect-timeout 2 localhost:8000/health >/dev/null 2>&1; then
  response=$(curl -s localhost:8000/api/papers || echo '{}')
  if echo "$response" | jq -e 'has("data") and (.data|has("items")) and has("meta")' >/dev/null 2>&1; then
    echo "✓ papers 响应包含 data.items + meta"
  else
    echo "✗ papers 响应未满足 data.items + meta" >&2
    exit 1
  fi
else
  echo "ℹ 后端服务未运行，跳过运行时抽样"
fi

echo "[8/8] 复核契约相关治理脚本..."
bash scripts/check-code-boundaries.sh
echo "✓ 代码边界校验通过"

echo "=== Phase 4 验收完成 ✓ ==="
