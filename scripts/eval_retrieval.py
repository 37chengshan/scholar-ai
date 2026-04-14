#!/usr/bin/env python
"""Retrieval evaluation harness per D-14.

Measures:
- Recall@5, Recall@10
- MRR (Mean Reciprocal Rank)
- Section hit rate
- Multimodal hit rate

Usage:
    python scripts/eval_retrieval.py --golden tests/evals/golden_queries.json
    python scripts/eval_retrieval.py --paper-id test-paper-001 test-paper-002
"""

import json
import asyncio
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add backend to path for imports
import sys
backend_path = Path(__file__).parent.parent / "backend-python"
if backend_path.exists():
    sys.path.insert(0, str(backend_path))


def calculate_recall_at_k(
    retrieved_ids: List[str],
    expected_ids: List[str],
    k: int
) -> float:
    """Calculate Recall@k.

    Recall@k = |retrieved ∩ expected| / |expected|

    Args:
        retrieved_ids: List of retrieved chunk IDs (ordered by relevance)
        expected_ids: List of expected/gold chunk IDs
        k: Number of top results to consider

    Returns:
        Recall@k score (0.0 to 1.0)
    """
    if not expected_ids:
        return 0.0
    retrieved_set = set(retrieved_ids[:k])
    expected_set = set(expected_ids)
    return len(retrieved_set & expected_set) / len(expected_set)


def calculate_mrr(
    retrieved_ids: List[str],
    expected_ids: List[str]
) -> float:
    """Calculate Mean Reciprocal Rank.

    MRR = 1 / rank of first relevant result
    If no relevant result found, MRR = 0

    Args:
        retrieved_ids: List of retrieved chunk IDs (ordered by relevance)
        expected_ids: List of expected/gold chunk IDs

    Returns:
        MRR score (0.0 to 1.0)
    """
    if not expected_ids:
        return 0.0
    expected_set = set(expected_ids)
    for i, id in enumerate(retrieved_ids):
        if id in expected_set:
            return 1.0 / (i + 1)
    return 0.0


def calculate_section_hit_rate(
    results: List[Dict],
    expected_sections: List[str]
) -> float:
    """Calculate section hit rate.

    Section hit rate = |sections hit in top 10| / |expected sections|

    Args:
        results: List of search results with section field
        expected_sections: List of expected section names

    Returns:
        Section hit rate (0.0 to 1.0)
    """
    if not expected_sections:
        return 0.0

    hit_sections = set()
    for r in results[:10]:
        section = r.get("section", "") or r.get("content_section", "")
        if section:
            # Normalize section names for comparison
            section_lower = section.lower()
            for expected in expected_sections:
                if expected.lower() in section_lower or section_lower in expected.lower():
                    hit_sections.add(expected.lower())

    return len(hit_sections) / len(expected_sections)


