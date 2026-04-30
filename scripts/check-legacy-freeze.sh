#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd -- "$script_dir/.." && pwd)"
cd "$repo_root"

legacy_files=(
  "apps/web/src/features/chat/components/ChatLegacy.tsx"
  "apps/web/src/features/kb/components/KnowledgeBaseDetailLegacy.tsx"
)
strict_closeout_docs=(
  "docs/plans/v3_0/active/overview/2026-04-29_v3_0_closeout_checklist.md"
  "docs/plans/PLAN_STATUS.md"
  "docs/specs/governance/phase-delivery-ledger.md"
)

base_ref="${GITHUB_BASE_REF:-main}"
if git rev-parse --verify "origin/${base_ref}" >/dev/null 2>&1; then
  merge_base="$(git merge-base HEAD "origin/${base_ref}")"
else
  merge_base="$(git rev-list --max-parents=0 HEAD | tail -n 1)"
fi

changed_files="$(
  {
    git diff --name-only "${merge_base}"...HEAD
    git diff --name-only
    git diff --name-only --cached
    git ls-files --others --exclude-standard
  } | awk 'NF' | sort -u
)"

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

if ! grep -Eq '^docs/plans/.*\.md$|^docs/plans/archive/reports/.*计划A.*\.md$' <<<"$changed_files"; then
  echo "[legacy-freeze] failed: legacy components changed but no migration planning document was updated" >&2
  echo "[legacy-freeze] requirement: update docs/plans/*.md or docs/plans/archive/reports/*计划A*.md in the same PR" >&2
  exit 1
fi

commit_messages="$(git log --format=%B "${merge_base}"..HEAD)"
if grep -Eqi 'Migration-Task:' <<<"$commit_messages"; then
  echo "[legacy-freeze] passed"
  exit 0
fi

missing_closeout_docs=()
for doc in "${strict_closeout_docs[@]}"; do
  if ! grep -Fxq "$doc" <<<"$changed_files"; then
    missing_closeout_docs+=("$doc")
  fi
done

if [[ "${#missing_closeout_docs[@]}" -gt 0 ]]; then
  echo "[legacy-freeze] failed: legacy components changed but no Migration-Task marker or strict close-out doc trail was found" >&2
  echo "[legacy-freeze] requirement: include 'Migration-Task: <task-id-or-link>' in a commit message, or update all strict close-out source docs:" >&2
  printf '  - %s\n' "${strict_closeout_docs[@]}" >&2
  exit 1
fi

echo "[legacy-freeze] passed via strict close-out doc trail"
