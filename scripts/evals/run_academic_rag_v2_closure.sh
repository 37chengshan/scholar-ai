#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-/Users/cc/.virtualenvs/scholar-ai-api/bin/python}"
BENCHMARK_USER_ID="${BENCHMARK_USER_ID:-benchmark-user}"
BACKEND="${BACKEND:-milvus}"
QUERY_COUNT="${QUERY_COUNT:-100}"
DATASET_PROFILE="${DATASET_PROFILE:-xlarge-main}"
OUTPUT_DIR="${OUTPUT_DIR:-$ROOT_DIR/artifacts/benchmarks/closure_v2}"
SPECTER2_MODEL_DIR="${SPECTER2_MODEL_DIR:-/Users/cc/models/specter2}"
EMBEDDING_BATCH_SIZE="${EMBEDDING_BATCH_SIZE:-32}"

mkdir -p "$OUTPUT_DIR"

eval_retrieval_mode() {
  local mode="$1"
  local collection="paper_contents_v2_qwen_v2_${mode}"
  local mode_dir="$OUTPUT_DIR/$mode"
  mkdir -p "$mode_dir"

  echo "[closure] preparing dataset mode=$mode collection=$collection"
  VECTOR_STORE_BACKEND="$BACKEND" \
  RETRIEVAL_MODEL_STACK="academic_hybrid" \
  EMBEDDING_MODEL="qwen3-vl-2b" \
  EMBEDDING_DIMENSION="2048" \
  MILVUS_COLLECTION_CONTENTS_V2="$collection" \
  SCIENTIFIC_TEXT_BRANCH_ENABLED="1" \
  SCIENTIFIC_TEXT_EMBEDDING_BACKEND="specter2" \
  SCIENTIFIC_TEXT_SPECTER_ADAPTER="adhoc_query" \
  SPECTER2_MODEL_DIR="$SPECTER2_MODEL_DIR" \
  "$PYTHON_BIN" "$ROOT_DIR/scripts/prepare_real_retrieval_dataset.py" \
    --user-id "$BENCHMARK_USER_ID" \
    --dataset-profile "$DATASET_PROFILE" \
    --model-stack "qwen_dual" \
    --query-count "$QUERY_COUNT" \
    --all-pages \
    --contextual-mode "$mode" \
    --embedding-batch-size "$EMBEDDING_BATCH_SIZE" \
    --output-dir "$ROOT_DIR/artifacts/benchmarks"

  local golden="$ROOT_DIR/artifacts/benchmarks/$DATASET_PROFILE/qwen_dual/golden_queries_${DATASET_PROFILE}.json"
  local retrieval_json="$mode_dir/retrieval_${mode}.json"
  local retrieval_md="$mode_dir/retrieval_${mode}.md"

  echo "[closure] round1 retrieval eval mode=$mode"
  VECTOR_STORE_BACKEND="$BACKEND" \
  RETRIEVAL_MODEL_STACK="academic_hybrid" \
  EMBEDDING_MODEL="qwen3-vl-2b" \
  RERANKER_MODEL="qwen3-vl-reranker" \
  EMBEDDING_DIMENSION="2048" \
  MILVUS_COLLECTION_CONTENTS_V2="$collection" \
  SCIENTIFIC_TEXT_BRANCH_ENABLED="1" \
  SCIENTIFIC_TEXT_EMBEDDING_BACKEND="specter2" \
  SCIENTIFIC_TEXT_SPECTER_ADAPTER="adhoc_query" \
  SPECTER2_MODEL_DIR="$SPECTER2_MODEL_DIR" \
  "$PYTHON_BIN" "$ROOT_DIR/scripts/eval_retrieval.py" \
    --golden "$golden" \
    --user-id "$BENCHMARK_USER_ID" \
    --dataset-label "xlarge-full" \
    --model-stack "academic_hybrid" \
    --run-label "$mode" \
    --use-reranker \
    --output "$retrieval_json" \
    --markdown-summary "$retrieval_md"

  local answer_json="$mode_dir/answer_${mode}.json"
  echo "[closure] round2 answer eval mode=$mode"
  VECTOR_STORE_BACKEND="$BACKEND" \
  RETRIEVAL_MODEL_STACK="academic_hybrid" \
  EMBEDDING_MODEL="qwen3-vl-2b" \
  RERANKER_MODEL="qwen3-vl-reranker" \
  EMBEDDING_DIMENSION="2048" \
  MILVUS_COLLECTION_CONTENTS_V2="$collection" \
  SCIENTIFIC_TEXT_BRANCH_ENABLED="1" \
  SCIENTIFIC_TEXT_EMBEDDING_BACKEND="specter2" \
  SCIENTIFIC_TEXT_SPECTER_ADAPTER="adhoc_query" \
  SPECTER2_MODEL_DIR="$SPECTER2_MODEL_DIR" \
  "$PYTHON_BIN" "$ROOT_DIR/scripts/eval_answer.py" \
    --real \
    --golden "$golden" \
    --output "$answer_json"
}

