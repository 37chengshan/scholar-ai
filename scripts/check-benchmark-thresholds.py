#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
API_ROOT = ROOT / "apps" / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from tests.benchmarks.thresholds import THRESHOLDS, evaluate_report  # noqa: E402


def main() -> int:
    artifacts_dir = ROOT / "apps" / "api" / "artifacts" / "benchmarks"
    if not artifacts_dir.exists():
        print(f"benchmark artifacts not found: {artifacts_dir}")
        return 1

    expected_reports = {
        suite: artifacts_dir / f"{suite}.json" for suite in THRESHOLDS.keys()
    }
    missing_suites = [suite for suite, report_path in expected_reports.items() if not report_path.exists()]
    if missing_suites:
        print("missing benchmark JSON reports for suites:")
        for suite in sorted(missing_suites):
            print(f"- {suite}")
        return 1

    report_files = sorted(expected_reports.values())

    failures: list[str] = []
    for report_file in report_files:
        report = json.loads(report_file.read_text(encoding="utf-8"))
        errors = evaluate_report(report)
        if errors:
            failures.extend([f"{report_file.name}: {error}" for error in errors])

    if failures:
        print("threshold check failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("threshold check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
