#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Any


VERDICT_PASS = "pass"
VERDICT_WARN = "warn"
VERDICT_FAIL = "fail"
VERDICT_EXPERIMENT_ONLY = "experiment-only"
VERDICT_CLASSES = (
    VERDICT_PASS,
    VERDICT_WARN,
    VERDICT_FAIL,
    VERDICT_EXPERIMENT_ONLY,
)
CASE_SOURCES = {"academic_public", "academic_blind", "workflow"}
REQUIRED_ENTRY_FIELDS = (
    "case_id",
    "case_source",
    "dataset_version",
    "task_family",
    "execution_mode",
    "truthfulness_report_summary",
    "retrieval_plane_policy",
    "degraded_conditions",
    "citation_coverage",
    "unsupported_claim_rate",
    "total_latency_ms",
    "cost_estimate",
    "runtime_truth",
    "mode_parity_with_baseline",
)
THRESHOLD_DEFAULTS = {
    "max_unsupported_regression": 0.03,
    "max_citation_regression": 0.0,
    "max_latency_ratio_regression": 0.15,
    "max_cost_ratio_regression": 0.20,
    "max_degraded_rate_regression": 0.05,
    "max_workflow_success_rate_regression": 0.05,
}
WORKFLOW_SUCCESS_STATES = {"pass", "partial"}


@dataclass(frozen=True)
class ThresholdPolicy:
    max_unsupported_regression: float = 0.03
    max_citation_regression: float = 0.0
    max_latency_ratio_regression: float = 0.15
    max_cost_ratio_regression: float = 0.20
    max_degraded_rate_regression: float = 0.05
    max_workflow_success_rate_regression: float = 0.05

    def as_dict(self) -> dict[str, float]:
        return {
            "max_unsupported_regression": self.max_unsupported_regression,
            "max_citation_regression": self.max_citation_regression,
            "max_latency_ratio_regression": self.max_latency_ratio_regression,
            "max_cost_ratio_regression": self.max_cost_ratio_regression,
            "max_degraded_rate_regression": self.max_degraded_rate_regression,
            "max_workflow_success_rate_regression": self.max_workflow_success_rate_regression,
        }


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    return None


def _mean(values: list[float]) -> float:
    return round(mean(values), 4) if values else 0.0


def _ratio_delta(candidate_value: float, baseline_value: float) -> float:
    if baseline_value == 0:
        return 0.0 if candidate_value == 0 else 1.0
    return round((candidate_value - baseline_value) / baseline_value, 4)


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_payload(path: Path) -> Any:
    payload = _load_json(path)
    if isinstance(payload, dict):
        payload.setdefault("_source_path", str(path))
    return payload


def _normalize_truthfulness_summary(entry: dict[str, Any], trace: dict[str, Any]) -> dict[str, Any]:
    direct = entry.get("truthfulness_report_summary")
    if isinstance(direct, dict):
        return direct
    legacy = entry.get("truthfulness_summary")
    if isinstance(legacy, dict):
        return legacy
    traced = trace.get("truthfulness_report_summary")
    if isinstance(traced, dict):
        return traced
    return {}


def _normalize_runtime_truth(entry: dict[str, Any], trace: dict[str, Any]) -> dict[str, Any]:
    runtime_truth = entry.get("runtime_truth")
    if isinstance(runtime_truth, dict):
        return runtime_truth
    traced = trace.get("runtime_truth")
    if isinstance(traced, dict):
        return traced
    return {}


def _normalize_retrieval_policy(entry: dict[str, Any], trace: dict[str, Any]) -> dict[str, Any]:
    policy = entry.get("retrieval_plane_policy")
    if isinstance(policy, dict):
        return policy
    traced = trace.get("retrieval_plane_policy")
    if isinstance(traced, dict):
        return traced
    return {}


def _normalize_degraded_conditions(entry: dict[str, Any], trace: dict[str, Any], runtime_truth: dict[str, Any]) -> list[str]:
    for candidate in (
        entry.get("degraded_conditions"),
        trace.get("degraded_conditions"),
        runtime_truth.get("degraded_conditions"),
    ):
        if isinstance(candidate, list):
            return [str(item).strip() for item in candidate if str(item).strip()]
    return []


