#!/usr/bin/env bash
set -euo pipefail

MODE="${1:-tracked}"
if [[ "$MODE" != "strict" && "$MODE" != "tracked" ]]; then
  echo "usage: bash scripts/check-runtime-hygiene.sh [strict|tracked]" >&2
  exit 2
fi

fail_count=0

tracked_forbidden_prefixes=(
  "logs/archive"
  "test-results"
  "playwright-report"
  "uploads"
  "apps/web/test-results"
  "apps/web/*.log"
  "apps/web/.github"
  "apps/web/packages"
  "apps/api/venv"
  "apps/api/venv_new"
  "apps/api/htmlcov"
  "apps/api/htmlcov_reranker"
  "scholar-ai"
)

for prefix in "${tracked_forbidden_prefixes[@]}"; do
  if git ls-files -- "$prefix" | grep -q .; then
    echo "[runtime-hygiene] tracked runtime artifact forbidden: $prefix" >&2
    fail_count=$((fail_count + 1))
  fi
done

while IFS= read -r tracked_pycache; do
  [[ -z "$tracked_pycache" ]] && continue
  echo "[runtime-hygiene] tracked __pycache__ forbidden: $tracked_pycache" >&2
  fail_count=$((fail_count + 1))
done < <(git ls-files "apps/api/**/__pycache__/**" 2>/dev/null || true)

if [[ "$MODE" == "strict" ]]; then
  existing_forbidden_paths=(
    "logs/archive"
    "test-results"
    "playwright-report"
    "uploads"
    "apps/web/test-results"
    "apps/web/.github"
    "apps/web/packages"
    "apps/api/venv"
    "apps/api/venv_new"
    "apps/api/htmlcov"
    "apps/api/htmlcov_reranker"
    "scholar-ai"
  )

  for path in "${existing_forbidden_paths[@]}"; do
    if [[ -e "$path" ]]; then
      echo "[runtime-hygiene] local runtime artifact forbidden: $path" >&2
      fail_count=$((fail_count + 1))
    fi
  done

  while IFS= read -r local_log; do
    [[ -z "$local_log" ]] && continue
    echo "[runtime-hygiene] local log file forbidden: $local_log" >&2
    fail_count=$((fail_count + 1))
  done < <(find apps/web -maxdepth 1 -type f -name "*.log" 2>/dev/null | sort || true)

  while IFS= read -r pycache_dir; do
    [[ -z "$pycache_dir" ]] && continue
    echo "[runtime-hygiene] local __pycache__ forbidden: $pycache_dir" >&2
    fail_count=$((fail_count + 1))
  done < <(
    find apps/api \
      \( -type d -name "venv" -o -type d -name "venv_new" \) -prune -o \
      -type d -name "__pycache__" -print 2>/dev/null | sort || true
  )

  while IFS= read -r htmlcov_dir; do
    [[ -z "$htmlcov_dir" ]] && continue
    echo "[runtime-hygiene] local coverage directory forbidden: $htmlcov_dir" >&2
    fail_count=$((fail_count + 1))
  done < <(find apps/api -maxdepth 1 -type d -name "htmlcov*" 2>/dev/null | sort || true)
fi

if [[ "$fail_count" -gt 0 ]]; then
  echo "[runtime-hygiene] failed with $fail_count issue(s)" >&2
  exit 1
fi

echo "[runtime-hygiene] passed ($MODE mode)"