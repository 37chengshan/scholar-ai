#!/usr/bin/env python
"""Answer quality evaluation per D-14.

Measures:
- Evidence support rate (claims backed by retrieved chunks)
- Citation grounding rate (citations per 100 words)
- Unsupported claim rate (claims without citations)

Usage:
    python scripts/eval_answer.py --golden tests/evals/golden_queries.json
    python scripts/eval_answer.py --real  # Use real services
"""

import json
import asyncio
import re
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional

# Add backend to path for imports
import sys
backend_path = Path(__file__).parent.parent / "apps" / "api"
if backend_path.exists():
    sys.path.insert(0, str(backend_path))


def extract_citations(answer: str) -> List[Tuple[str, str]]:
    """Extract citations from answer.

    Format: [Paper Title, Section] or [Paper Title, Page N]

    Args:
        answer: Generated answer text

    Returns:
        List of (paper_title, location) tuples
    """
    pattern = r"\[([^,\[\]]+),\s*([^\[\]]+)\]"
    matches = re.findall(pattern, answer)
    return [(paper.strip(), location.strip()) for paper, location in matches]


def count_sentences(text: str) -> int:
    """Count sentences in text.

    Args:
        text: Text to analyze

    Returns:
        Number of sentences
    """
    sentences = re.split(r'[.!?]+', text)
    return len([s for s in sentences if s.strip()])


def calculate_citation_density(answer: str) -> float:
    """Calculate citations per 100 words.

    Args:
        answer: Generated answer text

    Returns:
        Citation density (citations per 100 words)
    """
    citations = extract_citations(answer)
    # Remove citation markers to count pure content
    content_only = re.sub(r"\[([^,\[\]]+),\s*([^\[\]]+)\]", "", answer)
    words = content_only.split()
    if not words:
        return 0.0
    return (len(citations) / len(words)) * 100


def calculate_unsupported_rate(answer: str) -> float:
    """Calculate percentage of sentences without citations.

    Args:
        answer: Generated answer text

    Returns:
        Unsupported claim rate (0.0 to 1.0)
    """
    sentences = re.split(r'[.!?]+', answer)
    unsupported = 0
    for sentence in sentences:
        if sentence.strip() and not re.search(r"\[([^,\[\]]+),\s*([^\[\]]+)\]", sentence):
            unsupported += 1
    total = len([s for s in sentences if s.strip()])
    if total == 0:
        return 0.0
    return unsupported / total


def calculate_evidence_support_rate(
    sources: List[Dict[str, Any]],
    expected_chunks: List[str]
) -> float:
    """Calculate how many expected chunks were actually retrieved.

    Args:
        sources: Retrieved sources/chunks
        expected_chunks: Expected gold chunk IDs

    Returns:
        Evidence support rate (0.0 to 1.0)
    """
    if not expected_chunks:
        return 0.0

    retrieved_ids = set()
    for source in sources:
        chunk_id = source.get("chunk_id") or source.get("id")
        if chunk_id:
            retrieved_ids.add(chunk_id)

    expected_set = set(expected_chunks)
    intersection = len(retrieved_ids & expected_set)

    return intersection / len(expected_set)


