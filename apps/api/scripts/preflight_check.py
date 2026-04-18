#!/usr/bin/env python3
"""Run backend preflight checks."""

import argparse
import json

from app.utils.preflight import run_preflight


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run ScholarAI API preflight checks")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero on failures")
    args = parser.parse_args()

    report = run_preflight(strict=args.strict)
    print(json.dumps(report, ensure_ascii=False, indent=2))
