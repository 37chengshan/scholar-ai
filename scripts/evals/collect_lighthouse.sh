#!/usr/bin/env bash
# collect_lighthouse.sh -- Collect Lighthouse JSON for 4 routes.
#
# Produces files matching gate runner glob: lighthouse-{route_id}*.json
# Route IDs: route_landing, route_kb, route_read, route_chat
#
# Usage:
#   bash scripts/evals/collect_lighthouse.sh
#   bash scripts/evals/collect_lighthouse.sh --base-url http://localhost:5173
#   bash scripts/evals/collect_lighthouse.sh --output-dir artifacts/perf/v5_0

set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:5173}"
OUTPUT_DIR=""

# Parse args
while [[ $# -gt 0 ]]; do
  case "$1" in
    --base-url)
      BASE_URL="$2"
      shift 2
      ;;
    --output-dir)
      OUTPUT_DIR="$2"
      shift 2
      ;;
    --help|-h)
      echo "Usage: $0 [--base-url URL] [--output-dir DIR]"
      echo ""
      echo "Collect Lighthouse performance JSON for 4 routes."
      echo ""
      echo "Options:"
      echo "  --base-url URL     Base URL of the dev server (default: http://localhost:5173)"
      echo "  --output-dir DIR   Output directory (default: artifacts/perf/v5_0)"
      echo ""
      echo "Produces:"
      echo "  lighthouse-route_landing.json"
      echo "  lighthouse-route_kb.json"
      echo "  lighthouse-route_read.json"
      echo "  lighthouse-route_chat.json"
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      exit 1
      ;;
  esac
done

# Resolve output directory
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
if [[ -z "$OUTPUT_DIR" ]]; then
  OUTPUT_DIR="$PROJECT_ROOT/artifacts/perf/v5_0"
fi
mkdir -p "$OUTPUT_DIR"

# Route definitions matching gate runner _ROUTES dict
declare -A ROUTES=(
  [route_landing]="/"
  [route_kb]="/kb"
  [route_read]="/read"
  [route_chat]="/chat"
)

echo "[lighthouse] base_url=$BASE_URL"
echo "[lighthouse] output_dir=$OUTPUT_DIR"

FAILED=0

for route_id in route_landing route_kb route_read route_chat; do
  path="${ROUTES[$route_id]}"
  url="${BASE_URL}${path}"
  output_file="$OUTPUT_DIR/lighthouse-${route_id}.json"

  echo "[lighthouse] Running Lighthouse for $route_id ($url)..."

  if npx lighthouse "$url" \
    --output=json \
    --output-path="$output_file" \
    --chrome-flags="--headless --no-sandbox --disable-gpu" \
    --only-categories=performance,accessibility \
    --quiet 2>/dev/null; then
    echo "[lighthouse] $route_id -> $output_file (OK)"
  else
    echo "[lighthouse] ERROR: Lighthouse failed for $route_id ($url)" >&2
    FAILED=$((FAILED + 1))
  fi
done

if [[ $FAILED -gt 0 ]]; then
  echo "[lighthouse] ERROR: $FAILED route(s) failed" >&2
  exit 1
fi

echo "[lighthouse] All 4 routes collected successfully."
echo "[lighthouse] Files:"
ls -la "$OUTPUT_DIR"/lighthouse-route_*.json
