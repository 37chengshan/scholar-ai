"""Phase 6 Evaluation Service — filesystem-backed benchmark artifact reader and gate."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


PHASE6_ROOT = Path(__file__).resolve().parents[2] / "artifacts" / "benchmarks" / "phase6"

PHASE6_MIN_PAPER_COUNT = 50
PHASE6_MIN_QUERY_COUNT = 128
PHASE6_MAX_FALLBACK_USED_COUNT = 5
PHASE6_REQUIRED_QUERY_FAMILIES = {
    "single_fact",
    "method",
    "experiment_result",
    "table",
    "figure_caption",
    "multi_paper_compare",
    "kb_global",
    "no_answer",
}
PHASE6_REQUIRED_RUN_FILES = (
    "meta.json",
    "dashboard_summary.json",
    "retrieval.json",
    "answer_quality.json",
    "citation_jump.json",
)
PHASE6_NON_REGRESSION_METRICS = (
    "retrieval_hit_rate",
    "answer_supported_rate",
    "groundedness",
    "citation_jump_valid_rate",
    "abstain_precision",
    "recall_at_5",
)


def _phase6_root() -> Path:
    return PHASE6_ROOT


def _runs_dir() -> Path:
    return _phase6_root() / "runs"


def _run_dir(run_id: str) -> Path:
    return _runs_dir() / run_id


def _corpus_path() -> Path:
    return _phase6_root() / "corpus.json"


def _load_json(path: Path) -> Optional[Any]:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


@dataclass
class NormalizedMetrics:
    retrieval_hit_rate: float = 0.0
    recall_at_5: float = 0.0
    recall_at_10: float = 0.0
    rerank_gain: float = 0.0
    citation_jump_valid_rate: float = 0.0
    answer_supported_rate: float = 0.0
    groundedness: float = 0.0
    abstain_precision: float = 0.0
    fallback_used_count: int = 0
    latency_p50: float = 0.0
    latency_p95: float = 0.0
    cost_per_answer: float = 0.0
    cost_per_answer_present: bool = True
    overall_verdict: str = "UNKNOWN"
    gate_failures: List[str] = field(default_factory=list)


PHASE6_THRESHOLDS: Dict[str, Any] = {
    "retrieval_hit_rate": {"min": 0.80},
    "recall_at_5": {"min": 0.75},
    "citation_jump_valid_rate": {"min": 0.85},
    "answer_supported_rate": {"min": 0.80},
    "groundedness": {"min": 0.70},
    "abstain_precision": {"min": 0.80},
    "latency_p95": {"max": 8.0},
}


def _f(src: Dict[str, Any], key: str, default: float = 0.0) -> float:
    value = src.get(key, default)
    return float(value) if value is not None else default


def _i(src: Dict[str, Any], key: str, default: int = 0) -> int:
    value = src.get(key, default)
    return int(value) if value is not None else default


def _evaluate_gate(metrics: NormalizedMetrics) -> tuple[str, list[str]]:
    failures: list[str] = []
    for key, bounds in PHASE6_THRESHOLDS.items():
        value = getattr(metrics, key, None)
        if value is None:
            continue
        if "min" in bounds and float(value) < bounds["min"]:
            failures.append(f"{key}={value:.3f} below min={bounds['min']}")
        if "max" in bounds and float(value) > bounds["max"]:
            failures.append(f"{key}={value:.3f} above max={bounds['max']}")

    if metrics.fallback_used_count > PHASE6_MAX_FALLBACK_USED_COUNT:
        failures.append(
            f"fallback_used_count={metrics.fallback_used_count} above max={PHASE6_MAX_FALLBACK_USED_COUNT}"
        )
    if not metrics.cost_per_answer_present:
        failures.append("cost_per_answer missing from run summary")

    verdict = "PASS" if not failures else "FAIL"
    return verdict, failures


def _normalize_run(run_id: str, meta: Dict[str, Any]) -> NormalizedMetrics:
    run_dir = _run_dir(run_id)
    summary = _load_json(run_dir / "dashboard_summary.json") or {}
    retrieval = _load_json(run_dir / "retrieval.json") or {}
    answer_quality = _load_json(run_dir / "answer_quality.json") or {}
    citation_jump = _load_json(run_dir / "citation_jump.json") or {}
    top_k = summary.get("top_k_recall") or retrieval.get("top_k_recall") or {}

    metrics = NormalizedMetrics(
        retrieval_hit_rate=_f(summary, "retrieval_hit_rate") or _f(retrieval, "retrieval_hit_rate"),
        recall_at_5=_f(top_k, "recall_at_5") if isinstance(top_k, dict) else _f(retrieval, "recall_at_5"),
        recall_at_10=_f(top_k, "recall_at_10") if isinstance(top_k, dict) else _f(retrieval, "recall_at_10"),
        rerank_gain=_f(summary, "rerank_gain"),
        citation_jump_valid_rate=_f(summary, "citation_jump_valid_rate") or _f(citation_jump, "citation_jump_valid_rate"),
        answer_supported_rate=_f(summary, "answer_supported_rate") or _f(answer_quality, "answer_supported_rate"),
        groundedness=_f(summary, "groundedness") or _f(answer_quality, "groundedness"),
        abstain_precision=_f(summary, "abstain_precision") or _f(answer_quality, "abstain_precision"),
        fallback_used_count=_i(summary, "fallback_used_count"),
        latency_p50=_f(summary, "latency_p50"),
        latency_p95=_f(summary, "latency_p95"),
        cost_per_answer=_f(summary, "cost_per_answer"),
        cost_per_answer_present="cost_per_answer" in summary,
    )

    verdict, failures = _evaluate_gate(metrics)
    metrics.overall_verdict = verdict
    metrics.gate_failures = failures
    return metrics


def _metric_from_detail(detail: Dict[str, Any], key: str) -> float:
    metrics = detail.get("metrics", {})
    if key == "recall_at_5":
        return float((metrics.get("top_k_recall") or {}).get("recall_at_5", 0.0))
    return float(metrics.get(key, 0.0))


def _validate_corpus(corpus: Dict[str, Any] | None) -> list[str]:
    if not isinstance(corpus, dict):
        return ["phase6 corpus.json missing or unreadable"]

    failures: list[str] = []
    version = corpus.get("version") or corpus.get("dataset_version")
    if not version:
        failures.append("phase6 corpus version missing")

    paper_count = int(corpus.get("paper_count") or corpus.get("total_papers") or 0)
    query_count = int(corpus.get("query_count") or corpus.get("total_queries") or 0)
    if paper_count < PHASE6_MIN_PAPER_COUNT:
        failures.append(
            f"paper_count={paper_count} below min={PHASE6_MIN_PAPER_COUNT}"
        )
    if query_count < PHASE6_MIN_QUERY_COUNT:
        failures.append(
            f"query_count={query_count} below min={PHASE6_MIN_QUERY_COUNT}"
        )

    families = {
        str(family)
        for family in (corpus.get("query_families") or [])
        if str(family).strip()
    }
    missing_families = sorted(PHASE6_REQUIRED_QUERY_FAMILIES - families)
    if missing_families:
        failures.append(f"query_families missing required entries: {missing_families}")

    queries = corpus.get("queries")
    if not isinstance(queries, list):
        failures.append("queries[] missing from frozen corpus")
        return failures

    if len(queries) < query_count:
        failures.append(
            f"queries[] length={len(queries)} below declared query_count={query_count}"
        )

    actual_families = {
        str(query.get("family"))
        for query in queries
        if isinstance(query, dict) and str(query.get("family") or "").strip()
    }
    missing_actual_families = sorted(PHASE6_REQUIRED_QUERY_FAMILIES - actual_families)
    if missing_actual_families:
        failures.append(
            f"queries[] missing required family coverage: {missing_actual_families}"
        )

    return failures


def _validate_run_artifacts(run_id: str) -> list[str]:
    run_dir = _run_dir(run_id)
    failures: list[str] = []
    for filename in PHASE6_REQUIRED_RUN_FILES:
        if not (run_dir / filename).exists():
            failures.append(f"{run_id} missing artifact: {filename}")
    return failures


def _select_offline_baseline_and_candidate() -> tuple[Optional[str], Optional[str], list[str]]:
    offline_runs = [run for run in list_run_summaries() if run.get("mode") == "offline"]
    if not offline_runs:
        return None, None, ["no offline runs found in manifest"]

    candidate_run_id = str(offline_runs[0].get("run_id") or "")
    if len(offline_runs) < 2:
        return None, candidate_run_id or None, ["offline baseline and candidate runs are both required"]

    baseline_run_id = str(offline_runs[1].get("run_id") or "")
    if not baseline_run_id:
        return None, candidate_run_id or None, ["baseline run_id missing from manifest"]
    if not candidate_run_id:
        return baseline_run_id, None, ["candidate run_id missing from manifest"]
    return baseline_run_id, candidate_run_id, []


def load_corpus() -> Dict[str, Any]:
    corpus = _load_json(_corpus_path())
    return corpus if isinstance(corpus, dict) else {}


def load_manifest() -> Dict[str, Any]:
    manifest = _load_json(_phase6_root() / "manifest.json")
    return manifest if isinstance(manifest, dict) else {"runs": []}


def list_run_summaries() -> List[Dict[str, Any]]:
    manifest = load_manifest()
    runs = manifest.get("runs", [])
    return list(reversed(runs)) if isinstance(runs, list) else []


def get_latest_offline_run_id() -> Optional[str]:
    for run in list_run_summaries():
        if run.get("mode") == "offline":
            run_id = run.get("run_id")
            return str(run_id) if run_id else None
    return None


def get_run_detail(run_id: str) -> Optional[Dict[str, Any]]:
    meta = _load_json(_run_dir(run_id) / "meta.json")
    if not isinstance(meta, dict):
        return None

    metrics = _normalize_run(run_id, meta)
    retrieval = _load_json(_run_dir(run_id) / "retrieval.json") or {}
    answer_quality = _load_json(_run_dir(run_id) / "answer_quality.json") or {}
    citation_jump = _load_json(_run_dir(run_id) / "citation_jump.json") or {}

    return {
        "run_id": run_id,
        "meta": meta,
        "metrics": {
            "retrieval_hit_rate": metrics.retrieval_hit_rate,
            "top_k_recall": {"recall_at_5": metrics.recall_at_5, "recall_at_10": metrics.recall_at_10},
            "rerank_gain": metrics.rerank_gain,
            "citation_jump_valid_rate": metrics.citation_jump_valid_rate,
            "answer_supported_rate": metrics.answer_supported_rate,
            "groundedness": metrics.groundedness,
            "abstain_precision": metrics.abstain_precision,
            "fallback_used_count": metrics.fallback_used_count,
            "latency_p50": metrics.latency_p50,
            "latency_p95": metrics.latency_p95,
            "cost_per_answer": metrics.cost_per_answer,
            "overall_verdict": metrics.overall_verdict,
            "gate_failures": metrics.gate_failures,
        },
        "by_family": {
            "retrieval": retrieval.get("by_family", {}),
            "answer_quality": answer_quality.get("by_family", {}),
        },
        "citation_jump_detail": {
            "total_checked": citation_jump.get("total_citations_checked", 0),
            "valid": citation_jump.get("valid_citations", 0),
            "invalid": citation_jump.get("invalid_citations", 0),
            "invalid_reasons": citation_jump.get("invalid_reasons", {}),
        },
        "artifact_failures": _validate_run_artifacts(run_id),
    }


def get_overview() -> Dict[str, Any]:
    runs = list_run_summaries()
    passed, gate = run_offline_gate()
    latest_gate = None
    if gate.get("run_id"):
        latest_gate = {
            "run_id": gate.get("run_id"),
            "verdict": gate.get("verdict", "FAIL" if not passed else "PASS"),
            "gate_failures": gate.get("gate_failures", []),
            "metrics": gate.get("metrics", {}),
        }

    return {
        "latest_offline_gate": latest_gate,
        "run_count": len(runs),
        "offline_count": sum(1 for run in runs if run.get("mode") == "offline"),
        "online_count": sum(1 for run in runs if run.get("mode") == "online"),
        "recent_runs": runs[:5],
    }


def compute_diff(base_run_id: str, candidate_run_id: str) -> Optional[Dict[str, Any]]:
    base_detail = get_run_detail(base_run_id)
    candidate_detail = get_run_detail(candidate_run_id)
    if base_detail is None or candidate_detail is None:
        return None

    scalar_keys = [
        "retrieval_hit_rate",
        "recall_at_5",
        "recall_at_10",
        "rerank_gain",
        "citation_jump_valid_rate",
        "answer_supported_rate",
        "groundedness",
        "abstain_precision",
        "latency_p50",
        "latency_p95",
        "cost_per_answer",
    ]

    deltas: Dict[str, Any] = {}
    for key in scalar_keys:
        base_val = _metric_from_detail(base_detail, key)
        candidate_val = _metric_from_detail(candidate_detail, key)
        delta = round(candidate_val - base_val, 4)
        lower_is_better = key in {"latency_p50", "latency_p95", "cost_per_answer"}
        if lower_is_better:
            status = "improved" if delta < 0 else ("regressed" if delta > 0 else "unchanged")
        else:
            status = "improved" if delta > 0 else ("regressed" if delta < 0 else "unchanged")
        deltas[key] = {
            "base": base_val,
            "candidate": candidate_val,
            "delta": delta,
            "status": status,
        }

    fallback_delta = (
        int(candidate_detail["metrics"].get("fallback_used_count", 0))
        - int(base_detail["metrics"].get("fallback_used_count", 0))
    )

    non_regression_failures = [
        key for key in PHASE6_NON_REGRESSION_METRICS
        if deltas.get(key, {}).get("status") == "regressed"
    ]
    latency_regression_requires_justification = (
        deltas["latency_p95"]["status"] == "regressed"
        and candidate_detail["metrics"].get("latency_p95", 0.0) <= PHASE6_THRESHOLDS["latency_p95"]["max"]
    )

    return {
        "base_run_id": base_run_id,
        "candidate_run_id": candidate_run_id,
        "base_verdict": base_detail["metrics"]["overall_verdict"],
        "candidate_verdict": candidate_detail["metrics"]["overall_verdict"],
        "deltas": deltas,
        "fallback_used_count_delta": fallback_delta,
        "summary": {
            "improved": sum(1 for delta in deltas.values() if delta["status"] == "improved"),
            "regressed": sum(1 for delta in deltas.values() if delta["status"] == "regressed"),
            "unchanged": sum(1 for delta in deltas.values() if delta["status"] == "unchanged"),
        },
        "non_regression_failures": non_regression_failures,
        "latency_regression_requires_justification": latency_regression_requires_justification,
    }


def run_offline_gate() -> tuple[bool, Dict[str, Any]]:
    corpus_failures = _validate_corpus(load_corpus())
    baseline_run_id, candidate_run_id, manifest_failures = _select_offline_baseline_and_candidate()
    run_id = candidate_run_id or get_latest_offline_run_id()

    candidate_detail = get_run_detail(run_id) if run_id else None
    metrics = candidate_detail["metrics"] if candidate_detail else {}

    failures = list(corpus_failures)
    failures.extend(manifest_failures)

    if baseline_run_id:
        failures.extend(_validate_run_artifacts(baseline_run_id))
    if run_id:
        failures.extend(_validate_run_artifacts(run_id))

    if candidate_detail is None:
        failures.append("candidate run artifacts missing or unreadable")
    else:
        failures.extend(candidate_detail.get("artifact_failures", []))
        failures.extend(metrics.get("gate_failures", []))

    diff = None
    if baseline_run_id and run_id:
        diff = compute_diff(baseline_run_id, run_id)
        diff_artifact_path = _run_dir(run_id) / "diff_from_baseline.json"
        if not diff_artifact_path.exists():
            failures.append(f"{run_id} missing artifact: diff_from_baseline.json")
        if diff is None:
            failures.append("candidate vs baseline diff could not be computed")
        else:
            failures.extend(
                [f"non_regression_failed:{metric}" for metric in diff.get("non_regression_failures", [])]
            )

    deduped_failures = list(dict.fromkeys(failures))
    verdict = "PASS" if not deduped_failures and metrics.get("overall_verdict") == "PASS" else "FAIL"

    return verdict == "PASS", {
        "run_id": run_id,
        "baseline_run_id": baseline_run_id,
        "candidate_run_id": run_id,
        "verdict": verdict,
        "gate_failures": deduped_failures,
        "metrics": metrics,
        "diff": diff,
    }
