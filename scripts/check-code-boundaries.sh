#!/usr/bin/env bash
set -euo pipefail

baseline_file="docs/specs/governance/code-boundary-baseline.md"
fail_count=0

if [[ ! -f "$baseline_file" ]]; then
  echo "[code-boundaries] missing baseline file: $baseline_file" >&2
  exit 1
fi

# Frontend rule: pages/components should not directly call API clients.
frontend_pattern='\bfetch\s*\(|apiClient\.|axios\.|new\s+EventSource\s*\('
frontend_targets=(
  "apps/web/src/app/pages"
  "apps/web/src/app/components"
)

for target in "${frontend_targets[@]}"; do
  if [[ -d "$target" ]]; then
    while IFS= read -r line; do
      echo "[code-boundaries] frontend direct API usage forbidden: $line" >&2
      fail_count=$((fail_count + 1))
    done < <(rg -n "$frontend_pattern" "$target" -S || true)
  fi
done

# Frontend rule: avoid duplicate hook implementations across app/hooks and hooks.
shared_hooks_dir="apps/web/src/hooks"
app_hooks_dir="apps/web/src/app/hooks"
if [[ -d "$shared_hooks_dir" && -d "$app_hooks_dir" ]]; then
  while IFS= read -r shared_hook; do
    [[ -z "$shared_hook" ]] && continue
    hook_name="$(basename "$shared_hook")"
    if [[ -f "$app_hooks_dir/$hook_name" ]]; then
      echo "[code-boundaries] duplicate hook implementation detected: $hook_name" >&2
      fail_count=$((fail_count + 1))
    fi
  done < <(find "$shared_hooks_dir" -type f -name "*.ts" | sort)
fi

# Backend rule: prevent new API-layer direct DB operations.
backend_pattern='await db\.(execute|add|add_all|delete|flush|refresh|commit|scalar|scalars|get|merge)|\bdb\.(execute|add|add_all|delete|flush|refresh|commit|scalar|scalars|get|merge)\('

backend_db_files=()
while IFS= read -r file; do
  [[ -n "$file" ]] && backend_db_files+=("$file")
done < <(rg -n "$backend_pattern" apps/api/app/api -S | cut -d: -f1 | sort -u)

allowed_backend_files=()
while IFS= read -r file; do
  [[ -n "$file" ]] && allowed_backend_files+=("$file")
done < <(rg -n "^- apps/api/app/api/" "$baseline_file" -S | sed 's/^[0-9]*:- //' | sort -u)

for file in "${backend_db_files[@]}"; do
  if [[ -z "$file" ]]; then
    continue
  fi

  allowed=false
  for allowed_file in "${allowed_backend_files[@]}"; do
    if [[ "$file" == "$allowed_file" ]]; then
      allowed=true
      break
    fi
  done

  if [[ "$allowed" == false ]]; then
    echo "[code-boundaries] backend API direct DB access not in baseline: $file" >&2
    fail_count=$((fail_count + 1))
  fi
done

for allowed_file in "${allowed_backend_files[@]}"; do
  present=false
  for file in "${backend_db_files[@]}"; do
    if [[ "$file" == "$allowed_file" ]]; then
      present=true
      break
    fi
  done

  if [[ "$present" == false ]]; then
    echo "[code-boundaries] cleanup candidate: remove from baseline -> $allowed_file"
  fi
done

if [[ "$fail_count" -gt 0 ]]; then
  echo "[code-boundaries] failed with $fail_count issue(s)" >&2
  exit 1
fi

echo "[code-boundaries] passed"
