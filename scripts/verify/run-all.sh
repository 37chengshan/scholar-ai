#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"

run_stage() {
  local stage="$1"
  shift
  echo ""
  echo "[verify] stage=$stage start"
  "$@"
  echo "[verify] stage=$stage ok"
}

run_governance() {
  cd "$ROOT_DIR"
  bash scripts/check-runtime-hygiene.sh tracked
  bash scripts/check-doc-governance.sh
  bash scripts/check-structure-boundaries.sh
  bash scripts/check-code-boundaries.sh
  bash scripts/check-contract-gate.sh
  bash scripts/check-fallback-expiry.sh
  bash scripts/check-e2e-gate.sh --mode manifest
}

run_web() {
  cd "$ROOT_DIR/apps/web"
  npm install
  npm run type-check
  npm run test:run
}

run_packages() {
  cd "$ROOT_DIR/packages/types"
  npm install
  npm run build

  cd "$ROOT_DIR/packages/sdk"
  npm install
  npm run build
}

run_api() {
  cd "$ROOT_DIR"
  bash scripts/verify/bootstrap-api-env.sh

  local py_bin="$ROOT_DIR/apps/api/.venv/bin/python"
  cd "$ROOT_DIR/apps/api"

  "$py_bin" -m pytest -q tests/unit/test_services.py --maxfail=1

  local run_integration="${VERIFY_INTEGRATION:-1}"
  if [[ "${VERIFY_QUICK:-0}" == "1" ]]; then
    run_integration="0"
    echo "[verify] quick mode enabled: integration tests are skipped"
  fi

  if [[ "$run_integration" == "1" ]]; then
    "$py_bin" -m pytest -q tests/integration/test_imports_chat_contract.py --maxfail=1
  else
    echo "[verify] stage=api integration skipped (set VERIFY_INTEGRATION=1 or unset VERIFY_QUICK)"
  fi
}

run_stage governance run_governance
run_stage web run_web
run_stage packages run_packages
run_stage api run_api

echo ""
echo "[verify] all stages passed"