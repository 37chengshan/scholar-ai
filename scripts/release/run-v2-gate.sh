#!/usr/bin/env bash
# scripts/release/run-v2-gate.sh
# One-command v2 release gate. Exits non-zero on any failure.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
WEB="$REPO_ROOT/apps/web"
API="$REPO_ROOT/apps/api"

PASS=0
FAIL=0
RESULTS=()

run_check() {
  local name="$1"
  shift
  echo ""
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "[Gate] $name"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  if "$@"; then
    PASS=$((PASS + 1))
    RESULTS+=("✅  $name")
  else
    FAIL=$((FAIL + 1))
    RESULTS+=("❌  $name")
  fi
}

# ─── Web checks ─────────────────────────────────────────
run_check "Web type-check" bash -c "cd '$WEB' && pnpm type-check"

run_check "Chat critical (E2E)" bash -c \
  "cd '$WEB' && pnpm playwright test e2e/chat-critical.spec.ts --reporter=line"

run_check "Chat evidence (E2E)" bash -c \
  "cd '$WEB' && pnpm playwright test e2e/chat-evidence.spec.ts --reporter=line"

run_check "Notes rendering (E2E)" bash -c \
  "cd '$WEB' && pnpm playwright test e2e/notes-rendering.spec.ts --reporter=line"

run_check "Chat responsive (E2E)" bash -c \
  "cd '$WEB' && pnpm playwright test e2e/chat-responsive.spec.ts --reporter=line"

# ─── API checks ─────────────────────────────────────────
run_check "Backend fast path (unit)" bash -c \
  "cd '$API' && python3 -m pytest tests/unit/test_chat_fast_path.py -q"

# ─── Summary ────────────────────────────────────────────
echo ""
echo "══════════════════════════════════════════════════════"
echo "  Release Gate Summary"
echo "══════════════════════════════════════════════════════"
for r in "${RESULTS[@]}"; do
  echo "  $r"
done
echo ""
echo "  Passed: $PASS  Failed: $FAIL"
echo "══════════════════════════════════════════════════════"

if [[ $FAIL -gt 0 ]]; then
  echo "GATE FAILED — fix issues above before releasing."
  exit 1
fi

echo "GATE PASSED ✓"
exit 0
