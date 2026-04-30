#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import mean
from typing import Any


REQUIRED_HOOKS = (
    "task_family",
    "execution_mode",
    "truthfulness_report_summary",
    "retrieval_plane_policy",
    "degraded_conditions",
)


def _load_payload(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        if isinstance(payload.get("results"), list):
            return payload["results"]
        if isinstance(payload.get("case_results"), list):
            return payload["case_results"]
        if isinstance(payload.get("run_details"), list):
            return payload["run_details"]
    raise ValueError(f"Unsupported comparative gate payload: {path}")


def _normalize_entry(entry: dict[str, Any]) -> dict[str, Any]:
    trace = entry.get("trace") if isinstance(entry.get("trace"), dict) else {}
    quality = entry.get("quality") if isinstance(entry.get("quality"), dict) else {}
    truthfulness_summary = entry.get("truthfulness_report_summary")
    if not isinstance(truthfulness_summary, dict):
        if "truthfulness_summary" in entry and isinstance(entry.get("truthfulness_summary"), dict):
            truthfulness_summary = entry["truthfulness_summary"]
        elif "truthfulness_report_summary" in trace and isinstance(trace.get("truthfulness_report_summary"), dict):
            truthfulness_summary = trace["truthfulness_report_summary"]

    normalized: dict[str, Any] = {
        "case_id": entry.get("case_id") or trace.get("trace_id") or "unknown-case",
        "task_family": entry.get("task_family") or trace.get("task_family"),
        "execution_mode": entry.get("execution_mode") or trace.get("execution_mode"),
        "citation_coverage": float(
            quality.get("citation_coverage")
            or (truthfulness_summary or {}).get("citation_coverage")
            or 0.0
        ),
        "unsupported_claim_rate": float(
            quality.get("unsupported_claim_rate")
            or (truthfulness_summary or {}).get("unsupported_claim_rate")
            or 0.0
        ),
        "total_latency_ms": float(trace.get("total_latency_ms") or entry.get("total_latency_ms") or 0.0),
        "cost_estimate": float(entry.get("cost_estimate") or trace.get("cost_estimate") or 0.0),
    }
    if truthfulness_summary is not None:
        normalized["truthfulness_report_summary"] = truthfulness_summary
    if "retrieval_plane_policy" in entry:
        normalized["retrieval_plane_policy"] = entry["retrieval_plane_policy"]
    elif "retrieval_plane_policy" in trace:
        normalized["retrieval_plane_policy"] = trace["retrieval_plane_policy"]
    if "degraded_conditions" in entry:
        normalized["degraded_conditions"] = entry["degraded_conditions"]
    elif "degraded_conditions" in trace:
        normalized["degraded_conditions"] = trace["degraded_conditions"]
    return normalized


def summarize_run(entries: list[dict[str, Any]]) -> dict[str, Any]:
    normalized = [_normalize_entry(entry) for entry in entries]
    missing_hooks = 0
    for entry in normalized:
        for key in REQUIRED_HOOKS:
            if key not in entry:
                missing_hooks += 1
                continue
            value = entry.get(key)
            if value is None or value == "":
                missing_hooks += 1
                continue
            if key == "truthfulness_report_summary" and not isinstance(value, dict):
                missing_hooks += 1
                continue
            if key == "retrieval_plane_policy" and not isinstance(value, dict):
                missing_hooks += 1

    citation_values = [entry["citation_coverage"] for entry in normalized]
    unsupported_values = [entry["unsupported_claim_rate"] for entry in normalized]
    latency_values = [entry["total_latency_ms"] for entry in normalized]
    cost_values = [entry["cost_estimate"] for entry in normalized]
    degraded_rate = (
        sum(1 for entry in normalized if entry.get("degraded_conditions")) / len(normalized)
        if normalized
        else 0.0
    )
    return {
        "total_cases": len(normalized),
        "missing_hooks": missing_hooks,
        "average_citation_coverage": round(mean(citation_values), 4) if citation_values else 0.0,
        "average_unsupported_claim_rate": round(mean(unsupported_values), 4) if unsupported_values else 0.0,
        "average_latency_ms": round(mean(latency_values), 4) if latency_values else 0.0,
        "average_cost": round(mean(cost_values), 6) if cost_values else 0.0,
        "degraded_rate": round(degraded_rate, 4),
        "entries": normalized,
    }


def compare_runs(
    *,
    baseline: dict[str, Any],
    candidate: dict[str, Any],
    max_unsupported_regression: float = 0.03,
    max_latency_regression: float = 0.15,
    max_cost_regression: float = 0.2,
    max_degraded_regression: float = 0.05,
) -> dict[str, Any]:
    baseline_case_ids = {entry["case_id"] for entry in baseline.get("entries", [])}
    candidate_case_ids = {entry["case_id"] for entry in candidate.get("entries", [])}
    baseline_unsupported = float(baseline.get("average_unsupported_claim_rate") or 0.0)
    candidate_unsupported = float(candidate.get("average_unsupported_claim_rate") or 0.0)
    baseline_latency = float(baseline.get("average_latency_ms") or 0.0)
    candidate_latency = float(candidate.get("average_latency_ms") or 0.0)
    baseline_cost = float(baseline.get("average_cost") or 0.0)
    candidate_cost = float(candidate.get("average_cost") or 0.0)
    baseline_degraded = float(baseline.get("degraded_rate") or 0.0)
    candidate_degraded = float(candidate.get("degraded_rate") or 0.0)
    baseline_citation = float(baseline.get("average_citation_coverage") or 0.0)
    candidate_citation = float(candidate.get("average_citation_coverage") or 0.0)

    unsupported_delta = round(candidate_unsupported - baseline_unsupported, 4)
    latency_delta_ratio = round(
        ((candidate_latency - baseline_latency) / baseline_latency) if baseline_latency else 0.0,
        4,
    )
    cost_delta_ratio = round(
        ((candidate_cost - baseline_cost) / baseline_cost) if baseline_cost else 0.0,
        4,
    )
    degraded_delta = round(candidate_degraded - baseline_degraded, 4)
    citation_delta = round(candidate_citation - baseline_citation, 4)

    failures: list[str] = []
    if int(candidate.get("missing_hooks") or 0) > 0:
        failures.append("missing_required_hooks")
    if baseline_case_ids != candidate_case_ids:
        failures.append("case_set_mismatch")
    if unsupported_delta > max_unsupported_regression:
        failures.append("unsupported_claim_regression")
    if latency_delta_ratio > max_latency_regression:
        failures.append("latency_regression")
    if cost_delta_ratio > max_cost_regression:
        failures.append("cost_regression")
    if degraded_delta > max_degraded_regression:
        failures.append("degraded_rate_regression")
    if citation_delta < 0:
        failures.append("citation_coverage_regression")

    return {
        "pass": not failures,
        "failures": failures,
        "candidate_missing_hooks": int(candidate.get("missing_hooks") or 0),
        "baseline_missing_hooks": int(baseline.get("missing_hooks") or 0),
        "metric_diff": {
            "unsupported_claim_rate_delta": unsupported_delta,
            "citation_coverage_delta": citation_delta,
            "latency_delta_ratio": latency_delta_ratio,
            "cost_delta_ratio": cost_delta_ratio,
            "degraded_rate_delta": degraded_delta,
        },
        "baseline_summary": baseline,
        "candidate_summary": candidate,
        "case_set": {
            "baseline": sorted(baseline_case_ids),
            "candidate": sorted(candidate_case_ids),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Phase J comparative gate")
    parser.add_argument("--baseline", required=True, help="Baseline JSON payload")
    parser.add_argument("--candidate", required=True, help="Candidate JSON payload")
    parser.add_argument("--output", required=True, help="Output verdict path")
    args = parser.parse_args()

    baseline_summary = summarize_run(_load_payload(Path(args.baseline)))
    candidate_summary = summarize_run(_load_payload(Path(args.candidate)))
    verdict = compare_runs(baseline=baseline_summary, candidate=candidate_summary)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(verdict, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(verdict, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()