#!/usr/bin/env bash
set -euo pipefail

base_ref=""
head_ref="HEAD"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --base)
      base_ref="$2"
      shift 2
      ;;
    --head)
      head_ref="$2"
      shift 2
      ;;
    *)
      echo "[contract-gate] unknown argument: $1" >&2
      exit 2
      ;;
  esac
done

get_changed_files() {
  if [[ -n "$base_ref" ]] && git cat-file -e "$base_ref^{commit}" 2>/dev/null; then
    git diff --name-only "$base_ref"..."$head_ref"
    return
  fi

  if ! git diff --quiet HEAD --; then
    git diff --name-only HEAD --
    return
  fi

  if git rev-parse --verify HEAD~1 >/dev/null 2>&1; then
    git diff --name-only HEAD~1..HEAD
    return
  fi

  git diff --name-only
}

changed_files="$(get_changed_files)"
if [[ -z "$changed_files" ]]; then
  echo "[contract-gate] no changed files detected; skip"
  exit 0
fi

contract_surface_regex='^(apps/api/app/api/|apps/api/app/models/|apps/api/app/services/|apps/web/src/services/|packages/types/|packages/sdk/|docs/architecture/api-contract.md|docs/domain/resources.md)'

contract_surface_changed="false"
if grep -E "$contract_surface_regex" <<<"$changed_files" >/dev/null; then
  contract_surface_changed="true"
fi

if [[ "$contract_surface_changed" == "true" ]]; then
  required_docs=("docs/architecture/api-contract.md" "docs/domain/resources.md")
  for doc in "${required_docs[@]}"; do
    if ! grep -Fxq "$doc" <<<"$changed_files"; then
      echo "[contract-gate] contract surface changed but missing synced doc update: $doc" >&2
      exit 1
    fi
  done
fi

# Ban known legacy retrieval field aliases in changed contract-surface code files.
legacy_alias_fail=0
while IFS= read -r file; do
  [[ -f "$file" ]] || continue
  case "$file" in
    apps/api/tests/*|apps/web/e2e/*|docs/*|*.md|*.yml|*.yaml)
      continue
      ;;
  esac

  if grep -nE '\b(content_data|similarity)\b' "$file" >/dev/null; then
    echo "[contract-gate] detected legacy contract alias in $file" >&2
    grep -nE '\b(content_data|similarity)\b' "$file" >&2
    legacy_alias_fail=1
  fi
done < <(grep -E "$contract_surface_regex" <<<"$changed_files" || true)

if [[ "$legacy_alias_fail" -ne 0 ]]; then
  echo "[contract-gate] failed due to legacy contract alias usage" >&2
  exit 1
fi

echo "[contract-gate] passed"
