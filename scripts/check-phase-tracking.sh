#!/usr/bin/env bash
set -euo pipefail

plan_status_file="docs/plans/PLAN_STATUS.md"
ledger_file="docs/governance/phase-delivery-ledger.md"
pr_template_file=".github/pull_request_template.md"

required_plan_columns=(
  "phase_unit_id"
  "deliverable_unit_id"
  "pr_link"
  "coverage_scope"
  "risk_level"
)

required_pr_markers=(
  "## 交付单元追踪"
  "Phase ID"
  "Deliverable Unit"
  "Migration-Task"
  "未覆盖项"
)

fail_count=0

for file in "$plan_status_file" "$ledger_file" "$pr_template_file"; do
  if [[ ! -f "$file" ]]; then
    echo "[phase-tracking] missing required file: $file" >&2
    exit 1
  fi
done

for column in "${required_plan_columns[@]}"; do
  if ! grep -Fq "$column" "$plan_status_file"; then
    echo "[phase-tracking] PLAN_STATUS missing column: $column" >&2
    fail_count=$((fail_count + 1))
  fi
done

for marker in "${required_pr_markers[@]}"; do
  if ! grep -Fq "$marker" "$pr_template_file"; then
    echo "[phase-tracking] PR template missing required marker: $marker" >&2
    fail_count=$((fail_count + 1))
  fi
done

ledger_rows="$(awk -F'|' '
  /^\|/ {
    if ($0 ~ /^\|---/) next
    if ($0 ~ /deliverable_unit_id/) next
    id=$2
    phase=$3
    status=$8
    gsub(/^[[:space:]]+|[[:space:]]+$/, "", id)
    gsub(/^[[:space:]]+|[[:space:]]+$/, "", phase)
    gsub(/^[[:space:]]+|[[:space:]]+$/, "", status)
    if (id != "" && phase != "" && status != "") {
      print id "|" phase "|" status
    }
  }
' "$ledger_file")"

if [[ -z "$ledger_rows" ]]; then
  echo "[phase-tracking] no ledger rows found in $ledger_file" >&2
  fail_count=$((fail_count + 1))
else
  duplicate_ids="$(cut -d'|' -f1 <<<"$ledger_rows" | sort | uniq -d)"
  if [[ -n "$duplicate_ids" ]]; then
    echo "[phase-tracking] duplicate deliverable_unit_id found:" >&2
    echo "$duplicate_ids" >&2
    fail_count=$((fail_count + 1))
  fi

  invalid_ids="$(cut -d'|' -f1 <<<"$ledger_rows" | grep -Ev '^DU-[0-9]{8}-[0-9]{3}$' || true)"
  if [[ -n "$invalid_ids" ]]; then
    echo "[phase-tracking] invalid deliverable_unit_id format:" >&2
    echo "$invalid_ids" >&2
    fail_count=$((fail_count + 1))
  fi
fi

if [[ "$fail_count" -gt 0 ]]; then
  echo "[phase-tracking] failed with $fail_count issue(s)" >&2
  exit 1
fi

echo "[phase-tracking] passed"
