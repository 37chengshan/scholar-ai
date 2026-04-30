#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

echo "=== Phase 3 验收开始 ==="

echo "[1/8] 检查 schemas 目录..."
test -d apps/api/app/schemas
schema_count=$(ls apps/api/app/schemas/*.py 2>/dev/null | wc -l | tr -d ' ')
if [[ "$schema_count" -lt 3 ]]; then
  echo "✗ schemas 文件数不足: $schema_count" >&2
  exit 1
fi
echo "✓ schemas 目录存在，文件数: $schema_count"

echo "[2/8] 检查 repositories 目录..."
test -d apps/api/app/repositories
repo_count=$(ls apps/api/app/repositories/*.py 2>/dev/null | wc -l | tr -d ' ')
if [[ "$repo_count" -lt 2 ]]; then
  echo "✗ repositories 文件数不足: $repo_count" >&2
  exit 1
fi
echo "✓ repositories 目录存在，文件数: $repo_count"

echo "[3/8] 检查已迁移模型文件不再定义 Pydantic BaseModel..."
migrated_model_files=(
  "apps/api/app/models/note.py"
  "apps/api/app/models/session.py"
  "apps/api/app/models/rag.py"
)

for model_file in "${migrated_model_files[@]}"; do
  test -f "$model_file"
  if rg -n "class\s+.*\(.*BaseModel.*\)" "$model_file" -S >/dev/null; then
    echo "✗ 已迁移文件仍定义 BaseModel: $model_file" >&2
    exit 1
  fi
done
echo "✓ 已迁移模型文件已改为 schema shim"

echo "[4/8] 检查 paper_crud.py 无直接 SQL 查询..."
if rg -n "db\.(execute|add|delete|flush|refresh|commit)|\bselect\(|func\.count|text\(" apps/api/app/api/papers/paper_crud.py -S >/dev/null; then
  echo "✗ paper_crud.py 仍存在直接数据库调用" >&2
  exit 1
fi
echo "✓ paper_crud.py 已移除直接数据库调用"

echo "[5/8] 检查 search 入口收口..."
if [[ -f apps/api/app/api/search.py ]]; then
  if ! rg -n "deprecated|DEPRECATED" apps/api/app/api/search.py -S >/dev/null; then
    echo "✗ search.py 仍存在且未标记 deprecated" >&2
    exit 1
  fi
  echo "✓ search.py 存在但已标记 deprecated"
else
  echo "✓ search.py 已删除"
fi

echo "[6/8] 检查 paper_service 存在..."
test -f apps/api/app/services/paper_service.py
echo "✓ paper_service.py 存在"

echo "[7/8] 检查 code-boundary baseline 存在..."
test -f docs/specs/governance/code-boundary-baseline.md
echo "✓ baseline 文件存在"

echo "[8/8] 运行后端关键测试..."
(
  cd apps/api
  if [[ -x "venv_new/bin/python" ]]; then
    venv_new/bin/python -m pytest -q tests/unit/test_services.py --maxfail=1
    venv_new/bin/python -m pytest -q tests/test_unified_search.py --maxfail=1
  else
    python -m pytest -q tests/unit/test_services.py --maxfail=1
    python -m pytest -q tests/test_unified_search.py --maxfail=1
  fi
)
echo "✓ 后端关键测试通过"

echo "=== Phase 3 验收完成 ✓ ==="
