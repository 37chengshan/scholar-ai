#!/usr/bin/env bash
set -euo pipefail

plan_status_file="docs/plans/PLAN_STATUS.md"

if [[ ! -f "$plan_status_file" ]]; then
  echo "[plan-governance] missing $plan_status_file" >&2
  exit 1
fi

allowed_statuses=("not-started" "in-progress" "blocked" "done" "superseded")

fail_count=0

if ! command -v ruby >/dev/null 2>&1; then
  echo "[plan-governance] ruby is required for YAML frontmatter validation" >&2
  exit 1
fi

status_pattern="$(IFS='|'; echo "${allowed_statuses[*]}")"

normalize_list() {
  local input="${1:-}"
  input="${input//，/,}"

  if [[ -z "$input" || "$input" == "-" ]]; then
    echo ""
    return
  fi

  printf '%s\n' "$input" \
    | tr ',' '\n' \
    | sed 's/^[[:space:]]*//; s/[[:space:]]*$//' \
    | sed '/^$/d' \
    | sort \
    | paste -sd',' -
}

is_valid_evidence_token() {
  local token="$1"

  if [[ "$token" =~ ^[0-9a-f]{7,40}$ ]]; then
    return 0
  fi

  if [[ "$token" =~ ^historical-[a-z0-9._-]+$ ]]; then
    return 0
  fi

  if [[ "$token" =~ ^wip-[a-z0-9._-]+$ ]]; then
    return 0
  fi

  return 1
}

validate_evidence_list() {
  local list_csv="${1:-}"
  local require_no_wip="${2:-false}"

  if [[ -z "$list_csv" ]]; then
    return 1
  fi

  local token
  while IFS= read -r token; do
    [[ -z "$token" ]] && continue

    if ! is_valid_evidence_token "$token"; then
      return 1
    fi

    if [[ "$require_no_wip" == "true" && "$token" =~ ^wip- ]]; then
      return 1
    fi
  done < <(tr ',' '\n' <<<"$list_csv")

  return 0
}

extract_frontmatter() {
  local file="$1"
  awk '
    NR==1 {
      if ($0 != "---") {
        exit 2
      }
      in_fm=1
      next
    }
    in_fm && $0 == "---" {
      found_end=1
      exit
    }
    in_fm {
      print
    }
    END {
      if (!found_end) {
        exit 3
      }
    }
  ' "$file"
}

extract_table_column() {
  local plan_id="$1"
  local column_index="$2"
  local row

  row="$(grep -F "| ${plan_id} |" "$plan_status_file" | head -1 || true)"

  if [[ -z "$row" ]]; then
    echo ""
    return
  fi

  awk -F'|' -v idx="$column_index" '
    {
      value=$idx
      gsub(/^[[:space:]]+|[[:space:]]+$/, "", value)
      print value
    }
  ' <<<"$row"
}

while IFS= read -r plan_file; do
  [[ -f "$plan_file" ]] || continue

  plan_id="$(basename "$plan_file" .md)"

  if ! frontmatter="$(extract_frontmatter "$plan_file" 2>/dev/null)"; then
    echo "[plan-governance] invalid frontmatter boundaries in $plan_file" >&2
    fail_count=$((fail_count + 1))
    continue
  fi

  if grep -q $'\t' <<<"$frontmatter"; then
    echo "[plan-governance] tab indentation is forbidden in frontmatter: $plan_file" >&2
    fail_count=$((fail_count + 1))
    continue
  fi

  if ! ruby_result="$(ruby -e '
require "yaml"
require "date"
file = ARGV[0]
frontmatter = ARGV[1]
required = %w[owner status depends_on last_verified_at evidence_commits]

to_list = lambda do |value|
  case value
  when nil
    ""
  when Array
    value.map { |item| item.to_s.strip }.reject(&:empty?).join(",")
  else
    value.to_s.strip
  end
end

begin
  data = YAML.safe_load(frontmatter, permitted_classes: [Date], aliases: false)
rescue Psych::SyntaxError => e
  STDERR.puts("[plan-governance] invalid YAML in #{file}: #{e.message}")
  exit 11
end

unless data.is_a?(Hash)
  STDERR.puts("[plan-governance] frontmatter must parse to mapping in #{file}")
  exit 12
end

missing = required.reject { |key| data.key?(key) }
unless missing.empty?
  STDERR.puts("[plan-governance] missing metadata keys in #{file}: #{missing.join(", ")}")
  exit 13
end

owner = data["owner"].to_s.strip
status = data["status"].to_s.strip
depends_on = to_list.call(data["depends_on"])
last_verified_at = data["last_verified_at"].to_s.strip
evidence_commits = to_list.call(data["evidence_commits"])

if owner.empty? || owner !~ /\A[a-z0-9][a-z0-9-]*\z/
  STDERR.puts("[plan-governance] invalid owner format in #{file}: #{owner.inspect}")
  exit 14
end

begin
  Date.iso8601(last_verified_at)
rescue ArgumentError
  STDERR.puts("[plan-governance] invalid last_verified_at date in #{file}: #{last_verified_at.inspect}")
  exit 15
end

separator = "\u001F"
puts [owner, status, depends_on, last_verified_at, evidence_commits].join(separator)
' "$plan_file" "$frontmatter")"; then
    echo "[plan-governance] YAML metadata validation failed in $plan_file" >&2
    fail_count=$((fail_count + 1))
    continue
  fi

IFS=$'\x1f' read -r owner_value status_value depends_on_value last_verified_at_value evidence_commits_value <<<"$ruby_result"

if [[ ! "$status_value" =~ ^(${status_pattern})$ ]]; then
    echo "[plan-governance] invalid status '$status_value' in $plan_file" >&2
    fail_count=$((fail_count + 1))
  fi