def normalize_case_entry(entry: dict[str, Any]) -> dict[str, Any]:
    trace = entry.get("trace") if isinstance(entry.get("trace"), dict) else {}
    quality = entry.get("quality") if isinstance(entry.get("quality"), dict) else {}
    truthfulness_summary = _normalize_truthfulness_summary(entry, trace)
    runtime_truth = _normalize_runtime_truth(entry, trace)
    retrieval_plane_policy = _normalize_retrieval_policy(entry, trace)
    degraded_conditions = _normalize_degraded_conditions(entry, trace, runtime_truth)
    case_source = str(entry.get("case_source") or trace.get("case_source") or "").strip()
    dataset_version = str(entry.get("dataset_version") or trace.get("dataset_version") or "").strip()
    execution_mode = str(
        entry.get("execution_mode")
        or trace.get("execution_mode")
        or runtime_truth.get("runtime_mode")
        or entry.get("runtime_mode")
        or ""
    ).strip()
    mode_parity = _safe_bool(
        entry.get("mode_parity_with_baseline", runtime_truth.get("mode_parity_with_baseline"))
    )
    workflow_success_state = str(entry.get("workflow_success_state") or "").strip() or None

    return {
        "case_id": str(entry.get("case_id") or trace.get("trace_id") or "unknown-case").strip(),
        "case_source": case_source,
        "dataset_version": dataset_version,
        "task_family": str(entry.get("task_family") or trace.get("task_family") or "").strip(),
        "execution_mode": execution_mode,
        "truthfulness_report_summary": truthfulness_summary,
        "retrieval_plane_policy": retrieval_plane_policy,
        "degraded_conditions": degraded_conditions,
        "citation_coverage": _safe_float(
            quality.get("citation_coverage", truthfulness_summary.get("citation_coverage"))
        ),
        "unsupported_claim_rate": _safe_float(
            quality.get("unsupported_claim_rate", truthfulness_summary.get("unsupported_claim_rate"))
        ),
        "total_latency_ms": _safe_float(
            entry.get("total_latency_ms", trace.get("total_latency_ms", entry.get("latency_ms")))
        ),
        "cost_estimate": _safe_float(
            entry.get("cost_estimate", trace.get("cost_estimate", entry.get("cost_per_case")))
        ),
        "runtime_truth": runtime_truth,
        "mode_parity_with_baseline": mode_parity,
        "workflow_success_state": workflow_success_state,
    }


