#!/usr/bin/env python3
"""SPECTER2 Preflight — Gate 5.

Validates that SPECTER2 collections are ready for retrieval:
  1. Load SPECTER2 model and encode sample query
  2. Verify dim match (query_dim == collection_dim == 768)
  3. ID-only search (vector search, no metadata output)
  4. Full metadata search (source_chunk_id, paper_id, content_data, stage)
  5. Hydration test (content_data non-empty)

Usage:
  python scripts/preflight_specter2_retrieval.py

Output:
  artifacts/benchmarks/specter2_v2_1_20/specter2_preflight.json
  artifacts/benchmarks/specter2_v2_1_20/specter2_preflight.md
"""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
API_ROOT = ROOT / "apps" / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

OUT_DIR = ROOT / "artifacts/benchmarks/specter2_v2_1_20"

EXPECTED_DIM = 768
SAMPLE_QUERY = "transformer neural architecture attention mechanism self-supervised learning"

SPECTER2_COLLECTIONS = {
    "raw": "paper_contents_v2_specter2_raw_v2_1",
    "rule": "paper_contents_v2_specter2_rule_v2_1",
    "llm": "paper_contents_v2_specter2_llm_v2_1",
}


def run_preflight() -> dict:
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sample_query": SAMPLE_QUERY,
        "model_load": {},
        "dim_check": {},
        "stages": {},
        "status": "BLOCKED",
    }

    # ── Step 1: Load model ──
    print("Step 1: Loading SPECTER2 model ...")
    from app.core.specter2_embedding_service import Specter2EmbeddingService

    t0 = time.time()
    svc_embed = Specter2EmbeddingService(adapter="adhoc_query")
    svc_embed._load_model()
    load_time = round(time.time() - t0, 2)
    report["model_load"] = {"load_time_s": load_time, "status": "OK"}
    print(f"  Loaded in {load_time}s")

    # ── Step 2: Encode sample + dim check ──
    print("Step 2: Encoding sample query ...")
    t0 = time.time()
    vec = svc_embed.generate_embedding(SAMPLE_QUERY)
    enc_time = round(time.time() - t0, 3)
    query_dim = len(vec)
    dim_ok = query_dim == EXPECTED_DIM
    report["dim_check"] = {
        "query_dim": query_dim,
        "expected_dim": EXPECTED_DIM,
        "encode_time_s": enc_time,
        "status": "PASS" if dim_ok else "FAIL",
    }
    print(f"  dim={query_dim}, expected={EXPECTED_DIM}, {'PASS' if dim_ok else 'FAIL'}")

    if not dim_ok:
        report["status"] = "BLOCKED"
        report["blocked_reason"] = f"dim mismatch: {query_dim} != {EXPECTED_DIM}"
        return report

    # ── Connect Milvus ──
    from app.core.milvus_service import get_milvus_service
    from pymilvus import Collection, utility

    svc_milvus = get_milvus_service()
    svc_milvus.connect()
    alias = svc_milvus._alias
    print(f"  Milvus alias={alias}")

    search_params = {"metric_type": "COSINE", "params": {"nprobe": 10}}
    all_stages_ok = True

    for stage, col_name in SPECTER2_COLLECTIONS.items():
        print(f"\nStep 3+: Stage={stage} collection={col_name}")
        stage_result: dict = {
            "collection": col_name,
            "exists": False,
            "id_only_search": {},
            "metadata_search": {},
            "hydration": {},
            "status": "BLOCKED",
        }

        if not utility.has_collection(col_name, using=alias):
            stage_result["status"] = "BLOCKED"
            stage_result["blocked_reason"] = f"collection not found: {col_name}"
            report["stages"][stage] = stage_result
            all_stages_ok = False
            print(f"  BLOCKED: collection not found")
            continue

        stage_result["exists"] = True
        col = Collection(col_name, using=alias)
        col.load()

        # Dim match from collection schema
        for field in col.schema.fields:
            if field.name == "embedding":
                col_dim = field.params.get("dim", -1)
                if col_dim != EXPECTED_DIM:
                    stage_result["status"] = "BLOCKED"
                    stage_result["blocked_reason"] = f"collection dim {col_dim} != {EXPECTED_DIM}"
                    print(f"  BLOCKED: dim mismatch {col_dim}")
                    all_stages_ok = False
                else:
                    print(f"  collection dim={col_dim} OK")
                break

        # ID-only search
        try:
            t0 = time.time()
            results = col.search(
                data=[vec],
                anns_field="embedding",
                param=search_params,
                limit=5,
                output_fields=[],
            )
            elapsed = round(time.time() - t0, 3)
            hits = results[0] if results else []
            stage_result["id_only_search"] = {
                "hit_count": len(hits),
                "latency_s": elapsed,
                "status": "PASS" if len(hits) > 0 else "FAIL",
            }
            print(f"  id-only search: {len(hits)} hits in {elapsed}s")
        except Exception as e:
            stage_result["id_only_search"] = {"status": "FAIL", "error": str(e)}
            print(f"  id-only search FAIL: {e}")
            all_stages_ok = False

        # Metadata search
        try:
            t0 = time.time()
            results = col.search(
                data=[vec],
                anns_field="embedding",
                param=search_params,
                limit=3,
                output_fields=["source_chunk_id", "paper_id", "content_data", "stage"],
            )
            elapsed = round(time.time() - t0, 3)
            hits = results[0] if results else []
            sample_hits = []
            for hit in hits[:2]:
                entity = hit.entity
                sample_hits.append({
                    "paper_id": entity.get("paper_id", ""),
                    "source_chunk_id": entity.get("source_chunk_id", ""),
                    "stage_field": entity.get("stage", ""),
                    "content_len": len(entity.get("content_data") or ""),
                    "score": round(hit.score, 4),
                })
            stage_result["metadata_search"] = {
                "hit_count": len(hits),
                "latency_s": elapsed,
                "sample_hits": sample_hits,
                "status": "PASS" if len(hits) > 0 else "FAIL",
            }
            print(f"  metadata search: {len(hits)} hits in {elapsed}s")
        except Exception as e:
            stage_result["metadata_search"] = {"status": "FAIL", "error": str(e)}
            print(f"  metadata search FAIL: {e}")
            all_stages_ok = False

        # Hydration check
        try:
            hydrated = [
                h for h in sample_hits
                if h.get("content_len", 0) > 0
            ]
            stage_result["hydration"] = {
                "checked": len(sample_hits),
                "hydrated": len(hydrated),
                "status": "PASS" if hydrated else "FAIL",
            }
            print(f"  hydration: {len(hydrated)}/{len(sample_hits)} non-empty")
        except Exception as e:
            stage_result["hydration"] = {"status": "FAIL", "error": str(e)}
            all_stages_ok = False

        # Stage overall status
        checks = [
            stage_result.get("id_only_search", {}).get("status") == "PASS",
            stage_result.get("metadata_search", {}).get("status") == "PASS",
            stage_result.get("hydration", {}).get("status") == "PASS",
        ]
        stage_result["status"] = "PASS" if all(checks) else "BLOCKED"
        if stage_result["status"] != "PASS":
            all_stages_ok = False
        print(f"  => {stage_result['status']}")

        report["stages"][stage] = stage_result

    report["status"] = "PASS" if (dim_ok and all_stages_ok) else "BLOCKED"
    return report


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("SPECTER2 Preflight — Gate 5")
    print("=" * 60)

    report = run_preflight()

    json_path = OUT_DIR / "specter2_preflight.json"
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"\n  → {json_path.relative_to(ROOT)}")

    _write_md(report)

    print(f"\n[{report['status']}] SPECTER2 preflight")
    return 0 if report["status"] == "PASS" else 1