async def evaluate_retrieval(
    golden_queries_path: str,
    user_id: str = "eval-user",
    paper_ids_filter: Optional[List[str]] = None,
    mock_mode: bool = True
) -> Dict[str, Any]:
    """Run retrieval evaluation against golden queries.

    Args:
        golden_queries_path: Path to golden_queries.json
        user_id: User ID for Milvus filtering
        paper_ids_filter: Optional filter for specific paper IDs
        mock_mode: If True, use mock search (for testing without services)

    Returns:
        Evaluation report with aggregated metrics
    """

    with open(golden_queries_path) as f:
        golden = json.load(f)

    metrics = {
        "recall_at_5": [],
        "recall_at_10": [],
        "mrr": [],
        "section_hit_rate": [],
        "multimodal_hit_rate": [],
    }

    query_details = []

    # Evaluate paper queries
    for paper_data in golden.get("papers", []):
        paper_id = paper_data.get("paper_id")
        if paper_ids_filter and paper_id not in paper_ids_filter:
            continue

        for query_data in paper_data.get("queries", []):
            query_id = query_data.get("id")
            query = query_data.get("query")
            expected_chunks = query_data.get("expected_chunks", [])
            expected_sections = query_data.get("expected_sections", [])
            query_type = query_data.get("query_type", "single")

            if mock_mode:
                # Mock mode: simulate retrieval with expected chunks shuffled
                # In production, this would call actual MultimodalSearchService
                retrieved_ids = _mock_retrieval(expected_chunks, query_type)
                results = [{"id": id, "section": expected_sections[i % len(expected_sections)] if expected_sections else "General"}
                          for i, id in enumerate(retrieved_ids)]
            else:
                # Real mode: call MultimodalSearchService
                try:
                    from app.core.multimodal_search_service import get_multimodal_search_service

                    service = get_multimodal_search_service()
                    result = await service.search(
                        query=query,
                        paper_ids=[paper_id],
                        user_id=user_id,
                        top_k=10,
                        use_reranker=False,
                    )

                    retrieved_ids = [r.get("id") or r.get("chunk_id") or r.get("content_id")
                                    for r in result.get("results", [])]
                    results = result.get("results", [])
                except Exception as e:
                    print(f"Error retrieving for query {query_id}: {e}")
                    retrieved_ids = []
                    results = []

            # Calculate metrics
            recall_5 = calculate_recall_at_k(retrieved_ids, expected_chunks, 5)
            recall_10 = calculate_recall_at_k(retrieved_ids, expected_chunks, 10)
            mrr = calculate_mrr(retrieved_ids, expected_chunks)
            section_hit = calculate_section_hit_rate(results, expected_sections)

            metrics["recall_at_5"].append(recall_5)
            metrics["recall_at_10"].append(recall_10)
            metrics["mrr"].append(mrr)
            metrics["section_hit_rate"].append(section_hit)

            query_details.append({
                "query_id": query_id,
                "query": query[:50] + "..." if len(query) > 50 else query,
                "paper_id": paper_id,
                "query_type": query_type,
                "recall_at_5": recall_5,
                "recall_at_10": recall_10,
                "mrr": mrr,
                "section_hit_rate": section_hit,
                "expected_chunks_count": len(expected_chunks),
                "retrieved_count": len(retrieved_ids),
            })

    # Evaluate multimodal queries
    for mq in golden.get("multimodal_queries", []):
        query_id = mq.get("id")
        query = mq.get("query")
        expected_types = mq.get("expected_content_type", [])

        if mock_mode:
            # Mock: simulate multimodal hit
            hit = len(expected_types) > 0 and "text" in expected_types
            metrics["multimodal_hit_rate"].append(1.0 if hit else 0.0)
        else:
            try:
                from app.core.multimodal_search_service import get_multimodal_search_service

                service = get_multimodal_search_service()
                result = await service.search(
                    query=query,
                    paper_ids=paper_ids_filter or [],
                    user_id=user_id,
                    top_k=10,
                    content_types=["text", "image", "table"],
                )

                retrieved_types = [r.get("content_type") for r in result.get("results", [])[:10]]
                hit = any(t in retrieved_types for t in expected_types)
                metrics["multimodal_hit_rate"].append(1.0 if hit else 0.0)
            except Exception as e:
                print(f"Error in multimodal query {query_id}: {e}")
                metrics["multimodal_hit_rate"].append(0.0)

        query_details.append({
            "query_id": query_id,
            "query": query[:50] + "..." if len(query) > 50 else query,
            "query_type": "multimodal",
            "multimodal_hit": hit if mock_mode else False,
            "expected_types": expected_types,
        })

    # Evaluate cross-paper queries
    for cp in golden.get("cross_paper_queries", []):
        query_id = cp.get("id")
        query = cp.get("query")
        target_papers = cp.get("paper_ids", [])
        expected_chunks = cp.get("expected_chunks", [])
        expected_sections = cp.get("expected_sections", [])

        if mock_mode:
            retrieved_ids = _mock_retrieval(expected_chunks, "cross_paper")
            results = [{"id": id, "section": expected_sections[i % len(expected_sections)] if expected_sections else "General"}
                      for i, id in enumerate(retrieved_ids)]
        else:
            try:
                from app.core.multimodal_search_service import get_multimodal_search_service

                service = get_multimodal_search_service()
                result = await service.search(
                    query=query,
                    paper_ids=target_papers,
                    user_id=user_id,
                    top_k=10,
                    use_reranker=False,
                )

                retrieved_ids = [r.get("id") or r.get("chunk_id") for r in result.get("results", [])]
                results = result.get("results", [])
            except Exception as e:
                print(f"Error in cross-paper query {query_id}: {e}")
                retrieved_ids = []
                results = []

        recall_5 = calculate_recall_at_k(retrieved_ids, expected_chunks, 5)
        recall_10 = calculate_recall_at_k(retrieved_ids, expected_chunks, 10)
        mrr = calculate_mrr(retrieved_ids, expected_chunks)
        section_hit = calculate_section_hit_rate(results, expected_sections)

        metrics["recall_at_5"].append(recall_5)
        metrics["recall_at_10"].append(recall_10)
        metrics["mrr"].append(mrr)
        metrics["section_hit_rate"].append(section_hit)

        query_details.append({
            "query_id": query_id,
            "query": query[:50] + "..." if len(query) > 50 else query,
            "query_type": "cross_paper",
            "recall_at_5": recall_5,
            "recall_at_10": recall_10,
            "mrr": mrr,
            "section_hit_rate": section_hit,
            "target_papers": target_papers,
        })

    # Aggregate metrics
    def avg(lst: List[float]) -> float:
        return sum(lst) / len(lst) if lst else 0.0

    report = {
        "total_queries": len(metrics["recall_at_5"]),
        "recall_at_5_avg": avg(metrics["recall_at_5"]),
        "recall_at_10_avg": avg(metrics["recall_at_10"]),
        "mrr_avg": avg(metrics["mrr"]),
        "section_hit_rate_avg": avg(metrics["section_hit_rate"]),
        "multimodal_hit_rate_avg": avg(metrics["multimodal_hit_rate"]),
        "metrics_raw": {
            "recall_at_5": metrics["recall_at_5"],
            "recall_at_10": metrics["recall_at_10"],
            "mrr": metrics["mrr"],
            "section_hit_rate": metrics["section_hit_rate"],
            "multimodal_hit_rate": metrics["multimodal_hit_rate"],
        },
        "query_details": query_details,
        "evaluation_mode": "mock" if mock_mode else "real",
        "timestamp": _get_timestamp(),
    }

    return report


