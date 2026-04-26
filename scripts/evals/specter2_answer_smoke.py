#!/usr/bin/env python3
"""SPECTER2 Answer Smoke Test — Gate 6.

Runs 1 query × 3 stages (raw/rule/llm) using SPECTER2 only.
Prints benchmark header with branch/dim/collection info and validates
that results are non-empty and properly formed.

Usage:
  python scripts/evals/specter2_answer_smoke.py

Output:
  artifacts/benchmarks/specter2_v2_1_20/specter2_answer_smoke.json
  artifacts/benchmarks/specter2_v2_1_20/specter2_answer_smoke.md
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

SMOKE_QUERY = "How does multi-head self-attention enable transformers to capture long-range dependencies?"
TOP_K = 5
EXPECTED_DIM = 768

SPECTER2_COLLECTIONS = {
    "raw": "paper_contents_v2_specter2_raw_v2_1",
    "rule": "paper_contents_v2_specter2_rule_v2_1",
    "llm": "paper_contents_v2_specter2_llm_v2_1",
}


def run_smoke() -> dict:
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "smoke_query": SMOKE_QUERY,
        "branch": "specter2",
        "embedding_model": "allenai/specter2_base",
        "embedding_dim": EXPECTED_DIM,
        "top_k": TOP_K,
        "stages": {},
        "status": "BLOCKED",
    }

    # ── Load model ──
    print("\nLoading SPECTER2 model (adhoc_query adapter)...")
    from app.core.specter2_embedding_service import Specter2EmbeddingService

    t0 = time.time()
    svc_embed = Specter2EmbeddingService(adapter="adhoc_query")
    svc_embed._load_model()
    load_time = round(time.time() - t0, 2)
    print(f"  Loaded in {load_time}s")

    # Encode query
    vec = svc_embed.generate_embedding(SMOKE_QUERY)
    if len(vec) != EXPECTED_DIM:
        report["status"] = "BLOCKED"
        report["blocked_reason"] = f"query dim {len(vec)} != {EXPECTED_DIM}"
        return report

    # ── Connect Milvus ──
    from app.core.milvus_service import get_milvus_service
    from pymilvus import Collection, utility

    svc_milvus = get_milvus_service()
    svc_milvus.connect()
    alias = svc_milvus._alias

    search_params = {"metric_type": "COSINE", "params": {"nprobe": 10}}
    all_ok = True

    # ── Benchmark header ──
    print("\n" + "=" * 70)
    print("SPECTER2 Scientific Dense Line — 1×3 Smoke")
    print("=" * 70)
    print(f"  branch    : specter2")
    print(f"  model     : allenai/specter2_base")
    print(f"  dim       : {EXPECTED_DIM}")
    print(f"  top_k     : {TOP_K}")
    print(f"  query     : {SMOKE_QUERY[:80]}")
    print("=" * 70)

    for stage, col_name in SPECTER2_COLLECTIONS.items():
        print(f"\n  stage={stage} | collection={col_name}")
        stage_result: dict = {
            "collection": col_name,
            "query": SMOKE_QUERY,
            "hit_count": 0,
            "latency_s": 0.0,
            "top_hits": [],
            "status": "BLOCKED",
        }

        if not utility.has_collection(col_name, using=alias):
            stage_result["status"] = "BLOCKED"
            stage_result["blocked_reason"] = f"collection not found: {col_name}"
            report["stages"][stage] = stage_result
            print(f"  BLOCKED: collection not found")
            all_ok = False
            continue

        col = Collection(col_name, using=alias)
        col.load()

        try:
            t0 = time.time()
            results = col.search(
                data=[vec],
                anns_field="embedding",
                param=search_params,
                limit=TOP_K,
                output_fields=[
                    "source_chunk_id", "paper_id", "content_data", "stage", "section"
                ],
            )
            elapsed = round(time.time() - t0, 3)
            hits = results[0] if results else []

            top_hits = []
            for hit in hits:
                entity = hit.entity
                top_hits.append({
                    "paper_id": entity.get("paper_id", ""),
                    "source_chunk_id": entity.get("source_chunk_id", ""),
                    "section": entity.get("section", ""),
                    "stage_field": entity.get("stage", ""),
                    "content_preview": (entity.get("content_data") or "")[:200],
                    "score": round(hit.score, 4),
                })

            stage_result["hit_count"] = len(top_hits)
            stage_result["latency_s"] = elapsed
            stage_result["top_hits"] = top_hits

            # Validation
            checks = []
            if len(top_hits) >= 1:
                checks.append("PASS: got results")
            else:
                checks.append("FAIL: no results")
                all_ok = False

            if all(h.get("paper_id") for h in top_hits):
                checks.append("PASS: all hits have paper_id")
            else:
                checks.append("FAIL: some hits missing paper_id")
                all_ok = False

            if all(h.get("content_preview") for h in top_hits):
                checks.append("PASS: all hits have content_data")
            else:
                checks.append("FAIL: some hits missing content_data")
                all_ok = False

            stage_result["checks"] = checks
            stage_result["status"] = (
                "PASS" if all(c.startswith("PASS") for c in checks) else "BLOCKED"
            )

            # Print results
            print(f"  {len(top_hits)} hits | {elapsed}s latency")
            for i, h in enumerate(top_hits[:3]):
                print(f"  [{i+1}] {h['paper_id']} | score={h['score']} | "
                      f"{h['content_preview'][:80]}...")

        except Exception as e:
            stage_result["status"] = "BLOCKED"
            stage_result["blocked_reason"] = str(e)
            print(f"  BLOCKED: {e}")
            all_ok = False

        report["stages"][stage] = stage_result

    report["status"] = "PASS" if all_ok else "BLOCKED"
    return report


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    report = run_smoke()

    json_path = OUT_DIR / "specter2_answer_smoke.json"
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"\n  → {json_path.relative_to(ROOT)}")

    _write_md(report)

    print(f"\n[{report['status']}] SPECTER2 smoke test")
    return 0 if report["status"] == "PASS" else 1


def _write_md(report: dict) -> None:
    lines = [
        "# SPECTER2 Answer Smoke Test",
        "",
        f"**Generated:** {report['generated_at']}",
        f"**Status:** `{report['status']}`",
        "",
        "## Benchmark Header",
        "",
        "| Field | Value |",
        "|-------|-------|",
        f"| branch | {report['branch']} |",
        f"| model | {report['embedding_model']} |",
        f"| dim | {report['embedding_dim']} |",
        f"| top_k | {report['top_k']} |",
        f"| query | {report['smoke_query']} |",
        "",
        "## Stage Results",
        "",
    ]
    for stage, r in report.get("stages", {}).items():
        lines += [
            f"### {stage}",
            "",
            f"**Collection:** `{r['collection']}`  ",
            f"**Status:** `{r['status']}`  ",
            f"**Hits:** {r.get('hit_count', 0)}  ",
            f"**Latency:** {r.get('latency_s', '-')}s",
            "",
        ]
        top_hits = r.get("top_hits", [])
        if top_hits:
            lines += [
                "| # | paper_id | score | preview |",
                "|---|----------|-------|---------|",
            ]
            for i, h in enumerate(top_hits[:5]):
                prev = h.get("content_preview", "")[:100].replace("|", "\\|")
                lines.append(f"| {i+1} | {h['paper_id']} | {h['score']} | {prev} |")
            lines.append("")

    md_path = OUT_DIR / "specter2_answer_smoke.md"
    md_path.write_text("\n".join(lines))
    print(f"  → {md_path.relative_to(ROOT)}")


if __name__ == "__main__":
    sys.exit(main())
