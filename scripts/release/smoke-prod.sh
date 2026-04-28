#!/usr/bin/env bash
# scripts/release/smoke-prod.sh
# Post-deploy smoke test. Verifies basic connectivity and page availability.
#
# Usage:
#   BASE_URL=https://your-deploy-url bash scripts/release/smoke-prod.sh
#
# Set SMOKE_AUTH_TOKEN if API endpoints require Authorization header.
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"
FRONTEND_URL="${FRONTEND_URL:-http://localhost:5173}"
AUTH_TOKEN="${SMOKE_AUTH_TOKEN:-}"

PASS=0
FAIL=0
RESULTS=()

check_http() {
  local name="$1"
  local url="$2"
  local expected="${3:-200}"
  local extra_args=()

  if [[ -n "$AUTH_TOKEN" ]]; then
    extra_args+=(-H "Authorization: Bearer $AUTH_TOKEN")
  fi

  local code
  code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "${extra_args[@]}" "$url" || echo "000")

  if [[ "$code" == "$expected" ]]; then
    PASS=$((PASS + 1))
    RESULTS+=("✅  [$code] $name  ($url)")
  else
    FAIL=$((FAIL + 1))
    RESULTS+=("❌  [$code] $name  ($url)  — expected $expected")
  fi
}

check_json_field() {
  local name="$1"
  local url="$2"
  local jq_expr="$3"
  local extra_args=()

  if [[ -n "$AUTH_TOKEN" ]]; then
    extra_args+=(-H "Authorization: Bearer $AUTH_TOKEN")
  fi

  local body
  body=$(curl -s --max-time 10 "${extra_args[@]}" "$url" || echo "{}")

  if echo "$body" | python3 -c "import sys,json; d=json.load(sys.stdin); assert $jq_expr" 2>/dev/null; then
    PASS=$((PASS + 1))
    RESULTS+=("✅  $name  ($url)")
  else
    FAIL=$((FAIL + 1))
    RESULTS+=("❌  $name  ($url)  — assertion failed: $jq_expr")
    RESULTS+=("    response: $(echo "$body" | head -c 200)")
  fi
}

echo ""
echo "══════════════════════════════════════════════════════"
echo "  Production Smoke Test"
echo "  Backend:  $BASE_URL"
echo "  Frontend: $FRONTEND_URL"
echo "══════════════════════════════════════════════════════"

# ─── Backend health ───────────────────────────────────────
echo ""
echo "── Backend Health ──"
check_http   "API liveness"   "$BASE_URL/health/live"  "200"
check_http   "API readiness"  "$BASE_URL/health/ready" "200"
check_json_field "API live returns status:alive" \
  "$BASE_URL/health/live" \
  "d['status'] == 'alive'"

# ─── Auth endpoint reachable ─────────────────────────────
echo ""
echo "── Auth Reachable ──"
# Expect 422 (missing body) — confirms route exists and is not 404/502
check_http "Auth login endpoint reachable" \
  "$BASE_URL/api/v1/auth/login" "422"

# ─── Frontend pages ──────────────────────────────────────
echo ""
echo "── Frontend Pages ──"
check_http "Frontend root"      "$FRONTEND_URL/"            "200"
check_http "Frontend /login"    "$FRONTEND_URL/login"       "200"
check_http "Frontend /dashboard" "$FRONTEND_URL/dashboard"  "200"
check_http "Frontend /chat"     "$FRONTEND_URL/chat"        "200"
check_http "Frontend /notes"    "$FRONTEND_URL/notes"       "200"
check_http "Frontend /search"   "$FRONTEND_URL/search"      "200"

# ─── Summary ─────────────────────────────────────────────
echo ""
echo "══════════════════════════════════════════════════════"
echo "  Smoke Test Summary"
echo "══════════════════════════════════════════════════════"
for r in "${RESULTS[@]}"; do
  echo "  $r"
done
echo ""
echo "  Passed: $PASS  Failed: $FAIL"
echo "══════════════════════════════════════════════════════"

if [[ $FAIL -gt 0 ]]; then
  echo "SMOKE FAILED — deployment has issues."
  exit 1
fi

echo "SMOKE PASSED ✓"
exit 0
