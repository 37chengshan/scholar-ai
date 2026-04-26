#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from pymilvus import connections

ROOT = Path(__file__).resolve().parents[2]
API_ROOT = ROOT / "apps" / "api"
for p in (str(API_ROOT), str(ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)

from app.core.model_gateway import create_embedding_provider
from app.rag_v3.indexes.artifact_loader import build_indexes_from_artifacts
from app.rag_v3.retrieval.dense_evidence_retriever import DenseEvidenceRetriever
from app.rag_v3.retrieval.hierarchical_retriever import HierarchicalRetriever
from scripts.evals.v3_0_paper_section_recall_eval import (
    ARTIFACT_PAPERS_ROOT,
    COLLECTION_SUFFIX,
    EMBEDDING_MODEL,
    GOLDEN_PATH,
    load_golden,
    stage_collection_name,
)

OUT_DIR = ROOT / "artifacts" / "benchmarks" / "v3_2"
DOC_PATH = ROOT / "docs" / "reports" / "v3_2_milvus_fallback_cleanup.md"

FORBIDDEN_FIELDS = {"raw_data", "dynamic", "dynamic_fields", "sparse_vector"}


def _build_retriever(stage: str, milvus_host: str, milvus_port: int) -> tuple[HierarchicalRetriever, DenseEvidenceRetriever]:
    paper_index, section_index = build_indexes_from_artifacts(
        artifact_root=ARTIFACT_PAPERS_ROOT,
        stage=stage,
    )

    alias = f"v3_2_cleanup_{stage}"
    connections.connect(alias=alias, host=milvus_host, port=milvus_port)
    embedding_provider = create_embedding_provider("tongyi", EMBEDDING_MODEL)

    dense = DenseEvidenceRetriever(
        embedding_provider=embedding_provider,
        collection_name=stage_collection_name(stage, COLLECTION_SUFFIX),
        milvus_alias=alias,
        output_fields=["source_chunk_id", "paper_id", "normalized_section_path", "content_type", "anchor_text"],
    )
    retriever = HierarchicalRetriever(
        paper_index=paper_index,
        section_index=section_index,
        dense_retriever=dense,
    )
    return retriever, dense


def main() -> int:
    parser = argparse.ArgumentParser(description="v3.2 Milvus/Fallback cleanup audit")
    parser.add_argument("--stage", choices=["raw", "rule", "llm"], default="raw")
    parser.add_argument("--max-queries", type=int, default=20)
    parser.add_argument("--milvus-host", default="localhost")
    parser.add_argument("--milvus-port", type=int, default=19530)
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    DOC_PATH.parent.mkdir(parents=True, exist_ok=True)

    retriever, dense = _build_retriever(args.stage, args.milvus_host, args.milvus_port)
    rows = load_golden(GOLDEN_PATH, max_queries=args.max_queries)

    traces: list[dict[str, Any]] = []
    hydration_checks: list[dict[str, Any]] = []

    for row in rows:
        pack = retriever.retrieve_evidence(row.query, row.query_family, args.stage, top_k=10)
        trace = {
            "query_id": row.query_id,
            "collection": stage_collection_name(args.stage, COLLECTION_SUFFIX),
            "stage": args.stage,
            "search_path": dense.last_trace.get("search_path"),
            "top_k": 10,
            "output_fields": dense.last_trace.get("output_fields", []),
            "error_type": dense.last_trace.get("error_type"),
            "fallback_used": bool(dense.last_trace.get("fallback_used", False)),
        }
        traces.append(trace)

        for c in pack.candidates[:5]:
            hydration_checks.append(
                {
                    "query_id": row.query_id,
                    "source_chunk_id": c.source_chunk_id,
                    "paper_id": c.paper_id,
                    "content_type": c.content_type,
                    "has_source_chunk_id": bool(c.source_chunk_id),
                    "has_paper_id": bool(c.paper_id),
                }
            )

    forbidden_hits = []
    for t in traces:
        lower_fields = [str(f).lower() for f in t.get("output_fields", [])]
        for f in lower_fields:
            if any(b in f for b in FORBIDDEN_FIELDS):
                forbidden_hits.append({"query_id": t["query_id"], "field": f})

    output_fields_audit = {
        "forbidden_fields": sorted(FORBIDDEN_FIELDS),
        "forbidden_hits": forbidden_hits,
        "pass": len(forbidden_hits) == 0,
    }

    fallback_counter_report = {
        "unsupported_field_type_count": DenseEvidenceRetriever.unsupported_field_type_count,
        "fallback_used_count": DenseEvidenceRetriever.fallback_used_count,
        "fallback_reasons": sorted(
            {
                t.get("error_type")
                for t in traces
                if t.get("fallback_used") and t.get("error_type")
            }
        ),
        "fallback_stages": [args.stage] if DenseEvidenceRetriever.fallback_used_count > 0 else [],
        "id_only_success_count": sum(1 for t in traces if t.get("search_path") in {"fallback", "minimal_output_fields"}),
    }

    hydration_success = sum(
        1 for h in hydration_checks if h["has_source_chunk_id"] and h["has_paper_id"]
    ) / max(len(hydration_checks), 1)
    hydration_report = {
        "checked_records": len(hydration_checks),
        "hydration_success_rate": round(hydration_success, 4),
        "pass": hydration_success == 1.0,
    }

    id_only_smoke = {
        "stage": args.stage,
        "search_paths": {
            "minimal_output_fields": sum(1 for t in traces if t.get("search_path") == "minimal_output_fields"),
            "fallback": sum(1 for t in traces if t.get("search_path") == "fallback"),
            "disabled": sum(1 for t in traces if t.get("search_path") == "disabled"),
        },
    }

    (OUT_DIR / "milvus_output_fields_audit.json").write_text(
        json.dumps(output_fields_audit, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    trace_path = OUT_DIR / "milvus_search_trace.jsonl"
    with trace_path.open("w", encoding="utf-8") as f:
        for t in traces:
            f.write(json.dumps(t, ensure_ascii=False) + "\n")

    (OUT_DIR / "id_only_search_smoke.json").write_text(
        json.dumps(id_only_smoke, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (OUT_DIR / "fallback_counter_report.json").write_text(
        json.dumps(fallback_counter_report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (OUT_DIR / "hydration_consistency_report.json").write_text(
        json.dumps(hydration_report, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    if fallback_counter_report["unsupported_field_type_count"] == 0 and fallback_counter_report["fallback_used_count"] == 0 and hydration_report["pass"]:
        verdict = "PASS"
        strict_allowed = "YES"
    elif hydration_report["pass"]:
        verdict = "CONDITIONAL"
        strict_allowed = "NO"
    else:
        verdict = "BLOCKED"
        strict_allowed = "NO"

    doc = {
        "milvus_cleanup": verdict,
        "strict_release_allowed": strict_allowed,
        "artifacts": {
            "milvus_output_fields_audit": str((OUT_DIR / "milvus_output_fields_audit.json").relative_to(ROOT)),
            "milvus_search_trace": str(trace_path.relative_to(ROOT)),
            "id_only_search_smoke": str((OUT_DIR / "id_only_search_smoke.json").relative_to(ROOT)),
            "fallback_counter_report": str((OUT_DIR / "fallback_counter_report.json").relative_to(ROOT)),
            "hydration_consistency_report": str((OUT_DIR / "hydration_consistency_report.json").relative_to(ROOT)),
        },
    }
    DOC_PATH.write_text(
        "# v3.2 Milvus / Fallback Cleanup\n\n```json\n"
        + json.dumps(doc, ensure_ascii=False, indent=2)
        + "\n```\n",
        encoding="utf-8",
    )

    print(json.dumps(doc, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
