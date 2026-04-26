#!/usr/bin/env python3
"""SPECTER2 Scientific-Index Benchmark.

Queries the new scientific Milvus collection(s) using the *adhoc_query* adapter
and reports MRR@5, Hit@5, Hit@3, Hit@1, Precision@5 per stage.

Defaults to the sci_full collection (1272 chunks, reference-filtered).
Supports --collection to point at anchor or original collections.

Usage:
  SPECTER2_MODEL_DIR=/Users/cc/models/specter2 \\
  python scripts/evals/specter2_sci_benchmark.py

  # anchor-only collection
  SPECTER2_MODEL_DIR=/Users/cc/models/specter2 \\
  python scripts/evals/specter2_sci_benchmark.py \\
    --collection paper_contents_v2_specter2_sci_anchor_v2_1

  # run only per-paper queries (40 queries)
  python scripts/evals/specter2_sci_benchmark.py --query-types single_topic single_method

  # run 40 per-paper + 24 first cross-paper = 64 (approximate "64 queries")
  python scripts/evals/specter2_sci_benchmark.py --limit 64
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent.parent
API_ROOT = ROOT / "apps" / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

GOLDEN_PATH = ROOT / "artifacts/benchmarks/v2.1/qwen_dual/golden_queries_v2.1.json"
OUT_DIR = ROOT / "artifacts/benchmarks/specter2_v2_1_20"

DEFAULT_COLLECTION = "paper_contents_v2_specter2_sci_full_v2_1"
TOP_K = 5


# ── Query loading ──────────────────────────────────────────────────────────────

def load_queries(query_types: list[str] | None, limit: int | None) -> list[dict]:
    data = json.loads(GOLDEN_PATH.read_text())
    queries: list[dict] = []
    for paper in data.get("papers", []):
        pid = paper["paper_id"]
        for q in paper.get("queries", []):
            q.setdefault("expected_paper_ids", [pid])
            queries.append(q)
    for q in data.get("cross_paper_queries", []):
        queries.append(q)
    for q in data.get("multimodal_queries", []):
        queries.append(q)

    if query_types:
        queries = [q for q in queries if q.get("query_type", "") in query_types]

    if limit:
        queries = queries[:limit]

    return queries


def parse_ids(raw) -> list[str]:
    if isinstance(raw, list):
        return raw
    if isinstance(raw, str):
        try:
            return ast.literal_eval(raw)
        except Exception:
            return [raw] if raw else []
    return []


# ── Metrics ───────────────────────────────────────────────────────────────────

def reciprocal_rank(result_ids: list[str], expected_ids: list[str]) -> float:
    for rank, rid in enumerate(result_ids, start=1):
        if rid in expected_ids:
            return 1.0 / rank
    return 0.0


def compute_metrics(per_query: list[dict]) -> dict:
    n = len(per_query)
    if n == 0:
        return {}
    return {
        "n": n,
        "mrr_5": round(sum(q["rr"] for q in per_query) / n, 4),
        "hit_1": round(sum(1 for q in per_query if q["hit_1"]) / n, 4),
        "hit_3": round(sum(1 for q in per_query if q["hit_3"]) / n, 4),
        "hit_5": round(sum(1 for q in per_query if q["hit_5"]) / n, 4),
        "precision_5": round(sum(q["precision_5"] for q in per_query) / n, 4),
        "mean_latency_s": round(sum(q.get("latency_s", 0) for q in per_query) / n, 3),
    }


# ── Single-query search ────────────────────────────────────────────────────────

def search_query(query: dict, svc, col, top_k: int) -> dict:
    q_text = query["query"]
    t0 = time.time()
    emb = svc.generate_embeddings_batch([q_text])[0]
    results = col.search(
        data=[emb],
        anns_field="embedding",
        param={"metric_type": "COSINE", "params": {"nprobe": 10}},
        limit=top_k,
        output_fields=["paper_id", "source_chunk_id", "section"],
    )
    latency = time.time() - t0

    hits = results[0] if results else []
    result_paper_ids = [h.entity.get("paper_id", "") for h in hits]
    result_chunk_ids = [h.entity.get("source_chunk_id", "") for h in hits]

    expected_paper_ids = parse_ids(query.get("expected_paper_ids", []))
    expected_chunk_ids = parse_ids(query.get("expected_chunk_ids", []))

    # Use paper-level matching if no chunk-level ground truth
    if expected_chunk_ids:
        rr = reciprocal_rank(result_chunk_ids, expected_chunk_ids)
        hit_1 = result_chunk_ids[:1] and any(c in expected_chunk_ids for c in result_chunk_ids[:1])
        hit_3 = any(c in expected_chunk_ids for c in result_chunk_ids[:3])
        hit_5 = any(c in expected_chunk_ids for c in result_chunk_ids[:5])
        prec5 = sum(1 for c in result_chunk_ids[:5] if c in expected_chunk_ids) / top_k
    else:
        # paper-level fallback
        rr = reciprocal_rank(result_paper_ids, expected_paper_ids)
        hit_1 = bool(result_paper_ids[:1]) and any(p in expected_paper_ids for p in result_paper_ids[:1])
        hit_3 = any(p in expected_paper_ids for p in result_paper_ids[:3])
        hit_5 = any(p in expected_paper_ids for p in result_paper_ids[:5])
        prec5 = sum(1 for p in result_paper_ids[:5] if p in expected_paper_ids) / top_k

    return {
        "query_id": query.get("id", ""),
        "query_type": query.get("query_type", ""),
        "rr": rr,
        "hit_1": hit_1,
        "hit_3": hit_3,
        "hit_5": hit_5,
        "precision_5": prec5,
        "latency_s": latency,
        "result_paper_ids": result_paper_ids[:5],
        "expected_paper_ids": expected_paper_ids,
    }


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--collection", default=DEFAULT_COLLECTION,
                        help="Milvus collection to benchmark against")
    parser.add_argument("--query-types", nargs="*", default=None,
                        help="Filter by query_type(s). E.g. single_topic single_method cross_paper")
    parser.add_argument("--limit", type=int, default=None,
                        help="Limit total number of queries (e.g. 64)")
    parser.add_argument("--top-k", type=int, default=TOP_K)
    parser.add_argument("--out-tag", default="",
                        help="Optional tag appended to output filename")
    args = parser.parse_args()

    # ── Load queries
    queries = load_queries(args.query_types, args.limit)
    print(f"Queries: {len(queries)}", end="")
    if args.query_types:
        print(f" (types: {args.query_types})", end="")
    if args.limit:
        print(f" (limit: {args.limit})", end="")
    print()

    # ── Connect Milvus
    from pymilvus import Collection, connections
    connections.connect(alias="scholarai", host="localhost", port="19530")
    col = Collection(args.collection, using="scholarai")
    col.load()
    print(f"Collection: {args.collection} ({col.num_entities} entities)")

    # ── Load SPECTER2 with adhoc_query adapter
    print("Loading SPECTER2 adhoc_query adapter...")
    from app.core.specter2_embedding_service import Specter2EmbeddingService
    svc = Specter2EmbeddingService(adapter="adhoc_query")
    svc._load_model()
    print(f"  adapter: {getattr(svc._model, 'active_adapters', 'base')}")

    # ── Run benchmark
    print(f"\nRunning {len(queries)} queries (top_k={args.top_k})...")
    per_query = []
    for i, q in enumerate(queries, 1):
        result = search_query(q, svc, col, args.top_k)
        per_query.append(result)
        rr = result["rr"]
        qtype = result["query_type"]
        if i % 10 == 0 or i == len(queries):
            partial_mrr = sum(r["rr"] for r in per_query) / len(per_query)
            print(f"  [{i:3d}/{len(queries)}] running MRR@5={partial_mrr:.4f}")

    metrics = compute_metrics(per_query)

    # Per-type breakdown
    type_metrics = {}
    for qt in sorted({q.get("query_type", "") for q in per_query}):
        subset = [q for q in per_query if q.get("query_type", "") == qt]
        if subset:
            type_metrics[qt] = compute_metrics(subset)

    print(f"\n{'='*60}")
    print(f"Collection : {args.collection}")
    print(f"Queries    : {metrics['n']}")
    print(f"MRR@5      : {metrics['mrr_5']}")
    print(f"Hit@1      : {metrics['hit_1']}")
    print(f"Hit@3      : {metrics['hit_3']}")
    print(f"Hit@5      : {metrics['hit_5']}")
    print(f"Precision@5: {metrics['precision_5']}")
    print(f"Avg latency: {metrics['mean_latency_s']}s")
    print()
    for qt, tm in type_metrics.items():
        print(f"  [{qt}] n={tm['n']} MRR@5={tm['mrr_5']} Hit@5={tm['hit_5']}")
    print("="*60)

    # Save report
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    col_short = args.collection.replace("paper_contents_v2_", "").replace("_v2_1", "")
    tag = f"_{args.out_tag}" if args.out_tag else ""
    report_path = OUT_DIR / f"specter2_sci_benchmark_{col_short}{tag}.json"
    md_path = report_path.with_suffix(".md")

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "collection": args.collection,
        "query_types_filter": args.query_types,
        "query_limit": args.limit,
        "top_k": args.top_k,
        "metrics": metrics,
        "by_type": type_metrics,
        "per_query": per_query,
    }
    report_path.write_text(json.dumps(report, indent=2))

    md = f"""# SPECTER2 Scientific Benchmark

**Collection**: `{args.collection}`  
**Queries**: {metrics['n']}  
**Generated**: {report['generated_at']}  

## Summary Metrics

| Metric | Score |
|--------|-------|
| MRR@5 | **{metrics['mrr_5']}** |
| Hit@1 | {metrics['hit_1']} |
| Hit@3 | {metrics['hit_3']} |
| Hit@5 | {metrics['hit_5']} |
| Precision@5 | {metrics['precision_5']} |
| Avg Latency | {metrics['mean_latency_s']}s |

## By Query Type

| Type | N | MRR@5 | Hit@5 |
|------|---|-------|-------|
"""
    for qt, tm in type_metrics.items():
        md += f"| {qt} | {tm['n']} | {tm['mrr_5']} | {tm['hit_5']} |\n"
    md_path.write_text(md)

    print(f"\nReport saved:")
    print(f"  JSON: {report_path}")
    print(f"  MD  : {md_path}")


if __name__ == "__main__":
    main()
