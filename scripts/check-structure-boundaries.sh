#!/usr/bin/env bash
set -euo pipefail

required_dirs=(
  "apps"
  "apps/web"
  "apps/api"
  "packages"
  "infra"
  "tools"
  "docs"
  "frontend"
  "backend-python"
  "scripts"
  ".github/workflows"
)

forbidden_root_dirs=(
  "doc"
  "tmp"
  "legacy"
  "_new"
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
    echo "[structure-boundaries] forbidden root directory found: $dir" >&2
    fail_count=$((fail_count + 1))
  fi
done

for file in "${forbidden_root_files[@]}"; do
  if [[ -e "$file" ]]; then
    echo "[structure-boundaries] forbidden root runtime file found: $file" >&2
    fail_count=$((fail_count + 1))
  fi
done

# apps/* are logical mapping only in current phase.
# Block introducing real implementation files in apps/web and apps/api.
allowed_apps_files=(
  "README.md"
)

is_allowed_apps_file() {
  local filename="$1"
  for allowed in "${allowed_apps_files[@]}"; do
    if [[ "$filename" == "$allowed" ]]; then
      return 0
    fi
  done
  return 1
}

check_apps_logical_mapping() {
  local dir="$1"
  if [[ ! -d "$dir" ]]; then
    return
  fi

  while IFS= read -r file; do
    local base
    base="$(basename "$file")"
    if ! is_allowed_apps_file "$base"; then
      echo "[structure-boundaries] apps logical mapping violation: $file" >&2
      fail_count=$((fail_count + 1))
    fi
  done < <(
    find "$dir" -type f \( -name "*.py" -o -name "*.ts" -o -name "*.tsx" -o -name "*.js" -o -name "*.jsx" \) | sort
  )
}

check_apps_logical_mapping "apps/web"
check_apps_logical_mapping "apps/api"

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

if [[ -d "backend-python/app/api" ]]; then
  while IFS= read -r api_dup_dir; do
    echo "[structure-boundaries] forbidden duplicate API directory found: $api_dup_dir" >&2
    fail_count=$((fail_count + 1))
  done < <(find backend-python/app/api -type d -name "*_new" | sort)
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