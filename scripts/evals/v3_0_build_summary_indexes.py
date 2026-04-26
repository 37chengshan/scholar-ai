#!/usr/bin/env python3
"""v3.0 Phase 1 — Build and validate summary indexes from artifact chunks.

Usage:
    python scripts/evals/v3_0_build_summary_indexes.py [--stage raw|rule|llm] [--validate]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
API_ROOT = ROOT / "apps" / "api"
for p in [str(API_ROOT), str(ROOT)]:
    if p not in sys.path:
        sys.path.insert(0, p)

ARTIFACT_PAPERS_ROOT = ROOT / "artifacts" / "papers"
OUTPUT_DIR = ROOT / "artifacts" / "benchmarks" / "v3_0"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build v3.0 summary indexes from artifact chunks")
    p.add_argument("--stage", choices=["raw", "rule", "llm"], default="raw")
    p.add_argument("--validate", action="store_true", help="Run quick search validation after build")
    return p.parse_args()


def main() -> int:
    args = parse_args()

    from app.rag_v3.indexes.artifact_loader import build_indexes_from_artifacts

    print(f"[v3.0 build-summary-indexes] stage={args.stage}")
    print(f"  Artifact root: {ARTIFACT_PAPERS_ROOT}")
    t0 = time.perf_counter()

    paper_index, section_index = build_indexes_from_artifacts(
        artifact_root=ARTIFACT_PAPERS_ROOT,
        stage=args.stage,
    )
    elapsed = time.perf_counter() - t0

    paper_ids = paper_index.all_paper_ids()
    print(f"\n  Papers indexed:   {len(paper_ids)}")
    print(f"  Sections indexed: {len(section_index)}")
    print(f"  Build time:       {elapsed:.2f}s")

    if len(paper_ids) == 0:
        print("\n[ERROR] No papers indexed. Check artifact path.", file=sys.stderr)
        return 1

    # Print paper summary samples
    print("\n  Sample paper summaries:")
    for pid in paper_ids[:3]:
        art = paper_index.get(pid)
        if art:
            print(f"    {pid}: title={art.title[:60]!r}  abstract_len={len(art.abstract)}")

    if args.validate:
        print("\n  Validation searches:")
        test_queries = [
            "transformer attention mechanism",
            "GPT language model pre-training",
            "BERT fine-tuning NLP",
            "benchmark evaluation accuracy",
        ]
        for q in test_queries:
            papers = paper_index.search(q, top_k=3)
            sections = section_index.search(q, top_k=3)
            print(f"    Q: {q!r}")
            print(f"      papers: {[p.paper_id for p in papers]}")
            print(f"      sections: {[s.section_id[:60] for s in sections]}")

    # Save index manifest
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest = {
        "version": "v3.0-phase1",
        "stage": args.stage,
        "paper_count": len(paper_ids),
        "section_count": len(section_index),
        "paper_ids": paper_ids,
        "build_time_sec": round(elapsed, 3),
    }
    manifest_path = OUTPUT_DIR / f"index_manifest_{args.stage}.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))
    print(f"\n  Manifest saved: {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
