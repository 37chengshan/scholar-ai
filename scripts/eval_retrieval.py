#!/usr/bin/env python
"""Retrieval evaluation harness with planner/evidence metrics.

Usage:
    python scripts/eval_retrieval.py --golden tests/evals/golden_queries.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import sys

backend_path = Path(__file__).parent.parent / "apps" / "api"
if backend_path.exists():
    sys.path.insert(0, str(backend_path))


def _avg(values: List[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def calculate_recall_at_k(retrieved_ids: List[str], expected_ids: List[str], k: int) -> float:
    if not expected_ids:
        return 0.0
    retrieved = set(retrieved_ids[:k])
    expected = set(expected_ids)
    return len(retrieved & expected) / len(expected)


def calculate_mrr(retrieved_ids: List[str], expected_ids: List[str]) -> float:
    if not expected_ids:
        return 0.0
    expected = set(expected_ids)
    for idx, item in enumerate(retrieved_ids, start=1):
        if item in expected:
            return 1.0 / idx
    return 0.0


def calculate_section_hit_rate(results: List[Dict[str, Any]], expected_sections: List[str]) -> float:
    if not expected_sections:
        return 0.0
    hit_sections: set[str] = set()
    for result in results[:10]:
        section = str(result.get("section") or result.get("content_section") or "").lower()
        if not section:
            continue
        for expected in expected_sections:
            expected_lower = expected.lower()
            if expected_lower in section or section in expected_lower:
                hit_sections.add(expected_lower)
    return len(hit_sections) / len(expected_sections)


def calculate_paper_hit_rate(results: List[Dict[str, Any]], expected_paper_ids: List[str], k: int = 5) -> float:
    if not expected_paper_ids:
        return 0.0
    hit_papers = {
        str(item.get("paper_id"))
        for item in results[:k]
        if item.get("paper_id") in set(expected_paper_ids)
    }
    return len(hit_papers) / len(expected_paper_ids)


def calculate_top5_cross_paper_completeness(results: List[Dict[str, Any]], expected_paper_ids: List[str]) -> float:
    return calculate_paper_hit_rate(results, expected_paper_ids, k=5)


def calculate_table_hit_rate(results: List[Dict[str, Any]], expected_table_refs: List[str]) -> float:
    if not expected_table_refs:
        return 0.0
    refs = {str(item.get("table_ref") or "") for item in results[:10]}
    refs.discard("")
    return len(refs & set(expected_table_refs)) / len(expected_table_refs)


def calculate_figure_hit_rate(results: List[Dict[str, Any]], expected_figure_refs: List[str]) -> float:
    if not expected_figure_refs:
        return 0.0
    refs = {str(item.get("figure_ref") or "") for item in results[:10]}
    refs.discard("")
    return len(refs & set(expected_figure_refs)) / len(expected_figure_refs)


def calculate_numeric_qa_exact_match(results: List[Dict[str, Any]], gold_triplets: List[Dict[str, Any]]) -> float:
    if not gold_triplets:
        return 0.0
    observed = {
        (
            str(item.get("method") or "").lower(),
            str(item.get("dataset") or "").lower(),
            str(item.get("metric_name") or "").lower(),
            str(item.get("score_value") or "").lower(),
        )
        for item in results[:10]
    }
    gold = {
        (
            str(item.get("method") or "").lower(),
            str(item.get("dataset") or "").lower(),
            str(item.get("metric") or item.get("metric_name") or "").lower(),
            str(item.get("value") or item.get("score_value") or "").lower(),
        )
        for item in gold_triplets
    }
    return 1.0 if gold and observed & gold else 0.0


def _mock_results(query_data: Dict[str, Any], query_type: str) -> Dict[str, Any]:
    expected_paper_ids = query_data.get("expected_paper_ids") or query_data.get("paper_ids") or []
    expected_sections = query_data.get("expected_sections") or []
    expected_chunks = query_data.get("expected_chunks")

    if expected_chunks:
        result_ids = list(expected_chunks)
    elif expected_paper_ids:
        # Keep deterministic behavior for unit tests.
        if query_type in {"cross_paper", "compare"} and len(expected_paper_ids) > 1:
            result_ids = [expected_paper_ids[0]]
        else:
            result_ids = list(expected_paper_ids)
    else:
        result_ids = ["mock-source-1"]

    results = []
    for idx, source_id in enumerate(result_ids[:10]):
        section = expected_sections[idx % len(expected_sections)] if expected_sections else "General"
        paper_id = source_id if source_id in expected_paper_ids else (expected_paper_ids[0] if expected_paper_ids else "mock-paper")
        results.append(
            {
                "source_id": source_id,
                "id": source_id,
                "paper_id": paper_id,
                "section": section,
                "content_type": "table" if query_type == "table" else "text",
                "paper_role": "result",
                "table_ref": "table-1" if query_type in {"table", "numeric", "compare"} else None,
                "figure_ref": "figure-1" if query_type == "figure" else None,
                "method": "method-a",
                "dataset": "cifar-10",
                "metric_name": "accuracy",
                "score_value": "96.2",
                "evidence_bundle_id": f"bundle-{idx}",
                "evidence_types": ["text", "table"] if query_type in {"table", "numeric", "compare"} else ["text"],
            }
        )

    family = query_data.get("query_family") or query_type
    planner_queries = query_data.get("planner_queries") or [query_data.get("query", "")]

    return {
        "query_family": family,
        "planner_query_count": len(planner_queries),
        "decontextualized_query": query_data.get("decontextualized_query") or query_data.get("query", ""),
        "second_pass_used": bool(query_data.get("second_pass_used", False)),
        "second_pass_gain": float(query_data.get("second_pass_gain", 0.0)),
        "results": results,
    }


async def _run_single_query(
    service: Any,
    query_data: Dict[str, Any],
    *,
    user_id: str,
    paper_ids: List[str],
    use_reranker: bool,
    mock_mode: bool,
) -> Dict[str, Any]:
    query = query_data.get("query", "")
    query_type = query_data.get("query_type") or query_data.get("query_family")
    if not query_type:
        query_type = "compare" if len(paper_ids) > 1 else "fact"

    if mock_mode:
        return _mock_results(query_data, query_type)

    result = await service.search(
        query=query,
        paper_ids=paper_ids,
        user_id=user_id,
        top_k=10,
        use_reranker=use_reranker,
        content_types=query_data.get("content_types"),
    )
    return result


async def evaluate_retrieval(
    golden_queries_path: str,
    user_id: str = "eval-user",
    paper_ids_filter: Optional[List[str]] = None,
    mock_mode: bool = False,
    use_reranker: bool = False,
) -> Dict[str, Any]:
    with open(golden_queries_path, encoding="utf-8") as f:
        golden = json.load(f)

    service = None
    if not mock_mode:
        from app.core.multimodal_search_service import get_multimodal_search_service

        service = get_multimodal_search_service()

    metrics: Dict[str, List[float]] = {
        "recall_at_5": [],
        "recall_at_10": [],
        "mrr": [],
        "section_hit_rate": [],
        "multimodal_hit_rate": [],
        "paper_hit_rate": [],
        "planner_query_count": [],
        "second_pass_used": [],
        "second_pass_gain": [],
        "evidence_bundle_hit_count": [],
        "paper_role_hit_rate": [],
        "table_hit_rate": [],
        "figure_hit_rate": [],
        "numeric_qa_exact_match": [],
        "top5_cross_paper_completeness": [],
    }

    query_details: List[Dict[str, Any]] = []

    async def evaluate_case(query_data: Dict[str, Any], paper_ids: List[str], default_type: str) -> None:
        result = await _run_single_query(
            service,
            query_data,
            user_id=user_id,
            paper_ids=paper_ids,
            use_reranker=use_reranker,
            mock_mode=mock_mode,
        )

        results = result.get("results", [])
        retrieved_ids = [
            str(item.get("source_id") or item.get("id") or item.get("chunk_id") or item.get("paper_id") or "")
            for item in results
        ]
        expected_chunks = query_data.get("expected_chunks") or query_data.get("expected_paper_ids") or []
        expected_sections = query_data.get("expected_sections") or []
        expected_papers = query_data.get("expected_paper_ids") or query_data.get("paper_ids") or paper_ids
        query_family = result.get("query_family") or query_data.get("query_family") or query_data.get("query_type") or default_type

        recall_5 = calculate_recall_at_k(retrieved_ids, expected_chunks, 5)
        recall_10 = calculate_recall_at_k(retrieved_ids, expected_chunks, 10)
        mrr = calculate_mrr(retrieved_ids, expected_chunks)
        section_hit = calculate_section_hit_rate(results, expected_sections)
        paper_hit = calculate_paper_hit_rate(results, expected_papers)
        cross_paper_top5 = calculate_top5_cross_paper_completeness(results, expected_papers)
        table_hit = calculate_table_hit_rate(results, query_data.get("gold_table_refs") or [])
        figure_hit = calculate_figure_hit_rate(results, query_data.get("gold_figure_refs") or [])
        numeric_exact = calculate_numeric_qa_exact_match(results, query_data.get("gold_metric_triplets") or [])

        evidence_bundle_hit_count = len(
            {
                str(item.get("evidence_bundle_id"))
                for item in results[:10]
                if item.get("evidence_bundle_id")
            }
        )
        paper_role_hits = sum(1 for item in results[:10] if item.get("paper_role"))
        paper_role_hit_rate = (paper_role_hits / min(len(results), 10)) if results else 0.0

        metrics["recall_at_5"].append(recall_5)
        metrics["recall_at_10"].append(recall_10)
        metrics["mrr"].append(mrr)
        metrics["section_hit_rate"].append(section_hit)
        metrics["paper_hit_rate"].append(paper_hit)
        metrics["planner_query_count"].append(float(result.get("planner_query_count") or 0.0))
        metrics["second_pass_used"].append(1.0 if result.get("second_pass_used") else 0.0)
        metrics["second_pass_gain"].append(float(result.get("second_pass_gain") or 0.0))
        metrics["evidence_bundle_hit_count"].append(float(evidence_bundle_hit_count))
        metrics["paper_role_hit_rate"].append(paper_role_hit_rate)
        metrics["table_hit_rate"].append(table_hit)
        metrics["figure_hit_rate"].append(figure_hit)
        metrics["numeric_qa_exact_match"].append(numeric_exact)
        metrics["top5_cross_paper_completeness"].append(cross_paper_top5)

        query_details.append(
            {
                "query_id": query_data.get("id"),
                "query_family": query_family,
                "planner_query_count": int(result.get("planner_query_count") or 0),
                "decontextualized_query": result.get("decontextualized_query"),
                "second_pass_used": bool(result.get("second_pass_used")),
                "second_pass_gain": float(result.get("second_pass_gain") or 0.0),
                "evidence_bundle_hit_count": evidence_bundle_hit_count,
                "paper_role_hit_rate": paper_role_hit_rate,
                "table_hit_rate": table_hit,
                "figure_hit_rate": figure_hit,
                "numeric_qa_exact_match": numeric_exact,
                "top5_cross_paper_completeness": cross_paper_top5,
                "recall_at_5": recall_5,
                "recall_at_10": recall_10,
                "mrr": mrr,
                "paper_hit_rate": paper_hit,
                "section_hit_rate": section_hit,
            }
        )

    for paper_data in golden.get("papers", []):
        paper_id = paper_data.get("paper_id")
        if paper_ids_filter and paper_id not in paper_ids_filter:
            continue
        for query_data in paper_data.get("queries", []):
            await evaluate_case(query_data, [paper_id], "fact")

    for cp in golden.get("cross_paper_queries", []):
        target_papers = cp.get("paper_ids", [])
        if paper_ids_filter:
            target_papers = [pid for pid in target_papers if pid in paper_ids_filter]
        await evaluate_case(cp, target_papers, "compare")

    for mq in golden.get("multimodal_queries", []):
        result = await _run_single_query(
            service,
            mq,
            user_id=user_id,
            paper_ids=paper_ids_filter or mq.get("paper_ids", []),
            use_reranker=use_reranker,
            mock_mode=mock_mode,
        )
        results = result.get("results", [])
        expected_types = mq.get("expected_content_type", [])
        retrieved_types = [str(item.get("content_type")) for item in results[:10]]
        hit = any(item in retrieved_types for item in expected_types) if expected_types else False
        metrics["multimodal_hit_rate"].append(1.0 if hit else 0.0)
        query_details.append(
            {
                "query_id": mq.get("id"),
                "query_family": result.get("query_family") or mq.get("query_family") or "multimodal",
                "multimodal_hit": hit,
                "expected_types": expected_types,
                "planner_query_count": int(result.get("planner_query_count") or 0),
                "decontextualized_query": result.get("decontextualized_query"),
                "second_pass_used": bool(result.get("second_pass_used")),
                "second_pass_gain": float(result.get("second_pass_gain") or 0.0),
                "evidence_bundle_hit_count": len(
                    {
                        str(item.get("evidence_bundle_id"))
                        for item in results[:10]
                        if item.get("evidence_bundle_id")
                    }
                ),
            }
        )

    report = {
        "total_queries": len(metrics["recall_at_5"]),
        "recall_at_5_avg": _avg(metrics["recall_at_5"]),
        "recall_at_10_avg": _avg(metrics["recall_at_10"]),
        "mrr_avg": _avg(metrics["mrr"]),
        "section_hit_rate_avg": _avg(metrics["section_hit_rate"]),
        "multimodal_hit_rate_avg": _avg(metrics["multimodal_hit_rate"]),
        "paper_hit_rate_avg": _avg(metrics["paper_hit_rate"]),
        "planner_query_count_avg": _avg(metrics["planner_query_count"]),
        "second_pass_used_rate": _avg(metrics["second_pass_used"]),
        "second_pass_gain_avg": _avg(metrics["second_pass_gain"]),
        "evidence_bundle_hit_count_avg": _avg(metrics["evidence_bundle_hit_count"]),
        "paper_role_hit_rate_avg": _avg(metrics["paper_role_hit_rate"]),
        "table_hit_rate_avg": _avg(metrics["table_hit_rate"]),
        "figure_hit_rate_avg": _avg(metrics["figure_hit_rate"]),
        "numeric_qa_exact_match": _avg(metrics["numeric_qa_exact_match"]),
        "top5_cross_paper_completeness": _avg(metrics["top5_cross_paper_completeness"]),
        "metrics_raw": metrics,
        "query_details": query_details,
        "evaluation_mode": "mock" if mock_mode else "real",
        "use_reranker": bool(use_reranker),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Retrieval evaluation harness")
    parser.add_argument("--golden", default="tests/evals/golden_queries.json", help="Path to golden queries JSON")
    parser.add_argument("--paper-id", nargs="*", help="Filter by specific paper IDs")
    parser.add_argument("--output", default="eval_retrieval_report.json", help="Output report path")
    parser.add_argument("--allow-mock", action="store_true", help="Run in mock mode")
    parser.add_argument("--use-reranker", action="store_true", help="Enable reranker during evaluation")
    args = parser.parse_args()

    report = asyncio.run(
        evaluate_retrieval(
            args.golden,
            paper_ids_filter=args.paper_id,
            mock_mode=args.allow_mock,
            use_reranker=args.use_reranker,
        )
    )

    output_path = Path(args.output)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print("=" * 60)
    print("Retrieval Evaluation Report")
    print("=" * 60)
    print(f"Total Queries: {report['total_queries']}")
    print(f"Recall@5: {report['recall_at_5_avg']:.2%}")
    print(f"MRR: {report['mrr_avg']:.2%}")
    print(f"Paper Hit Rate: {report['paper_hit_rate_avg']:.2%}")
    print(f"Table Hit Rate: {report['table_hit_rate_avg']:.2%}")
    print(f"Figure Hit Rate: {report['figure_hit_rate_avg']:.2%}")
    print(f"Numeric QA EM: {report['numeric_qa_exact_match']:.2%}")
    print(f"Top5 Cross-paper Completeness: {report['top5_cross_paper_completeness']:.2%}")
    print("=" * 60)
    print(f"Report saved to: {output_path}")


if __name__ == "__main__":
    main()
