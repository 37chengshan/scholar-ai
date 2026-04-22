from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.agentic_retrieval import AgenticRetrievalOrchestrator


@pytest.mark.asyncio
async def test_agentic_retrieval_includes_graph_metadata() -> None:
    orchestrator = AgenticRetrievalOrchestrator(max_rounds=1)
    orchestrator.decomposer = MagicMock()
    orchestrator.decomposer.decompose_query = AsyncMock(
        return_value=[
            {
                "question": "Which paper improved F1 on SQuAD over baseline BERT?",
                "query_type": "compare",
                "target_papers": ["paper-a", "paper-b"],
                "rationale": "graph compare",
            }
        ]
    )
    orchestrator.graph_query_compiler = MagicMock()
    orchestrator.graph_query_compiler.compile.return_value = {
        "query_family": "compare",
        "requires_graph": True,
    }
    orchestrator.graph_retrieval_service = MagicMock()
    orchestrator.graph_retrieval_service.expand_graph_context = AsyncMock(
        return_value=[
            {
                "graph_candidate_id": "graph-1",
                "paper_id": "paper-a",
                "relation": "improves_metric_on_dataset",
                "score": 0.88,
            }
        ]
    )
    orchestrator.search_service = MagicMock()
    orchestrator.search_service.search = AsyncMock(
        return_value={
            "intent": "compare",
            "results": [
                {
                    "paper_id": "paper-a",
                    "paper_title": "Paper A",
                    "text": "Paper A improves F1 on SQuAD over baseline BERT.",
                    "score": 0.91,
                    "page_num": 4,
                    "source_id": "source-1",
                    "section": "Results",
                }
            ],
        }
    )
    orchestrator._final_synthesis = AsyncMock(
        return_value="Paper A improves F1 on SQuAD over baseline BERT [Paper A, Results]."
    )

    result = await orchestrator.retrieve(
        query="Which paper improved F1 on SQuAD over baseline BERT?",
        query_type="compare",
        paper_ids=["paper-a", "paper-b"],
        user_id="user-1",
        top_k_per_subquestion=3,
    )

    metadata = result["metadata"]
    assert metadata["graph_retrieval_used"] is True
    assert metadata["graph_candidate_count"] == 1
    assert metadata["graph_vector_merged_evidence"] == 1
    assert metadata["benchmarkMetrics"]["compare_accuracy"] == 1.0
