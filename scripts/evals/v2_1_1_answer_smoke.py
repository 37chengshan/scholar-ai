#!/usr/bin/env python
from __future__ import annotations

import argparse
import asyncio
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import sys

ROOT = Path(__file__).resolve().parents[2]
API_ROOT = ROOT / "apps" / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from app.config import settings
from app.core.agentic_retrieval import AgenticRetrievalOrchestrator
from app.core.retrieval_branch_registry import get_qwen_collection


def _flatten_queries(golden: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for paper in golden.get("papers", []):
        paper_id = str(paper.get("paper_id") or "")
        for q in paper.get("queries", []):
            rows.append(
                {
                    "query": str(q.get("query") or ""),
                    "query_id": str(q.get("id") or ""),
                    "query_family": str(q.get("query_family") or "fact"),
                    "paper_ids": [paper_id] if paper_id else (q.get("expected_paper_ids") or []),
                    "expected_evidence_type": q.get("expected_evidence_type") or [],
                }
            )

    for q in golden.get("cross_paper_queries", []):
        rows.append(
            {
                "query": str(q.get("query") or ""),
                "query_id": str(q.get("id") or ""),
                "query_family": str(q.get("query_family") or "compare"),
                "paper_ids": q.get("expected_papers") or q.get("paper_ids") or q.get("expected_paper_ids") or [],
                "expected_evidence_type": q.get("expected_evidence_type") or [],
            }
        )

    for q in golden.get("multimodal_queries", []):
        rows.append(
            {
                "query": str(q.get("query") or ""),
                "query_id": str(q.get("id") or ""),
                "query_family": str(q.get("query_family") or "table"),
                "paper_ids": q.get("paper_ids") or q.get("expected_papers") or [],
                "expected_evidence_type": q.get("expected_evidence_type") or q.get("expected_content_type") or [],
            }
        )

    return [row for row in rows if row["query"]]


def _sample_queries(rows: list[dict[str, Any]], per_family: int = 2) -> list[dict[str, Any]]:
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        buckets[str(row.get("query_family") or "unknown")].append(row)

    picked: list[dict[str, Any]] = []
    for family in sorted(buckets.keys()):
        picked.extend(buckets[family][:per_family])
    return picked


async def _run_stage(stage: str, rows: list[dict[str, Any]], user_id: str) -> dict[str, Any]:
    settings.MILVUS_COLLECTION_CONTENTS_V2 = get_qwen_collection(stage)  # stage-specific qwen collection
    orchestrator = AgenticRetrievalOrchestrator(max_rounds=1)

    detail: list[dict[str, Any]] = []
    errors: list[str] = []

    for row in rows:
        try:
            result = await orchestrator.retrieve(
                query=row["query"],
                paper_ids=[str(pid) for pid in (row.get("paper_ids") or [])],
                user_id=user_id,
                top_k_per_subquestion=10,
            )
            meta = result.get("metadata") or {}
            sources = result.get("sources") or []
            detail.append(
                {
                    "query_id": row.get("query_id"),
                    "query_family": row.get("query_family"),
                    "source_count": len(sources),
                    "answer_mode": meta.get("answerMode"),
                    "citation_coverage": float(meta.get("citation_coverage") or 0.0),
                    "unsupported_claim_rate": float(meta.get("unsupported_claim_rate") or 0.0),
                    "answer_evidence_consistency": float(meta.get("answer_evidence_consistency") or 0.0),
                    "error": "",
                }
            )
        except Exception as exc:
            msg = str(exc)
            errors.append(msg)
            detail.append(
                {
                    "query_id": row.get("query_id"),
                    "query_family": row.get("query_family"),
                    "source_count": 0,
                    "answer_mode": "error",
                    "citation_coverage": 0.0,
                    "unsupported_claim_rate": 1.0,
                    "answer_evidence_consistency": 0.0,
                    "error": msg,
                }
            )

    vector_dim_errors = sum(1 for item in detail if "vector dimension mismatch" in (item.get("error") or "").lower())
    unsupported_type_errors = sum(1 for item in detail if "unsupported field type" in (item.get("error") or "").lower())

    return {
        "stage": stage,
        "collection": settings.MILVUS_COLLECTION_CONTENTS_V2,
        "total_queries": len(detail),
        "successful_queries": sum(1 for item in detail if not item.get("error")),
        "vector_dimension_mismatch_errors": vector_dim_errors,
        "unsupported_field_type_errors": unsupported_type_errors,
        "citation_coverage_avg": sum(item["citation_coverage"] for item in detail) / max(len(detail), 1),
        "unsupported_claim_rate_avg": sum(item["unsupported_claim_rate"] for item in detail) / max(len(detail), 1),
        "answer_evidence_consistency_avg": sum(item["answer_evidence_consistency"] for item in detail) / max(len(detail), 1),
        "details": detail,
        "errors": errors,
    }


def _to_md(report: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# v2.1.1 Answer Smoke Report")
    lines.append("")
    lines.append(f"- overall_status: {report['overall_status']}")
    lines.append(f"- sampled_queries: {report['sampled_queries']}")
    lines.append("")
    lines.append("| stage | collection | total | success | vector_dim_errors | unsupported_field_type_errors | citation_coverage_avg | answer_evidence_consistency_avg |")
    lines.append("|---|---|---:|---:|---:|---:|---:|---:|")
    for stage_report in report.get("stages", []):
        lines.append(
            f"| {stage_report['stage']} | {stage_report['collection']} | {stage_report['total_queries']} | "
            f"{stage_report['successful_queries']} | {stage_report['vector_dimension_mismatch_errors']} | "
            f"{stage_report['unsupported_field_type_errors']} | {stage_report['citation_coverage_avg']:.4f} | "
            f"{stage_report['answer_evidence_consistency_avg']:.4f} |"
        )
    lines.append("")
    return "\n".join(lines) + "\n"


async def main_async(args: argparse.Namespace) -> int:
    golden = json.loads(Path(args.golden).read_text(encoding="utf-8"))
    rows = _flatten_queries(golden)
    sampled = _sample_queries(rows, per_family=args.per_family)

    stage_reports = []
    for stage in ["raw", "rule", "llm"]:
        stage_reports.append(await _run_stage(stage, sampled, args.user_id))

    overall_status = "PASS"
    for stage_report in stage_reports:
        if stage_report["vector_dimension_mismatch_errors"] > 0 or stage_report["unsupported_field_type_errors"] > 0:
            overall_status = "BLOCKED"
            break

    report = {
        "overall_status": overall_status,
        "sampled_queries": len(sampled),
        "per_family": args.per_family,
        "stages": stage_reports,
    }

    out_json = Path(args.output_json)
    out_md = Path(args.output_md)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    out_md.write_text(_to_md(report), encoding="utf-8")

    print(f"answer_smoke_json={out_json}")
    print(f"answer_smoke_md={out_md}")
    print(f"overall_status={overall_status}")
    return 0 if overall_status == "PASS" else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Run v2.1.1 answer smoke benchmark")
    parser.add_argument(
        "--golden",
        default=str(ROOT / "artifacts" / "benchmarks" / "v2_1_20" / "golden_queries_acceptance_v2_1.json"),
    )
    parser.add_argument(
        "--output-json",
        default=str(ROOT / "artifacts" / "benchmarks" / "v2_1_20" / "answer_smoke_v2_1_1.json"),
    )
    parser.add_argument(
        "--output-md",
        default=str(ROOT / "artifacts" / "benchmarks" / "v2_1_20" / "answer_smoke_v2_1_1.md"),
    )
    parser.add_argument("--user-id", default="benchmark-user")
    parser.add_argument("--per-family", type=int, default=2)
    args = parser.parse_args()
    return asyncio.run(main_async(args))


if __name__ == "__main__":
    raise SystemExit(main())
