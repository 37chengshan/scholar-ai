#!/usr/bin/env python3
"""SPECTER2 Full Benchmark — Gate 7.

Runs all golden queries × 3 stages (raw/rule/llm) using SPECTER2.
Uses queries from artifacts/benchmarks/v2.1/qwen_dual/golden_queries_v2.1.json.

Metrics computed:
  - MRR@5, MRR@10
  - Hit@1, Hit@3, Hit@5
  - Precision@5
  - Mean latency

Usage:
  python scripts/evals/specter2_full_benchmark.py
  python scripts/evals/specter2_full_benchmark.py --stage raw
  python scripts/evals/specter2_full_benchmark.py --limit-queries 10

Output:
  artifacts/benchmarks/specter2_v2_1_20/specter2_answer_raw.json
  artifacts/benchmarks/specter2_v2_1_20/specter2_answer_rule.json
  artifacts/benchmarks/specter2_v2_1_20/specter2_answer_llm.json
  artifacts/benchmarks/specter2_v2_1_20/specter2_answer_comparison.json
  artifacts/benchmarks/specter2_v2_1_20/specter2_scientific_line_report.md
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent.parent
API_ROOT = ROOT / "apps" / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

OUT_DIR = ROOT / "artifacts/benchmarks/specter2_v2_1_20"
GOLDEN_QUERIES_PATH = (
    ROOT / "artifacts/benchmarks/v2.1/qwen_dual/golden_queries_v2.1.json"
)

EXPECTED_DIM = 768
TOP_K = 10

SPECTER2_COLLECTIONS = {
    "raw": "paper_contents_v2_specter2_raw_v2_1",
    "rule": "paper_contents_v2_specter2_rule_v2_1",
    "llm": "paper_contents_v2_specter2_llm_v2_1",
}

SEARCH_PARAMS = {"metric_type": "COSINE", "params": {"nprobe": 10}}


# ── Metrics ──────────────────────────────────────────────────────────────────

def compute_mrr(hits: list[str], expected_paper_ids: list[str], k: int = 5) -> float:
    for rank, paper_id in enumerate(hits[:k], start=1):
        if paper_id in expected_paper_ids:
            return 1.0 / rank
    return 0.0


def compute_hit_at_k(hits: list[str], expected_paper_ids: list[str], k: int) -> bool:
    return any(p in expected_paper_ids for p in hits[:k])


def compute_precision_at_k(hits: list[str], expected_paper_ids: list[str], k: int = 5) -> float:
    relevant = sum(1 for p in hits[:k] if p in expected_paper_ids)
    return relevant / k if k > 0 else 0.0


def compute_metrics(hits: list[str], expected_paper_ids: list[str]) -> dict:
    return {
        "mrr_5": round(compute_mrr(hits, expected_paper_ids, 5), 4),
        "mrr_10": round(compute_mrr(hits, expected_paper_ids, 10), 4),
        "hit_1": compute_hit_at_k(hits, expected_paper_ids, 1),
        "hit_3": compute_hit_at_k(hits, expected_paper_ids, 3),
        "hit_5": compute_hit_at_k(hits, expected_paper_ids, 5),
        "precision_5": round(compute_precision_at_k(hits, expected_paper_ids, 5), 4),
    }


def aggregate_metrics(per_query: list[dict]) -> dict:
    if not per_query:
        return {}
    n = len(per_query)
    return {
        "query_count": n,
        "mrr_5": round(sum(q["mrr_5"] for q in per_query) / n, 4),
        "mrr_10": round(sum(q["mrr_10"] for q in per_query) / n, 4),
        "hit_1": round(sum(1 for q in per_query if q["hit_1"]) / n, 4),
        "hit_3": round(sum(1 for q in per_query if q["hit_3"]) / n, 4),
        "hit_5": round(sum(1 for q in per_query if q["hit_5"]) / n, 4),
        "precision_5": round(sum(q["precision_5"] for q in per_query) / n, 4),
        "mean_latency_s": round(
            sum(q.get("latency_s", 0) for q in per_query) / n, 3
        ),
    }


# ── Load queries ──────────────────────────────────────────────────────────────

def load_all_queries() -> list[dict]:
    data = json.loads(GOLDEN_QUERIES_PATH.read_text())
    queries = []
    for paper in data.get("papers", []):
        for q in paper.get("queries", []):
            q.setdefault("expected_paper_ids", [paper["paper_id"]])
            queries.append(q)
    for q in data.get("cross_paper_queries", []):
        queries.append(q)
    for q in data.get("multimodal_queries", []):
        queries.append(q)
    return queries


# ── Run one stage ─────────────────────────────────────────────────────────────

def run_stage(
    stage: str,
    queries: list[dict],
    vec_cache: dict[str, list[float]],
    svc_embed: Any,
    col: Any,
    top_k: int = TOP_K,
) -> dict:
    per_query = []
    t_start = time.time()

    for i, q in enumerate(queries):
        query_text = q["query"]

        # Encode (cached)
        if query_text not in vec_cache:
            vec_cache[query_text] = svc_embed.generate_embedding(query_text)
        vec = vec_cache[query_text]

        expected_paper_ids = set(q.get("expected_paper_ids", []))

        t0 = time.time()
        try:
            results = col.search(
                data=[vec],
                anns_field="embedding",
                param=SEARCH_PARAMS,
                limit=top_k,
                output_fields=["paper_id", "source_chunk_id"],
            )
            elapsed = round(time.time() - t0, 3)
            hits = results[0] if results else []
            hit_paper_ids = [h.entity.get("paper_id", "") for h in hits]
        except Exception as e:
            hit_paper_ids = []
            elapsed = round(time.time() - t0, 3)
            print(f"  [ERROR] query {i} '{query_text[:40]}': {e}", file=sys.stderr)

        metrics = compute_metrics(hit_paper_ids, list(expected_paper_ids))
        metrics["query_id"] = q.get("id", f"q{i}")
        metrics["query_text"] = query_text
        metrics["latency_s"] = elapsed
        metrics["expected_paper_ids"] = list(expected_paper_ids)
        metrics["retrieved_paper_ids"] = hit_paper_ids[:5]
        per_query.append(metrics)

        if (i + 1) % 10 == 0:
            print(f"  [{stage}] {i+1}/{len(queries)} done")

    total_elapsed = round(time.time() - t_start, 1)
    agg = aggregate_metrics(per_query)
    agg["total_time_s"] = total_elapsed
    print(
        f"  [{stage}] done | MRR@5={agg['mrr_5']} | Hit@5={agg['hit_5']} | "
        f"latency={agg['mean_latency_s']}s/q | total={total_elapsed}s"
    )
    return {"aggregate": agg, "per_query": per_query}


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description="SPECTER2 full benchmark")
    parser.add_argument("--stage", choices=["raw", "rule", "llm", "all"], default="all")
    parser.add_argument("--limit-queries", type=int, default=0)
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("SPECTER2 Full Benchmark — Gate 7")
    print("=" * 70)

    # Load queries
    queries = load_all_queries()
    if args.limit_queries > 0:
        queries = queries[: args.limit_queries]
    print(f"  Loaded {len(queries)} queries")

    # Load model
    print("\nLoading SPECTER2 model (adhoc_query) ...")
    from app.core.specter2_embedding_service import Specter2EmbeddingService

    svc_embed = Specter2EmbeddingService(adapter="adhoc_query")
    svc_embed._load_model()
    print("  Model loaded.")

    # Verify dim
    probe = svc_embed.generate_embedding("test")
    assert len(probe) == EXPECTED_DIM, f"dim mismatch: {len(probe)}"

    # Connect Milvus
    from app.core.milvus_service import get_milvus_service
    from pymilvus import Collection, utility

    svc_milvus = get_milvus_service()
    svc_milvus.connect()
    alias = svc_milvus._alias

    # Determine stages
    stages_to_run = ["raw", "rule", "llm"] if args.stage == "all" else [args.stage]

    results: dict[str, Any] = {}
    vec_cache: dict[str, list[float]] = {}
    ts = datetime.now(timezone.utc).isoformat()

    for stage in stages_to_run:
        col_name = SPECTER2_COLLECTIONS[stage]
        print(f"\nStage={stage} | {col_name}")

        if not utility.has_collection(col_name, using=alias):
            print(f"  SKIP: collection not found")
            results[stage] = {
                "status": "SKIPPED",
                "reason": f"collection not found: {col_name}",
            }
            continue

        col = Collection(col_name, using=alias)
        col.load()

        stage_result = run_stage(
            stage=stage,
            queries=queries,
            vec_cache=vec_cache,
            svc_embed=svc_embed,
            col=col,
            top_k=TOP_K,
        )
        stage_result["collection"] = col_name
        stage_result["status"] = "DONE"
        stage_result["generated_at"] = ts
        results[stage] = stage_result

        # Write per-stage output
        out_file = OUT_DIR / f"specter2_answer_{stage}.json"
        out_file.write_text(
            json.dumps(
                {"generated_at": ts, "stage": stage, **stage_result},
                indent=2,
                ensure_ascii=False,
            )
        )
        print(f"  → {out_file.relative_to(ROOT)}")

    # Write comparison
    comparison = {
        "generated_at": ts,
        "query_count": len(queries),
        "embedding_model": "allenai/specter2_base",
        "embedding_dim": EXPECTED_DIM,
        "top_k": TOP_K,
        "stages": {
            stage: r.get("aggregate", {})
            for stage, r in results.items()
        },
    }
    comp_path = OUT_DIR / "specter2_answer_comparison.json"
    comp_path.write_text(json.dumps(comparison, indent=2, ensure_ascii=False))
    print(f"\n  → {comp_path.relative_to(ROOT)}")

    _write_final_report(comparison, results)

    print(f"\n[DONE] SPECTER2 full benchmark complete.")
    return 0


def _write_final_report(comparison: dict, results: dict) -> None:
    ts = comparison["generated_at"]
    lines = [
        "# SPECTER2 Scientific Line Report",
        "",
        f"**Generated:** {ts}",
        f"**Model:** `{comparison['embedding_model']}`",
        f"**Dim:** {comparison['embedding_dim']}",
        f"**Queries:** {comparison['query_count']}",
        f"**Top-K:** {comparison['top_k']}",
        "",
        "## Aggregate Metrics by Stage",
        "",
        "| Stage | MRR@5 | MRR@10 | Hit@1 | Hit@3 | Hit@5 | P@5 | Latency |",
        "|-------|-------|--------|-------|-------|-------|-----|---------|",
    ]
    for stage, agg in comparison.get("stages", {}).items():
        if not agg:
            continue
        lines.append(
            f"| {stage} | {agg.get('mrr_5','–')} | {agg.get('mrr_10','–')} | "
            f"{agg.get('hit_1','–')} | {agg.get('hit_3','–')} | {agg.get('hit_5','–')} | "
            f"{agg.get('precision_5','–')} | {agg.get('mean_latency_s','–')}s |"
        )
    lines += [
        "",
        "## Stage Summary",
        "",
    ]
    for stage, r in results.items():
        if r.get("status") == "SKIPPED":
            lines.append(f"- **{stage}**: SKIPPED — {r.get('reason', '')}")
        else:
            agg = r.get("aggregate", {})
            lines.append(
                f"- **{stage}**: MRR@5={agg.get('mrr_5','–')}, "
                f"Hit@5={agg.get('hit_5','–')}, "
                f"Queries={agg.get('query_count','–')}"
            )

    lines += [
        "",
        "## Notes",
        "",
        "- SPECTER2 uses `allenai/specter2_base` base model (no adapter library).",
        "- Adapter type: `adhoc_query` (short query retrieval).",
        "- Collections indexed with COSINE IVF_FLAT (nlist=128).",
        "- Search params: nprobe=10.",
        "",
    ]

    md_path = OUT_DIR / "specter2_scientific_line_report.md"
    md_path.write_text("\n".join(lines))
    print(f"  → {md_path.relative_to(ROOT)}")


if __name__ == "__main__":
    sys.exit(main())
