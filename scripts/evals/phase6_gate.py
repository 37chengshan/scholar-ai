#!/usr/bin/env python3
"""Phase 6 offline quality gate runner.

Usage:
  python scripts/evals/phase6_gate.py            # strict offline gate
  python scripts/evals/phase6_gate.py --online   # report-only online check (non-blocking)

Exit codes:
  0  PASS
  1  FAIL (only for offline mode; online is always exit 0)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Allow running from repo root without installing the package
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "apps" / "api"))

from app.services.eval_service import (
    get_latest_offline_run_id,
    get_run_detail,
    list_run_summaries,
    run_offline_gate,
)


def _print_divider(char: str = "─", width: int = 60) -> None:
    print(char * width)


def _fmt_pct(v: float) -> str:
    return f"{v * 100:.1f}%"


def _fmt_sec(v: float) -> str:
    return f"{v:.2f}s"


def _run_offline(verbose: bool = False) -> int:
    """Run the frozen offline benchmark gate. Returns 0=PASS, 1=FAIL."""
    print()
    _print_divider("═")
    print("  Phase 6 Offline Quality Gate")
    _print_divider("═")

    passed, detail = run_offline_gate()

    run_id = detail.get("run_id", "—")
    verdict = detail.get("verdict", "UNKNOWN")
    gate_failures = detail.get("gate_failures", [])
    metrics = detail.get("metrics", {})

    print(f"\n  Run:     {run_id}")
    print(f"  Verdict: {verdict}\n")

    _print_divider()
    print("  Metrics")
    _print_divider()

    DISPLAY_METRICS = [
        ("retrieval_hit_rate", "Retrieval Hit Rate", lambda v: _fmt_pct(v)),
        ("recall_at_5",        "Recall@5",           lambda v: _fmt_pct(v)),
        ("recall_at_10",       "Recall@10",          lambda v: _fmt_pct(v)),
        ("citation_jump_valid_rate", "Citation Jump Valid Rate", lambda v: _fmt_pct(v)),
        ("answer_supported_rate",    "Answer Supported Rate",    lambda v: _fmt_pct(v)),
        ("groundedness",       "Groundedness",       lambda v: _fmt_pct(v)),
        ("abstain_precision",  "Abstain Precision",  lambda v: _fmt_pct(v)),
        ("latency_p50",        "Latency P50",        lambda v: _fmt_sec(v)),
        ("latency_p95",        "Latency P95",        lambda v: _fmt_sec(v)),
        ("cost_per_answer",    "Cost/Answer",        lambda v: f"${v:.4f}"),
    ]

    for key, label, fmt in DISPLAY_METRICS:
        raw = metrics
        # handle nested top_k_recall
        if key == "recall_at_5":
            raw_val = (metrics.get("top_k_recall") or {}).get("recall_at_5", 0.0)
        elif key == "recall_at_10":
            raw_val = (metrics.get("top_k_recall") or {}).get("recall_at_10", 0.0)
        else:
            raw_val = metrics.get(key, 0.0)

        try:
            display = fmt(float(raw_val))
        except (TypeError, ValueError):
            display = str(raw_val)

        mark = "  "
        if gate_failures:
            for failure in gate_failures:
                if key in failure:
                    mark = "✗ "
                    break

        print(f"  {mark}{label:<32} {display}")

    fallback = metrics.get("fallback_used_count", 0)
    print(f"\n  Fallback count: {fallback}")

    if gate_failures:
        _print_divider()
        print("  Gate Failures")
        _print_divider()
        for f in gate_failures:
            print(f"  ✗ {f}")

    _print_divider("═")
    verdict_color = "\033[32m" if passed else "\033[31m"
    reset = "\033[0m"
    print(f"  {verdict_color}Result: {verdict}{reset}")
    _print_divider("═")
    print()

    return 0 if passed else 1


def _run_online() -> int:
    """Report-only online run check. Always exits 0 (non-blocking)."""
    print()
    _print_divider("═")
    print("  Phase 6 Online Run Report (non-blocking)")
    _print_divider("═")

    runs = [r for r in list_run_summaries() if r.get("mode") == "online"]
    if not runs:
        print("  No online runs found in manifest.")
        _print_divider("═")
        print()
        return 0

    print(f"  Found {len(runs)} online run(s):\n")
    for run in runs[:5]:
        rid = run.get("run_id", "—")
        verdict = run.get("overall_verdict", "—")
        created = run.get("created_at", "—")
        print(f"  {verdict:<6}  {rid}  ({created})")

    # Load detail for latest online run
    latest_online = runs[0]
    detail = get_run_detail(latest_online["run_id"])
    if detail:
        failures = detail["metrics"].get("gate_failures", [])
        if failures:
            print(f"\n  Note: {len(failures)} gate threshold(s) not met (informational only):")
            for f in failures:
                print(f"    - {f}")
        else:
            print("\n  All thresholds met (informational).")

    _print_divider("═")
    print("  Online check complete (exit 0 regardless of verdict).")
    _print_divider("═")
    print()
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 6 quality gate runner")
    parser.add_argument(
        "--online",
        action="store_true",
        default=False,
        help="Run report-only online check instead of blocking offline gate",
    )
    parser.add_argument(
        "--json",
        dest="json_output",
        action="store_true",
        default=False,
        help="Emit JSON result to stdout instead of human-readable output",
    )
    args = parser.parse_args()

    if args.json_output:
        # Machine-readable output for CI integration
        if args.online:
            runs = [r for r in list_run_summaries() if r.get("mode") == "online"]
            print(json.dumps({"mode": "online", "run_count": len(runs), "runs": runs[:5]}))
            sys.exit(0)
        else:
            passed, detail = run_offline_gate()
            print(json.dumps({"mode": "offline", "passed": passed, **detail}))
            sys.exit(0 if passed else 1)

    if args.online:
        sys.exit(_run_online())
    else:
        sys.exit(_run_offline())


if __name__ == "__main__":
    main()
