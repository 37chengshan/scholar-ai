#!/usr/bin/env bash
set -euo pipefail

required_dirs=(
  "apps"
  "apps/web"
  "apps/web/src"
  "apps/api"
  "apps/api/app"
  "packages"
  "infra"
  "tools"
  "docs"
  "scripts"
  ".github/workflows"
)

forbidden_root_dirs=(
  "doc"
  "tmp"
  "legacy"
  "_new"
  "frontend"
  "backend-python"
  "scholar-ai"
)

forbidden_root_files=(
  "backend.pid"
  "frontend.pid"
  "cookies.txt"
)

fail_count=0

for path in "${required_dirs[@]}"; do
  if [[ ! -d "$path" ]]; then
    echo "[structure-boundaries] missing required directory: $path" >&2
    fail_count=$((fail_count + 1))
  fi
done

for dir in "${forbidden_root_dirs[@]}"; do
  if [[ -d "$dir" ]]; then
    echo "[structure-boundaries] legacy root implementation path forbidden: $dir" >&2
    fail_count=$((fail_count + 1))
  fi
done

for file in "${forbidden_root_files[@]}"; do
  if [[ -e "$file" ]]; then
    echo "[structure-boundaries] forbidden root runtime file found: $file" >&2
    fail_count=$((fail_count + 1))
  fi
done

forbidden_local_paths=(
  "apps/web/.github"
  "apps/web/packages"
)

for path in "${forbidden_local_paths[@]}"; do
  if [[ -e "$path" ]]; then
    echo "[structure-boundaries] forbidden nested/runtime path found: $path" >&2
    fail_count=$((fail_count + 1))
  fi
done

shopt -s nullglob
root_pid=(./*.pid)
root_log=(./*.log)
root_out=(./*.out)
shopt -u nullglob

if (( ${#root_pid[@]} > 0 )); then
  echo "[structure-boundaries] forbidden root pid files found" >&2
  fail_count=$((fail_count + 1))
fi

if (( ${#root_log[@]} > 0 )); then
  echo "[structure-boundaries] forbidden root log files found" >&2
  fail_count=$((fail_count + 1))
fi

if (( ${#root_out[@]} > 0 )); then
  echo "[structure-boundaries] forbidden root out files found" >&2
  fail_count=$((fail_count + 1))
fi

while IFS= read -r nested_workflow; do
  echo "[structure-boundaries] workflow must live under .github/workflows: $nested_workflow" >&2
  fail_count=$((fail_count + 1))
done < <(
  find . \
    -path "./.git" -prune -o \
    -path "./.claude" -prune -o \
    -path "*/node_modules" -prune -o \
    -type f \( -path "*/.github/workflows/*.yml" -o -path "*/.github/workflows/*.yaml" \) ! -path "./.github/workflows/*" -print | sort
)

if [[ "$fail_count" -gt 0 ]]; then
  echo "[structure-boundaries] failed with $fail_count issue(s)" >&2
  exit 1
fi

echo "[structure-boundaries] passed"