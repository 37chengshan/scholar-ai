#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd -- "$script_dir/.." && pwd)"
cd "$repo_root"

required_files=(
  "README.md"
  "AGENTS.md"
  "architecture.md"
  ".gitignore"
  ".github/pull_request_template.md"
  ".github/ISSUE_TEMPLATE/bug-report.yml"
  ".github/ISSUE_TEMPLATE/feature-request.yml"
  ".github/ISSUE_TEMPLATE/governance-task.yml"
  ".github/workflows/governance.yml"
  ".github/workflows/contract-gate.yml"
  ".github/workflows/fallback-expiry-gate.yml"
  ".github/workflows/branch-lifecycle.yml"
  ".github/workflows/e2e-gate.yml"
  ".github/workflows/governance-kpi.yml"
  "docs/specs/README.md"
  "docs/specs/architecture/system-overview.md"
  "docs/specs/architecture/api-contract.md"
  "docs/specs/domain/resources.md"
  "docs/specs/development/coding-standards.md"
  "docs/specs/development/documentation-validation.md"
  "docs/specs/development/pr-process.md"
  "docs/specs/development/testing-strategy.md"
  "docs/specs/governance/code-boundary-baseline.md"
  "docs/specs/governance/harness-engineering-playbook.md"
  "docs/specs/governance/phase-delivery-ledger.md"
  "docs/specs/governance/branch-lifecycle-policy.md"
  "docs/specs/governance/fallback-register.yaml"
  "docs/specs/governance/governance-kpi-spec.md"
  "docs/specs/governance/e2e-failure-handbook.md"
  "docs/plans/PLAN_STATUS.md"
  "scripts/check-legacy-freeze.sh"
  "scripts/check-plan-governance.sh"
  "scripts/check-phase-tracking.sh"
  "scripts/check-branch-lifecycle.sh"
  "scripts/check-contract-gate.sh"
  "scripts/check-fallback-expiry.sh"
  "scripts/check-e2e-gate.sh"
  "scripts/audit-governance-kpi.sh"
  "scripts/check-runtime-hygiene.sh"
  "scripts/clean-repo-artifacts.sh"
)

for file in "${required_files[@]}"; do
  if [[ ! -f "$file" ]]; then
    echo "missing required governance file: $file" >&2
    exit 1
  fi
done

required_gitignore_patterns=(
  "cookies.txt:::^[[:space:]]*cookies\\.txt([[:space:]]*(#.*)?)?$"
  "backend.pid:::^[[:space:]]*backend\\.pid([[:space:]]*(#.*)?)?$"
  "frontend.pid:::^[[:space:]]*frontend\\.pid([[:space:]]*(#.*)?)?$"
  "runtime/:::^[[:space:]]*runtime/\\*?([[:space:]]*(#.*)?)?$"
  "artifacts/:::^[[:space:]]*artifacts/\\*?([[:space:]]*(#.*)?)?$"
  "apps/web/test-results/:::^[[:space:]]*apps/web/test-results/\\*?([[:space:]]*(#.*)?)?$"
  "apps/api/venv/:::^[[:space:]]*apps/api/venv/\\*?([[:space:]]*(#.*)?)?$"
  "apps/api/htmlcov/:::^[[:space:]]*apps/api/htmlcov/\\*?([[:space:]]*(#.*)?)?$"
  "scholar-ai/:::^[[:space:]]*scholar-ai/\\*?([[:space:]]*(#.*)?)?$"
)

for rule in "${required_gitignore_patterns[@]}"; do
  entry_name="${rule%%:::*}"
  entry_pattern="${rule#*:::}"
  if ! grep -Eq "$entry_pattern" .gitignore; then
    echo "missing required .gitignore entry: $entry_name" >&2
    exit 1
  fi
done

bash scripts/check-doc-governance.sh
bash scripts/check-plan-governance.sh
bash scripts/check-phase-tracking.sh
bash scripts/check-legacy-freeze.sh
bash scripts/check-structure-boundaries.sh
bash scripts/check-code-boundaries.sh
bash scripts/check-branch-lifecycle.sh
bash scripts/check-contract-gate.sh
bash scripts/check-fallback-expiry.sh
bash scripts/check-e2e-gate.sh --mode manifest
bash scripts/check-runtime-hygiene.sh tracked

echo "governance baseline check passed"
