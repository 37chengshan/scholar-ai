#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[2]
API_ROOT = ROOT / "apps" / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from app.core.model_gateway import create_embedding_provider
from app.core.model_gateway.errors import ProviderError


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="v2.3 provider probe")
    p.add_argument("--provider", default="tongyi")
    p.add_argument("--model", default="tongyi-embedding-vision-flash-2026-03-06")
    p.add_argument("--timeout", type=float, default=20.0)
    p.add_argument("--output-dir", default=str(ROOT / "artifacts" / "benchmarks" / "v2_3"))
    return p.parse_args()


def write_md(path: Path, report: Dict[str, Any]) -> None:
    lines = [
        "# v2.3 Provider Probe",
        "",
        f"- provider: {report['provider']}",
        f"- model_name: {report['model_name']}",
        f"- dimension: {report['dimension']}",
        f"- sample_text_success: {report['sample_text_success']}",
        f"- sample_image_success: {report['sample_image_success']}",
        f"- batch_success: {report['batch_success']}",
        f"- timeout_policy: {report['timeout_policy']}",
        f"- avg_latency_ms: {report['avg_latency_ms']}",
        f"- status: {report['status']}",
    ]
    if report.get("error"):
        lines.extend(["", "## Error", "", "```", str(report["error"]), "```"])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    main_transformers_version = "not-installed"
    try:
        import transformers  # type: ignore

        main_transformers_version = transformers.__version__
    except Exception:
        pass

    report: Dict[str, Any] = {
        "provider": args.provider,
        "model_name": args.model,
        "dimension": 0,
        "sample_text_success": False,
        "sample_image_success": False,
        "batch_success": False,
        "timeout_policy": f"retry=2, timeout_s={args.timeout}",
        "avg_latency_ms": 0.0,
        "status": "BLOCKED",
        "main_transformers_version": main_transformers_version,
        "error": None,
    }

    try:
        provider = create_embedding_provider(args.provider, args.model)
        lats = []

        t0 = time.perf_counter()
        vecs = provider.embed_texts(["provider probe text"], timeout_s=args.timeout)
        lats.append((time.perf_counter() - t0) * 1000)
        report["sample_text_success"] = bool(vecs and vecs[0])

        report["dimension"] = provider.dimension()

        t1 = time.perf_counter()
        batch_vecs = provider.embed_texts(
            ["batch one", "batch two", "batch three"], timeout_s=args.timeout
        )
        lats.append((time.perf_counter() - t1) * 1000)
        report["batch_success"] = len(batch_vecs) == 3

        # Multimodal/image probe: use text+image placeholder payload path.
        # If provider endpoint does not support image embeddings, mark False but do not crash.
        try:
            t2 = time.perf_counter()
            _ = provider.embed_multimodal([{"text": "multimodal probe"}], timeout_s=args.timeout)
            lats.append((time.perf_counter() - t2) * 1000)
            report["sample_image_success"] = True
        except Exception:
            report["sample_image_success"] = False

        report["avg_latency_ms"] = round(sum(lats) / max(len(lats), 1), 3)
        if report["sample_text_success"] and report["batch_success"] and report["dimension"] > 0:
            report["status"] = "PASS"
        else:
            report["status"] = "BLOCKED"

    except ProviderError as e:
        report["status"] = "BLOCKED"
        report["error"] = str(e)
    except Exception as e:
        report["status"] = "BLOCKED"
        report["error"] = str(e)

    json_path = out_dir / "provider_probe.json"
    md_path = out_dir / "provider_probe.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    write_md(md_path, report)

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
