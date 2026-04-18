#!/usr/bin/env bash
set -euo pipefail

window="14d"
output_file=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --window)
      window="$2"
      shift 2
      ;;
    --output)
      output_file="$2"
      shift 2
      ;;
    *)
      echo "[governance-kpi] unknown argument: $1" >&2
      exit 2
      ;;
  esac
done

if [[ -z "$output_file" ]]; then
  echo "[governance-kpi] --output is required" >&2
  exit 1
fi

plan_status_file="docs/plans/PLAN_STATUS.md"
ledger_file="docs/governance/phase-delivery-ledger.md"
fallback_file="docs/governance/fallback-register.yaml"

for file in "$plan_status_file" "$ledger_file" "$fallback_file"; do
  if [[ ! -f "$file" ]]; then
    echo "[governance-kpi] missing required file: $file" >&2
    exit 1
  fi
done

plan_totals="$(awk -F'|' '
  /^\|/ {
    if ($0 ~ /^\|---/) next
    if ($0 ~ /计划/) next
    status=$4
    gsub(/^[[:space:]]+|[[:space:]]+$/, "", status)
    if (status == "") next
    total++
    if (status == "done") done_count++
    if (status == "in-progress") active_count++
    if (status == "blocked") blocked_count++
  }
  END { printf "%d|%d|%d|%d", total+0, done_count+0, active_count+0, blocked_count+0 }
' "$plan_status_file")"

IFS='|' read -r total_plans done_plans in_progress_plans blocked_plans <<<"$plan_totals"

active_or_done=$((done_plans + in_progress_plans + blocked_plans))
if [[ "$active_or_done" -eq 0 ]]; then
  planning_delivery_rate="0.00"
else
  planning_delivery_rate="$(python3 - <<'PY' "$done_plans" "$active_or_done"
import sys
num = int(sys.argv[1])
den = int(sys.argv[2])
print(f"{num / den:.2f}")
PY
)"
fi

ledger_phase_count="$(awk -F'|' '
  /^\|/ {
    if ($0 ~ /^\|---/) next
    if ($0 ~ /deliverable_unit_id/) next
    phase=$3
    status=$9
    gsub(/^[[:space:]]+|[[:space:]]+$/, "", phase)
    gsub(/^[[:space:]]+|[[:space:]]+$/, "", status)
    if (phase != "" && (status == "done" || status == "in-progress")) {
      seen[phase]=1
    }
  }
  END {
    count=0
    for (k in seen) count++
    print count + 0
  }
' "$ledger_file")"

if [[ "$active_or_done" -eq 0 ]]; then
  phase_coverage_rate="0.00"
else
  phase_coverage_rate="$(python3 - <<'PY' "$ledger_phase_count" "$active_or_done"
import sys
num = int(sys.argv[1])
den = int(sys.argv[2])
print(f"{num / den:.2f}")
PY
)"
fi

fallback_metrics="$(ruby -e '
require "yaml"
require "date"

data = YAML.safe_load(File.read(ARGV[0]), aliases: false)
records = Array(data["records"])
active = records.select { |r| r.is_a?(Hash) && r["status"].to_s == "active" }
expired = active.count do |r|
  begin
    Date.iso8601(r["expires_at"].to_s) < Date.today
  rescue ArgumentError
    false
  end
end
ages = active.map do |r|
  begin
    (Date.today - Date.iso8601(r["introduced_at"].to_s)).to_i
  rescue ArgumentError
    nil
  end
end.compact
avg_age = ages.empty? ? 0.0 : ages.sum.to_f / ages.length
puts [active.length, expired, format("%.2f", avg_age)].join("|")
' "$fallback_file")"

IFS='|' read -r fallback_active_count fallback_expired_active fallback_active_days_avg <<<"$fallback_metrics"

if [[ -f docs/reports/governance-kpi/e2e-history.csv ]]; then
  e2e_counts="$(awk -F',' 'NR>1 { if ($2 == "pass") p++; if ($2 == "fail") f++; } END { printf "%d|%d", p+0, f+0 }' docs/reports/governance-kpi/e2e-history.csv)"
  IFS='|' read -r e2e_pass e2e_fail <<<"$e2e_counts"
else
  e2e_pass=0
  e2e_fail=0
fi

e2e_total=$((e2e_pass + e2e_fail))
if [[ "$e2e_total" -eq 0 ]]; then
  e2e_gate_pass_rate="N/A"
else
  e2e_gate_pass_rate="$(python3 - <<'PY' "$e2e_pass" "$e2e_total"
import sys
num = int(sys.argv[1])
den = int(sys.argv[2])
print(f"{num / den:.2f}")
PY
)"
fi

since_date="$(python3 - <<'PY' "$window"
import datetime
import re
import sys
w = sys.argv[1]
m = re.fullmatch(r"(\d+)d", w)
if not m:
    print((datetime.date.today() - datetime.timedelta(days=14)).isoformat())
else:
    days = int(m.group(1))
    print((datetime.date.today() - datetime.timedelta(days=days)).isoformat())
PY
)"

merge_count="$(git log --since="$since_date" --pretty=format:'%s' | wc -l | tr -d ' ')"
revert_count="$(git log --since="$since_date" --pretty=format:'%s' | (grep -Ei '^revert|revert:' || true) | wc -l | tr -d ' ')"

if [[ "$merge_count" -eq 0 ]]; then
  rollback_rate="N/A"
else
  rollback_rate="$(python3 - <<'PY' "$revert_count" "$merge_count"
import sys
num = int(sys.argv[1])
den = int(sys.argv[2])
print(f"{num / den:.2f}")
PY
)"
fi

mkdir -p "$(dirname "$output_file")"

cat > "$output_file" <<EOF
# Governance KPI Report

- generated_at: $(date +%F)
- window: $window
- since: $since_date

## Delivery Consistency

| metric | value | threshold |
|---|---:|---:|
| phase_coverage_rate | $phase_coverage_rate | >= 1.00 |
| planning_delivery_rate | $planning_delivery_rate | >= 0.85 |
| rollback_rate | $rollback_rate | <= 0.10 |

## Contract Health

| metric | value | threshold |
|---|---:|---:|
| fallback_expired_active | $fallback_expired_active | = 0 |
| fallback_active_days_avg | $fallback_active_days_avg | <= 14 |
| fallback_active_count | $fallback_active_count | monitor |

## Release Quality

| metric | value | threshold |
|---|---:|---:|
| e2e_gate_pass_rate | $e2e_gate_pass_rate | >= 0.95 |
| post_merge_48h_incident_rate | N/A | <= 0.05 |

## Raw Counters

- total_plans: $total_plans
- done_plans: $done_plans
- in_progress_plans: $in_progress_plans
- blocked_plans: $blocked_plans
- ledger_phase_count: $ledger_phase_count
- e2e_pass: $e2e_pass
- e2e_fail: $e2e_fail
- commits_in_window: $merge_count
- reverts_in_window: $revert_count
EOF

echo "[governance-kpi] report generated: $output_file"
