from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tests.benchmarks.thresholds import evaluate_report


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    sorted_values = sorted(values)
    if len(sorted_values) == 1:
        return round(sorted_values[0], 2)
    rank = (len(sorted_values) - 1) * p
    low = int(rank)
    high = min(low + 1, len(sorted_values) - 1)
    weight = rank - low
    return round(sorted_values[low] * (1 - weight) + sorted_values[high] * weight, 2)


def build_suite_report(suite: str, cases: list[dict[str, Any]]) -> dict[str, Any]:
    latencies = [float(case.get("latency_ms", 0)) for case in cases]
    passed = sum(1 for case in cases if case.get("status") == "passed")
    failed = len(cases) - passed
    report = {
        "suite": suite,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "cases": cases,
        "summary": {
            "passed": passed,
            "failed": failed,
            "p50_ms": percentile(latencies, 0.5),
            "p95_ms": percentile(latencies, 0.95),
        },
    }

    family_metrics: dict[str, dict[str, Any]] = {}
    aggregate_metric_values: dict[str, list[float]] = {}
    for case in cases:
        metrics = case.get("metrics", {}) if isinstance(case.get("metrics"), dict) else {}
        family = str(metrics.get("query_family") or case.get("query_family") or "unknown")
        bucket = family_metrics.setdefault(
            family,
            {
                "cases": 0,
                "passed": 0,
                "failed": 0,
                "planner_query_count_avg": [],
                "second_pass_used_rate": [],
                "second_pass_gain_avg": [],
                "evidence_bundle_hit_count_avg": [],
                "paper_role_hit_rate_avg": [],
                "table_hit_rate_avg": [],
                "figure_hit_rate_avg": [],
                "numeric_qa_exact_match_avg": [],
                "top5_cross_paper_completeness_avg": [],
            },
        )
        bucket["cases"] += 1
        if case.get("status") == "passed":
            bucket["passed"] += 1
        else:
            bucket["failed"] += 1
        for metric_name in (
            "planner_query_count",
            "second_pass_used",
            "second_pass_gain",
            "evidence_bundle_hit_count",
            "paper_role_hit_rate",
            "table_hit_rate",
            "figure_hit_rate",
            "numeric_qa_exact_match",
            "top5_cross_paper_completeness",
        ):
            value = metrics.get(metric_name)
            if value is None:
                continue
            target_key = f"{metric_name}_avg"
            if target_key in bucket:
                bucket[target_key].append(float(value))
        for metric_name, value in metrics.items():
            if isinstance(value, bool):
                aggregate_metric_values.setdefault(metric_name, []).append(float(value))
            elif isinstance(value, (int, float)):
                aggregate_metric_values.setdefault(metric_name, []).append(float(value))

    report["summary"]["success_rate"] = round((passed / len(cases)) if cases else 0.0, 4)
    report["summary"]["threshold_errors"] = evaluate_report(report)
    report["summary"]["threshold_passed"] = not report["summary"]["threshold_errors"]
    report["summary"]["aggregate_metrics"] = {
        name: round(sum(values) / len(values), 4)
        for name, values in sorted(aggregate_metric_values.items())
        if values
    }
    report["summary"]["family_metrics"] = {
        family: {
            "cases": data["cases"],
            "passed": data["passed"],
            "failed": data["failed"],
            "success_rate": round((data["passed"] / data["cases"]) if data["cases"] else 0.0, 4),
            "planner_query_count_avg": round(sum(data["planner_query_count_avg"]) / len(data["planner_query_count_avg"]) if data["planner_query_count_avg"] else 0.0, 4),
            "second_pass_used_rate": round(sum(data["second_pass_used_rate"]) / len(data["second_pass_used_rate"]) if data["second_pass_used_rate"] else 0.0, 4),
            "second_pass_gain_avg": round(sum(data["second_pass_gain_avg"]) / len(data["second_pass_gain_avg"]) if data["second_pass_gain_avg"] else 0.0, 4),
            "evidence_bundle_hit_count_avg": round(sum(data["evidence_bundle_hit_count_avg"]) / len(data["evidence_bundle_hit_count_avg"]) if data["evidence_bundle_hit_count_avg"] else 0.0, 4),
            "paper_role_hit_rate_avg": round(sum(data["paper_role_hit_rate_avg"]) / len(data["paper_role_hit_rate_avg"]) if data["paper_role_hit_rate_avg"] else 0.0, 4),
            "table_hit_rate_avg": round(sum(data["table_hit_rate_avg"]) / len(data["table_hit_rate_avg"]) if data["table_hit_rate_avg"] else 0.0, 4),
            "figure_hit_rate_avg": round(sum(data["figure_hit_rate_avg"]) / len(data["figure_hit_rate_avg"]) if data["figure_hit_rate_avg"] else 0.0, 4),
            "numeric_qa_exact_match_avg": round(sum(data["numeric_qa_exact_match_avg"]) / len(data["numeric_qa_exact_match_avg"]) if data["numeric_qa_exact_match_avg"] else 0.0, 4),
            "top5_cross_paper_completeness_avg": round(sum(data["top5_cross_paper_completeness_avg"]) / len(data["top5_cross_paper_completeness_avg"]) if data["top5_cross_paper_completeness_avg"] else 0.0, 4),
        }
        for family, data in sorted(family_metrics.items())
    }
    return report


def write_json_report(report: dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


def write_markdown_report(report: dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    summary = report.get("summary", {})
    threshold_errors = summary.get("threshold_errors", [])
    lines = [
        f"# Benchmark Report: {report.get('suite')}",
        "",
        f"Generated at: {report.get('generated_at')}",
        "",
        "## Summary",
        f"- Passed: {summary.get('passed', 0)}",
        f"- Failed: {summary.get('failed', 0)}",
        f"- Success rate: {summary.get('success_rate', 0):.2%}",
        f"- P50: {summary.get('p50_ms', 0)}ms",
        f"- P95: {summary.get('p95_ms', 0)}ms",
        f"- Threshold passed: {summary.get('threshold_passed', False)}",
        "",
        "## Threshold Check",
    ]

    if threshold_errors:
        lines.extend([f"- {error}" for error in threshold_errors])
    else:
        lines.append("- All configured thresholds passed")

    family_metrics = summary.get("family_metrics", {})
    if family_metrics:
        lines.extend([
            "",
            "## Query Family Summary",
        ])
        for family, metrics in family_metrics.items():
            lines.append(
                f"- {family}: cases={metrics.get('cases', 0)}, success_rate={metrics.get('success_rate', 0):.2%}, planner_queries={metrics.get('planner_query_count_avg', 0)}"
            )

    aggregate_metrics = summary.get("aggregate_metrics", {})
    if aggregate_metrics:
        lines.extend([
            "",
            "## Aggregate Metrics",
        ])
        for metric_name, value in aggregate_metrics.items():
            lines.append(f"- {metric_name}: {value}")

    lines.extend(["", "## Cases"])
    for case in report.get("cases", []):
        lines.append(
            f"- {case.get('case_id')}: {case.get('status')} (latency={case.get('latency_ms', 0)}ms)"
        )
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