table_owner="$(extract_table_column "$plan_id" 3)"
table_status="$(extract_table_column "$plan_id" 4)"
table_depends_on="$(extract_table_column "$plan_id" 5)"
table_last_verified_at="$(extract_table_column "$plan_id" 6)"
table_evidence="$(extract_table_column "$plan_id" 7)"
table_phase_unit_id="$(extract_table_column "$plan_id" 8)"
table_deliverable_unit_id="$(extract_table_column "$plan_id" 9)"
table_pr_link="$(extract_table_column "$plan_id" 10)"
table_coverage_scope="$(extract_table_column "$plan_id" 11)"
table_risk_level="$(extract_table_column "$plan_id" 12)"

if [[ -z "$table_status" ]]; then
    echo "[plan-governance] PLAN_STATUS missing row for $plan_id" >&2
    fail_count=$((fail_count + 1))
    continue
  fi

if [[ "$table_owner" != "$owner_value" ]]; then
    echo "[plan-governance] owner mismatch for $plan_id: frontmatter=$owner_value table=$table_owner" >&2
    fail_count=$((fail_count + 1))
  fi

if [[ "$table_status" != "$status_value" ]]; then
    echo "[plan-governance] status mismatch for $plan_id: frontmatter=$status_value table=$table_status" >&2
    fail_count=$((fail_count + 1))
  fi

normalized_depends_frontmatter="$(normalize_list "$depends_on_value")"
normalized_depends_table="$(normalize_list "$table_depends_on")"
if [[ "$normalized_depends_frontmatter" != "$normalized_depends_table" ]]; then
    echo "[plan-governance] depends_on mismatch for $plan_id: frontmatter=$normalized_depends_frontmatter table=$normalized_depends_table" >&2
    fail_count=$((fail_count + 1))
  fi

if [[ "$table_last_verified_at" != "$last_verified_at_value" ]]; then
    echo "[plan-governance] last_verified_at mismatch for $plan_id: frontmatter=$last_verified_at_value table=$table_last_verified_at" >&2
    fail_count=$((fail_count + 1))
  fi

normalized_evidence_frontmatter="$(normalize_list "$evidence_commits_value")"
normalized_evidence_table="$(normalize_list "$table_evidence")"

if [[ "$normalized_evidence_frontmatter" != "$normalized_evidence_table" ]]; then
    echo "[plan-governance] evidence_commits mismatch for $plan_id: frontmatter=$normalized_evidence_frontmatter table=$normalized_evidence_table" >&2
    fail_count=$((fail_count + 1))
  fi

if [[ "$status_value" == "done" || "$status_value" == "in-progress" ]]; then
    if [[ -z "$normalized_evidence_frontmatter" ]]; then
      echo "[plan-governance] missing evidence_commits in PLAN_STATUS for active/done plan $plan_id" >&2
      fail_count=$((fail_count + 1))
    elif [[ "$status_value" == "done" ]]; then
      if ! validate_evidence_list "$normalized_evidence_frontmatter" "true"; then
        echo "[plan-governance] invalid evidence_commits format for done plan $plan_id (only sha/historical allowed)" >&2
        fail_count=$((fail_count + 1))
      fi
    elif ! validate_evidence_list "$normalized_evidence_frontmatter" "false"; then
      echo "[plan-governance] invalid evidence_commits format for in-progress plan $plan_id" >&2
      fail_count=$((fail_count + 1))
    fi

    if [[ -z "$table_phase_unit_id" || "$table_phase_unit_id" == "-" ]]; then
      echo "[plan-governance] missing phase_unit_id in PLAN_STATUS for active/done plan $plan_id" >&2
      fail_count=$((fail_count + 1))
    fi

    if [[ -z "$table_deliverable_unit_id" || ! "$table_deliverable_unit_id" =~ ^DU-[0-9]{8}-[0-9]{3}$ ]]; then
      echo "[plan-governance] invalid deliverable_unit_id in PLAN_STATUS for active/done plan $plan_id" >&2
      fail_count=$((fail_count + 1))
    fi

    if [[ -z "$table_pr_link" || "$table_pr_link" == "-" ]]; then
      echo "[plan-governance] missing pr_link in PLAN_STATUS for active/done plan $plan_id" >&2
      fail_count=$((fail_count + 1))
    fi

    if [[ -z "$table_coverage_scope" || "$table_coverage_scope" == "-" ]]; then
      echo "[plan-governance] missing coverage_scope in PLAN_STATUS for active/done plan $plan_id" >&2
      fail_count=$((fail_count + 1))
    fi

    if [[ ! "$table_risk_level" =~ ^(low|medium|high)$ ]]; then
      echo "[plan-governance] invalid risk_level in PLAN_STATUS for active/done plan $plan_id: $table_risk_level" >&2
      fail_count=$((fail_count + 1))
    fi
  fi
done < <(find docs/plans -maxdepth 1 -type f -name 'PR*.md' | sort)

active_shared_contract_count="$(awk -F'|' '
  /PR[56]_共享契约收口_与_前端工作台可用性方案/ {
    status=$4
    gsub(/^[[:space:]]+|[[:space:]]+$/, "", status)
    if (status != "superseded") count++
  }
  END { print count + 0 }
' "$plan_status_file")"

if [[ "$active_shared_contract_count" -ne 1 ]]; then
  echo "[plan-governance] exactly one active shared-contract plan is required (PR5/PR6 pair)" >&2
  fail_count=$((fail_count + 1))
fi

if [[ "$fail_count" -gt 0 ]]; then
  echo "[plan-governance] failed with $fail_count issue(s)" >&2
  exit 1
fi

echo "[plan-governance] passed"
