#!/usr/bin/env bash
set -euo pipefail

required_docs=(
  "README.md"
  "AGENTS.md"
  "architecture.md"
  "docs/architecture/system-overview.md"
  "docs/architecture/api-contract.md"
  "docs/domain/resources.md"
  "docs/development/coding-standards.md"
  "docs/development/documentation-validation.md"
  "docs/development/pr-process.md"
  "docs/development/testing-strategy.md"
  "docs/governance/code-boundary-baseline.md"
  "docs/governance/harness-engineering-playbook.md"
  "docs/governance/phase-delivery-ledger.md"
  "docs/governance/branch-lifecycle-policy.md"
  "docs/governance/governance-kpi-spec.md"
  "docs/governance/e2e-failure-handbook.md"
)

required_sections=(
  "## Purpose"
  "## Scope"
  "## Source of Truth"
  "## Rules"
  "## Required Updates"
  "## Verification"
  "## Open Questions"
)

required_references=(
  "README.md:docs/architecture/system-overview.md"
  "README.md:docs/architecture/api-contract.md"
  "README.md:docs/domain/resources.md"
  "README.md:docs/development/documentation-validation.md"
  "README.md:docs/governance/code-boundary-baseline.md"
  "README.md:docs/governance/harness-engineering-playbook.md"
  "README.md:docs/governance/phase-delivery-ledger.md"
  "README.md:docs/governance/branch-lifecycle-policy.md"
  "README.md:docs/governance/governance-kpi-spec.md"
  "README.md:docs/governance/e2e-failure-handbook.md"
  "AGENTS.md:docs/architecture/system-overview.md"
  "AGENTS.md:docs/architecture/api-contract.md"
  "AGENTS.md:docs/domain/resources.md"
  "AGENTS.md:docs/development/documentation-validation.md"
  "AGENTS.md:docs/governance/code-boundary-baseline.md"
  "AGENTS.md:docs/governance/harness-engineering-playbook.md"
  "AGENTS.md:docs/governance/phase-delivery-ledger.md"
  "AGENTS.md:docs/governance/branch-lifecycle-policy.md"
  "AGENTS.md:docs/governance/governance-kpi-spec.md"
  "AGENTS.md:docs/governance/e2e-failure-handbook.md"
  "architecture.md:docs/architecture/system-overview.md"
  "architecture.md:docs/architecture/api-contract.md"
  "docs/development/pr-process.md:docs/development/testing-strategy.md"
  "docs/development/testing-strategy.md:docs/development/pr-process.md"
)

fail_count=0

for file in "${required_docs[@]}"; do
  if [[ ! -f "$file" ]]; then
    echo "[doc-governance] missing required doc: $file" >&2
    fail_count=$((fail_count + 1))
  fi
done

for file in "${required_docs[@]}"; do
  [[ -f "$file" ]] || continue
  for section in "${required_sections[@]}"; do
    if ! grep -Fq "$section" "$file"; then
      echo "[doc-governance] missing section '$section' in $file" >&2
      fail_count=$((fail_count + 1))
    fi
  done
done

for item in "${required_references[@]}"; do
  source_file="${item%%:*}"
  expected_ref="${item#*:}"
  if [[ -f "$source_file" ]] && ! grep -Fq "$expected_ref" "$source_file"; then
    echo "[doc-governance] missing reference '$expected_ref' in $source_file" >&2
    fail_count=$((fail_count + 1))
  fi
done

# Validate local markdown links in governance-critical docs only.
markdown_sources=(
  "README.md"
  "AGENTS.md"
  "architecture.md"
  "docs/README.md"
)

while IFS= read -r doc_file; do
  markdown_sources+=("$doc_file")
done < <(find docs/architecture docs/domain docs/development docs/governance -type f -name "*.md" | sort)

for source in "${markdown_sources[@]}"; do
  [[ -f "$source" ]] || continue
  while IFS=: read -r file line target; do
    clean_target="$target"
    if [[ "$clean_target" == "<"* && "$clean_target" == *">" ]]; then
      clean_target="${clean_target#<}"
      clean_target="${clean_target%>}"
    fi
    clean_target="${clean_target%% \"*}"
    clean_target="${clean_target%% \'*}"
    clean_target="${clean_target%%\#*}"
    clean_target="${clean_target%%\?*}"
    clean_target="${clean_target//%20/ }"

    if [[ -z "$clean_target" ]]; then
      continue
    fi

    case "$clean_target" in
      http://*|https://*|mailto:*|tel:*|\#*)
        continue
        ;;
    esac

    if [[ "$clean_target" == /* ]]; then
      resolved_path=".${clean_target}"
    else
      resolved_path="$(dirname "$file")/$clean_target"
    fi

    if [[ ! -e "$resolved_path" ]]; then
      echo "[doc-governance] broken local link in $file:$line -> $target" >&2
      fail_count=$((fail_count + 1))
    fi
  done < <(perl -ne 'if (/^```/) { $in_code = !$in_code; next; } next if $in_code; while (/\[[^\]]+\]\(([^)]+)\)/g) { print "$ARGV:$.:$1\n"; }' "$source")
done

if [[ "$fail_count" -gt 0 ]]; then
  echo "[doc-governance] failed with $fail_count issue(s)" >&2
  exit 1
fi

echo "[doc-governance] passed"