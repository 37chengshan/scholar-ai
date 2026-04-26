#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import json
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List

from app.core.model_gateway import create_embedding_provider
from app.core.model_gateway.errors import ProviderError

from scripts.evals.v2_4_common import (
    DEFAULT_OUTPUT_DIR,
    OFFICIAL_MODEL,
    OFFICIAL_PROVIDER,
    infer_ingest_status,
    write_json,
    write_markdown,
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="v2.4 provider probe")
    p.add_argument("--provider", default=OFFICIAL_PROVIDER)
    p.add_argument("--model", default=OFFICIAL_MODEL)
    p.add_argument("--timeout", type=float, default=20.0)
    p.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    return p.parse_args()


def _write_tiny_png(path: Path) -> None:
    png_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO7Zx5sAAAAASUVORK5CYII="
    path.write_bytes(base64.b64decode(png_b64))


def _stable_dim(dims: List[int]) -> bool:
    return bool(dims) and all(d == dims[0] for d in dims) and dims[0] > 0


def main() -> int:
    args = parse_args()
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    report: Dict[str, Any] = {
        "provider": args.provider,
        "model": args.model,
        "dimension": 0,
        "supports_batch": False,
        "supports_image": False,
        "sample_text_success": False,
        "sample_image_success": False,
        "sample_batch_success": False,
        "dimension_stable": False,
        "timeout_retry_enabled": True,
        "status": "BLOCKED",
        "error": None,
    }

    try:
        provider = create_embedding_provider(args.provider, args.model)
        report["supports_image"] = bool(provider.supports_image())

        dims: List[int] = []

        t0 = time.perf_counter()
        vecs = provider.embed_texts(["provider probe text"], timeout_s=args.timeout)
        t1 = time.perf_counter()
        report["sample_text_success"] = bool(vecs and vecs[0])
        if vecs and vecs[0]:
            dims.append(len(vecs[0]))

        batch = provider.embed_texts(["batch-a", "batch-b", "batch-c"], timeout_s=args.timeout)
        report["supports_batch"] = True
        report["sample_batch_success"] = len(batch) == 3 and all(len(v) > 0 for v in batch)
        if batch and batch[0]:
            dims.append(len(batch[0]))

        # dimension() internally probes once more; included for stability check.
        dims.append(int(provider.dimension()))

        image_probe_error = None
        if provider.supports_image():
            try:
                with tempfile.TemporaryDirectory(prefix="v24_probe_") as td:
                    sample_png = Path(td) / "sample.png"
                    _write_tiny_png(sample_png)
                    img_vecs = provider.embed_multimodal([
                        {"text": "sample page"},
                        {"image_path": str(sample_png)},
                    ], timeout_s=args.timeout)
                    report["sample_image_success"] = len(img_vecs) == 2 and all(len(v) > 0 for v in img_vecs)
                    if img_vecs and img_vecs[0]:
                        dims.append(len(img_vecs[0]))
            except Exception as exc:
                image_probe_error = str(exc)
                report["sample_image_success"] = False

        report["dimension_stable"] = _stable_dim(dims)
        report["dimension"] = dims[0] if dims else 0

        errors: List[str] = []
        if not report["sample_text_success"]:
            errors.append("sample_text_failed")
        if not report["sample_batch_success"]:
            errors.append("sample_batch_failed")
        if provider.supports_image() and not report["sample_image_success"] and image_probe_error:
            report["image_probe_note"] = f"image_probe_failed_non_blocking:{image_probe_error}"
        if not report["dimension_stable"]:
            errors.append(f"dimension_unstable:{dims}")

        report["latency_ms"] = round((t1 - t0) * 1000.0, 3)
        report["status"] = infer_ingest_status(errors)
        if errors:
            report["error"] = ";".join(errors)

    except ProviderError as exc:
        report["status"] = "BLOCKED"
        report["error"] = str(exc)
    except Exception as exc:
        report["status"] = "BLOCKED"
        report["error"] = str(exc)

    write_json(out_dir / "provider_probe.json", report)

    md_lines = [
        f"- provider: {report['provider']}",
        f"- model: {report['model']}",
        f"- dimension: {report['dimension']}",
        f"- supports_batch: {report['supports_batch']}",
        f"- supports_image: {report['supports_image']}",
        f"- sample_text_success: {report['sample_text_success']}",
        f"- sample_image_success: {report['sample_image_success']}",
        f"- sample_batch_success: {report['sample_batch_success']}",
        f"- dimension_stable: {report['dimension_stable']}",
        f"- status: {report['status']}",
    ]
    if report.get("error"):
        md_lines.extend(["", "## Error", "", "```", str(report["error"]), "```"])
    write_markdown(out_dir / "provider_probe.md", "v2.4 Provider Probe", md_lines)

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
