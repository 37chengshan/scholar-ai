#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-/Users/cc/.virtualenvs/scholar-ai-api/bin/python}"
BENCHMARK_USER_ID="${BENCHMARK_USER_ID:-benchmark-user}"
BACKEND="${BACKEND:-milvus}"
OUTPUT_DIR="${OUTPUT_DIR:-$ROOT_DIR/artifacts/benchmarks}"
DATASET_PROFILE="${DATASET_PROFILE:-v2}"
QUERY_COUNT="${QUERY_COUNT:-80}"
EMBEDDING_BATCH_SIZE="${EMBEDDING_BATCH_SIZE:-32}"
SPECTER2_MODEL_DIR="${SPECTER2_MODEL_DIR:-/Users/cc/models/specter2}"

SKIP_PARSE=0
SKIP_RAW=0
SKIP_RULE=0
SKIP_LLM=0
SKIP_RETRIEVAL=0
SKIP_ANSWER=0
ONLY_STAGE=""
ALL_PAGES=1

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dataset-profile) DATASET_PROFILE="$2"; shift 2 ;;
    --skip-parse) SKIP_PARSE=1; shift ;;
    --skip-raw) SKIP_RAW=1; shift ;;
    --skip-rule) SKIP_RULE=1; shift ;;
    --skip-llm) SKIP_LLM=1; shift ;;
    --skip-retrieval) SKIP_RETRIEVAL=1; shift ;;
    --skip-answer) SKIP_ANSWER=1; shift ;;
    --only) ONLY_STAGE="$2"; shift 2 ;;
    --all-pages) ALL_PAGES=1; shift ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

log_phase() {
  echo ""
  echo "=================================================="
  echo "PHASE: $1"
  echo "=================================================="
}

phase_secs() {
  local start="$1"
  local end
  end=$(date +%s)
  echo $((end - start))
}

RAW_COLLECTION="paper_contents_v2_qwen_v2_raw_v2"
RULE_COLLECTION="paper_contents_v2_qwen_v2_rule_v2"
LLM_COLLECTION="paper_contents_v2_qwen_v2_llm_v2"

if [[ "$DATASET_PROFILE" == "v2.1" ]]; then
  RAW_COLLECTION="paper_contents_v2_qwen_v2_raw_v2_1"
  RULE_COLLECTION="paper_contents_v2_qwen_v2_rule_v2_1"
  LLM_COLLECTION="paper_contents_v2_qwen_v2_llm_v2_1"
fi

mkdir -p "$OUTPUT_DIR/$DATASET_PROFILE/reports"
TIMING_REPORT="$OUTPUT_DIR/$DATASET_PROFILE/reports/stage_timing_v2.json"
STAGE_TIMING_FILE="$OUTPUT_DIR/$DATASET_PROFILE/reports/.stage_timing_pairs"
: > "$STAGE_TIMING_FILE"

if [[ $SKIP_PARSE -eq 0 && -z "$ONLY_STAGE" ]]; then
  log_phase "prepare_raw_base"
  t0=$(date +%s)
  VECTOR_STORE_BACKEND="$BACKEND" \
  "$PYTHON_BIN" "$ROOT_DIR/scripts/prepare_raw_base.py" \
    --dataset-profile "$DATASET_PROFILE" \
    --all-pages \
    --output-dir "$OUTPUT_DIR"
  echo "prepare_raw_base=$(phase_secs "$t0")" >> "$STAGE_TIMING_FILE"
fi

build_stage() {
  local stage="$1"
  local skip="$2"
  local collection="$3"

  if [[ "$skip" -eq 1 ]]; then
    echo "[v2] skip stage=$stage"
    return
  fi
  if [[ -n "$ONLY_STAGE" && "$ONLY_STAGE" != "$stage" ]]; then
    echo "[v2] skip stage=$stage due to --only $ONLY_STAGE"
    return
  fi

  log_phase "build:$stage"
  t0=$(date +%s)
  VECTOR_STORE_BACKEND="$BACKEND" \
  RETRIEVAL_MODEL_STACK="academic_hybrid" \
  EMBEDDING_MODEL="qwen3-vl-2b" \
  EMBEDDING_DIMENSION="2048" \
  MILVUS_COLLECTION_CONTENTS_V2="$collection" \
  SCIENTIFIC_TEXT_BRANCH_ENABLED="1" \
  SCIENTIFIC_TEXT_EMBEDDING_BACKEND="specter2" \
  SCIENTIFIC_TEXT_SPECTER_ADAPTER="adhoc_query" \
  SPECTER2_MODEL_DIR="$SPECTER2_MODEL_DIR" \
  "$PYTHON_BIN" "$ROOT_DIR/scripts/build_stage_variant.py" \
    --dataset-profile "$DATASET_PROFILE" \
    --stage "$stage" \
    --user-id "$BENCHMARK_USER_ID" \
    --embedding-batch-size "$EMBEDDING_BATCH_SIZE" \
    --output-dir "$OUTPUT_DIR" \
    --skip-if-complete
  echo "build_$stage=$(phase_secs "$t0")" >> "$STAGE_TIMING_FILE"
}

