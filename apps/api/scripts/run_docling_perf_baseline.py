#!/usr/bin/env python3
"""Generate born-digital vs scanned OCR fallback baseline report."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, asdict
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.docling_service import DoclingParser, ParserConfig


@dataclass(frozen=True)
class BaselineResult:
    kind: str
    success: bool
    elapsed_ms: float
    markdown_chars: int
    ocr_used: bool
    parse_mode: str


def _run_single(parser: DoclingParser, pdf_path: Path, force_ocr: bool) -> BaselineResult:
    started = time.perf_counter()
    result = parser.parse_file(pdf_path, force_ocr=force_ocr)
    elapsed_ms = (time.perf_counter() - started) * 1000

    metadata = result.get("metadata", {})
    return BaselineResult(
        kind="scanned" if force_ocr else "born-digital",
        success=True,
        elapsed_ms=round(elapsed_ms, 2),
        markdown_chars=len(result.get("markdown", "")),
        ocr_used=bool(metadata.get("ocr_used", False)),
        parse_mode=str(metadata.get("parse_mode", "unknown")),
    )


def main() -> None:
    fixture_dir = Path("tests/fixtures")
    born_digital = fixture_dir / "sample.pdf"
    scanned = fixture_dir / "sample_scanned.pdf"

    parser = DoclingParser(config=ParserConfig.from_settings())
    results = []

    if born_digital.exists():
        results.append(asdict(_run_single(parser, born_digital, force_ocr=False)))

    if scanned.exists():
        # For scanned placeholders this still exercises forced OCR route contract.
        results.append(asdict(_run_single(parser, scanned, force_ocr=True)))

    report = {
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "results": results,
        "summary": {
            "total_cases": len(results),
            "all_success": all(item["success"] for item in results) if results else False,
        },
    }

    out_dir = Path("artifacts/benchmarks")
    out_dir.mkdir(parents=True, exist_ok=True)

    json_path = out_dir / "docling_perf_baseline.json"
    md_path = out_dir / "docling_perf_baseline.md"

    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# Docling Perf Baseline",
        "",
        f"Generated at: {report['generated_at']}",
        "",
        "| kind | success | elapsed_ms | markdown_chars | ocr_used | parse_mode |",
        "|---|---:|---:|---:|---:|---|",
    ]

    for item in results:
        lines.append(
            f"| {item['kind']} | {item['success']} | {item['elapsed_ms']} | {item['markdown_chars']} | {item['ocr_used']} | {item['parse_mode']} |"
        )

    lines.extend([
        "",
        "## Notes",
        "- born-digital should normally run native parser path first.",
        "- scanned case is executed with force_ocr=True for deterministic fallback verification.",
    ])

    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Wrote baseline report: {json_path}")
    print(f"Wrote baseline markdown: {md_path}")


if __name__ == "__main__":
    main()
