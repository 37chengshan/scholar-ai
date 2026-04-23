#!/usr/bin/env bash
set -uo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-/Users/cc/.virtualenvs/scholar-ai-api/bin/python}"
OUTPUT_ROOT="${OUTPUT_ROOT:-$ROOT_DIR/artifacts/benchmarks/matrix_runs}"
BACKEND="${BACKEND:-milvus}"
PAGES_PER_PAPER="${PAGES_PER_PAPER:-4}"
STATUS_FILE="$OUTPUT_ROOT/matrix_status.tsv"
QUERY_COUNT_LARGE="${QUERY_COUNT_LARGE:-48}"
QUERY_COUNT_XLARGE="${QUERY_COUNT_XLARGE:-100}"
REUSE_PREPARED_DATASET="${REUSE_PREPARED_DATASET:-1}"

mkdir -p "$OUTPUT_ROOT"
printf "dataset\tmodel_stack\treranker\tround\tstatus\n" > "$STATUS_FILE"

record_status() {
  local dataset_label="$1"
  local model_stack="$2"
  local rerank_state="$3"
  local run_label="$4"
  local status="$5"
  printf "%s\t%s\t%s\t%s\t%s\n" "$dataset_label" "$model_stack" "$rerank_state" "$run_label" "$status" >> "$STATUS_FILE"
}

run_eval() {
  local dataset_profile="$1"
  local dataset_label="$2"
  local model_stack="$3"
  local embedding_model="$4"
  local reranker_model="$5"
  local rerank_state="$6"
  local run_label="$7"

  local out_dir="$OUTPUT_ROOT/$dataset_label/$model_stack"
  local report_json="$out_dir/${dataset_label}_${model_stack}_${rerank_state}_${run_label}.json"
  local report_md="$out_dir/${dataset_label}_${model_stack}_${rerank_state}_${run_label}.md"
  local golden_path="$ROOT_DIR/artifacts/benchmarks/${dataset_profile}/${model_stack}/golden_queries_${dataset_profile}.json"
  local query_count="$QUERY_COUNT_LARGE"
  if [[ "$dataset_label" == "xlarge" ]]; then
    query_count="$QUERY_COUNT_XLARGE"
  fi

  mkdir -p "$out_dir"

  local rerank_flag=""
  local embedding_dim="2048"
  local collection_name="paper_contents_v2_${model_stack}"
  if [[ "$model_stack" == "bge_dual" ]]; then
    embedding_dim="1024"
  fi
  if [[ "$rerank_state" == "on" ]]; then
    rerank_flag="--use-reranker"
  fi

  if VECTOR_STORE_BACKEND="$BACKEND" \
  EMBEDDING_DIMENSION="$embedding_dim" \
  MILVUS_COLLECTION_CONTENTS_V2="$collection_name" \
  MILVUS_FORCE_QUERY_FALLBACK="1" \
  EMBEDDING_MODEL="$embedding_model" \
  RERANKER_MODEL="$reranker_model" \
  RETRIEVAL_MODEL_STACK="$model_stack" \
  "$PYTHON_BIN" "$ROOT_DIR/scripts/eval_retrieval.py" \
    --golden "$golden_path" \
    --dataset-label "$dataset_label" \
    --model-stack "$model_stack" \
    --run-label "$run_label" \
    --output "$report_json" \
    --markdown-summary "$report_md" \
    $rerank_flag; then
    record_status "$dataset_label" "$model_stack" "$rerank_state" "$run_label" "ok"
  else
    cat > "$report_json" <<EOF
{
  "dataset_label": "$dataset_label",
  "model_stack": "$model_stack",
  "run_label": "$run_label",
  "use_reranker": $([[ "$rerank_state" == "on" ]] && echo "true" || echo "false"),
  "evaluation_mode": "real",
  "failed": true,
  "recall_at_5_avg": 0.0,
  "recall_at_10_avg": 0.0,
  "mrr_avg": 0.0,
  "paper_hit_rate_avg": 0.0,
  "section_hit_rate_avg": 0.0,
  "chunk_hit_rate_avg": 0.0,
  "cross_paper_recall_at_5": 0.0,
  "hard_query_hit_rate": 0.0,
  "latency_avg_ms": 0.0,
  "latency_p95_ms": 0.0,
  "query_details": []
}
EOF
    cat > "$report_md" <<EOF
| dataset | model_stack | reranker | run | status |
|---|---|---|---|---|
| $dataset_label | $model_stack | $rerank_state | $run_label | failed |
EOF
    record_status "$dataset_label" "$model_stack" "$rerank_state" "$run_label" "failed"
    return 1
  fi
}