if [[ -z "$ONLY_STAGE" || "$ONLY_STAGE" == "raw" ]]; then
  build_stage "raw" "$SKIP_RAW" "$RAW_COLLECTION"
fi
if [[ -z "$ONLY_STAGE" || "$ONLY_STAGE" == "rule" ]]; then
  build_stage "rule" "$SKIP_RULE" "$RULE_COLLECTION"
fi
if [[ -z "$ONLY_STAGE" || "$ONLY_STAGE" == "llm" ]]; then
  build_stage "llm" "$SKIP_LLM" "$LLM_COLLECTION"
fi

GOLDEN="$OUTPUT_DIR/$DATASET_PROFILE/qwen_dual/golden_queries_${DATASET_PROFILE}.json"
REPORT_DIR="$OUTPUT_DIR/$DATASET_PROFILE/reports"
RAW_RETRIEVAL="$REPORT_DIR/retrieval_raw_${DATASET_PROFILE}.json"
RULE_RETRIEVAL="$REPORT_DIR/retrieval_rule_${DATASET_PROFILE}.json"
LLM_RETRIEVAL="$REPORT_DIR/retrieval_llm_${DATASET_PROFILE}.json"

run_retrieval() {
  local mode="$1"
  local collection="$2"
  local output="$3"
  local md="$REPORT_DIR/retrieval_${mode}_${DATASET_PROFILE}.md"
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
    --golden "$GOLDEN" \
    --user-id "$BENCHMARK_USER_ID" \
    --dataset-label "${DATASET_PROFILE}-20" \
    --model-stack "academic_hybrid" \
    --run-label "${mode}-${DATASET_PROFILE}" \
    --use-reranker \
    --output "$output" \
    --markdown-summary "$md"
}

if [[ -z "$ONLY_STAGE" && $SKIP_RETRIEVAL -eq 0 ]]; then
  log_phase "eval:retrieval"
  t0=$(date +%s)
  run_retrieval raw "$RAW_COLLECTION" "$RAW_RETRIEVAL"
  run_retrieval rule "$RULE_COLLECTION" "$RULE_RETRIEVAL"
  run_retrieval llm "$LLM_COLLECTION" "$LLM_RETRIEVAL"
  echo "eval_retrieval=$(phase_secs "$t0")" >> "$STAGE_TIMING_FILE"

  PASS_FLAG=$(RAW="$RAW_RETRIEVAL" RULE="$RULE_RETRIEVAL" LLM="$LLM_RETRIEVAL" "$PYTHON_BIN" - <<'PY'
import json, os
raw=json.loads(open(os.environ['RAW']).read())
rule=json.loads(open(os.environ['RULE']).read())
llm=json.loads(open(os.environ['LLM']).read())
r_raw=float(raw.get('recall_at_20_avg',0.0))
r_rule=float(rule.get('recall_at_20_avg',0.0))
r_llm=float(llm.get('recall_at_20_avg',0.0))
ok=(r_rule >= r_raw) and (r_llm >= r_rule*0.95)
print('PASS' if ok else 'FAIL')
PY
)
else
  PASS_FLAG="SKIP"
fi