async def evaluate_answer(
    golden_queries_path: str,
    user_id: str = "eval-user",
    mock_mode: bool = True
) -> Dict[str, Any]:
    """Run answer quality evaluation.

    Args:
        golden_queries_path: Path to golden_queries.json
        user_id: User ID for retrieval filtering
        mock_mode: If True, use mock answers (for testing)

    Returns:
        Evaluation report with answer quality metrics
    """
    with open(golden_queries_path) as f:
        golden = json.load(f)

    metrics = {
        "citation_density": [],
        "unsupported_rate": [],
        "evidence_support": [],
        "citation_count": [],
        "source_count": [],
    }

    query_reports = []

    # Evaluate paper queries
    for paper_data in golden.get("papers", []):
        paper_id = paper_data.get("paper_id")
        paper_title = paper_data.get("title", "Unknown Paper")

        for query_data in paper_data.get("queries", []):
            query_id = query_data.get("id")
            query = query_data.get("query")
            expected_chunks = query_data.get("expected_chunks", [])

            if mock_mode:
                # Mock: generate a sample answer with citations
                answer, sources = _mock_answer_generation(
                    query, paper_title, expected_chunks
                )
            else:
                # Real: call AgenticRetrievalOrchestrator
                try:
                    from app.core.agentic_retrieval import AgenticRetrievalOrchestrator

                    orchestrator = AgenticRetrievalOrchestrator(max_rounds=1)
                    result = await orchestrator.retrieve(
                        query=query,
                        paper_ids=[paper_id],
                        user_id=user_id,
                        top_k_per_subquestion=10,
                    )

                    answer = result.get("answer", "")
                    sources = result.get("sources", [])
                except Exception as e:
                    print(f"Error in agentic retrieval for {query_id}: {e}")
                    answer = "Error: Unable to generate answer."
                    sources = []

            # Calculate metrics
            citations = extract_citations(answer)
            citation_density = calculate_citation_density(answer)
            unsupported_rate = calculate_unsupported_rate(answer)
            evidence_support = calculate_evidence_support_rate(sources, expected_chunks)

            metrics["citation_density"].append(citation_density)
            metrics["unsupported_rate"].append(unsupported_rate)
            metrics["evidence_support"].append(evidence_support)
            metrics["citation_count"].append(len(citations))
            metrics["source_count"].append(len(sources))

            query_reports.append({
                "query_id": query_id,
                "query": query[:50] + "..." if len(query) > 50 else query,
                "paper_id": paper_id,
                "answer_preview": answer[:200] + "..." if len(answer) > 200 else answer,
                "citation_count": len(citations),
                "citation_density": citation_density,
                "unsupported_rate": unsupported_rate,
                "evidence_support": evidence_support,
                "source_count": len(sources),
                "expected_chunks_count": len(expected_chunks),
                "citations": citations[:5],  # First 5 citations
            })

    # Evaluate cross-paper queries
    for cp in golden.get("cross_paper_queries", []):
        query_id = cp.get("id")
        query = cp.get("query")
        target_papers = cp.get("paper_ids", [])
        expected_chunks = cp.get("expected_chunks", [])

        if mock_mode:
            answer, sources = _mock_answer_generation(
                query, "Multiple Papers", expected_chunks
            )
        else:
            try:
                from app.core.agentic_retrieval import AgenticRetrievalOrchestrator

                orchestrator = AgenticRetrievalOrchestrator(max_rounds=1)
                result = await orchestrator.retrieve(
                    query=query,
                    paper_ids=target_papers,
                    user_id=user_id,
                    top_k_per_subquestion=10,
                )

                answer = result.get("answer", "")
                sources = result.get("sources", [])
            except Exception as e:
                print(f"Error in cross-paper query {query_id}: {e}")
                answer = "Error: Unable to generate answer."
                sources = []

        citations = extract_citations(answer)
        citation_density = calculate_citation_density(answer)
        unsupported_rate = calculate_unsupported_rate(answer)
        evidence_support = calculate_evidence_support_rate(sources, expected_chunks)

        metrics["citation_density"].append(citation_density)
        metrics["unsupported_rate"].append(unsupported_rate)
        metrics["evidence_support"].append(evidence_support)
        metrics["citation_count"].append(len(citations))
        metrics["source_count"].append(len(sources))

        query_reports.append({
            "query_id": query_id,
            "query": query[:50] + "..." if len(query) > 50 else query,
            "query_type": "cross_paper",
            "answer_preview": answer[:200] + "..." if len(answer) > 200 else answer,
            "citation_count": len(citations),
            "citation_density": citation_density,
            "unsupported_rate": unsupported_rate,
            "evidence_support": evidence_support,
            "source_count": len(sources),
            "target_papers": target_papers,
        })

    # Aggregate metrics
    def avg(lst: List[float]) -> float:
        return sum(lst) / len(lst) if lst else 0.0

    report = {
        "total_queries": len(metrics["citation_density"]),
        "citation_density_avg": avg(metrics["citation_density"]),
        "unsupported_rate_avg": avg(metrics["unsupported_rate"]),
        "evidence_support_avg": avg(metrics["evidence_support"]),
        "citation_count_avg": avg(metrics["citation_count"]),
        "source_count_avg": avg(metrics["source_count"]),
        "metrics_raw": {
            "citation_density": metrics["citation_density"],
            "unsupported_rate": metrics["unsupported_rate"],
            "evidence_support": metrics["evidence_support"],
        },
        "queries": query_reports,
        "evaluation_mode": "mock" if mock_mode else "real",
        "timestamp": _get_timestamp(),
    }

    return report


