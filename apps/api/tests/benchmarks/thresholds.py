from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SuiteThreshold:
    min_success_rate: float
    max_p95_ms: float


THRESHOLDS: dict[str, SuiteThreshold] = {
    "chat_stability": SuiteThreshold(min_success_rate=0.95, max_p95_ms=3000),
    "search_workflow": SuiteThreshold(min_success_rate=0.95, max_p95_ms=2500),
    "import_workflow": SuiteThreshold(min_success_rate=0.95, max_p95_ms=2500),
    "rag_quality": SuiteThreshold(min_success_rate=0.90, max_p95_ms=5000),
    "performance_baseline": SuiteThreshold(min_success_rate=1.0, max_p95_ms=5000),
}


def evaluate_report(report: dict[str, Any]) -> list[str]:
    suite = report.get("suite")
    summary = report.get("summary", {})
    threshold = THRESHOLDS.get(suite)
    if threshold is None:
        return [f"No threshold configured for suite: {suite}"]

    total = int(summary.get("passed", 0)) + int(summary.get("failed", 0))
    success_rate = (int(summary.get("passed", 0)) / total) if total else 0.0
    p95 = float(summary.get("p95_ms", 0))

    errors: list[str] = []
    if success_rate < threshold.min_success_rate:
        errors.append(
            f"{suite} success_rate {success_rate:.2f} below {threshold.min_success_rate:.2f}"
        )
    if p95 > threshold.max_p95_ms:
        errors.append(f"{suite} p95 {p95:.2f}ms above {threshold.max_p95_ms:.2f}ms")
    return errors