def _write_md(report: dict) -> None:
    lines = [
        "# SPECTER2 Preflight Report",
        "",
        f"**Generated:** {report['generated_at']}",
        f"**Status:** `{report['status']}`",
        "",
        "## Model Load",
        "",
        f"| Field | Value |",
        f"|-------|-------|",
        f"| load_time_s | {report['model_load'].get('load_time_s', '-')} |",
        f"| status | {report['model_load'].get('status', '-')} |",
        "",
        "## Dim Check",
        "",
        f"| Field | Value |",
        f"|-------|-------|",
        f"| query_dim | {report['dim_check'].get('query_dim', '-')} |",
        f"| expected_dim | {report['dim_check'].get('expected_dim', '-')} |",
        f"| encode_time_s | {report['dim_check'].get('encode_time_s', '-')} |",
        f"| status | {report['dim_check'].get('status', '-')} |",
        "",
        "## Stage Results",
        "",
    ]
    for stage, r in report.get("stages", {}).items():
        lines += [
            f"### {stage} — `{r['collection']}`",
            "",
            f"**Status:** `{r['status']}`",
            "",
            "| Test | Result |",
            "|------|--------|",
            f"| id_only_search | {r.get('id_only_search', {}).get('status', '-')} |",
            f"| metadata_search | {r.get('metadata_search', {}).get('status', '-')} |",
            f"| hydration | {r.get('hydration', {}).get('status', '-')} |",
            "",
        ]

    md_path = OUT_DIR / "specter2_preflight.md"
    md_path.write_text("\n".join(lines))
    print(f"  → {md_path.relative_to(ROOT)}")


if __name__ == "__main__":
    sys.exit(main())
