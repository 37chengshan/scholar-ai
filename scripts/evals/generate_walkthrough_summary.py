#!/usr/bin/env python3
"""Generate walkthrough summary JSON from Playwright test results.

Parses Playwright JSON reporter output, matches test titles to journey IDs
(J1-J7) via regex on spec filename, and outputs a summary JSON that the
gate runner's Face C parser expects.

Usage:
    python scripts/evals/generate_walkthrough_summary.py \
        --playwright-json /tmp/pw-results.json \
        --output artifacts/walkthrough/v5_0/latest_summary.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]

# Regex to extract journey ID from spec filename.
# Matches: journey-j1-landing-login-dashboard.spec.ts -> J1
_JOURNEY_RE = re.compile(r"journey-j(\d+)-.*\.spec\.ts$")

# All expected journey IDs.
_EXPECTED_JOURNEYS = {f"J{i}" for i in range(1, 8)}


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _extract_journey_id(spec_file: str) -> str | None:
    """Extract J{n} from a spec filename like 'journey-j3-search.spec.ts'."""
    basename = Path(spec_file).name
    m = _JOURNEY_RE.match(basename)
    return f"J{m.group(1)}" if m else None


def _collect_journey_statuses(data: dict[str, Any]) -> dict[str, dict[str, str]]:
    """Walk Playwright JSON results and collect per-journey status.

    Returns dict: {journey_id: {"status": "passed"|"failed"|"skipped", "error_summary": str|None}}
    A journey is considered passed only if ALL its tests pass.
    """
    journeys: dict[str, dict[str, str]] = {}

    suites = data.get("suites", [])
    _walk_suites(suites, journeys)

    # Fill in any missing expected journeys as skipped.
    for jid in _EXPECTED_JOURNEYS:
        if jid not in journeys:
            journeys[jid] = {"status": "skipped", "error_summary": None}

    return journeys


def _walk_suites(suites: list[dict], journeys: dict[str, dict[str, str]]) -> None:
    """Recursively walk suite tree."""
    for suite in suites:
        spec_file = suite.get("file", "")
        journey_id = _extract_journey_id(spec_file)

        if journey_id:
            for spec in suite.get("specs", []):
                for test in spec.get("tests", []):
                    for result in test.get("results", []):
                        status = result.get("status", "skipped")
                        error_msg = None
                        if status == "failed":
                            errors = result.get("errors", [])
                            error_msg = errors[0].get("message", "unknown") if errors else "unknown"

                        if journey_id not in journeys:
                            journeys[journey_id] = {"status": "passed", "error_summary": None}

                        if status == "failed":
                            journeys[journey_id] = {"status": "failed", "error_summary": error_msg}
                        elif status == "skipped" and journeys[journey_id]["status"] != "failed":
                            journeys[journey_id] = {"status": "skipped", "error_summary": error_msg}
                        # "passed" doesn't override "failed"

        # Recurse into nested suites.
        _walk_suites(suite.get("suites", []), journeys)


def generate_summary(
    playwright_json_path: Path,
    output_path: Path,
) -> dict[str, Any]:
    """Generate walkthrough summary from Playwright JSON results.

    Args:
        playwright_json_path: Path to Playwright JSON reporter output.
        output_path: Path to write the summary JSON.

    Returns:
        The generated summary dict.
    """
    if not playwright_json_path.exists():
        print(f"[walkthrough] WARNING: {playwright_json_path} not found, generating all-skipped summary",
              file=sys.stderr)
        journeys = {f"J{i}": {"status": "skipped", "error_summary": None} for i in range(1, 8)}
    else:
        data = json.loads(playwright_json_path.read_text(encoding="utf-8"))
        journeys = _collect_journey_statuses(data)

    passed = sum(1 for v in journeys.values() if v["status"] == "passed")
    failed = sum(1 for v in journeys.values() if v["status"] == "failed")
    skipped = sum(1 for v in journeys.values() if v["status"] == "skipped")

    details = [
        {
            "journey_id": jid,
            "status": journeys[jid]["status"],
            "error_summary": journeys[jid]["error_summary"],
        }
        for jid in sorted(journeys.keys(), key=lambda x: int(x[1:]))
    ]

    summary = {
        "journey_passed_count": passed,
        "journey_failed_count": failed,
        "journey_skipped_count": skipped,
        "journey_details": details,
        "last_run_at": _now_iso(),
        "playwright_report_path": "apps/web/playwright-report",
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[walkthrough] passed={passed} failed={failed} skipped={skipped}")
    print(f"[walkthrough] output={output_path}")

    return summary


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Generate walkthrough summary from Playwright JSON results"
    )
    ap.add_argument(
        "--playwright-json",
        default=None,
        help="Path to Playwright JSON reporter output",
    )
    ap.add_argument(
        "--output",
        default=str(ROOT / "artifacts" / "walkthrough" / "v5_0" / "latest_summary.json"),
        help="Output path for summary JSON (default: artifacts/walkthrough/v5_0/latest_summary.json)",
    )
    args = ap.parse_args()

    pw_path = Path(args.playwright_json) if args.playwright_json else Path("/tmp/pw-results.json")
    out_path = Path(args.output)

    generate_summary(pw_path, out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
