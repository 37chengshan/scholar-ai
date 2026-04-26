#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-/Users/cc/.virtualenvs/scholar-ai-api/bin/python}"
PROFILE="${DATASET_PROFILE:-v2.1}"
OUTPUT_DIR="${OUTPUT_DIR:-$ROOT_DIR/artifacts/benchmarks}"
BENCHMARK_USER_ID="${BENCHMARK_USER_ID:-benchmark-user}"

SKIP_BUILD=0
SKIP_RETRIEVAL=0
SKIP_ANSWER=0
GENERATE_QUERIES_ONLY=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dataset-profile) PROFILE="$2"; shift 2 ;;
    --skip-build) SKIP_BUILD=1; shift ;;
    --skip-retrieval) SKIP_RETRIEVAL=1; shift ;;
    --skip-answer) SKIP_ANSWER=1; shift ;;
    --generate-queries-only) GENERATE_QUERIES_ONLY=1; shift ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

log_phase() {
  echo ""
  echo "=================================================="
  echo "PHASE: $1"
  echo "=================================================="
}

GOLDEN_PATH="$OUTPUT_DIR/$PROFILE/qwen_dual/golden_queries_${PROFILE}.json"

if [[ ! -f "$GOLDEN_PATH" || "$GENERATE_QUERIES_ONLY" -eq 1 ]]; then
  log_phase "generate-queries"
  "$PYTHON_BIN" "$ROOT_DIR/scripts/prepare_real_retrieval_dataset.py" \
    --dataset-profile "$PROFILE" \
    --model-stack qwen_dual \
    --all-pages \
    --queries-only \
    --output-dir "$OUTPUT_DIR"
fi

if [[ "$GENERATE_QUERIES_ONLY" -eq 1 ]]; then
  echo "[scaffold] queries generated only: $GOLDEN_PATH"
  exit 0
fi

if [[ "$SKIP_BUILD" -eq 0 ]]; then
  log_phase "build-raw-rule-llm"
  "$ROOT_DIR/scripts/evals/run_academic_rag_v2.sh" --dataset-profile "$PROFILE" --skip-parse --only raw
  "$ROOT_DIR/scripts/evals/run_academic_rag_v2.sh" --dataset-profile "$PROFILE" --skip-parse --only rule
  "$ROOT_DIR/scripts/evals/run_academic_rag_v2.sh" --dataset-profile "$PROFILE" --skip-parse --only llm
fi

log_phase "eval-compare"
CMD=("$ROOT_DIR/scripts/evals/run_academic_rag_v2.sh" "--dataset-profile" "$PROFILE" "--skip-parse" "--skip-raw" "--skip-rule" "--skip-llm")
if [[ "$SKIP_RETRIEVAL" -eq 1 ]]; then
  CMD+=("--skip-retrieval")
fi
if [[ "$SKIP_ANSWER" -eq 1 ]]; then
  CMD+=("--skip-answer")
fi
"${CMD[@]}"

REPORT_DIR="$OUTPUT_DIR/$PROFILE/reports"

OUTPUT_DIR="$OUTPUT_DIR" PROFILE="$PROFILE" "$PYTHON_BIN" - <<'PY'
import json
import os
from pathlib import Path

output_dir = Path(os.environ["OUTPUT_DIR"])
profile = os.environ["PROFILE"]
report_dir = output_dir / profile / "reports"

rows = []
for mode in ("raw", "rule", "llm"):
    retrieval = report_dir / f"retrieval_{mode}_{profile}.json"
    answer = report_dir / f"answer_{mode}_{profile}.json"
    if not retrieval.exists():
        continue
    r = json.loads(retrieval.read_text(encoding="utf-8"))
    a = json.loads(answer.read_text(encoding="utf-8")) if answer.exists() else {}
    rows.append({
        "mode": mode,
        "recall20": float(r.get("recall_at_20_avg", 0.0)),
        "ndcg10": float(r.get("ndcg_at_10_avg", 0.0)),
        "evidence_hit": float(r.get("evidence_hit_rate_avg", 0.0)),
        "citation_density": float(a.get("citation_density_avg", 0.0)),
        "unsupported_rate": float(a.get("unsupported_rate_avg", 0.0)),
    })

lines = [
    f"# {profile} raw/rule/llm 对照评测",
    "",
    "| mode | Recall@20 | nDCG@10 | evidence hit rate | citation density | unsupported rate |",
    "|---|---:|---:|---:|---:|---:|",
]
for row in rows:
    lines.append(
        f"| {row['mode']} | {row['recall20']:.4f} | {row['ndcg10']:.4f} | {row['evidence_hit']:.4f} | {row['citation_density']:.4f} | {row['unsupported_rate']:.4f} |"
    )

out = report_dir / f"compare_{profile}.md"
out.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(out)
PY

echo "[scaffold] done profile=$PROFILE user=$BENCHMARK_USER_ID"