summarize_report() {
  local report="$OUTPUT_DIR/closure_report.md"
  OUTPUT_ROOT="$OUTPUT_DIR" "$PYTHON_BIN" <<'PY'
import json
import os
from pathlib import Path

root = Path(os.environ["OUTPUT_ROOT"])
modes = ["raw", "rule", "llm"]
rows = []
for mode in modes:
    retrieval = root / mode / f"retrieval_{mode}.json"
    answer = root / mode / f"answer_{mode}.json"
    if not retrieval.exists() or not answer.exists():
        continue
    r = json.loads(retrieval.read_text())
    a = json.loads(answer.read_text())
    rows.append({
        "mode": mode,
        "recall20": round(float(r.get("recall_at_20_avg", 0.0)), 4),
        "ndcg10": round(float(r.get("ndcg_at_10_avg", 0.0)), 4),
        "evidence_hit": round(float(r.get("evidence_hit_rate_avg", 0.0)), 4),
        "citation_faithfulness": round(float(a.get("citation_density_avg", 0.0)), 4),
        "unsupported_claim_rate": round(float(a.get("unsupported_rate_avg", 0.0)), 4),
    })

lines = []
lines.append("# Academic-RAG v2 收口测试报告")
lines.append("")
lines.append("| mode | Recall@20 | nDCG@10 | evidence hit rate | citation density | unsupported claim rate |")
lines.append("|---|---:|---:|---:|---:|---:|")
for row in rows:
    lines.append(
        f"| {row['mode']} | {row['recall20']:.4f} | {row['ndcg10']:.4f} | {row['evidence_hit']:.4f} | {row['citation_faithfulness']:.4f} | {row['unsupported_claim_rate']:.4f} |"
    )

if rows:
    mode_map = {row["mode"]: row for row in rows}
    lines.append("")
    lines.append("## 结论")
    if "raw" in mode_map and "rule" in mode_map:
        delta = mode_map["rule"]["recall20"] - mode_map["raw"]["recall20"]
        lines.append(f"- Round1 raw→rule Recall@20 差值: {delta:+.4f}")
    if "rule" in mode_map and "llm" in mode_map:
        delta = mode_map["llm"]["recall20"] - mode_map["rule"]["recall20"]
        lines.append(f"- Round1 rule→llm Recall@20 差值: {delta:+.4f}")
    if "raw" in mode_map and "llm" in mode_map:
        delta = mode_map["llm"]["unsupported_claim_rate"] - mode_map["raw"]["unsupported_claim_rate"]
        lines.append(f"- Round2 raw→llm unsupported claim rate 差值: {delta:+.4f}")

report_path = root / "closure_report.md"
report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(report_path)
PY

  echo "[closure] report generated at: $report"
}

eval_retrieval_mode raw
eval_retrieval_mode rule
eval_retrieval_mode llm
summarize_report

echo "[closure] done"
