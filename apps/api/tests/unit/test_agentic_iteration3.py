from unittest.mock import AsyncMock

import pytest

from app.core.agentic_retrieval import AgenticRetrievalOrchestrator


@pytest.mark.asyncio
async def test_iteration3_triggers_iterative_on_weak_first_pass(monkeypatch: pytest.MonkeyPatch) -> None:
    orchestrator = AgenticRetrievalOrchestrator(max_rounds=2)

    async def fake_decompose_query(**_: object):
        return [{"question": "compare methods", "rationale": "seed"}]

    async def fake_expand_graph_context(**_: object):
        return []

    async def fake_reason_citation_context(**_: object):
        return {
            "foundational": [{"paper_id": "paper-found", "relation": "foundational"}],
            "follow_up": [],
            "competing": [],
            "evolution_chain": [],
            "merged_candidates": [{"paper_id": "paper-found", "relation": "foundational"}],
        }

    async def fake_execute_subquestions_parallel(**kwargs: object):
        if kwargs.get("graph_candidates"):
            return [
                {
                    "sub_question": "improved round",
                    "chunks": [
                        {
                            "source_id": "chunk-2",
                            "paper_id": "paper-found",
                            "paper_title": "Foundational Paper",
                            "text": "Method B outperforms baseline.",
                            "score": 0.9,
                            "page_num": 3,
                            "section": "Results",
                        }
                    ],
                    "success": True,
                }
            ]
        return [
            {
                "sub_question": "weak round",
                "chunks": [
                    {
                        "source_id": "chunk-1",
                        "paper_id": "paper-a",
                        "paper_title": "Paper A",
                        "text": "Very limited evidence.",
                        "score": 0.22,
                        "page_num": 1,
                        "section": "Intro",
                        "content_type": "text",
                    }
                ],
                "success": True,
            }
        ]

    monkeypatch.setattr(orchestrator.decomposer, "decompose_query", fake_decompose_query)
    monkeypatch.setattr(orchestrator.graph_retrieval_service, "expand_graph_context", fake_expand_graph_context)
    monkeypatch.setattr(orchestrator.graph_retrieval_service, "reason_citation_context", fake_reason_citation_context)
    monkeypatch.setattr(orchestrator, "_execute_subquestions_parallel", fake_execute_subquestions_parallel)
    monkeypatch.setattr(orchestrator, "_synthesize_results", AsyncMock(return_value="round synthesis"))
    monkeypatch.setattr(
        orchestrator,
        "_final_synthesis",
        AsyncMock(return_value="Claim supported by evidence [Foundational Paper, Results]."),
    )

    result = await orchestrator.retrieve(
        query="compare method A and B",
        query_type="compare",
        paper_ids=["paper-a", "paper-b"],
        user_id="user-1",
        top_k_per_subquestion=3,
    )

    meta = result["metadata"]
    assert meta["iterative_retrieval_triggered"] is True
    assert meta["retrieval_evaluator"]["is_weak"] is True
    assert meta["citation_aware_metadata"]["citation_expansion_applied"] is True
    assert meta["retrieval_trace"]["iterative_triggered"] is True
    assert meta["answer_outline"]