def _validate_required_fields(entry: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    for key in REQUIRED_ENTRY_FIELDS:
        value = entry.get(key)
        if key in {"truthfulness_report_summary", "retrieval_plane_policy", "runtime_truth"}:
            if not isinstance(value, dict) or not value:
                failures.append(key)
            continue
        if key == "degraded_conditions":
            if not isinstance(value, list):
                failures.append(key)
            continue
        if key == "mode_parity_with_baseline":
            if value not in {True, False}:
                failures.append(key)
            continue
        if value is None or value == "":
            failures.append(key)
            continue
    if entry.get("case_source") not in CASE_SOURCES:
        failures.append("case_source")
    return failures


def _bundle_entries_from_phase_j_payload(payload: dict[str, Any]) -> list[dict[str, Any]] | None:
    if isinstance(payload.get("entries"), list):
        return [item for item in payload["entries"] if isinstance(item, dict)]
    return None


def _bundle_entries_from_legacy_payload(payload: dict[str, Any]) -> list[dict[str, Any]] | None:
    for key in ("results", "case_results", "run_details"):
        value = payload.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    return None


def _workflow_summary_to_entries(payload: dict[str, Any]) -> list[dict[str, Any]] | None:
    if str(payload.get("comparative_bundle_type") or "").strip() != "phase_j_workflow_bundle":
        return None
    value = payload.get("entries")
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    return []


def _academic_run_to_entries(payload: dict[str, Any]) -> list[dict[str, Any]] | None:
    benchmark = str(payload.get("benchmark") or "").strip()
    run_type = str(payload.get("comparative_bundle_type") or "").strip()
    if run_type != "phase_j_academic_bundle" and benchmark != "v3_0_academic":
        return None
    entries = payload.get("entries")
    if isinstance(entries, list):
        return [item for item in entries if isinstance(item, dict)]
    return None


def extract_entries(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if not isinstance(payload, dict):
        raise ValueError("Unsupported comparative gate payload shape")

    for loader in (
        _bundle_entries_from_phase_j_payload,
        _workflow_summary_to_entries,
        _academic_run_to_entries,
        _bundle_entries_from_legacy_payload,
    ):
        entries = loader(payload)
        if entries is not None:
            return entries
    raise ValueError("Unsupported comparative gate payload")


def summarize_run(entries: list[dict[str, Any]]) -> dict[str, Any]:
    normalized_entries = [normalize_case_entry(entry) for entry in entries]
    missing_hooks = 0
    missing_hook_details: dict[str, list[str]] = {}
    case_source_counts: dict[str, int] = {}
    dataset_versions: set[str] = set()
    task_family_counts: dict[str, int] = {}
    mode_parity_false_cases: list[str] = []
    workflow_success_case_count = 0
    workflow_total_case_count = 0

    for normalized in normalized_entries:
        entry_failures = _validate_required_fields(normalized)
        if entry_failures:
            missing_hooks += len(entry_failures)
            missing_hook_details[normalized["case_id"]] = entry_failures
        case_source = normalized.get("case_source") or "unknown"
        case_source_counts[case_source] = case_source_counts.get(case_source, 0) + 1
        dataset_version = str(normalized.get("dataset_version") or "").strip()
        if dataset_version:
            dataset_versions.add(dataset_version)
        task_family = str(normalized.get("task_family") or "unknown")
        task_family_counts[task_family] = task_family_counts.get(task_family, 0) + 1
        if normalized.get("mode_parity_with_baseline") is False:
            mode_parity_false_cases.append(normalized["case_id"])
        if normalized.get("case_source") == "workflow":
            workflow_total_case_count += 1
            if normalized.get("workflow_success_state") in WORKFLOW_SUCCESS_STATES:
                workflow_success_case_count += 1

    degraded_rate = (
        sum(1 for entry in normalized_entries if entry.get("degraded_conditions")) / len(normalized_entries)
        if normalized_entries
        else 0.0
    )
    workflow_success_rate = (
        round(workflow_success_case_count / workflow_total_case_count, 4)
        if workflow_total_case_count
        else None
    )

    return {
        "total_cases": len(normalized_entries),
        "missing_hooks": missing_hooks,
        "missing_hook_details": missing_hook_details,
        "average_citation_coverage": _mean([entry["citation_coverage"] for entry in normalized_entries]),
        "average_unsupported_claim_rate": _mean([entry["unsupported_claim_rate"] for entry in normalized_entries]),
        "average_latency_ms": _mean([entry["total_latency_ms"] for entry in normalized_entries]),
        "average_cost": round(mean([entry["cost_estimate"] for entry in normalized_entries]), 6)
        if normalized_entries
        else 0.0,
        "degraded_rate": round(degraded_rate, 4),
        "workflow_success_rate": workflow_success_rate,
        "case_source_counts": case_source_counts,
        "dataset_versions": sorted(dataset_versions),
        "task_family_counts": task_family_counts,
        "mode_parity_false_cases": sorted(mode_parity_false_cases),
        "entries": normalized_entries,
    }


def _per_bucket_diff(
    baseline_entries: list[dict[str, Any]],
    candidate_entries: list[dict[str, Any]],
) -> dict[str, Any]:
    baseline_by_case = {entry["case_id"]: entry for entry in baseline_entries}
    candidate_by_case = {entry["case_id"]: entry for entry in candidate_entries}
    shared_case_ids = sorted(set(baseline_by_case) & set(candidate_by_case))
    case_diffs = []
    for case_id in shared_case_ids:
        baseline_entry = baseline_by_case[case_id]
        candidate_entry = candidate_by_case[case_id]
        case_diffs.append(
            {
                "case_id": case_id,
                "case_source": baseline_entry.get("case_source"),
                "task_family": baseline_entry.get("task_family"),
                "execution_mode": baseline_entry.get("execution_mode"),
                "citation_coverage_delta": round(
                    candidate_entry.get("citation_coverage", 0.0)
                    - baseline_entry.get("citation_coverage", 0.0),
                    4,
                ),
                "unsupported_claim_rate_delta": round(
                    candidate_entry.get("unsupported_claim_rate", 0.0)
                    - baseline_entry.get("unsupported_claim_rate", 0.0),
                    4,
                ),
                "latency_delta_ms": round(
                    candidate_entry.get("total_latency_ms", 0.0)
                    - baseline_entry.get("total_latency_ms", 0.0),
                    4,
                ),
                "cost_delta": round(
                    candidate_entry.get("cost_estimate", 0.0)
                    - baseline_entry.get("cost_estimate", 0.0),
                    6,
                ),
                "baseline_degraded_conditions": baseline_entry.get("degraded_conditions", []),
                "candidate_degraded_conditions": candidate_entry.get("degraded_conditions", []),
                "mode_parity_with_baseline": candidate_entry.get("mode_parity_with_baseline"),
                "workflow_success_state": candidate_entry.get("workflow_success_state"),
            }
        )

    bucket_rollup: dict[str, dict[str, Any]] = {}
    for diff in case_diffs:
        bucket = f"{diff['case_source']}::{diff['task_family']}"
        bucket_data = bucket_rollup.setdefault(
            bucket,
            {
                "case_count": 0,
                "citation_coverage_deltas": [],
                "unsupported_claim_rate_deltas": [],
                "latency_delta_ms": [],
                "cost_deltas": [],
            },
        )
        bucket_data["case_count"] += 1
        bucket_data["citation_coverage_deltas"].append(diff["citation_coverage_delta"])
        bucket_data["unsupported_claim_rate_deltas"].append(diff["unsupported_claim_rate_delta"])
        bucket_data["latency_delta_ms"].append(diff["latency_delta_ms"])
        bucket_data["cost_deltas"].append(diff["cost_delta"])

    bucket_summary = {}
    for bucket, metrics in bucket_rollup.items():
        bucket_summary[bucket] = {
            "case_count": metrics["case_count"],
            "average_citation_coverage_delta": _mean(metrics["citation_coverage_deltas"]),
            "average_unsupported_claim_rate_delta": _mean(metrics["unsupported_claim_rate_deltas"]),
            "average_latency_delta_ms": _mean(metrics["latency_delta_ms"]),
            "average_cost_delta": round(mean(metrics["cost_deltas"]), 6) if metrics["cost_deltas"] else 0.0,
        }
    return {"bucket_summary": bucket_summary, "case_diffs": case_diffs}


def compare_runs(
    *,
    baseline: dict[str, Any],
    candidate: dict[str, Any],
    threshold_policy: ThresholdPolicy | None = None,
) -> dict[str, Any]:
    policy = threshold_policy or ThresholdPolicy()
    baseline_case_ids = {entry["case_id"] for entry in baseline.get("entries", [])}
    candidate_case_ids = {entry["case_id"] for entry in candidate.get("entries", [])}

    baseline_unsupported = _safe_float(baseline.get("average_unsupported_claim_rate"))
    candidate_unsupported = _safe_float(candidate.get("average_unsupported_claim_rate"))
    baseline_latency = _safe_float(baseline.get("average_latency_ms"))
    candidate_latency = _safe_float(candidate.get("average_latency_ms"))
    baseline_cost = _safe_float(baseline.get("average_cost"))
    candidate_cost = _safe_float(candidate.get("average_cost"))
    baseline_degraded = _safe_float(baseline.get("degraded_rate"))
    candidate_degraded = _safe_float(candidate.get("degraded_rate"))
    baseline_citation = _safe_float(baseline.get("average_citation_coverage"))
    candidate_citation = _safe_float(candidate.get("average_citation_coverage"))
    baseline_workflow_success = baseline.get("workflow_success_rate")
    candidate_workflow_success = candidate.get("workflow_success_rate")

    unsupported_delta = round(candidate_unsupported - baseline_unsupported, 4)
    citation_delta = round(candidate_citation - baseline_citation, 4)
    latency_delta_ratio = _ratio_delta(candidate_latency, baseline_latency)
    cost_delta_ratio = _ratio_delta(candidate_cost, baseline_cost)
    degraded_delta = round(candidate_degraded - baseline_degraded, 4)
    workflow_success_delta = (
        round(_safe_float(candidate_workflow_success) - _safe_float(baseline_workflow_success), 4)
        if baseline_workflow_success is not None and candidate_workflow_success is not None
        else None
    )

    fail_reasons: list[str] = []
    warn_reasons: list[str] = []
    experiment_reasons: list[str] = []

    if int(candidate.get("missing_hooks") or 0) > 0 or int(baseline.get("missing_hooks") or 0) > 0:
        fail_reasons.append("missing_required_hooks")
    if baseline_case_ids != candidate_case_ids:
        fail_reasons.append("case_set_mismatch")
    if sorted(baseline.get("dataset_versions") or []) != sorted(candidate.get("dataset_versions") or []):
        fail_reasons.append("dataset_version_mismatch")
    if unsupported_delta > policy.max_unsupported_regression:
        fail_reasons.append("unsupported_claim_regression")
    elif unsupported_delta > 0:
        warn_reasons.append("unsupported_claim_regression_within_budget")
    if citation_delta < -policy.max_citation_regression:
        fail_reasons.append("citation_coverage_regression")
    if latency_delta_ratio > policy.max_latency_ratio_regression:
        warn_reasons.append("latency_regression")
    if cost_delta_ratio > policy.max_cost_ratio_regression:
        warn_reasons.append("cost_regression")
    if degraded_delta > policy.max_degraded_rate_regression:
        warn_reasons.append("degraded_rate_regression")
    if workflow_success_delta is not None and workflow_success_delta < (-policy.max_workflow_success_rate_regression):
        warn_reasons.append("workflow_success_regression")
    if candidate.get("mode_parity_false_cases"):
        experiment_reasons.append("mode_parity_mismatch")

    if fail_reasons:
        verdict_class = VERDICT_FAIL
    elif experiment_reasons:
        verdict_class = VERDICT_EXPERIMENT_ONLY
    elif warn_reasons:
        verdict_class = VERDICT_WARN
    else:
        verdict_class = VERDICT_PASS

    per_bucket_diff = _per_bucket_diff(
        baseline.get("entries", []),
        candidate.get("entries", []),
    )

    return {
        "verdict": verdict_class,
        "pass": verdict_class == VERDICT_PASS,
        "failures": fail_reasons,
        "warnings": warn_reasons,
        "experiment_reasons": experiment_reasons,
        "candidate_missing_hooks": int(candidate.get("missing_hooks") or 0),
        "baseline_missing_hooks": int(baseline.get("missing_hooks") or 0),
        "metric_diff": {
            "unsupported_claim_rate_delta": unsupported_delta,
            "citation_coverage_delta": citation_delta,
            "latency_delta_ratio": latency_delta_ratio,
            "cost_delta_ratio": cost_delta_ratio,
            "degraded_rate_delta": degraded_delta,
            "workflow_success_rate_delta": workflow_success_delta,
        },
        "threshold_policy": policy.as_dict(),
        "baseline_summary": baseline,
        "candidate_summary": candidate,
        "case_set": {
            "baseline": sorted(baseline_case_ids),
            "candidate": sorted(candidate_case_ids),
        },
        "per_bucket_diff": per_bucket_diff,
        "recommendation": _recommendation_for_verdict(verdict_class),
    }


def _recommendation_for_verdict(verdict: str) -> str:
    if verdict == VERDICT_PASS:
        return "adopt"
    if verdict == VERDICT_WARN:
        return "hold"
    if verdict == VERDICT_EXPERIMENT_ONLY:
        return "hold"
    return "reject"


def render_markdown_summary(
    *,
    verdict: dict[str, Any],
    baseline_label: str,
    candidate_label: str,
) -> str:
    metric_diff = verdict.get("metric_diff") or {}
    baseline_summary = verdict.get("baseline_summary") or {}
    candidate_summary = verdict.get("candidate_summary") or {}
    per_bucket = (verdict.get("per_bucket_diff") or {}).get("bucket_summary") or {}
    threshold_policy = verdict.get("threshold_policy") or {}

    lines = [
        "# Phase J Comparative Close-out",
        "",
        f"- baseline: {baseline_label}",
        f"- candidate: {candidate_label}",
        f"- verdict: {verdict.get('verdict')}",
        f"- recommendation: {verdict.get('recommendation')}",
        f"- dataset_versions: {', '.join(candidate_summary.get('dataset_versions') or []) or 'unknown'}",
        "",
        "## Parity",
        "",
        f"- baseline_case_count: {baseline_summary.get('total_cases', 0)}",
        f"- candidate_case_count: {candidate_summary.get('total_cases', 0)}",
        f"- mode_parity_false_cases: {', '.join(candidate_summary.get('mode_parity_false_cases') or []) or 'none'}",
        f"- case_source_counts: {candidate_summary.get('case_source_counts') or {}}",
        "",
        "## Metric Deltas",
        "",
        f"- unsupported_claim_rate_delta: {metric_diff.get('unsupported_claim_rate_delta')}",
        f"- citation_coverage_delta: {metric_diff.get('citation_coverage_delta')}",
        f"- latency_delta_ratio: {metric_diff.get('latency_delta_ratio')}",
        f"- cost_delta_ratio: {metric_diff.get('cost_delta_ratio')}",
        f"- degraded_rate_delta: {metric_diff.get('degraded_rate_delta')}",
        f"- workflow_success_rate_delta: {metric_diff.get('workflow_success_rate_delta')}",
        "",
        "## Failure Buckets",
        "",
        f"- failures: {', '.join(verdict.get('failures') or []) or 'none'}",
        f"- warnings: {', '.join(verdict.get('warnings') or []) or 'none'}",
        f"- experiment_reasons: {', '.join(verdict.get('experiment_reasons') or []) or 'none'}",
        "",
        "## Threshold Policy",
        "",
    ]
    for key, value in threshold_policy.items():
        lines.append(f"- {key}: {value}")

    lines.extend([
        "",
        "## Per-bucket Diff",
        "",
    ])
    if per_bucket:
        for bucket, bucket_summary in sorted(per_bucket.items()):
            lines.append(
                f"- {bucket}: cases={bucket_summary.get('case_count')}, "
                f"citation_delta={bucket_summary.get('average_citation_coverage_delta')}, "
                f"unsupported_delta={bucket_summary.get('average_unsupported_claim_rate_delta')}, "
                f"latency_delta_ms={bucket_summary.get('average_latency_delta_ms')}, "
                f"cost_delta={bucket_summary.get('average_cost_delta')}"
            )
    else:
        lines.append("- no shared buckets")

    degraded_case_lines = []
    for entry in candidate_summary.get("entries", []):
        degraded = entry.get("degraded_conditions") or []
        if degraded:
            degraded_case_lines.append(f"{entry.get('case_id')}: {' | '.join(degraded)}")

    lines.extend([
        "",
        "## Degraded Conditions",
        "",
    ])
    if degraded_case_lines:
        for item in degraded_case_lines:
            lines.append(f"- {item}")
    else:
        lines.append("- none")

    return "\n".join(lines) + "\n"


def run_gate(
    *,
    baseline_payload: Any,
    candidate_payload: Any,
    baseline_label: str = "baseline",
    candidate_label: str = "candidate",
    threshold_policy: ThresholdPolicy | None = None,
) -> dict[str, Any]:
    baseline_summary = summarize_run(extract_entries(baseline_payload))
    candidate_summary = summarize_run(extract_entries(candidate_payload))
    verdict = compare_runs(
        baseline=baseline_summary,
        candidate=candidate_summary,
        threshold_policy=threshold_policy,
    )
    verdict["markdown_summary"] = render_markdown_summary(
        verdict=verdict,
        baseline_label=baseline_label,
        candidate_label=candidate_label,
    )
    return verdict


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Phase J comparative gate")
    parser.add_argument("--baseline", required=True, help="Baseline JSON payload")
    parser.add_argument("--candidate", required=True, help="Candidate JSON payload")
    parser.add_argument("--output", required=True, help="Output verdict JSON path")
    parser.add_argument("--diff-output", help="Output per-bucket diff JSON path")
    parser.add_argument("--markdown-output", help="Output markdown summary path")
    parser.add_argument("--baseline-label", default="baseline")
    parser.add_argument("--candidate-label", default="candidate")
    args = parser.parse_args()

    baseline_payload = _load_payload(Path(args.baseline))
    candidate_payload = _load_payload(Path(args.candidate))
    verdict = run_gate(
        baseline_payload=baseline_payload,
        candidate_payload=candidate_payload,
        baseline_label=args.baseline_label,
        candidate_label=args.candidate_label,
    )

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(verdict, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.diff_output:
        diff_path = Path(args.diff_output)
        diff_path.parent.mkdir(parents=True, exist_ok=True)
        diff_path.write_text(
            json.dumps(verdict.get("per_bucket_diff") or {}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    if args.markdown_output:
        markdown_path = Path(args.markdown_output)
        markdown_path.parent.mkdir(parents=True, exist_ok=True)
        markdown_path.write_text(verdict.get("markdown_summary") or "", encoding="utf-8")

    print(json.dumps(verdict, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
