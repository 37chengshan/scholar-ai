from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


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
    return {
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


def write_json_report(report: dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


def write_markdown_report(report: dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    summary = report.get("summary", {})
    lines = [
        f"# Benchmark Report: {report.get('suite')}",
        "",
        f"Generated at: {report.get('generated_at')}",
        "",
        "## Summary",
        f"- Passed: {summary.get('passed', 0)}",
        f"- Failed: {summary.get('failed', 0)}",
        f"- P50: {summary.get('p50_ms', 0)}ms",
        f"- P95: {summary.get('p95_ms', 0)}ms",
        "",
        "## Cases",
    ]
    for case in report.get("cases", []):
        lines.append(
            f"- {case.get('case_id')}: {case.get('status')} (latency={case.get('latency_ms', 0)}ms)"
        )
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
