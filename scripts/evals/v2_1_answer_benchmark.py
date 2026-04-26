#!/usr/bin/env python
from __future__ import annotations

import argparse
import asyncio
import json
import re
import statistics
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import sys

ROOT = Path(__file__).resolve().parents[2]
API_ROOT = ROOT / "apps" / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from app.core.agentic_retrieval import AgenticRetrievalOrchestrator


CITATION_PATTERN = re.compile(r"\[([^\[\],]+),\s*([^\[\]]+)\]")


def _p50(values: list[float]) -> float:
    if not values:
        return 0.0
    return float(statistics.median(values))


def _p95(values: list[float]) -> float:
    if not values:
        return 0.0
    values = sorted(values)
    index = max(int(len(values) * 0.95) - 1, 0)
    return float(values[index])


def _parse_queries(golden: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for paper in golden.get("papers", []):
        paper_id = paper.get("paper_id")
        for q in paper.get("queries", []):
            rows.append({"query": q, "paper_ids": [paper_id] if paper_id else []})
    for q in golden.get("cross_paper_queries", []):
        rows.append({"query": q, "paper_ids": q.get("expected_papers") or q.get("paper_ids") or []})
    return rows


def _citation_jump_validity(answer: str, sources: list[dict[str, Any]]) -> float:
    citations = CITATION_PATTERN.findall(answer or "")
    if not citations:
        return 0.0
    valid_set = set()
    for source in sources:
        paper = str(source.get("paper_title") or source.get("paper_id") or "").strip()
        section = str(source.get("section") or source.get("section_path") or source.get("page_num") or "").strip()
        if paper and section:
            valid_set.add((paper[:30], section))
    hit = 0
    for paper, section in citations:
        key = (paper.strip()[:30], section.strip())
        if key in valid_set:
            hit += 1
    return hit / max(len(citations), 1)


def _table_figure_grounding_validity(expected_types: list[str], sources: list[dict[str, Any]]) -> tuple[float, float]:
    source_types = [str(item.get("content_type") or "").lower() for item in sources]
    has_table = any(t == "table" for t in source_types)
    has_figure = any(t == "figure" for t in source_types)
    table_expected = "table" in [t.lower() for t in expected_types]
    figure_expected = "figure" in [t.lower() for t in expected_types]
    table_valid = 1.0 if (not table_expected or has_table) else 0.0
    figure_valid = 1.0 if (not figure_expected or has_figure) else 0.0
    return table_valid, figure_valid


def _failure_type(detail: dict[str, Any]) -> str:
    if detail["latency_ms"] > detail["latency_p95_threshold_ms"]:
        return "latency_bad"
    if detail["source_count"] == 0:
        return "retrieval_miss"
    if detail["answer_mode"] == "abstain" and detail["expected_should_answer"]:
        return "abstain_wrong"
    if detail["unsupported_claim_rate"] > 0.5:
        return "unsupported_claim"
    if detail["citation_coverage"] < 0.3:
        return "citation_wrong"
    if detail["answer_evidence_consistency"] < 0.35:
        return "answer_hallucination"
    if detail["expected_table"] and not detail["table_grounding_valid"]:
        return "evidence_type_wrong"
    if detail["expected_figure"] and not detail["figure_grounding_valid"]:
        return "evidence_type_wrong"
    if detail["graph_expected"] and not detail["graph_used"]:
        return "graph_miss"
    return ""


async def run_benchmark(golden_path: Path, user_id: str, output_path: Path) -> None:
    golden = json.loads(golden_path.read_text(encoding="utf-8"))
    queries = _parse_queries(golden)
    orchestrator = AgenticRetrievalOrchestrator(max_rounds=1)

    details: list[dict[str, Any]] = []
    latency_values: list[float] = []

    for row in queries:
        q = row["query"]
        query_text = str(q.get("query") or "")
        paper_ids = [str(pid) for pid in (row.get("paper_ids") or []) if str(pid)]
        expected_types = [str(t) for t in (q.get("expected_evidence_type") or [])]
        t0 = time.perf_counter()
        result = await orchestrator.retrieve(
            query=query_text,
            paper_ids=paper_ids,
            user_id=user_id,
            top_k_per_subquestion=10,
        )
        latency_ms = (time.perf_counter() - t0) * 1000.0
        latency_values.append(latency_ms)

        metadata = result.get("metadata") or {}
        citation_report = metadata.get("citation_verification") or {}
        answer_mode = str(metadata.get("answerMode") or "unknown")
        consistency = float(metadata.get("answer_evidence_consistency") or 0.0)
        unsupported = float(metadata.get("unsupported_claim_rate") or 0.0)
        citation_coverage = float(metadata.get("citation_coverage") or citation_report.get("citation_coverage") or 0.0)
        sources = result.get("sources") or []
        jump_validity = _citation_jump_validity(str(result.get("answer") or ""), sources)
        table_valid, figure_valid = _table_figure_grounding_validity(expected_types, sources)

        detail = {
            "query_id": str(q.get("id") or ""),
            "query_family": str(q.get("query_family") or "unknown"),
            "answer_mode": answer_mode,
            "citation_coverage": citation_coverage,
            "unsupported_claim_rate": unsupported,
            "answer_evidence_consistency": consistency,
            "table_grounding_valid": bool(table_valid),
            "figure_grounding_valid": bool(figure_valid),
            "citation_jump_validity": jump_validity,
            "latency_ms": latency_ms,
            "source_count": len(sources),
            "expected_table": "table" in [t.lower() for t in expected_types],
            "expected_figure": "figure" in [t.lower() for t in expected_types],
            "expected_should_answer": True,
            "graph_expected": str(q.get("query_family") or "") in {"compare", "evolution", "survey"},
            "graph_used": bool(metadata.get("graph_retrieval_used") or False),
            "latency_p95_threshold_ms": 20000.0,
        }
        detail["failure_type"] = _failure_type(detail)
        details.append(detail)

    by_family: dict[str, dict[str, Any]] = defaultdict(lambda: {
        "count": 0,
        "citation_coverage": [],
        "unsupported_claim_rate": [],
        "answer_evidence_consistency": [],
        "citation_jump_validity": [],
        "latency_ms": [],
    })
    for item in details:
        bucket = by_family[item["query_family"]]
        bucket["count"] += 1
        bucket["citation_coverage"].append(item["citation_coverage"])
        bucket["unsupported_claim_rate"].append(item["unsupported_claim_rate"])
        bucket["answer_evidence_consistency"].append(item["answer_evidence_consistency"])
        bucket["citation_jump_validity"].append(item["citation_jump_validity"])
        bucket["latency_ms"].append(item["latency_ms"])

    mode_dist = Counter(item["answer_mode"] for item in details)
    failure_dist = Counter(item["failure_type"] for item in details if item["failure_type"])

    report = {
        "total_queries": len(details),
        "citation_coverage_avg": sum(item["citation_coverage"] for item in details) / max(len(details), 1),
        "unsupported_claim_rate_avg": sum(item["unsupported_claim_rate"] for item in details) / max(len(details), 1),
        "answer_evidence_consistency_avg": sum(item["answer_evidence_consistency"] for item in details) / max(len(details), 1),
        "table_grounding_validity": sum(1.0 if item["table_grounding_valid"] else 0.0 for item in details) / max(len(details), 1),
        "figure_grounding_validity": sum(1.0 if item["figure_grounding_valid"] else 0.0 for item in details) / max(len(details), 1),
        "citation_jump_validity": sum(item["citation_jump_validity"] for item in details) / max(len(details), 1),
        "answer_latency_p50_ms": _p50(latency_values),
        "answer_latency_p95_ms": _p95(latency_values),
        "answer_mode_distribution": dict(mode_dist),
        "failure_types": dict(failure_dist),
        "by_query_family": {
            family: {
                "count": values["count"],
                "citation_coverage_avg": sum(values["citation_coverage"]) / max(values["count"], 1),
                "unsupported_claim_rate_avg": sum(values["unsupported_claim_rate"]) / max(values["count"], 1),
                "answer_evidence_consistency_avg": sum(values["answer_evidence_consistency"]) / max(values["count"], 1),
                "citation_jump_validity_avg": sum(values["citation_jump_validity"]) / max(values["count"], 1),
                "latency_p50_ms": _p50(values["latency_ms"]),
                "latency_p95_ms": _p95(values["latency_ms"]),
            }
            for family, values in by_family.items()
        },
        "query_details": details,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"answer_report={output_path}")
    print(f"total_queries={report['total_queries']}")


def main() -> None:
    parser = argparse.ArgumentParser(description="v2.1 answer benchmark")
    parser.add_argument("--golden", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--user-id", default="benchmark-user")
    args = parser.parse_args()

    asyncio.run(
        run_benchmark(
            golden_path=Path(args.golden),
            user_id=args.user_id,
            output_path=Path(args.output),
        )
    )


if __name__ == "__main__":
    main()