def _mock_answer_generation(
    query: str,
    paper_title: str,
    expected_chunks: List[str]
) -> Tuple[str, List[Dict]]:
    """Mock answer generation for testing without services.

    Args:
        query: Query text
        paper_title: Paper title for citations
        expected_chunks: Expected chunk IDs

    Returns:
        Tuple of (answer, sources)
    """
    # Generate mock answer with citations
    if not expected_chunks:
        answer = f"I could not find specific evidence for '{query[:30]}...' in the paper."
        sources = []
    else:
        # Create a mock answer with proper citations
        answer = f"""Based on the analysis of {paper_title}, the answer to your query is:

The main findings indicate significant results in the methodology section [{paper_title[:30]}, Methods]. Key contributions are discussed in the introduction [{paper_title[:30]}, Introduction], with supporting evidence in the results [{paper_title[:30]}, Results].

The proposed approach demonstrates improvements over baseline methods, as shown in the comparison analysis [{paper_title[:30]}, Comparison]. This represents a meaningful advancement in the field."""
        sources = [
            {"chunk_id": expected_chunks[0] if expected_chunks else "mock-1",
             "paper_id": "test-paper-001",
             "content_preview": "Mock content for testing...",
             "section": "Methods"}
        ]

    return answer, sources


def _get_timestamp() -> str:
    """Get current timestamp in ISO format."""
    from datetime import datetime
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def main():
    parser = argparse.ArgumentParser(description="Answer quality evaluation per D-14")
    parser.add_argument(
        "--golden",
        default="tests/evals/golden_queries.json",
        help="Path to golden queries JSON file"
    )
    parser.add_argument(
        "--output",
        default="eval_answer_report.json",
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

    print(f"Running answer quality evaluation in {mock_mode} mode...")
    print(f"Golden queries: {args.golden}")

    report = asyncio.run(evaluate_answer(
        args.golden,
        mock_mode=mock_mode
    ))

    # Save report
    output_path = Path(args.output)
    with open(output_path, "w") as f:
        json.dump(report, f, indent=2)

    # Print summary
    print("=" * 60)
    print("Answer Quality Evaluation Report (D-14)")
    print("=" * 60)
    print(f"Total Queries: {report['total_queries']}")
    print(f"Citation Density: {report['citation_density_avg']:.2f} per 100 words")
    print(f"Unsupported Rate: {report['unsupported_rate_avg']:.2%}")
    print(f"Evidence Support: {report['evidence_support_avg']:.2%}")
    print(f"Avg Citation Count: {report['citation_count_avg']:.1f}")
    print(f"Avg Source Count: {report['source_count_avg']:.1f}")
    print("=" * 60)
    print(f"Report saved to: {output_path}")

    # Print per-query breakdown
    print("\nQuery Details:")
    for q in report["queries"][:5]:
        print(f"  {q['query_id']}: citations={q['citation_count']}, support={q['evidence_support']:.2%}")
    if len(report["queries"]) > 5:
        print(f"  ... and {len(report['queries']) - 5} more queries")


if __name__ == "__main__":
    main()