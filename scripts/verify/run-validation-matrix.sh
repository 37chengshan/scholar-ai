#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
INPUT_JSON="${1:-$ROOT_DIR/artifacts/validation-results/2026-04-vnext-plus1.sample.json}"
OUT_JSON="${2:-$ROOT_DIR/artifacts/validation-results/2026-04-vnext-plus1.summary.json}"
OUT_MD="${3:-$ROOT_DIR/artifacts/validation-results/2026-04-vnext-plus1.summary.md}"

if [[ ! -f "$INPUT_JSON" ]]; then
  echo "[run-validation-matrix] input not found: $INPUT_JSON"
  exit 1
fi

python3 "$ROOT_DIR/scripts/verify/summarize_validation_results.py" \
  --input "$INPUT_JSON" \
  --output-json "$OUT_JSON" \
  --output-md "$OUT_MD"

echo "[run-validation-matrix] summary json: $OUT_JSON"
echo "[run-validation-matrix] summary md: $OUT_MD"