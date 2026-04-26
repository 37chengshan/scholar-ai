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
    write_json_report,
    write_md_report,
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Step6.1 task F: filter expr diagnostic")
    p.add_argument("--golden-path", default=str(DEFAULT_GOLDEN_PATH))
    p.add_argument("--collection-suffix", default="v2_4")
    p.add_argument("--milvus-host", default="localhost")
    p.add_argument("--milvus-port", type=int, default=19530)
    p.add_argument("--top-k", type=int, default=10)
    return p.parse_args()


def _run_mode(col: Collection, query_vec: List[float], expr: str | None, top_k: int) -> Dict[str, Any]:
    hits = run_dense_search(
        collection=col,
        query_vector=query_vec,
        top_k=top_k,
        expr=expr,
        output_fields=["source_chunk_id", "paper_id", "section", "content_type", "raw_data"],
    )
    return {
        "expr": expr,
        "top10_source_chunk_ids": [str(h.get("source_chunk_id") or "") for h in hits],
        "top10_paper_ids": [str(h.get("paper_id") or "") for h in hits],
    }


def main() -> int:
    args = parse_args()
    out_dir = ensure_output_dir()
    rows = load_regression_rows(Path(args.golden_path), max_queries=16)
    provider = load_provider()
    connect_milvus(alias="v261_f", host=args.milvus_host, port=args.milvus_port)

    details: List[Dict[str, Any]] = []
    mode_stats = {
        "no_filter": {"hit": 0, "total": 0},
        "user_filter": {"hit": 0, "total": 0},
        "full_expr": {"hit": 0, "total": 0},
    }
    full_expr_suspect = 0

    for stage in ["raw", "rule", "llm"]:
        collection_name = stage_collection(stage, args.collection_suffix)
        col = Collection(collection_name, using="v261_f")
        col.load()

        for row in rows:
            vec = provider.embed_texts([row.query])[0]
            expected_sources = set(row.expected_source_chunk_ids)
            expected_papers = set(row.expected_paper_ids)

            no_filter = _run_mode(col, vec, None, args.top_k)
            user_filter = _run_mode(col, vec, "user_id == 'benchmark-user'", args.top_k)
            full_expr = _run_mode(col, vec, "indexable == true", args.top_k)

            def _recall(mode: Dict[str, Any]) -> float:
                got = set(mode["top10_source_chunk_ids"])
                return round(len(got & expected_sources) / max(len(expected_sources), 1), 4)

            def _paper_filtered_out(mode: Dict[str, Any]) -> bool:
                got_papers = set(mode["top10_paper_ids"])
                return bool(expected_papers) and not bool(got_papers & expected_papers)

            no_recall = _recall(no_filter)
            user_recall = _recall(user_filter)
            full_recall = _recall(full_expr)

            mode_stats["no_filter"]["total"] += 1
            mode_stats["user_filter"]["total"] += 1
            mode_stats["full_expr"]["total"] += 1
            if no_recall > 0:
                mode_stats["no_filter"]["hit"] += 1
            if user_recall > 0:
                mode_stats["user_filter"]["hit"] += 1
            if full_recall > 0:
                mode_stats["full_expr"]["hit"] += 1

            if no_recall > 0 and full_recall == 0:
                full_expr_suspect += 1

            details.append(
                {
                    "query_id": row.query_id,
                    "query_family": row.query_family,
                    "stage": stage,
                    "collection": collection_name,
                    "expected_source_chunk_ids": row.expected_source_chunk_ids,
                    "expected_paper_ids": row.expected_paper_ids,
                    "modes": {
                        "no_filter": {
                            **no_filter,
                            "recall_at_10": no_recall,
                            "expected_paper_filtered_out": _paper_filtered_out(no_filter),
                        },
                        "user_filter_only": {
                            **user_filter,
                            "recall_at_10": user_recall,
                            "expected_paper_filtered_out": _paper_filtered_out(user_filter),
                        },
                        "current_full_expr_filter": {
                            **full_expr,
                            "recall_at_10": full_recall,
                            "expected_paper_filtered_out": _paper_filtered_out(full_expr),
                        },
                    },
                    "indexable_filter_suspected": no_recall > 0 and full_recall == 0,
                }
            )

    report = {
        "status": "BLOCKED" if full_expr_suspect > 0 else "PASS",
        "full_expr_suspected_filter_bug_count": full_expr_suspect,
        "summary": {
            "no_filter_hit_rate": round(mode_stats["no_filter"]["hit"] / max(mode_stats["no_filter"]["total"], 1), 4),
            "user_filter_hit_rate": round(mode_stats["user_filter"]["hit"] / max(mode_stats["user_filter"]["total"], 1), 4),
            "full_expr_hit_rate": round(mode_stats["full_expr"]["hit"] / max(mode_stats["full_expr"]["total"], 1), 4),
        },
        "details": details,
    }

    json_path = out_dir / "filter_expr_diagnostic_report.json"
    md_path = out_dir / "filter_expr_diagnostic_report.md"
    write_json_report(json_path, report)

    lines = [
        f"- status: {report['status']}",
        f"- full_expr_suspected_filter_bug_count: {report['full_expr_suspected_filter_bug_count']}",
        f"- no_filter_hit_rate: {report['summary']['no_filter_hit_rate']}",
        f"- user_filter_hit_rate: {report['summary']['user_filter_hit_rate']}",
        f"- full_expr_hit_rate: {report['summary']['full_expr_hit_rate']}",
    ]
    write_md_report(md_path, "Step6.1 Filter Expr Diagnostic", lines)
    print(json_path)
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
