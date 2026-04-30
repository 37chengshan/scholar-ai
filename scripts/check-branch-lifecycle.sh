#!/usr/bin/env bash
set -euo pipefail

policy_file="docs/specs/governance/branch-lifecycle-policy.md"
stale_days="${BRANCH_STALE_DAYS:-14}"
review_ready_days="${BRANCH_REVIEW_READY_DAYS:-7}"

if [[ ! -f "$policy_file" ]]; then
  echo "[branch-lifecycle] missing required file: $policy_file" >&2
  exit 1
fi

allowed_states_regex='^(created|active|review-ready|merged|superseded|archived)$'

fail_count=0

table_rows="$(awk -F'|' '
  /^\|/ {
    if ($0 ~ /^\|---/) next
    if ($0 ~ /branch_name/) next
    branch=$2
    state=$3
    owner=$4
    last=$5
    decision=$6
    replacement=$7
    gsub(/^[[:space:]]+|[[:space:]]+$/, "", branch)
    gsub(/^[[:space:]]+|[[:space:]]+$/, "", state)
    gsub(/^[[:space:]]+|[[:space:]]+$/, "", owner)
    gsub(/^[[:space:]]+|[[:space:]]+$/, "", last)
    gsub(/^[[:space:]]+|[[:space:]]+$/, "", decision)
    gsub(/^[[:space:]]+|[[:space:]]+$/, "", replacement)
    if (branch != "" && state != "") {
      printf "%s|%s|%s|%s|%s|%s\n", branch, state, owner, last, decision, replacement
    }
  }
' "$policy_file")"

if [[ -z "$table_rows" ]]; then
  echo "[branch-lifecycle] no branch registry rows found in $policy_file" >&2
  exit 1
fi

while IFS='|' read -r branch state owner last_activity decision replacement; do
  if [[ ! "$state" =~ $allowed_states_regex ]]; then
    echo "[branch-lifecycle] invalid lifecycle_state for $branch: $state" >&2
    fail_count=$((fail_count + 1))
    continue
  fi

  if [[ -z "$owner" || "$owner" == "-" ]]; then
    echo "[branch-lifecycle] owner is required for $branch" >&2
    fail_count=$((fail_count + 1))
  fi

  if [[ -z "$last_activity" || "$last_activity" == "-" ]]; then
    echo "[branch-lifecycle] last_activity_date is required for $branch" >&2
    fail_count=$((fail_count + 1))
    continue
  fi

  age_days="$(python3 - <<'PY' "$last_activity"
import datetime
import sys

last = sys.argv[1]
try:
    last_date = datetime.date.fromisoformat(last)
except ValueError:
    print("INVALID")
    sys.exit(0)

today = datetime.date.today()
print((today - last_date).days)
PY
)"

  if [[ "$age_days" == "INVALID" ]]; then
    echo "[branch-lifecycle] invalid date format for $branch: $last_activity" >&2
    fail_count=$((fail_count + 1))
    continue
  fi

  if [[ "$state" == "active" && "$age_days" -gt "$stale_days" ]]; then
    echo "[branch-lifecycle] stale active branch: $branch (age=${age_days}d > ${stale_days}d)" >&2
    fail_count=$((fail_count + 1))
  fi

  if [[ "$state" == "review-ready" && "$age_days" -gt "$review_ready_days" && ( -z "$decision" || "$decision" == "-" ) ]]; then
    echo "[branch-lifecycle] review-ready branch missing decision note: $branch" >&2
    fail_count=$((fail_count + 1))
  fi

  if [[ "$state" == "superseded" && ( -z "$replacement" || "$replacement" == "-" ) ]]; then
    echo "[branch-lifecycle] superseded branch must declare replacement_branch: $branch" >&2
    fail_count=$((fail_count + 1))
  fi

done <<<"$table_rows"

if [[ "$fail_count" -gt 0 ]]; then
  echo "[branch-lifecycle] failed with $fail_count issue(s)" >&2
  exit 1
fi

echo "[branch-lifecycle] passed"
