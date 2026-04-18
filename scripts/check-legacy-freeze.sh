#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd -- "$script_dir/.." && pwd)"
cd "$repo_root"

legacy_files=(
  "apps/web/src/features/chat/components/ChatLegacy.tsx"
  "apps/web/src/features/kb/components/KnowledgeBaseDetailLegacy.tsx"
)

base_ref="${GITHUB_BASE_REF:-main}"
if git rev-parse --verify "origin/${base_ref}" >/dev/null 2>&1; then
  merge_base="$(git merge-base HEAD "origin/${base_ref}")"
else
  merge_base="$(git rev-list --max-parents=0 HEAD | tail -n 1)"
fi

changed_files="$(git diff --name-only "${merge_base}"...HEAD)"

legacy_touched=0
for legacy_file in "${legacy_files[@]}"; do
  if grep -Fxq "$legacy_file" <<<"$changed_files"; then
    legacy_touched=1
    break
  fi
done

if [[ "$legacy_touched" -eq 0 ]]; then
  echo "[legacy-freeze] passed (no legacy component changed)"
  exit 0
fi

if ! grep -Eq '^docs/plans/.*\.md$|^docs/reports/.*计划A.*\.md$' <<<"$changed_files"; then
  echo "[legacy-freeze] failed: legacy components changed but no migration planning document was updated" >&2
  echo "[legacy-freeze] requirement: update docs/plans/*.md or docs/reports/*计划A*.md in the same PR" >&2
  exit 1
fi

if ! git log --format=%B "${merge_base}"..HEAD | grep -Eqi 'Migration-Task:'; then
  echo "[legacy-freeze] failed: legacy components changed but commit messages lack 'Migration-Task:' marker" >&2
  echo "[legacy-freeze] requirement: include 'Migration-Task: <task-id-or-link>' in at least one commit message" >&2
  exit 1
fi

echo "[legacy-freeze] passed"