prepare_dataset() {
  local dataset_profile="$1"
  local model_stack="$2"
  local embedding_model="$3"
  local reranker_model="$4"
  local query_count="$QUERY_COUNT_LARGE"
  if [[ "$dataset_profile" == "xlarge-main" ]]; then
    query_count="$QUERY_COUNT_XLARGE"
  fi

  local dataset_dir="$ROOT_DIR/artifacts/benchmarks/${dataset_profile}/${model_stack}"
  local manifest_path="$dataset_dir/dataset_manifest_${dataset_profile}.json"
  local golden_path="$dataset_dir/golden_queries_${dataset_profile}.json"
  local cache_key="${dataset_profile}_${model_stack}"
  local cache_marker="$OUTPUT_ROOT/.prepared_${cache_key}"

  if [[ -f "$cache_marker" ]]; then
    echo "[matrix] reuse in-run prepared dataset for ${cache_key}"
    return 0
  fi

  if [[ "$REUSE_PREPARED_DATASET" == "1" && -f "$manifest_path" && -f "$golden_path" ]]; then
    echo "[matrix] reuse existing dataset files for ${cache_key}"
    : > "$cache_marker"
    return 0
  fi

  local embedding_dim="2048"
  local collection_name="paper_contents_v2_${model_stack}"
  if [[ "$model_stack" == "bge_dual" ]]; then
    embedding_dim="1024"
  fi

  VECTOR_STORE_BACKEND="$BACKEND" \
  EMBEDDING_DIMENSION="$embedding_dim" \
  MILVUS_COLLECTION_CONTENTS_V2="$collection_name" \
  EMBEDDING_MODEL="$embedding_model" \
  RERANKER_MODEL="$reranker_model" \
  RETRIEVAL_MODEL_STACK="$model_stack" \
  "$PYTHON_BIN" "$ROOT_DIR/scripts/prepare_real_retrieval_dataset.py" \
    --dataset-profile "$dataset_profile" \
    --model-stack "$model_stack" \
    --query-count "$query_count" \
    --pages-per-paper "$PAGES_PER_PAPER" \
    --output-dir "$ROOT_DIR/artifacts/benchmarks"

  : > "$cache_marker"
}

run_combo() {
  local dataset_profile="$1"
  local dataset_label="$2"
  local model_stack="$3"
  local embedding_model="$4"
  local reranker_model="$5"

  if ! prepare_dataset "$dataset_profile" "$model_stack" "$embedding_model" "$reranker_model"; then
    record_status "$dataset_label" "$model_stack" "off" "round1" "dataset_failed"
    record_status "$dataset_label" "$model_stack" "off" "round2" "dataset_failed"
    record_status "$dataset_label" "$model_stack" "on" "round1" "dataset_failed"
    record_status "$dataset_label" "$model_stack" "on" "round2" "dataset_failed"
    return 1
  fi

  run_eval "$dataset_profile" "$dataset_label" "$model_stack" "$embedding_model" "$reranker_model" "off" "round1" || true
  run_eval "$dataset_profile" "$dataset_label" "$model_stack" "$embedding_model" "$reranker_model" "off" "round2" || true
  run_eval "$dataset_profile" "$dataset_label" "$model_stack" "$embedding_model" "$reranker_model" "on" "round1" || true
  run_eval "$dataset_profile" "$dataset_label" "$model_stack" "$embedding_model" "$reranker_model" "on" "round2" || true
}

run_combo "large-baseline" "large" "bge_dual" "bge-m3" "bge-reranker"
run_combo "large-baseline" "large" "qwen_dual" "qwen3-vl-2b" "qwen3-vl-reranker"
run_combo "xlarge-main" "xlarge" "bge_dual" "bge-m3" "bge-reranker"
run_combo "xlarge-main" "xlarge" "qwen_dual" "qwen3-vl-2b" "qwen3-vl-reranker"

echo "Matrix benchmark completed. Outputs at: $OUTPUT_ROOT"
