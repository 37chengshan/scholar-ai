#!/usr/bin/env python3
"""SPECTER2 Embedding Probe.

Loads SPECTER2 model, encodes a sample text, records real embedding dimension,
and outputs a probe report.

Output:
  artifacts/benchmarks/specter2_v2_1_20/specter2_embedding_probe.json
  artifacts/benchmarks/specter2_v2_1_20/specter2_embedding_probe.md
"""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
API_ROOT = ROOT / "apps" / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

OUT_DIR = ROOT / "artifacts/benchmarks/specter2_v2_1_20"

SAMPLE_TEXTS = [
    "Attention is all you need. We propose a new simple network architecture, the Transformer.",
    "Large language models demonstrate emergent capabilities at scale.",
    "Retrieval augmented generation improves factual accuracy in language models.",
]


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print("=" * 60)
    print("SPECTER2 Embedding Probe")
    print("=" * 60)

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model_class": "Specter2EmbeddingService",
        "base_model": "allenai/specter2_base",
        "adapter": "proximity",
        "device": None,
        "adapters_available": None,
        "dimension": None,
        "sample_texts_tested": len(SAMPLE_TEXTS),
        "sample_vector_len": None,
        "load_time_seconds": None,
        "encode_time_seconds": None,
        "encode_batch_time_seconds": None,
        "status": "BLOCKED",
        "blocked_reason": "",
    }

    # -- Load model --
    try:
        from app.core.specter2_embedding_service import (
            ADAPTERS_AVAILABLE,
            Specter2EmbeddingService,
        )
        report["adapters_available"] = ADAPTERS_AVAILABLE

        t0 = time.time()
        svc = Specter2EmbeddingService(adapter="proximity")
        svc._load_model()
        report["load_time_seconds"] = round(time.time() - t0, 3)
        report["device"] = svc.device
        report["dimension"] = svc.dimension

        print(f"  model: {svc.BASE_MODEL}")
        print(f"  device: {svc.device}")
        print(f"  adapters_available: {ADAPTERS_AVAILABLE}")
        print(f"  declared_dim: {svc.dimension}")
        print(f"  load_time: {report['load_time_seconds']}s")

    except Exception as e:
        report["blocked_reason"] = f"Model load failed: {e}"
        _write_outputs(report)
        print(f"\n[BLOCKED] {e}")
        return 1

    # -- Encode single --
    try:
        t0 = time.time()
        vec = svc.generate_embedding(SAMPLE_TEXTS[0])
        report["encode_time_seconds"] = round(time.time() - t0, 3)
        report["sample_vector_len"] = len(vec)

        if len(vec) == 0:
            raise ValueError("encode returned empty vector")

        print(f"  single encode OK, dim: {len(vec)}, time: {report['encode_time_seconds']}s")

        if len(vec) != svc.dimension:
            report["blocked_reason"] = (
                f"Actual encode dim ({len(vec)}) != declared dim ({svc.dimension})"
            )
            _write_outputs(report)
            print(f"\n[BLOCKED] {report['blocked_reason']}")
            return 1

    except Exception as e:
        report["blocked_reason"] = f"Single encode failed: {e}"
        _write_outputs(report)
        print(f"\n[BLOCKED] {e}")
        return 1

    # -- Encode batch --
    try:
        t0 = time.time()
        vecs = svc.generate_embeddings_batch(SAMPLE_TEXTS, batch_size=3)
        report["encode_batch_time_seconds"] = round(time.time() - t0, 3)

        if len(vecs) != len(SAMPLE_TEXTS):
            raise ValueError(f"Batch returned {len(vecs)} vectors, expected {len(SAMPLE_TEXTS)}")
        for v in vecs:
            if len(v) != svc.dimension:
                raise ValueError(f"Batch vector dim mismatch: {len(v)} != {svc.dimension}")

        print(f"  batch encode OK, {len(vecs)} texts, time: {report['encode_batch_time_seconds']}s")

    except Exception as e:
        report["blocked_reason"] = f"Batch encode failed: {e}"
        _write_outputs(report)
        print(f"\n[BLOCKED] {e}")
        return 1

    report["status"] = "PASS"
    _write_outputs(report)
    print(f"\n[PASS] SPECTER2 embedding probe complete. dim={report['dimension']}")
    return 0


def _write_outputs(report: dict) -> None:
    json_path = OUT_DIR / "specter2_embedding_probe.json"
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"\n  → {json_path.relative_to(ROOT)}")

    md_lines = [
        "# SPECTER2 Embedding Probe",
        f"\n**Generated:** {report['generated_at']}",
        f"\n**Status:** `{report['status']}`",
        "",
        "## Results",
        "",
        "| Field | Value |",
        "|-------|-------|",
        f"| base_model | {report['base_model']} |",
        f"| adapter | {report['adapter']} |",
        f"| device | {report['device']} |",
        f"| adapters_available | {report['adapters_available']} |",
        f"| dimension | {report['dimension']} |",
        f"| sample_vector_len | {report['sample_vector_len']} |",
        f"| load_time_seconds | {report['load_time_seconds']} |",
        f"| encode_time_seconds | {report['encode_time_seconds']} |",
        f"| encode_batch_time_seconds | {report['encode_batch_time_seconds']} |",
    ]

    if report.get("blocked_reason"):
        md_lines += ["", "## BLOCKED Reason", "", f"> {report['blocked_reason']}", ""]

    md_path = OUT_DIR / "specter2_embedding_probe.md"
    md_path.write_text("\n".join(md_lines))
    print(f"  → {md_path.relative_to(ROOT)}")


if __name__ == "__main__":
    sys.exit(main())