if [[ -z "$ONLY_STAGE" && $SKIP_ANSWER -eq 0 ]]; then
  if [[ "$PASS_FLAG" == "PASS" || "$PASS_FLAG" == "SKIP" ]]; then
    log_phase "eval:answer"
    t0=$(date +%s)
    for mode in raw rule llm; do
      case "$mode" in
        raw) c="$RAW_COLLECTION" ;;
        rule) c="$RULE_COLLECTION" ;;
        llm) c="$LLM_COLLECTION" ;;
      esac
      VECTOR_STORE_BACKEND="$BACKEND" \
      RETRIEVAL_MODEL_STACK="academic_hybrid" \
      EMBEDDING_MODEL="qwen3-vl-2b" \
      RERANKER_MODEL="qwen3-vl-reranker" \
      EMBEDDING_DIMENSION="2048" \
      MILVUS_COLLECTION_CONTENTS_V2="$c" \
      SCIENTIFIC_TEXT_BRANCH_ENABLED="1" \
      SCIENTIFIC_TEXT_EMBEDDING_BACKEND="specter2" \
      SCIENTIFIC_TEXT_SPECTER_ADAPTER="adhoc_query" \
      SPECTER2_MODEL_DIR="$SPECTER2_MODEL_DIR" \
      "$PYTHON_BIN" "$ROOT_DIR/scripts/eval_answer.py" \
        --real \
        --golden "$GOLDEN" \
        --output "$REPORT_DIR/answer_${mode}_${DATASET_PROFILE}.json"
    done
    echo "eval_answer=$(phase_secs "$t0")" >> "$STAGE_TIMING_FILE"
  else
    echo "[v2] retrieval gate failed, skip eval:answer"
  fi
fi

# Merge stage timing into report json
STAGE_TIMING_JSON=$(awk -F'=' 'BEGIN{printf "{"} NF==2 {if(n++) printf ","; printf "\"%s\":%s", $1, $2} END{printf "}"}' "$STAGE_TIMING_FILE")

RAW_BASE_TIMING="$OUTPUT_DIR/$DATASET_PROFILE/raw_base/paper_stage_timing.jsonl"
RULE_TIMING="$OUTPUT_DIR/$DATASET_PROFILE/variants/timing_rule.jsonl"
LLM_TIMING="$OUTPUT_DIR/$DATASET_PROFILE/variants/timing_llm.jsonl"

STAGE_TIMING_JSON="$STAGE_TIMING_JSON" RAW_BASE_TIMING="$RAW_BASE_TIMING" RULE_TIMING="$RULE_TIMING" LLM_TIMING="$LLM_TIMING" TIMING_REPORT_PATH="$TIMING_REPORT" DATASET_PROFILE="$DATASET_PROFILE" "$PYTHON_BIN" - <<'PY'
import json, os
from pathlib import Path

def load_jsonl(path: Path):
    if not path.exists():
        return []
    out=[]
    for line in path.read_text(encoding='utf-8').splitlines():
        line=line.strip()
        if line:
            out.append(json.loads(line))
    return out

stage_timing=json.loads(os.environ['STAGE_TIMING_JSON']) if os.environ.get('STAGE_TIMING_JSON') else {}
raw_rows=load_jsonl(Path(os.environ['RAW_BASE_TIMING']))
rule_rows=load_jsonl(Path(os.environ['RULE_TIMING']))
llm_rows=load_jsonl(Path(os.environ['LLM_TIMING']))

per_paper={}
for row in raw_rows + rule_rows + llm_rows:
    pid=row['paper_id']
    per_paper.setdefault(pid, {
        'paper_id': pid,
        'parse_pdf_seconds': 0.0,
        'chunk_raw_seconds': 0.0,
        'build_rule_seconds': 0.0,
        'build_llm_seconds': 0.0,
        'embed_dense_seconds': 0.0,
        'build_sparse_seconds': 0.0,
        'insert_index_seconds': 0.0,
        'summary_index_seconds': 0.0,
    })
    for key in [
        'parse_pdf_seconds','chunk_raw_seconds','build_rule_seconds','build_llm_seconds',
        'embed_dense_seconds','build_sparse_seconds','insert_index_seconds','summary_index_seconds'
    ]:
        per_paper[pid][key]+=float(row.get(key,0.0))

report={
  'dataset_profile': os.environ.get('DATASET_PROFILE', 'v2'),
    'stage_timing_seconds': stage_timing,
    'per_paper_timing': list(per_paper.values()),
    'reuse_raw_base': True,
}
out_path=Path(os.environ['TIMING_REPORT_PATH'])
out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
print(out_path)
PY

echo ""
echo "[${DATASET_PROFILE}] complete"
echo "[${DATASET_PROFILE}] stage timing report: $TIMING_REPORT"