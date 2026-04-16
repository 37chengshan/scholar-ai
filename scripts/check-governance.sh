#!/usr/bin/env bash
set -euo pipefail

required_files=(
  "README.md"
  "AGENTS.md"
  "architecture.md"
  ".gitignore"
  ".github/PULL_REQUEST_TEMPLATE.md"
  ".github/ISSUE_TEMPLATE/bug-report.yml"
  ".github/ISSUE_TEMPLATE/feature-request.yml"
  ".github/ISSUE_TEMPLATE/governance-task.yml"
  ".github/workflows/governance-baseline.yml"
  "docs/architecture/system-overview.md"
  "docs/architecture/api-contract.md"
  "docs/domain/resources.md"
  "docs/development/coding-standards.md"
  "docs/development/documentation-validation.md"
  "docs/development/pr-process.md"
  "docs/development/testing-strategy.md"
  "docs/governance/code-boundary-baseline.md"
  "docs/governance/harness-engineering-playbook.md"
)

for file in "${required_files[@]}"; do
  if [[ ! -f "$file" ]]; then
    echo "missing required governance file: $file" >&2
    exit 1
  fi
done

required_gitignore_entries=(
  "cookies.txt"
  "backend.pid"
  "frontend.pid"
  "runtime/"
  "artifacts/"
)

for entry in "${required_gitignore_entries[@]}"; do
  if ! grep -Fq "$entry" .gitignore; then
    echo "missing required .gitignore entry: $entry" >&2
    exit 1
  fi
done

bash scripts/check-doc-governance.sh
bash scripts/check-structure-boundaries.sh
bash scripts/check-code-boundaries.sh

echo "governance baseline check passed"
