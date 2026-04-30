#!/usr/bin/env python3
"""Generate the Phase D real-world validation summary JSON and Markdown report."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
API_ROOT = ROOT / "apps" / "api"

import sys

if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from app.services.real_world_validation_service import (  # noqa: E402
    render_markdown_report,
    summarize_real_world_validation,
    validate_real_world_payload,
)


DEFAULT_INPUT = ROOT / "artifacts" / "validation-results" / "phase_d" / "real_world_validation.json"
DEFAULT_OUTPUT_JSON = ROOT / "artifacts" / "validation-results" / "phase_d" / "real_world_validation.summary.json"
DEFAULT_OUTPUT_MD = ROOT / "docs" / "reports" / "v3_0_real_world_validation.md"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate v3.0 real-world validation report")
    parser.add_argument("--input", default=str(DEFAULT_INPUT), help="Path to real-world validation payload JSON")
    parser.add_argument("--output-json", default=str(DEFAULT_OUTPUT_JSON), help="Path to summary JSON")
    parser.add_argument("--output-md", default=str(DEFAULT_OUTPUT_MD), help="Path to Markdown report")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_json = Path(args.output_json)
    output_md = Path(args.output_md)

    payload = json.loads(input_path.read_text(encoding="utf-8"))
    errors = validate_real_world_payload(payload)
    if errors:
        raise SystemExit("Invalid Phase D payload: " + "; ".join(errors))

    summary = summarize_real_world_validation(payload)
    markdown = render_markdown_report(summary)

    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_md.parent.mkdir(parents=True, exist_ok=True)

    output_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    output_md.write_text(markdown, encoding="utf-8")

    print(f"summary_json={output_json}")
    print(f"summary_md={output_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())