def _mock_retrieval(expected_chunks: List[str], query_type: str) -> List[str]:
    """Mock retrieval for testing without services.

    Simulates realistic retrieval behavior:
    - Good retrieval for single queries (70-90% recall)
    - Moderate for compare (50-70%)
    - Lower for evolution/cross_paper (40-60%)

    Args:
        expected_chunks: Expected chunk IDs
        query_type: Type of query

    Returns:
        Simulated retrieved chunk IDs
    """
    import random

    if not expected_chunks:
        return []

    # Add noise chunks (simulate false positives)
    noise_chunks = [f"noise-{i}" for i in range(5)]

    # Determine hit rate based on query type
    hit_rates = {
        "single": 0.7,
        "compare": 0.5,
        "evolution": 0.4,
        "cross_paper": 0.4,
        "multimodal": 0.6,
    }

    hit_rate = hit_rates.get(query_type, 0.5)

    # Shuffle expected chunks and select based on hit rate
    shuffled_expected = list(expected_chunks)
    random.shuffle(shuffled_expected)

    hits = shuffled_expected[:int(len(shuffled_expected) * hit_rate + 1)]

    # Mix hits and noise
    result = []
    for i in range(10):
        if i < len(hits):
            result.append(hits[i])
        else:
            result.append(noise_chunks[i - len(hits)] if i - len(hits) < len(noise_chunks) else f"extra-{i}")

    return result


def _get_timestamp() -> str:
    """Get current timestamp in ISO format."""
    from datetime import datetime
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def main():
    parser = argparse.ArgumentParser(description="Retrieval evaluation per D-14")
    parser.add_argument(
        "--golden",
        default="tests/evals/golden_queries.json",
        help="Path to golden queries JSON file"
    )
    parser.add_argument(
        "--paper-id",
        nargs="*",
        help="Filter by specific paper IDs"
    )
    parser.add_argument(
        "--output",
        default="eval_retrieval_report.json",
        help="Output report file path"
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        default=True,
        help="Use mock mode (no real service calls)"
    )
    parser.add_argument(
        "--real",
        action="store_true",
        help="Use real mode (call actual services)"
    )

    args = parser.parse_args()

    # Determine mode
    mock_mode = not args.real

    print(f"Running retrieval evaluation in {mock_mode} mode...")
    print(f"Golden queries: {args.golden}")

    report = asyncio.run(evaluate_retrieval(
        args.golden,
        paper_ids_filter=args.paper_id,
        mock_mode=mock_mode
    ))

    # Save report
    output_path = Path(args.output)
    with open(output_path, "w") as f:
        json.dump(report, f, indent=2)

    # Print summary
    print("=" * 60)
    print("Retrieval Evaluation Report (D-14)")
    print("=" * 60)
    print(f"Total Queries: {report['total_queries']}")
    print(f"Recall@5: {report['recall_at_5_avg']:.2%}")
    print(f"Recall@10: {report['recall_at_10_avg']:.2%}")
    print(f"MRR: {report['mrr_avg']:.2%}")
    print(f"Section Hit Rate: {report['section_hit_rate_avg']:.2%}")
    print(f"Multimodal Hit Rate: {report['multimodal_hit_rate_avg']:.2%}")
    print("=" * 60)
    print(f"Report saved to: {output_path}")

    # Print per-query breakdown
    print("\nQuery Details:")
    for q in report["query_details"][:5]:
        print(f"  {q['query_id']}: R@5={q.get('recall_at_5', 0):.2f}, R@10={q.get('recall_at_10', 0):.2f}")
    if len(report["query_details"]) > 5:
        print(f"  ... and {len(report['query_details']) - 5} more queries")


if __name__ == "__main__":
    main()