#!/usr/bin/env python3
"""v3.0 academic benchmark gate runner.

Usage:
  python scripts/evals/v3_0_academic_gate.py              # public offline gate
  python scripts/evals/v3_0_academic_gate.py --json       # machine-readable output
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "apps" / "api"))

from app.services.eval_service import list_run_summaries, run_offline_gate


def _print_divider(char: str = "-", width: int = 72) -> None:
    print(char * width)


def main() -> None:
    parser = argparse.ArgumentParser(description="v3.0 academic benchmark gate")
    parser.add_argument("--json", action="store_true", default=False, dest="json_output")
    args = parser.parse_args()

    passed, detail = run_offline_gate("v3_0_academic")

    if args.json_output:
        print(json.dumps({"benchmark": "v3_0_academic", "passed": passed, **detail}))
        sys.exit(0 if passed else 1)

    _print_divider("=")
    print("v3.0 Academic Benchmark Gate")
    _print_divider("=")
    print(f"run:      {detail.get('run_id')}")
    print(f"baseline: {detail.get('baseline_run_id')}")
    print(f"candidate:{detail.get('candidate_run_id')}")
    print(f"verdict:  {detail.get('verdict')}")

    metrics = detail.get("metrics") or {}
    if metrics:
        _print_divider()
        print("metrics")
        _print_divider()
        print(f"retrieval_hit_rate:      {metrics.get('retrieval_hit_rate')}")
        print(f"recall_at_5:             {(metrics.get('top_k_recall') or {}).get('recall_at_5')}")
        print(f"citation_jump_valid_rate:{metrics.get('citation_jump_valid_rate')}")
        print(f"answer_supported_rate:   {metrics.get('answer_supported_rate')}")
        print(f"groundedness:            {metrics.get('groundedness')}")
        print(f"abstain_precision:       {metrics.get('abstain_precision')}")
        print(f"latency_p95:             {metrics.get('latency_p95')}")
        print(f"fallback_used_count:     {metrics.get('fallback_used_count')}")

    failures = detail.get("gate_failures") or []
    if failures:
        _print_divider()
        print("gate failures")
        _print_divider()
        for item in failures:
            print(f"- {item}")

    runs = list_run_summaries("v3_0_academic")
    _print_divider()
    print(f"manifest runs: {len(runs)}")
    _print_divider("=")

    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
