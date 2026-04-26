#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import signal
import statistics
import sys
import time
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Set, Tuple

ROOT = Path(__file__).resolve().parents[2]
API_ROOT = ROOT / "apps" / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.evals.v2_4_common import OFFICIAL_OUTPUT_FIELDS, STAGES, read_json, stage_collection_name, write_json, write_markdown


OUTPUT_DIR = ROOT / "artifacts" / "benchmarks" / "v2_6"
DOC_REPORT = ROOT / "docs" / "reports" / "official_rag_evaluation" / "official_rag_evaluation_v2_6_report.md"

RUNTIME_PROFILE = "api_flash_qwen_rerank_glm"
EMBEDDING_MODEL = "tongyi-embedding-vision-flash-2026-03-06"
RERANKER_MODEL = "qwen3-vl-rerank"
LLM_MODEL = "glm-4.5-air"

DEFAULT_GOLDEN_PATH = ROOT / "artifacts" / "benchmarks" / "v2_5" / "golden_queries_real_50.json"
DEFAULT_CONSISTENCY_PATH = ROOT / "artifacts" / "benchmarks" / "v2_5" / "golden_consistency_50.json"
DEFAULT_FAMILY_STATS_PATH = ROOT / "artifacts" / "benchmarks" / "v2_5" / "golden_family_stats_50.json"


class BenchmarkGuardError(RuntimeError):
    """Raised when official evaluation preconditions are violated."""


@dataclass(frozen=True)
class GoldenRow:
    query_id: str
    query: str
    query_family: str
    expected_paper_ids: List[str]
    expected_source_chunk_ids: List[str]
    expected_content_types: List[str]
    expected_sections: List[str]
    expected_answer_mode: str
    evidence_anchors: List[Dict[str, Any]]


@dataclass(frozen=True)
class StageRunContext:
    stage: str
    collection: str
    runtime_profile: str
    collection_suffix: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Step6 Official RAG Evaluation")
    parser.add_argument("--runtime-profile", default=RUNTIME_PROFILE)
    parser.add_argument("--golden-path", default=str(DEFAULT_GOLDEN_PATH))
    parser.add_argument("--collection-suffix", default="v2_4")
    parser.add_argument("--stage", choices=["raw", "rule", "llm", "all"], default="all")
    parser.add_argument("--mode", choices=["regression", "official"], default="regression")
    parser.add_argument("--max-queries", type=int, default=None)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--timeout-per-query-seconds", type=int, default=120)
    parser.add_argument("--save-every", type=int, default=1)
    parser.add_argument("--dashboard-interval-seconds", type=int, default=10)
    parser.add_argument("--fail-fast", default="false")
    parser.add_argument("--milvus-host", default="localhost")
    parser.add_argument("--milvus-port", type=int, default=19530)
    return parser.parse_args()


