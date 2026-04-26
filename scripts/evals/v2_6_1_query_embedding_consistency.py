#!/usr/bin/env python3
from __future__ import annotations

import argparse
import random
from pathlib import Path
from typing import Any, Dict, List

from pymilvus import Collection, connections

from scripts.evals.v2_6_1_common import cosine_similarity, ensure_output_dir, load_provider, read_json, vector_norm, write_json_report, write_md_report


ROOT = Path(__file__).resolve().parents[2]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Step6.1 task E: query embedding consistency")
    p.add_argument("--collection-suffix", default="v2_4")
    p.add_argument("--milvus-host", default="localhost")
    p.add_argument("--milvus-port", type=int, default=19530)
    p.add_argument("--corpus-sample", type=int, default=200)
    return p.parse_args()


def _dim(col: Collection) -> int:
    for field in col.schema.fields:
        if field.name == "embedding":
            return int((field.params or {}).get("dim", 0))
    return 0


def main() -> int:
    args = parse_args()
    out_dir = ensure_output_dir()

    provider_probe = read_json(ROOT / "artifacts" / "benchmarks" / "v2_4" / "provider_probe.json")
    ingest_report = read_json(ROOT / "artifacts" / "benchmarks" / "v2_4" / "api_flash_ingest_report.json")

    provider = load_provider()
    planned_model = "tongyi-embedding-vision-flash-2026-03-06"
    resolved_model = provider.model_name()

    sample_text = "ScholarAI v2.6.1 embedding consistency probe"
    vectors = provider.embed_texts([sample_text] * 5)
    norms = [vector_norm(v) for v in vectors]
    pair_cos: List[float] = []
    for i in range(len(vectors)):
        for j in range(i + 1, len(vectors)):
            pair_cos.append(cosine_similarity(vectors[i], vectors[j]))

    connections.connect(alias="v261_e", host=args.milvus_host, port=args.milvus_port)
    raw_collection = Collection(f"paper_contents_v2_api_tongyi_flash_raw_{args.collection_suffix}", using="v261_e")
    raw_collection.load()
    collection_dim = _dim(raw_collection)

    rows = raw_collection.query(expr="id >= 0", output_fields=["embedding"], limit=max(args.corpus_sample, 50))
    random.shuffle(rows)
    sample_rows = rows[: args.corpus_sample]
    corpus_norms = [vector_norm(list(r.get("embedding") or [])) for r in sample_rows if list(r.get("embedding") or [])]

    alias_used = planned_model != resolved_model
    dim_match = len(vectors[0]) == collection_dim if vectors else False
    embedding_space_mismatch = not dim_match

    report = {
        "status": "PASS" if not embedding_space_mismatch else "BLOCKED",
        "blocked_categories": ["EMBEDDING_SPACE_MISMATCH"] if embedding_space_mismatch else [],
        "provider_probe": {
            "provider": provider_probe.get("provider"),
            "requested_model_name": provider_probe.get("model"),
            "probe_dimension": provider_probe.get("dimension"),
            "probe_status": provider_probe.get("status"),
        },
        "step6_runner_embedding": {
            "provider": provider.name(),
            "requested_model_name": planned_model,
            "actual_model_name": resolved_model,
            "alias_used": alias_used,
            "query_embedding_dim": len(vectors[0]) if vectors else 0,
        },
        "collection_embedding": {
            "collection": f"paper_contents_v2_api_tongyi_flash_raw_{args.collection_suffix}",
            "collection_dim": collection_dim,
            "ingest_requested_model_name": ingest_report.get("model"),
            "ingest_provider": ingest_report.get("provider"),
        },
        "same_text_repeatability": {
            "sample_count": len(vectors),
            "norm_min": min(norms) if norms else 0.0,
            "norm_max": max(norms) if norms else 0.0,
            "pairwise_cosine_min": min(pair_cos) if pair_cos else 0.0,
            "pairwise_cosine_max": max(pair_cos) if pair_cos else 0.0,
            "pairwise_cosine_avg": sum(pair_cos) / max(len(pair_cos), 1),
        },
        "embedding_norm_diagnostics": {
            "query_norm_min": min(norms) if norms else 0.0,
            "query_norm_max": max(norms) if norms else 0.0,
            "query_norm_avg": sum(norms) / max(len(norms), 1),
            "corpus_norm_min": min(corpus_norms) if corpus_norms else 0.0,
            "corpus_norm_max": max(corpus_norms) if corpus_norms else 0.0,
            "corpus_norm_avg": sum(corpus_norms) / max(len(corpus_norms), 1),
            "corpus_sample_size": len(corpus_norms),
        },
        "dim_match": dim_match,
        "embedding_space_mismatch": embedding_space_mismatch,
    }

    json_path = out_dir / "query_embedding_consistency_report.json"
    md_path = out_dir / "query_embedding_consistency_report.md"
    write_json_report(json_path, report)

    lines = [
        f"- status: {report['status']}",
        f"- blocked_categories: {', '.join(report['blocked_categories']) if report['blocked_categories'] else 'none'}",
        f"- provider_probe_model: {report['provider_probe']['requested_model_name']}",
        f"- step6_requested_model: {report['step6_runner_embedding']['requested_model_name']}",
        f"- step6_actual_model: {report['step6_runner_embedding']['actual_model_name']}",
        f"- alias_used: {report['step6_runner_embedding']['alias_used']}",
        f"- collection_dim: {report['collection_embedding']['collection_dim']}",
        f"- query_embedding_dim: {report['step6_runner_embedding']['query_embedding_dim']}",
        f"- dim_match: {report['dim_match']}",
        f"- embedding_space_mismatch: {report['embedding_space_mismatch']}",
    ]
    write_md_report(md_path, "Step6.1 Query Embedding Consistency Report", lines)
    print(json_path)
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
