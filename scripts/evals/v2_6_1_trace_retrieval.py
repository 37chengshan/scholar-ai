#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Dict, List

from pymilvus import Collection

from scripts.evals.v2_6_1_common import (
    DEFAULT_GOLDEN_PATH,
    connect_milvus,
    ensure_output_dir,
    load_provider,
    load_regression_rows,
    run_dense_search,
    stage_collection,
    write_jsonl,
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Step6.1 task C: retrieval trace 16x3")
    p.add_argument("--golden-path", default=str(DEFAULT_GOLDEN_PATH))
    p.add_argument("--collection-suffix", default="v2_4")
    p.add_argument("--milvus-host", default="localhost")
    p.add_argument("--milvus-port", type=int, default=19530)
    p.add_argument("--top-k", type=int, default=10)
    return p.parse_args()


def _dim(collection: Collection) -> int:
    for field in collection.schema.fields:
        if field.name == "embedding":
            return int((field.params or {}).get("dim", 0))
    return 0


def _field_source_label(hits: List[Dict[str, Any]]) -> str:
    values = sorted({str(h.get("source_chunk_id_field_source") or "unknown") for h in hits})
    if not values:
        return "unknown"
    if len(values) == 1:
        return values[0]
    return "|".join(values)


def main() -> int:
    args = parse_args()
    out_dir = ensure_output_dir()
    rows = load_regression_rows(Path(args.golden_path), max_queries=16)

    provider = load_provider()
    connect_milvus(alias="v261_c", host=args.milvus_host, port=args.milvus_port)

    traces: List[Dict[str, Any]] = []
    for stage in ["raw", "rule", "llm"]:
        collection_name = stage_collection(stage, args.collection_suffix)
        col = Collection(collection_name, using="v261_c")
        col.load()
        collection_dim = _dim(col)

        for row in rows:
            errors: List[str] = []
            query_vector = provider.embed_texts([row.query])[0]
            query_dim = len(query_vector)
            search_expr = "indexable == true"

            hits: List[Dict[str, Any]] = []
            try:
                hits = run_dense_search(
                    collection=col,
                    query_vector=query_vector,
                    top_k=args.top_k,
                    expr=search_expr,
                    output_fields=[
                        "source_chunk_id",
                        "paper_id",
                        "section",
                        "content_type",
                        "anchor_text",
                        "raw_data",
                    ],
                )
            except Exception as exc:  # noqa: BLE001
                errors.append(str(exc))

            expected_sources = set(row.expected_source_chunk_ids)
            expected_papers = set(row.expected_paper_ids)
            expected_sections = set(row.expected_sections)
            expected_types = set(row.expected_content_types)

            retrieved_source_ids = [str(h.get("source_chunk_id") or "") for h in hits]
            retrieved_papers = [str(h.get("paper_id") or "") for h in hits]
            retrieved_sections = [str(h.get("section") or "") for h in hits]
            retrieved_types = [str(h.get("content_type") or "") for h in hits]

            source_hit = len(expected_sources & set(retrieved_source_ids))
            paper_hit = len(expected_papers & set(retrieved_papers))
            section_hit = len(expected_sections & set(retrieved_sections))
            type_hit = len(expected_types & set(retrieved_types))

            traces.append(
                {
                    "query_id": row.query_id,
                    "query_family": row.query_family,
                    "stage": stage,
                    "collection": collection_name,
                    "query_text": row.query,
                    "embedding_provider": provider.name(),
                    "embedding_model": provider.model_name(),
                    "query_dim": query_dim,
                    "collection_dim": collection_dim,
                    "search_expr": search_expr,
                    "top_k": args.top_k,
                    "expected_source_chunk_ids": row.expected_source_chunk_ids,
                    "expected_paper_ids": row.expected_paper_ids,
                    "expected_sections": row.expected_sections,
                    "expected_content_types": row.expected_content_types,
                    "retrieved_source_chunk_ids": retrieved_source_ids,
                    "retrieved_paper_ids": retrieved_papers,
                    "retrieved_sections": retrieved_sections,
                    "retrieved_content_types": retrieved_types,
                    "retrieved_anchor_texts": [str(h.get("anchor_text") or "") for h in hits],
                    "raw_hit_ids": [str(h.get("milvus_id") or "") for h in hits],
                    "source_chunk_id_field_source": _field_source_label(hits),
                    "recall_at_10": round(source_hit / max(len(expected_sources), 1), 4),
                    "paper_hit_rate": round(paper_hit / max(len(expected_papers), 1), 4),
                    "section_hit_rate": round(section_hit / max(len(expected_sections), 1), 4),
                    "content_type_hit_rate": round(type_hit / max(len(expected_types), 1), 4),
                    "errors": errors,
                }
            )

    out_path = out_dir / "retrieval_trace_16x3.jsonl"
    write_jsonl(out_path, traces)
    print(out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
