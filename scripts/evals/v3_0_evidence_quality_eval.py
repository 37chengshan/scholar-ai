#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from pymilvus import connections

ROOT = Path(__file__).resolve().parents[2]
API_ROOT = ROOT / "apps" / "api"
for p in (str(API_ROOT), str(ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)

from app.core.model_gateway import create_embedding_provider
from app.rag_v3.evaluation.answer_policy import build_answer_contract
from app.rag_v3.evaluation.evidence_quality import score_evidence
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

OUTPUT_DIR = ROOT / "artifacts" / "benchmarks" / "v3_0"
DOC_DIR = ROOT / "docs" / "reports" / "official_rag_evaluation"


@dataclass
class QualityRow:
    query_id: str
    query_family: str
    answer_mode: str
    claim_count: int
    unsupported_claim_count: int
    citation_count: int
    missing_evidence_count: int
    citation_coverage: float
    answer_evidence_consistency: float
    dense_fallback_used: float
    dense_unsupported_field_type_count: float


def _eval_one(query_id: str, query: str, query_family: str, stage: str, retriever: HierarchicalRetriever) -> QualityRow:
    pack = retriever.retrieve_evidence(query=query, query_family=query_family, stage=stage, top_k=10)
    quality = score_evidence(pack)
    contract = build_answer_contract(pack, quality)

    claim_count = len(contract.claims)
    unsupported = len(contract.unsupported_claims)
    citations = len(contract.citations)

    if claim_count > 0:
        claims_with_citation = sum(1 for c in contract.claims if c.citation_ids)
        citation_coverage = float(claims_with_citation) / float(claim_count)
        consistent_claims = sum(1 for c in contract.claims if c.support_status != "unsupported")
        consistency = float(consistent_claims) / float(claim_count)
    else:
        citation_coverage = 0.0
        consistency = 0.0

    return QualityRow(
        query_id=query_id,
        query_family=query_family,
        answer_mode=contract.answer_mode,
        claim_count=claim_count,
        unsupported_claim_count=unsupported,
        citation_count=citations,
        missing_evidence_count=len(contract.missing_evidence),
        citation_coverage=round(citation_coverage, 4),
        answer_evidence_consistency=round(consistency, 4),
        dense_fallback_used=float(pack.diagnostics.get("dense_fallback_used", 0.0)),
        dense_unsupported_field_type_count=float(pack.diagnostics.get("dense_unsupported_field_type_count", 0.0)),
    )


def _aggregate(rows: list[QualityRow]) -> dict[str, Any]:
    total = len(rows)
    total_claims = sum(r.claim_count for r in rows)

    citation_coverage = sum(r.citation_coverage for r in rows) / max(total, 1)
    unsupported_claim_rate = sum(r.unsupported_claim_count for r in rows) / max(total_claims, 1)
    consistency = sum(r.answer_evidence_consistency for r in rows) / max(total, 1)

    abstain_total = sum(1 for r in rows if r.answer_mode == "abstain")
    abstain_good = sum(1 for r in rows if r.answer_mode == "abstain" and r.missing_evidence_count > 0)
    abstain_precision = abstain_good / max(abstain_total, 1)

    partial_total = sum(1 for r in rows if r.answer_mode == "partial")
    partial_good = sum(1 for r in rows if r.answer_mode == "partial" and r.unsupported_claim_count == 0)
    partial_accuracy = partial_good / max(partial_total, 1)

    return {
        "total": total,
        "citation_coverage": round(citation_coverage, 4),
        "unsupported_claim_rate": round(unsupported_claim_rate, 4),
        "answer_evidence_consistency": round(consistency, 4),
        "abstain_precision": round(abstain_precision, 4),
        "partial_answer_accuracy": round(partial_accuracy, 4),
        "mode_distribution": {
            "full": sum(1 for r in rows if r.answer_mode == "full"),
            "partial": partial_total,
            "abstain": abstain_total,
        },
        "fallback_used_count": int(sum(1 for r in rows if r.dense_fallback_used > 0)),
        "unsupported_field_type_count": int(max((r.dense_unsupported_field_type_count for r in rows), default=0.0)),
    }


def _build_retriever(stage: str, milvus_host: str, milvus_port: int) -> HierarchicalRetriever:
    paper_index, section_index = build_indexes_from_artifacts(
        artifact_root=ARTIFACT_PAPERS_ROOT,
        stage=stage,
    )

    connections.connect(alias="v3_phase5_6", host=milvus_host, port=milvus_port)
    embedding_provider = create_embedding_provider("tongyi", EMBEDDING_MODEL)
    collection_name = stage_collection_name(stage, COLLECTION_SUFFIX)

    dense_retriever = DenseEvidenceRetriever(
        embedding_provider=embedding_provider,
        collection_name=collection_name,
        milvus_alias="v3_phase5_6",
        output_fields=["source_chunk_id", "paper_id", "normalized_section_path", "content_type", "anchor_text"],
    )

    return HierarchicalRetriever(
        paper_index=paper_index,
        section_index=section_index,
        dense_retriever=dense_retriever,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="v3.0 Phase 5/6 evidence quality evaluation")
    parser.add_argument("--stage", choices=["raw", "rule", "llm"], default="raw")
    parser.add_argument("--max-queries", type=int, default=16)
    parser.add_argument("--milvus-host", default="localhost")
    parser.add_argument("--milvus-port", type=int, default=19530)
    args = parser.parse_args()

    retriever = _build_retriever(args.stage, args.milvus_host, args.milvus_port)
    rows = load_golden(GOLDEN_PATH, max_queries=args.max_queries)
    quality_rows = [_eval_one(r.query_id, r.query, r.query_family, args.stage, retriever) for r in rows]
    summary = _aggregate(quality_rows)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    DOC_DIR.mkdir(parents=True, exist_ok=True)

    payload = {
        "version": "v3.0-phase5-6",
        "stage": args.stage,
        "summary": summary,
        "results": [asdict(r) for r in quality_rows],
    }

    out_json = OUTPUT_DIR / f"phase5_6_evidence_quality_{args.stage}.json"
    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    report_lines = [
        "# v3.0 Phase 5/6 Evidence Quality Report",
        "",
        f"- stage: {args.stage}",
        f"- total: {summary['total']}",
        f"- citation_coverage: {summary['citation_coverage']}",
        f"- unsupported_claim_rate: {summary['unsupported_claim_rate']}",
        f"- answer_evidence_consistency: {summary['answer_evidence_consistency']}",
        f"- abstain_precision: {summary['abstain_precision']}",
        f"- partial_answer_accuracy: {summary['partial_answer_accuracy']}",
        f"- mode_distribution: {summary['mode_distribution']}",
    ]

    out_md = OUTPUT_DIR / f"phase5_6_evidence_quality_{args.stage}_report.md"
    out_md.write_text("\n".join(report_lines), encoding="utf-8")

    doc_out = DOC_DIR / "v3_0_phase5_6_report.md"
    doc_out.write_text(out_md.read_text(encoding="utf-8"), encoding="utf-8")

    print(f"[v3.0 Phase 5/6] summary: {summary}")
    print(f"Results saved: {out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