def _bool_arg(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def _p95(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(float(v) for v in values)
    index = max(math.ceil(0.95 * len(ordered)) - 1, 0)
    return float(ordered[index])


def _mean(values: Iterable[float]) -> float:
    seq = [float(v) for v in values]
    if not seq:
        return 0.0
    return float(statistics.mean(seq))


def _parse_numbers(text: str) -> Set[str]:
    import re

    return set(re.findall(r"\b\d+(?:\.\d+)?%?\b", text or ""))


def _normalize_paper_ids(values: Iterable[Any]) -> List[str]:
    return [str(v) for v in values if str(v or "").strip()]


def _looks_like_real_golden(payload: Dict[str, Any]) -> bool:
    version = str(payload.get("version") or "").lower()
    return "real_golden" in version or "v2_5" in version


def load_golden_rows(path: Path, mode: str = "official") -> List[GoldenRow]:
    if not path.exists():
        raise BenchmarkGuardError(f"EVAL_BLOCKED: real golden file missing: {path}")

    payload = read_json(path)
    if not isinstance(payload, dict) or not isinstance(payload.get("queries"), list):
        raise BenchmarkGuardError("EVAL_BLOCKED: invalid real golden schema")

    if mode == "official" and not _looks_like_real_golden(payload):
        raise BenchmarkGuardError("EVAL_BLOCKED: synthetic golden is not allowed in official mode")

    rows: List[GoldenRow] = []
    for item in payload.get("queries", []):
        query_id = str(item.get("query_id") or "").strip()
        query = str(item.get("query") or "").strip()
        family = str(item.get("query_family") or "fact").strip()
        expected_paper_ids = _normalize_paper_ids(item.get("expected_paper_ids") or [])
        expected_source_chunk_ids = _normalize_paper_ids(item.get("expected_source_chunk_ids") or [])
        if any(paper_id.startswith("test-paper-") for paper_id in expected_paper_ids):
            raise BenchmarkGuardError("EVAL_BLOCKED: synthetic golden is not allowed in official mode")
        if not query_id or not query:
            continue
        rows.append(
            GoldenRow(
                query_id=query_id,
                query=query,
                query_family=family,
                expected_paper_ids=expected_paper_ids,
                expected_source_chunk_ids=expected_source_chunk_ids,
                expected_content_types=_normalize_paper_ids(item.get("expected_content_types") or ["text"]),
                expected_sections=_normalize_paper_ids(item.get("expected_sections") or ["body"]),
                expected_answer_mode=str(item.get("expected_answer_mode") or "full"),
                evidence_anchors=list(item.get("evidence_anchors") or []),
            )
        )

    if mode == "official" and not rows:
        raise BenchmarkGuardError("EVAL_BLOCKED: real golden contains no usable rows")
    return rows


def load_completed_result_keys(path: Path) -> Set[str]:
    if not path.exists():
        return set()
    completed: Set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        query_id = str(payload.get("query_id") or "").strip()
        stage = str(payload.get("stage") or "").strip()
        if query_id and stage:
            completed.add(f"{query_id}::{stage}")
    return completed


def filter_pending_rows(rows: Sequence[GoldenRow], stage: str, completed_keys: Set[str]) -> List[GoldenRow]:
    return [row for row in rows if f"{row.query_id}::{stage}" not in completed_keys]


def append_jsonl(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def persist_json_list(path: Path, items: Sequence[Dict[str, Any]]) -> None:
    write_json(path, list(items))


def _dcg(relevances: Sequence[int]) -> float:
    total = 0.0
    for index, rel in enumerate(relevances, start=1):
        total += float(rel) / math.log2(index + 1)
    return total


def _mrr(retrieved_ids: Sequence[str], expected_ids: Set[str]) -> float:
    for rank, value in enumerate(retrieved_ids, start=1):
        if value in expected_ids:
            return round(1.0 / rank, 4)
    return 0.0


def _ndcg(retrieved_ids: Sequence[str], expected_ids: Set[str], limit: int = 10) -> float:
    actual = [1 if value in expected_ids else 0 for value in retrieved_ids[:limit]]
    ideal = sorted(actual, reverse=True)
    actual_dcg = _dcg(actual)
    ideal_dcg = _dcg(ideal)
    if ideal_dcg <= 0:
        return 0.0
    return round(actual_dcg / ideal_dcg, 4)


def _ordered_unique(values: Sequence[str]) -> List[str]:
    seen: Set[str] = set()
    ordered: List[str] = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered


def compute_retrieval_metrics(
    *,
    row: GoldenRow,
    retrieved_hits: Sequence[Dict[str, Any]],
    answer_text: str,
    citation_report: Dict[str, Any],
    claim_report: Dict[str, Any],
    answer_evidence_consistency: float,
    answer_mode: str,
) -> Dict[str, float]:
    expected_source_ids = set(row.expected_source_chunk_ids)
    expected_paper_ids = set(row.expected_paper_ids)
    expected_sections = set(row.expected_sections)
    expected_content_types = set(row.expected_content_types)

    top10_source_ids = [str(hit.get("source_chunk_id") or hit.get("source_id") or "") for hit in retrieved_hits[:10]]
    top5_source_ids = top10_source_ids[:5]
    top10_paper_ids = [str(hit.get("paper_id") or "") for hit in retrieved_hits[:10]]
    top5_paper_ids = top10_paper_ids[:5]
    top5_sections = [str(hit.get("section") or "") for hit in retrieved_hits[:5]]
    top5_content_types = [str(hit.get("content_type") or "") for hit in retrieved_hits[:5]]

    matched_at_5 = len(expected_source_ids & set(top5_source_ids)) if expected_source_ids else 0
    matched_at_10 = len(expected_source_ids & set(top10_source_ids)) if expected_source_ids else 0
    recall_at_5 = round(matched_at_5 / max(len(expected_source_ids), 1), 4) if expected_source_ids else 0.0
    recall_at_10 = round(matched_at_10 / max(len(expected_source_ids), 1), 4) if expected_source_ids else 0.0

    paper_hit_rate = round(len(expected_paper_ids & set(top5_paper_ids)) / max(len(expected_paper_ids), 1), 4) if expected_paper_ids else 0.0
    section_hit_rate = round(len(expected_sections & set(top5_sections)) / max(len(expected_sections), 1), 4) if expected_sections else 0.0
    chunk_hit_rate = 1.0 if matched_at_5 > 0 else 0.0

    table_hit_rate = 1.0 if (row.query_family == "table" and (expected_content_types & set(top5_content_types) or any(v == "table" for v in top5_content_types))) else 0.0
    figure_hit_rate = 1.0 if (row.query_family == "figure" and (expected_content_types & set(top5_content_types) or any(v in {"figure", "caption", "page"} for v in top5_content_types))) else 0.0

    expected_anchor_text = " ".join(str(anchor.get("anchor_text") or "") for anchor in row.evidence_anchors)
    expected_numbers = _parse_numbers(expected_anchor_text)
    answer_numbers = _parse_numbers(answer_text)
    numeric_exact_match = 1.0 if row.query_family == "numeric" and expected_numbers and (expected_numbers & answer_numbers) else 0.0

    citation_count = int(citation_report.get("citation_count") or 0)
    matched_citation_count = int(citation_report.get("matched_citation_count") or 0)
    citation_jump_validity = round(matched_citation_count / citation_count, 4) if citation_count else 0.0

    return {
        "recall_at_5": recall_at_5,
        "recall_at_10": recall_at_10,
        "mrr": _mrr(top10_source_ids, expected_source_ids) if expected_source_ids else 0.0,
        "ndcg_at_10": _ndcg(top10_source_ids, expected_source_ids),
        "paper_hit_rate": paper_hit_rate,
        "section_hit_rate": section_hit_rate,
        "chunk_hit_rate": chunk_hit_rate,
        "table_hit_rate": table_hit_rate,
        "figure_hit_rate": figure_hit_rate,
        "numeric_exact_match": numeric_exact_match,
        "citation_coverage": round(float(citation_report.get("citation_coverage") or 0.0), 4),
        "unsupported_claim_rate": round(float(claim_report.get("unsupportedClaimRate") or 0.0), 4),
        "answer_evidence_consistency": round(float(answer_evidence_consistency), 4),
        "citation_jump_validity": citation_jump_validity,
        "answer_mode_accuracy": 1.0 if answer_mode == row.expected_answer_mode else 0.0,
        "abstain_precision": 1.0 if answer_mode == "abstain" else 0.0,
    }


def build_result_record(
    *,
    row: GoldenRow,
    stage: str,
    collection: str,
    runtime_profile: str,
    retrieved_source_chunk_ids_top5: Sequence[str],
    retrieved_paper_ids_top5: Sequence[str],
    metrics: Dict[str, float],
    answer_mode: str,
    fallback_used: bool,
    deprecated_branch_used: bool,
    dimension_mismatch: bool,
    provider_error: Optional[str],
    timeout: bool,
    latency_ms: int,
) -> Dict[str, Any]:
    return {
        "query_id": row.query_id,
        "query_family": row.query_family,
        "stage": stage,
        "runtime_profile": runtime_profile,
        "embedding_model": EMBEDDING_MODEL,
        "reranker_model": RERANKER_MODEL,
        "llm_model": LLM_MODEL,
        "collection": collection,
        "expected_paper_ids": row.expected_paper_ids,
        "expected_source_chunk_ids": row.expected_source_chunk_ids,
        "retrieved_source_chunk_ids_top5": list(retrieved_source_chunk_ids_top5),
        "retrieved_paper_ids_top5": list(retrieved_paper_ids_top5),
        "recall_at_5": round(float(metrics.get("recall_at_5", 0.0)), 4),
        "recall_at_10": round(float(metrics.get("recall_at_10", 0.0)), 4),
        "mrr": round(float(metrics.get("mrr", 0.0)), 4),
        "ndcg_at_10": round(float(metrics.get("ndcg_at_10", 0.0)), 4),
        "paper_hit_rate": round(float(metrics.get("paper_hit_rate", 0.0)), 4),
        "section_hit_rate": round(float(metrics.get("section_hit_rate", 0.0)), 4),
        "chunk_hit_rate": round(float(metrics.get("chunk_hit_rate", 0.0)), 4),
        "table_hit_rate": round(float(metrics.get("table_hit_rate", 0.0)), 4),
        "figure_hit_rate": round(float(metrics.get("figure_hit_rate", 0.0)), 4),
        "numeric_exact_match": round(float(metrics.get("numeric_exact_match", 0.0)), 4),
        "citation_coverage": round(float(metrics.get("citation_coverage", 0.0)), 4),
        "unsupported_claim_rate": round(float(metrics.get("unsupported_claim_rate", 0.0)), 4),
        "answer_evidence_consistency": round(float(metrics.get("answer_evidence_consistency", 0.0)), 4),
        "citation_jump_validity": round(float(metrics.get("citation_jump_validity", 0.0)), 4),
        "answer_mode": answer_mode,
        "fallback_used": bool(fallback_used),
        "deprecated_branch_used": bool(deprecated_branch_used),
        "dimension_mismatch": bool(dimension_mismatch),
        "provider_error": provider_error,
        "timeout": bool(timeout),
        "latency_ms": int(latency_ms),
    }


def summarize_results(results: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for record in results:
        grouped[str(record.get("query_family") or "unknown")].append(record)

    def _summary(records: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
        latency_values = [float(item.get("latency_ms") or 0.0) for item in records]
        answer_modes = [str(item.get("answer_mode") or "") for item in records]
        cross_paper_hits = [1.0 for item in records if str(item.get("query_family") or "") == "cross_paper" and float(item.get("recall_at_10") or 0.0) > 0.0]
        return {
            "total": len(records),
            "recall_at_5": round(_mean(item.get("recall_at_5", 0.0) for item in records), 4),
            "recall_at_10": round(_mean(item.get("recall_at_10", 0.0) for item in records), 4),
            "mrr": round(_mean(item.get("mrr", 0.0) for item in records), 4),
            "ndcg_at_10": round(_mean(item.get("ndcg_at_10", 0.0) for item in records), 4),
            "paper_hit_rate": round(_mean(item.get("paper_hit_rate", 0.0) for item in records), 4),
            "section_hit_rate": round(_mean(item.get("section_hit_rate", 0.0) for item in records), 4),
            "chunk_hit_rate": round(_mean(item.get("chunk_hit_rate", 0.0) for item in records), 4),
            "table_hit_rate": round(_mean(item.get("table_hit_rate", 0.0) for item in records), 4),
            "figure_hit_rate": round(_mean(item.get("figure_hit_rate", 0.0) for item in records), 4),
            "numeric_exact_match": round(_mean(item.get("numeric_exact_match", 0.0) for item in records), 4),
            "citation_coverage": round(_mean(item.get("citation_coverage", 0.0) for item in records), 4),
            "unsupported_claim_rate": round(_mean(item.get("unsupported_claim_rate", 0.0) for item in records), 4),
            "answer_evidence_consistency": round(_mean(item.get("answer_evidence_consistency", 0.0) for item in records), 4),
            "citation_jump_validity": round(_mean(item.get("citation_jump_validity", 0.0) for item in records), 4),
            "answer_mode_accuracy": round(_mean(1.0 if item.get("answer_mode") == "full" else 0.0 for item in records), 4),
            "abstain_precision": round(_mean(item.get("abstain_precision", 1.0 if item.get("answer_mode") == "abstain" else 0.0) for item in records), 4),
            "latency_p50_ms": round(statistics.median(latency_values), 3) if latency_values else 0.0,
            "latency_p95_ms": round(_p95(latency_values), 3),
            "timeout_count": sum(1 for item in records if item.get("timeout") is True),
            "provider_error_count": sum(1 for item in records if item.get("provider_error")),
            "provider_hard_error_count": sum(1 for item in records if item.get("provider_error") and item.get("timeout") is not True),
            "fallback_used_count": sum(1 for item in records if item.get("fallback_used") is True),
            "deprecated_branch_used_count": sum(1 for item in records if item.get("deprecated_branch_used") is True),
            "dimension_mismatch_count": sum(1 for item in records if item.get("dimension_mismatch") is True),
            "cross_paper_coverage": round(sum(cross_paper_hits) / max(sum(1 for item in records if str(item.get("query_family") or "") == "cross_paper"), 1), 4),
            "answer_mode_distribution": {mode: answer_modes.count(mode) for mode in sorted(set(answer_modes))},
        }

    return {
        "overall": _summary(results),
        "by_query_family": {family: _summary(items) for family, items in sorted(grouped.items())},
    }


def decide_gate(overall: Dict[str, Any]) -> Dict[str, Any]:
    reasons: List[str] = []
    blocked = False

    hard_block_checks = {
        "fallback_used_count": int(overall.get("fallback_used_count") or 0) > 0,
        "deprecated_branch_used_count": int(overall.get("deprecated_branch_used_count") or 0) > 0,
        "dimension_mismatch_count": int(overall.get("dimension_mismatch_count") or 0) > 0,
        "provider_hard_error_count": int(overall.get("provider_hard_error_count") or 0) > 0,
        "citation_coverage": float(overall.get("citation_coverage") or 0.0) < 0.75,
        "unsupported_claim_rate": float(overall.get("unsupported_claim_rate") or 0.0) > 0.20,
        "answer_evidence_consistency": float(overall.get("answer_evidence_consistency") or 0.0) < 0.55,
    }
    for key, failed in hard_block_checks.items():
        if failed:
            blocked = True
            reasons.append(key)

    if blocked:
        return {"status": "BLOCKED", "reasons": reasons}

    pass_checks = [
        float(overall.get("citation_coverage") or 0.0) >= 0.85,
        float(overall.get("unsupported_claim_rate") or 0.0) <= 0.10,
        float(overall.get("answer_evidence_consistency") or 0.0) >= 0.65,
        float(overall.get("citation_jump_validity") or 0.0) >= 0.90,
        float(overall.get("recall_at_10") or 0.0) >= 0.85,
        float(overall.get("table_hit_rate") or 0.0) > 0.0,
        float(overall.get("figure_hit_rate") or 0.0) > 0.0,
        float(overall.get("cross_paper_coverage") or 0.0) > 0.0,
    ]
    if all(pass_checks):
        return {"status": "PASS", "reasons": []}

    conditional_checks = [
        float(overall.get("citation_coverage") or 0.0) >= 0.75,
        float(overall.get("unsupported_claim_rate") or 0.0) <= 0.20,
        float(overall.get("answer_evidence_consistency") or 0.0) >= 0.55,
        float(overall.get("recall_at_10") or 0.0) >= 0.75,
    ]
    if all(conditional_checks):
        weak_areas = []
        if float(overall.get("table_hit_rate") or 0.0) <= 0.0:
            weak_areas.append("table")
        if float(overall.get("figure_hit_rate") or 0.0) <= 0.0:
            weak_areas.append("figure")
        if float(overall.get("cross_paper_coverage") or 0.0) <= 0.0:
            weak_areas.append("cross_paper")
        return {"status": "CONDITIONAL", "reasons": weak_areas}

    return {"status": "BLOCKED", "reasons": ["thresholds_not_met"]}


def build_stage_comparison(stage_summaries: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    def _score(stage: str) -> Tuple[float, float, float]:
        overall = stage_summaries.get(stage, {}).get("overall", {})
        return (
            float(overall.get("citation_coverage") or 0.0),
            float(overall.get("answer_evidence_consistency") or 0.0),
            -float(overall.get("latency_p95_ms") or 0.0),
        )

    candidates = [stage for stage in ["raw", "rule", "llm"] if stage in stage_summaries]
    recommended = max(candidates, key=_score) if candidates else "raw"
    best_citation = max(candidates, key=lambda stage: float(stage_summaries.get(stage, {}).get("overall", {}).get("citation_coverage") or 0.0)) if candidates else "raw"
    best_latency = min(candidates, key=lambda stage: float(stage_summaries.get(stage, {}).get("overall", {}).get("latency_p95_ms") or 0.0)) if candidates else "raw"

    raw_cov = float(stage_summaries.get("raw", {}).get("overall", {}).get("citation_coverage") or 0.0)
    llm_cov = float(stage_summaries.get("llm", {}).get("overall", {}).get("citation_coverage") or 0.0)
    llm_pollution = llm_cov + 0.05 < raw_cov

    return {
        "recommended_default_stage": recommended,
        "recommendation_reason": f"{recommended} has the strongest citation/stability tradeoff under official thresholds.",
        "best_overall_stage": recommended,
        "best_citation_stage": best_citation,
        "best_latency_stage": best_latency,
        "has_material_stage_difference": any(abs(_score(stage)[0] - _score(recommended)[0]) >= 0.03 for stage in candidates if stage != recommended),
        "llm_retrieval_pollution_detected": llm_pollution,
        "raw": stage_summaries.get("raw", {}),
        "rule": stage_summaries.get("rule", {}),
        "llm": stage_summaries.get("llm", {}),
        "stage_delta": {
            "raw_vs_rule_citation": round(raw_cov - float(stage_summaries.get("rule", {}).get("overall", {}).get("citation_coverage") or 0.0), 4),
            "raw_vs_llm_citation": round(raw_cov - llm_cov, 4),
        },
    }


def _timeout_handler(signum: int, frame: Any) -> None:
    raise TimeoutError("query timed out")


def _with_timeout(timeout_seconds: int, fn: Callable[[], Dict[str, Any]]) -> Dict[str, Any]:
    if timeout_seconds <= 0:
        return fn()
    previous = signal.signal(signal.SIGALRM, _timeout_handler)
    try:
        signal.alarm(int(timeout_seconds))
        return fn()
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, previous)


def process_rows(
    *,
    rows: Sequence[GoldenRow],
    stage: str,
    runtime_profile: str,
    evaluator: Callable[[GoldenRow, str], Dict[str, Any]],
    partial_results_path: Path,
    failed_queries_path: Path,
    timeout_queries_path: Path,
    timeout_seconds: int,
    save_every: int,
    fail_fast: bool,
) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    failed_queries: List[Dict[str, Any]] = []
    timeout_queries: List[Dict[str, Any]] = []

    for index, row in enumerate(rows, start=1):
        started = time.perf_counter()
        try:
            payload = _with_timeout(timeout_seconds, lambda: evaluator(row, stage))
        except TimeoutError as exc:
            payload = {
                "query_id": row.query_id,
                "query_family": row.query_family,
                "stage": stage,
                "runtime_profile": runtime_profile,
                "status": "timeout",
                "timeout": True,
                "provider_error": None,
                "fallback_used": False,
                "deprecated_branch_used": False,
                "dimension_mismatch": False,
                "latency_ms": int((time.perf_counter() - started) * 1000),
            }
            timeout_queries.append(payload)
        except Exception as exc:  # noqa: BLE001
            payload = {
                "query_id": row.query_id,
                "query_family": row.query_family,
                "stage": stage,
                "runtime_profile": runtime_profile,
                "status": "error",
                "timeout": False,
                "provider_error": str(exc),
                "fallback_used": False,
                "deprecated_branch_used": False,
                "dimension_mismatch": False,
                "latency_ms": int((time.perf_counter() - started) * 1000),
            }
            failed_queries.append(payload)
            if fail_fast:
                append_jsonl(partial_results_path, payload)
                results.append(payload)
                persist_json_list(failed_queries_path, failed_queries)
                persist_json_list(timeout_queries_path, timeout_queries)
                break

        append_jsonl(partial_results_path, payload)
        results.append(payload)
        if payload.get("status") == "error":
            failed_queries.append(payload)
        if payload.get("status") == "timeout":
            timeout_queries.append(payload)

        if index % max(save_every, 1) == 0:
            persist_json_list(failed_queries_path, failed_queries)
            persist_json_list(timeout_queries_path, timeout_queries)

    persist_json_list(failed_queries_path, failed_queries)
    persist_json_list(timeout_queries_path, timeout_queries)
    return results


def select_regression_rows(rows: Sequence[GoldenRow], max_queries: int = 16) -> List[GoldenRow]:
    by_family: Dict[str, List[GoldenRow]] = defaultdict(list)
    for row in rows:
        by_family[row.query_family].append(row)

    selected: List[GoldenRow] = []
    families = ["fact", "method", "table", "figure", "numeric", "compare", "cross_paper", "hard"]
    for family in families:
        selected.extend(by_family.get(family, [])[:2])

    deduped: List[GoldenRow] = []
    seen: Set[str] = set()
    for row in selected:
        if row.query_id in seen:
            continue
        seen.add(row.query_id)
        deduped.append(row)
    return deduped[:max_queries]


def validate_runtime_profile(runtime_profile: str) -> None:
    if runtime_profile != RUNTIME_PROFILE:
        raise BenchmarkGuardError(f"EVAL_BLOCKED: runtime_profile must be {RUNTIME_PROFILE}")


def _build_citation(source: Dict[str, Any]) -> str:
    section = str(source.get("section") or f"Page {source.get('page_num')}")
    return f"[{source.get('paper_id')}, {section}]"


class OfficialRagEvaluator:
    def __init__(self, *, collection_suffix: str, milvus_host: str, milvus_port: int):
        from pymilvus import connections

        from app.core.model_gateway import create_embedding_provider
        from app.core.reranker.factory import get_reranker_service
        from app.core.citation_verifier import get_citation_verifier
        from app.core.claim_extractor import get_claim_extractor
        from app.core.claim_verifier import get_claim_verifier
        from app.core.abstention_policy import get_abstention_policy
        from app.utils.zhipu_client import ZhipuLLMClient

        self.collection_suffix = collection_suffix
        self.embedding_provider = create_embedding_provider("tongyi", EMBEDDING_MODEL)
        self.reranker = get_reranker_service()
        self.reranker.load_model()
        self.citation_verifier = get_citation_verifier()
        self.claim_extractor = get_claim_extractor()
        self.claim_verifier = get_claim_verifier()
        self.abstention_policy = get_abstention_policy()
        self.llm_client = ZhipuLLMClient(model=LLM_MODEL)
        self._connections = connections
        self._connections.connect(alias="v2_6_eval", host=milvus_host, port=milvus_port)

    def _collection(self, stage: str):
        from pymilvus import Collection

        collection_name = stage_collection_name(stage, self.collection_suffix)
        collection = Collection(collection_name, using="v2_6_eval")
        collection.load()
        return collection_name, collection

    @staticmethod
    def _collection_dim(collection: Any) -> int:
        for field in getattr(collection.schema, "fields", []):
            if getattr(field, "name", "") == "embedding":
                params = getattr(field, "params", {}) or {}
                if isinstance(params, dict) and params.get("dim") is not None:
                    return int(params.get("dim"))
                if hasattr(field, "dim") and getattr(field, "dim") is not None:
                    return int(getattr(field, "dim"))
        return 0

    async def generate_answer(self, *, row: GoldenRow, sources: List[Dict[str, Any]]) -> str:
        evidence_lines = []
        for source in sources[:5]:
            evidence_lines.append(f"- {_build_citation(source)} {str(source.get('anchor_text') or source.get('content_data') or '')[:300]}")
        prompt = "\n".join(
            [
                "You are evaluating official scholarly RAG.",
                "Answer only from evidence below.",
                "Every factual sentence must end with a citation in the exact format [paper_id, section].",
                "If evidence is insufficient, say so briefly with citations to the closest evidence.",
                f"Question: {row.query}",
                "Evidence:",
                *evidence_lines,
            ]
        )
        return await self.llm_client.simple_completion(prompt, max_tokens=400, temperature=0.1)

    def evaluate(self, row: GoldenRow, stage: str) -> Dict[str, Any]:
        collection_name, collection = self._collection(stage)
        started = time.perf_counter()

        query_vector = self.embedding_provider.embed_texts([row.query])[0]
        query_dim = len(query_vector)
        collection_dim = self._collection_dim(collection)
        dimension_mismatch = query_dim != collection_dim
        if dimension_mismatch:
            return build_result_record(
                row=row,
                stage=stage,
                collection=collection_name,
                runtime_profile=RUNTIME_PROFILE,
                retrieved_source_chunk_ids_top5=[],
                retrieved_paper_ids_top5=[],
                metrics={},
                answer_mode="abstain",
                fallback_used=False,
                deprecated_branch_used=False,
                dimension_mismatch=True,
                provider_error="query_dim != collection_dim",
                timeout=False,
                latency_ms=int((time.perf_counter() - started) * 1000),
            )

        search_output_fields = list(OFFICIAL_OUTPUT_FIELDS)
        if "source_chunk_id" not in search_output_fields:
            search_output_fields.insert(0, "source_chunk_id")

        expr = "indexable == true"
        results = collection.search(
            data=[query_vector],
            anns_field="embedding",
            param={"metric_type": "COSINE", "params": {"nprobe": 10}},
            limit=10,
            expr=expr,
            output_fields=search_output_fields,
        )

        raw_hits: List[Dict[str, Any]] = []
        for batch in results:
            for hit in batch:
                entity = hit.entity
                raw_hits.append(
                    {
                        "source_chunk_id": str(entity.get("source_chunk_id") or hit.id),
                        "source_id": str(entity.get("source_chunk_id") or hit.id),
                        "paper_id": str(entity.get("paper_id") or ""),
                        "page_num": entity.get("page_num"),
                        "content_type": str(entity.get("content_type") or "text"),
                        "section": str(entity.get("section") or "body"),
                        "anchor_text": str(entity.get("anchor_text") or entity.get("content_data") or ""),
                        "content_data": str(entity.get("content_data") or ""),
                        "score": max(0.0, min(1.0 - float(hit.distance), 1.0)),
                        "citation": f"[{str(entity.get('paper_id') or '')}, {str(entity.get('section') or 'body')}]",
                    }
                )

        documents = [hit.get("anchor_text") or hit.get("content_data") or "" for hit in raw_hits]
        reranked = self.reranker.rerank(row.query, documents, top_k=min(5, len(documents))) if documents else []
        reranked_hits: List[Dict[str, Any]] = []
        for ranked in reranked:
            rank = int(ranked.get("rank") or 0)
            if rank < len(raw_hits):
                reranked_hits.append(raw_hits[rank])
        if not reranked_hits:
            reranked_hits = raw_hits[:5]

        import asyncio

        try:
            answer = asyncio.run(self.generate_answer(row=row, sources=reranked_hits))
        except RuntimeError:
            loop = asyncio.new_event_loop()
            try:
                answer = loop.run_until_complete(self.generate_answer(row=row, sources=reranked_hits))
            finally:
                loop.close()

        citation_report = self.citation_verifier.verify(answer, reranked_hits)
        claims = self.claim_extractor.extract(answer)
        claim_results = self.claim_verifier.verify(claims, reranked_hits)
        claim_report = self.claim_verifier.build_report(claim_results)
        answer_evidence_consistency = round(
            (int(claim_report.get("supportedClaimCount") or 0) + 0.5 * int(claim_report.get("weaklySupportedClaimCount") or 0))
            / max(int(claim_report.get("totalClaims") or 0), 1),
            4,
        )
        abstain = self.abstention_policy.decide(
            claim_report=claim_report,
            citation_report=citation_report,
            answer_evidence_consistency=answer_evidence_consistency,
        )
        metrics = compute_retrieval_metrics(
            row=row,
            retrieved_hits=reranked_hits,
            answer_text=answer,
            citation_report=citation_report,
            claim_report=claim_report,
            answer_evidence_consistency=answer_evidence_consistency,
            answer_mode=abstain.answer_mode.value,
        )

        retrieved_source_chunk_ids_top5 = _ordered_unique([str(hit.get("source_chunk_id") or hit.get("source_id") or "") for hit in reranked_hits[:5]])
        retrieved_paper_ids_top5 = _ordered_unique([str(hit.get("paper_id") or "") for hit in reranked_hits[:5]])
        record = build_result_record(
            row=row,
            stage=stage,
            collection=collection_name,
            runtime_profile=RUNTIME_PROFILE,
            retrieved_source_chunk_ids_top5=retrieved_source_chunk_ids_top5,
            retrieved_paper_ids_top5=retrieved_paper_ids_top5,
            metrics=metrics,
            answer_mode=abstain.answer_mode.value,
            fallback_used=False,
            deprecated_branch_used=False,
            dimension_mismatch=False,
            provider_error=None,
            timeout=False,
            latency_ms=int((time.perf_counter() - started) * 1000),
        )
        record["_answer"] = answer
        record["_citation_report"] = citation_report
        record["_claim_report"] = claim_report
        return record


def write_dashboard(path_json: Path, path_md: Path, *, mode: str, stage_summaries: Dict[str, Dict[str, Any]], gate: Optional[Dict[str, Any]]) -> None:
    payload = {
        "mode": mode,
        "updated_at": int(time.time()),
        "stages": stage_summaries,
        "gate": gate,
    }
    write_json(path_json, payload)

    lines = [f"- mode: {mode}", f"- updated_at: {payload['updated_at']}", ""]
    lines.extend(["| stage | total | citation_coverage | recall_at_10 | p95_ms | status |", "|---|---:|---:|---:|---:|---|"])
    for stage, summary in stage_summaries.items():
        overall = summary.get("overall", {})
        lines.append(
            f"| {stage} | {overall.get('total', 0)} | {overall.get('citation_coverage', 0.0)} | {overall.get('recall_at_10', 0.0)} | {overall.get('latency_p95_ms', 0.0)} | {summary.get('gate', {}).get('status', 'PENDING')} |"
        )
    if gate:
        lines.extend(["", f"- final_gate: {gate.get('status')}", f"- reasons: {', '.join(gate.get('reasons', []))}"])
    write_markdown(path_md, "Official RAG Dashboard", lines)


def write_stage_report(path: Path, title: str, summary: Dict[str, Any]) -> None:
    overall = summary.get("overall", {})
    lines = [
        f"- total: {overall.get('total', 0)}",
        f"- citation_coverage: {overall.get('citation_coverage', 0.0)}",
        f"- unsupported_claim_rate: {overall.get('unsupported_claim_rate', 0.0)}",
        f"- answer_evidence_consistency: {overall.get('answer_evidence_consistency', 0.0)}",
        f"- recall_at_10: {overall.get('recall_at_10', 0.0)}",
        f"- latency_p95_ms: {overall.get('latency_p95_ms', 0.0)}",
        "",
        "| family | total | citation_coverage | recall_at_10 | unsupported_claim_rate |",
        "|---|---:|---:|---:|---:|",
    ]
    for family, family_summary in summary.get("by_query_family", {}).items():
        lines.append(
            f"| {family} | {family_summary.get('total', 0)} | {family_summary.get('citation_coverage', 0.0)} | {family_summary.get('recall_at_10', 0.0)} | {family_summary.get('unsupported_claim_rate', 0.0)} |"
        )
    write_markdown(path, title, lines)


def validate_step5_inputs() -> None:
    if not DEFAULT_CONSISTENCY_PATH.exists() or not DEFAULT_FAMILY_STATS_PATH.exists() or not DEFAULT_GOLDEN_PATH.exists():
        raise BenchmarkGuardError("EVAL_BLOCKED: Step5 outputs are incomplete")
    consistency = read_json(DEFAULT_CONSISTENCY_PATH)
    if str(consistency.get("status") or "") != "PASS":
        raise BenchmarkGuardError("EVAL_BLOCKED: Step5 golden consistency is not PASS")


def _sanitize_for_json(record: Dict[str, Any]) -> Dict[str, Any]:
    return {key: value for key, value in record.items() if not str(key).startswith("_")}


def run_stage(
    *,
    evaluator: OfficialRagEvaluator,
    rows: Sequence[GoldenRow],
    stage: str,
    runtime_profile: str,
    partial_results_path: Path,
    failed_queries_path: Path,
    timeout_queries_path: Path,
    timeout_seconds: int,
    save_every: int,
    fail_fast: bool,
    resume: bool,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    completed_keys = load_completed_result_keys(partial_results_path) if resume else set()
    pending_rows = filter_pending_rows(rows, stage, completed_keys)

    def _evaluate(row: GoldenRow, current_stage: str) -> Dict[str, Any]:
        return _sanitize_for_json(evaluator.evaluate(row, current_stage))

    processed = process_rows(
        rows=pending_rows,
        stage=stage,
        runtime_profile=runtime_profile,
        evaluator=_evaluate,
        partial_results_path=partial_results_path,
        failed_queries_path=failed_queries_path,
        timeout_queries_path=timeout_queries_path,
        timeout_seconds=timeout_seconds,
        save_every=save_every,
        fail_fast=fail_fast,
    )

    prior_records: List[Dict[str, Any]] = []
    if resume and partial_results_path.exists():
        for line in partial_results_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            payload = json.loads(line)
            if payload.get("stage") == stage:
                prior_records.append(payload)
    else:
        prior_records = processed

    stage_records = [record for record in prior_records if record.get("stage") == stage]
    summary = summarize_results(stage_records)
    return stage_records, summary


def render_final_report(
    *,
    golden_path: Path,
    collection_suffix: str,
    regression_summary: Optional[Dict[str, Any]],
    regression_gate: Dict[str, Any],
    official_stage_summaries: Dict[str, Dict[str, Any]],
    official_gate: Optional[Dict[str, Any]],
    comparison: Optional[Dict[str, Any]],
    failed_queries: Sequence[Dict[str, Any]],
    timeout_queries: Sequence[Dict[str, Any]],
) -> None:
    lines = [
        "## Inputs",
        "",
        f"- golden_file: {golden_path}",
        f"- consistency_file: {DEFAULT_CONSISTENCY_PATH}",
        f"- family_stats_file: {DEFAULT_FAMILY_STATS_PATH}",
        f"- runtime_profile: {RUNTIME_PROFILE}",
        f"- collection_suffix: {collection_suffix}",
        f"- raw_collection: {stage_collection_name('raw', collection_suffix)}",
        f"- rule_collection: {stage_collection_name('rule', collection_suffix)}",
        f"- llm_collection: {stage_collection_name('llm', collection_suffix)}",
        "",
        "## Regression 16x3",
        "",
        f"- status: {regression_gate.get('status')}",
        f"- reasons: {', '.join(regression_gate.get('reasons', []))}",
    ]
    if regression_summary:
        overall = regression_summary.get("overall", {})
        lines.extend(
            [
                f"- total: {overall.get('total', 0)}",
                f"- citation_coverage: {overall.get('citation_coverage', 0.0)}",
                f"- unsupported_claim_rate: {overall.get('unsupported_claim_rate', 0.0)}",
                f"- answer_evidence_consistency: {overall.get('answer_evidence_consistency', 0.0)}",
                f"- recall_at_10: {overall.get('recall_at_10', 0.0)}",
            ]
        )

    lines.extend(["", "## Official Stage Results", ""])
    for stage in ["raw", "rule", "llm"]:
        summary = official_stage_summaries.get(stage)
        if not summary:
            continue
        overall = summary.get("overall", {})
        lines.extend(
            [
                f"### {stage}",
                "",
                f"- total: {overall.get('total', 0)}",
                f"- citation_coverage: {overall.get('citation_coverage', 0.0)}",
                f"- unsupported_claim_rate: {overall.get('unsupported_claim_rate', 0.0)}",
                f"- answer_evidence_consistency: {overall.get('answer_evidence_consistency', 0.0)}",
                f"- recall_at_10: {overall.get('recall_at_10', 0.0)}",
                f"- latency_p95_ms: {overall.get('latency_p95_ms', 0.0)}",
                "",
            ]
        )

    lines.extend(["## Comparison", ""])
    if comparison:
        lines.extend(
            [
                f"- recommended_default_stage: {comparison.get('recommended_default_stage')}",
                f"- recommendation_reason: {comparison.get('recommendation_reason')}",
                f"- llm_retrieval_pollution_detected: {comparison.get('llm_retrieval_pollution_detected')}",
            ]
        )

    lines.extend(["", "## Failures", ""])
    lines.append(f"- failed_queries: {len(failed_queries)}")
    lines.append(f"- timeout_queries: {len(timeout_queries)}")

    lines.extend(["", "## Final Gate", ""])
    if official_gate:
        lines.append(f"- Official 64/80x3: {official_gate.get('status')}")
    else:
        lines.append("- Official 64/80x3: BLOCKED")
    lines.append(f"- Default stage: {(comparison or {}).get('recommended_default_stage', 'raw')}")
    api_allowed = "ALLOWED" if official_gate and official_gate.get("status") in {"PASS", "CONDITIONAL"} else "NOT_ALLOWED"
    step7_allowed = "ALLOWED" if official_gate and official_gate.get("status") == "PASS" else "NOT_ALLOWED"
    lines.append(f"- API flash as official RAG: {api_allowed}")
    lines.append(f"- Step7 Product Integration: {step7_allowed}")

    write_markdown(DOC_REPORT, "Official RAG Evaluation v2.6", lines)


def main() -> int:
    args = parse_args()
    fail_fast = _bool_arg(args.fail_fast)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    DOC_REPORT.parent.mkdir(parents=True, exist_ok=True)

    validate_runtime_profile(args.runtime_profile)
    validate_step5_inputs()

    golden_path = Path(args.golden_path)
    rows = load_golden_rows(golden_path, mode="official")
    if args.mode == "regression":
        rows = select_regression_rows(rows, max_queries=args.max_queries or 16)
    elif args.max_queries:
        rows = list(rows[: args.max_queries])

    evaluator = OfficialRagEvaluator(
        collection_suffix=args.collection_suffix,
        milvus_host=args.milvus_host,
        milvus_port=args.milvus_port,
    )

    dashboard_json = OUTPUT_DIR / "official_rag_dashboard.json"
    dashboard_md = OUTPUT_DIR / "official_rag_dashboard.md"
    partial_results_path = OUTPUT_DIR / "partial_results.jsonl"
    failed_queries_path = OUTPUT_DIR / "failed_queries.json"
    timeout_queries_path = OUTPUT_DIR / "timeout_queries.json"

    stages = [args.stage] if args.stage != "all" else list(STAGES)
    stage_summaries: Dict[str, Dict[str, Any]] = {}
    stage_records_map: Dict[str, List[Dict[str, Any]]] = {}

    regression_gate = {"status": "BLOCKED", "reasons": ["not_run"]}
    regression_summary: Optional[Dict[str, Any]] = None

    if args.mode == "regression":
        regression_records: List[Dict[str, Any]] = []
        for stage in stages:
            stage_records, stage_summary = run_stage(
                evaluator=evaluator,
                rows=rows,
                stage=stage,
                runtime_profile=args.runtime_profile,
                partial_results_path=partial_results_path,
                failed_queries_path=failed_queries_path,
                timeout_queries_path=timeout_queries_path,
                timeout_seconds=args.timeout_per_query_seconds,
                save_every=args.save_every,
                fail_fast=fail_fast,
                resume=args.resume,
            )
            stage_records_map[stage] = stage_records
            stage_summaries[stage] = stage_summary
            regression_records.extend(stage_records)

        regression_summary = summarize_results(regression_records)
        overall = regression_summary.get("overall", {})
        reasons: List[str] = []
        expected_total = len(rows) * len(stages)
        if int(overall.get("total") or 0) != expected_total:
            reasons.append("total")
        if int(overall.get("fallback_used_count") or 0) != 0:
            reasons.append("fallback_used")
        if int(overall.get("deprecated_branch_used_count") or 0) != 0:
            reasons.append("deprecated_branch_used")
        if int(overall.get("dimension_mismatch_count") or 0) != 0:
            reasons.append("dimension_mismatch")
        if int(overall.get("provider_hard_error_count") or 0) != 0:
            reasons.append("provider_hard_error")
        if float(overall.get("latency_p95_ms") or 0.0) >= 120000.0:
            reasons.append("p95_latency")
        if float(overall.get("citation_coverage") or 0.0) < 0.75:
            reasons.append("citation_coverage")
        if float(overall.get("unsupported_claim_rate") or 0.0) > 0.20:
            reasons.append("unsupported_claim_rate")

        regression_gate = {"status": "PASS" if not reasons else "BLOCKED", "reasons": reasons}
        stage_summaries["regression"] = {**regression_summary, "gate": regression_gate}
        write_dashboard(dashboard_json, dashboard_md, mode="regression", stage_summaries=stage_summaries, gate=regression_gate)
        write_json(OUTPUT_DIR / "api_flash_16x3_regression_results.json", regression_records)
        write_stage_report(OUTPUT_DIR / "api_flash_16x3_regression_report.md", "API Flash 16x3 Regression Report", regression_summary)

        if regression_gate["status"] != "PASS":
            write_markdown(
                OUTPUT_DIR / "v2_6_regression_blocked_report.md",
                "v2.6 Regression Blocked",
                [f"- reasons: {', '.join(regression_gate['reasons'])}", "- official_run_allowed: false"],
            )
            render_final_report(
                golden_path=golden_path,
                collection_suffix=args.collection_suffix,
                regression_summary=regression_summary,
                regression_gate=regression_gate,
                official_stage_summaries={},
                official_gate=None,
                comparison=None,
                failed_queries=read_json(failed_queries_path) if failed_queries_path.exists() else [],
                timeout_queries=read_json(timeout_queries_path) if timeout_queries_path.exists() else [],
            )
            print(json.dumps({"status": "BLOCKED", "reason": "regression_failed"}, ensure_ascii=False, indent=2))
            return 1

    official_stage_summaries: Dict[str, Dict[str, Any]] = {}
    if args.mode == "official":
        if args.stage == "all":
            stages = ["raw", "rule", "llm"]
        for stage in stages:
            partial_path = OUTPUT_DIR / "partial_results.jsonl"
            failed_path = OUTPUT_DIR / "failed_queries.json"
            timeout_path = OUTPUT_DIR / "timeout_queries.json"
            stage_records, stage_summary = run_stage(
                evaluator=evaluator,
                rows=rows,
                stage=stage,
                runtime_profile=args.runtime_profile,
                partial_results_path=partial_path,
                failed_queries_path=failed_path,
                timeout_queries_path=timeout_path,
                timeout_seconds=args.timeout_per_query_seconds,
                save_every=args.save_every,
                fail_fast=fail_fast,
                resume=args.resume,
            )
            official_stage_summaries[stage] = stage_summary
            stage_records_map[stage] = stage_records
            write_json(OUTPUT_DIR / f"api_flash_official_{stage}_results.json", stage_records)

        comparison = build_stage_comparison(official_stage_summaries)
        overall_stage = comparison.get("recommended_default_stage") or "raw"
        official_gate = decide_gate(official_stage_summaries.get(overall_stage, {}).get("overall", {}))

        write_json(OUTPUT_DIR / "api_flash_official_comparison.json", comparison)
        write_dashboard(dashboard_json, dashboard_md, mode="official", stage_summaries=official_stage_summaries, gate=official_gate)
        write_stage_report(
            OUTPUT_DIR / "api_flash_official_report.md",
            "API Flash Official Report",
            {"overall": official_stage_summaries.get(overall_stage, {}).get("overall", {}), "by_query_family": official_stage_summaries.get(overall_stage, {}).get("by_query_family", {})},
        )
        render_final_report(
            golden_path=golden_path,
            collection_suffix=args.collection_suffix,
            regression_summary=regression_summary,
            regression_gate=regression_gate,
            official_stage_summaries=official_stage_summaries,
            official_gate=official_gate,
            comparison=comparison,
            failed_queries=read_json(failed_queries_path) if failed_queries_path.exists() else [],
            timeout_queries=read_json(timeout_queries_path) if timeout_queries_path.exists() else [],
        )
        print(json.dumps({"status": official_gate["status"], "recommended_default_stage": comparison["recommended_default_stage"]}, ensure_ascii=False, indent=2))
        return 0 if official_gate["status"] in {"PASS", "CONDITIONAL"} else 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())