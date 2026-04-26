#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-/Users/cc/.virtualenvs/scholar-ai-api/bin/python}"
OUTPUT_DIR="${OUTPUT_DIR:-$ROOT_DIR/artifacts/benchmarks}"

if [[ ! -f "$ROOT_DIR/scripts/evals/run_academic_rag_v2.sh" ]]; then
  echo "v2 runner missing"
  exit 1
fi

# v2.1: strict raw reuse by default.
# If raw_base exists, do not re-parse; only rebuild variants.
if [[ -f "$OUTPUT_DIR/v2.1/raw_base/raw_chunks.jsonl" ]]; then
  echo "[v2.1] reuse raw base: $OUTPUT_DIR/v2.1/raw_base/raw_chunks.jsonl"
  exec "$ROOT_DIR/scripts/evals/run_academic_rag_v2.sh" --dataset-profile v2.1 --skip-parse "$@"
else
  echo "[v2.1] raw base not found, prepare once then reuse"
  exec "$ROOT_DIR/scripts/evals/run_academic_rag_v2.sh" --dataset-profile v2.1 "$@"
fi
