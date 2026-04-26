#!/usr/bin/env python3
"""SPECTER2 Scientific Index Builder.

Builds a deduplicated, high-signal Milvus collection for SPECTER2:
  1. Filters out Reference / Bibliography chunks (heuristic: high citation density)
  2. Optionally restricts to scientific-anchor sections (abstract, intro, conclusion, ...)
  3. Uses local adapters via SPECTER2_MODEL_DIR (proximity adapter for docs)

Collection names:
  paper_contents_v2_specter2_sci_full_v2_1   — all chunks minus references
  paper_contents_v2_specter2_sci_anchor_v2_1 — only abstract/intro/conclusion/discussion

Usage:
  SPECTER2_MODEL_DIR=/Users/cc/models/specter2 \\
  python scripts/evals/build_specter2_scientific_index.py --mode full
  
  SPECTER2_MODEL_DIR=/Users/cc/models/specter2 \\
  python scripts/evals/build_specter2_scientific_index.py --mode anchor
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
API_ROOT = ROOT / "apps" / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

OUT_DIR = ROOT / "artifacts/benchmarks/specter2_v2_1_20"
RAW_CHUNKS_PATH = ROOT / "artifacts/benchmarks/v2.1/raw_base/raw_chunks.jsonl"

SPECTER2_DIM = 768

COLLECTIONS = {
    "full": "paper_contents_v2_specter2_sci_full_v2_1",
    "anchor": "paper_contents_v2_specter2_sci_anchor_v2_1",
}

# Sections considered high-signal "scientific anchor"
ANCHOR_SECTIONS = {"abstract", "introduction", "conclusion", "conclusions", "discussion",
                   "related work", "related works", "summary"}

# Reference heuristic thresholds
REF_BRACKET_THRESHOLD = 5   # more than N "[123]" citations in chunk → likely ref list
REF_DOI_THRESHOLD = 2       # more than N "doi:" occurrences
REF_ETAL_DENSE_THRESHOLD = 3  # more than N "et al" in short chunk (<300 words)


# ── Filter helpers ─────────────────────────────────────────────────────────────

def is_reference_chunk(chunk: dict) -> bool:
    """Return True if chunk looks like a bibliography/reference list entry."""
    sp = chunk.get("section_path", "").lower().strip()
    # explicit section name check
    if any(kw in sp for kw in ("reference", "bibliography", "works cited", "citations")):
        return True
    txt = chunk.get("raw_chunk_text", "")
    words = len(txt.split())
    bracket_refs = len(re.findall(r"\[\d+\]", txt))
    doi_count = txt.lower().count("doi:")
    etal_count = txt.lower().count(" et al")
    if bracket_refs > REF_BRACKET_THRESHOLD:
        return True
    if doi_count > REF_DOI_THRESHOLD:
        return True
    if etal_count > REF_ETAL_DENSE_THRESHOLD and words < 300:
        return True
    return False


def is_anchor_chunk(chunk: dict) -> bool:
    """Return True if chunk is in a scientific-anchor section."""
    sp = chunk.get("section_path", "").lower().strip()
    return sp in ANCHOR_SECTIONS


def load_and_filter_chunks(mode: str) -> tuple[list[dict], dict]:
    raw_chunks = []
    with open(RAW_CHUNKS_PATH) as f:
        for line in f:
            line = line.strip()
            if line:
                raw_chunks.append(json.loads(line))

    total = len(raw_chunks)
    ref_filtered = [c for c in raw_chunks if not is_reference_chunk(c)]
    ref_removed = total - len(ref_filtered)

    if mode == "anchor":
        kept = [c for c in ref_filtered if is_anchor_chunk(c)]
    else:
        kept = ref_filtered

    stats = {
        "total_input": total,
        "ref_removed": ref_removed,
        "after_ref_filter": len(ref_filtered),
        "anchor_kept": len(kept) if mode == "anchor" else None,
        "final_count": len(kept),
        "mode": mode,
    }
    return kept, stats


# ── Milvus helpers ─────────────────────────────────────────────────────────────

def ensure_collection(col_name: str, dim: int):
    from pymilvus import Collection, CollectionSchema, DataType, FieldSchema, connections, utility

    connections.connect(alias="scholarai", host="localhost", port="19530")

    if utility.has_collection(col_name, using="scholarai"):
        print(f"  [drop] existing collection {col_name}")
        utility.drop_collection(col_name, using="scholarai")

    fields = [
        FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
        FieldSchema(name="source_chunk_id", dtype=DataType.VARCHAR, max_length=64),
        FieldSchema(name="paper_id", dtype=DataType.VARCHAR, max_length=64),
        FieldSchema(name="user_id", dtype=DataType.VARCHAR, max_length=64),
        FieldSchema(name="page_num", dtype=DataType.INT64),
        FieldSchema(name="section", dtype=DataType.VARCHAR, max_length=256),
        FieldSchema(name="content_type", dtype=DataType.VARCHAR, max_length=32),
        FieldSchema(name="content_data", dtype=DataType.VARCHAR, max_length=32000),
        FieldSchema(name="stage", dtype=DataType.VARCHAR, max_length=16),
        FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=dim),
    ]
    schema = CollectionSchema(fields=fields, description=f"SPECTER2 scientific index ({col_name})")
    col = Collection(name=col_name, schema=schema, using="scholarai")
    col.create_index(
        field_name="embedding",
        index_params={"metric_type": "COSINE", "index_type": "IVF_FLAT", "params": {"nlist": 128}},
    )
    col.load()
    print(f"  [created] {col_name} dim={dim}")
    return col


def ingest_chunks(col, chunks: list[dict], svc, batch_size: int = 32) -> int:
    inserted = 0
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        texts = [c.get("raw_chunk_text", "") for c in batch]
        embeddings = svc.generate_embeddings_batch(texts)
        records = []
        for c, emb in zip(batch, embeddings):
            records.append({
                "source_chunk_id": str(c.get("source_chunk_id", ""))[:64],
                "paper_id": str(c.get("paper_id", ""))[:64],
                "user_id": "system",
                "page_num": int(c.get("page_num", 0) or 0),
                "section": str(c.get("section_path", ""))[:256],
                "content_type": "text",
                "content_data": texts[batch.index(c)][:32000],
                "stage": "proximity",
                "embedding": emb,
            })
        col.insert(records)
        inserted += len(records)
        print(f"  inserted {inserted}/{len(chunks)}", end="\r", flush=True)
    print()
    return inserted


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Build SPECTER2 scientific index")
    parser.add_argument("--mode", choices=["full", "anchor"], default="full",
                        help="full = all chunks minus references; anchor = abstract/intro/conclusion only")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    # ── Load and filter chunks
    print(f"\n=== Loading chunks (mode={args.mode}) ===")
    chunks, stats = load_and_filter_chunks(args.mode)
    print(f"  total input     : {stats['total_input']}")
    print(f"  ref removed     : {stats['ref_removed']}")
    print(f"  after ref filter: {stats['after_ref_filter']}")
    if stats['anchor_kept'] is not None:
        print(f"  anchor kept     : {stats['anchor_kept']}")
    print(f"  final count     : {stats['final_count']}")

    if args.dry_run:
        # Show section distribution
        from collections import Counter
        sp_dist = Counter(c.get("section_path", "").lower() for c in chunks)
        print("\nSection distribution in final set:")
        for s, n in sp_dist.most_common(20):
            print(f"  {n:4d}  {s!r}")
        print("\n[dry-run] done")
        return

    # ── Load embedding service with proximity adapter
    print("\n=== Loading SPECTER2 (proximity adapter) ===")
    from app.core.specter2_embedding_service import Specter2EmbeddingService
    svc = Specter2EmbeddingService(adapter="proximity")
    svc._load_model()
    print(f"  adapter: {getattr(svc._model, 'active_adapters', 'base')}")

    # ── Create collection
    col_name = COLLECTIONS[args.mode]
    print(f"\n=== Creating collection: {col_name} ===")
    col = ensure_collection(col_name, SPECTER2_DIM)

    # ── Ingest
    print(f"\n=== Ingesting {len(chunks)} chunks ===")
    t0 = time.time()
    inserted = ingest_chunks(col, chunks, svc)
    # Ensure inserts are durable and num_entities is up to date.
    col.flush()
    elapsed = time.time() - t0
    print(f"  done: {inserted} records in {elapsed:.1f}s")
    print(f"  persisted entities: {col.num_entities}")

    # ── Save report
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": args.mode,
        "collection": col_name,
        "stats": stats,
        "inserted": inserted,
        "elapsed_seconds": round(elapsed, 2),
    }
    report_path = OUT_DIR / f"specter2_sci_{args.mode}_ingest_report.json"
    report_path.write_text(json.dumps(report, indent=2))
    print(f"\n  Report: {report_path}")
    print("  DONE")


if __name__ == "__main__":
    main()
