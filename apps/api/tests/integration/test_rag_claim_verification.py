import importlib
from unittest.mock import AsyncMock, patch

import pytest


def _load_rag_symbols():
    from starlette.routing import Router

    original_init = Router.__init__

    def compatible_init(self, *args, **kwargs):
        kwargs.pop("on_startup", None)
        kwargs.pop("on_shutdown", None)
        kwargs.pop("lifespan", None)
        return original_init(self, *args, **kwargs)

    with patch.object(Router, "__init__", compatible_init):
        rag_module = importlib.import_module("app.api.rag")
    return rag_module.RAGQueryRequest, rag_module.rag_query


@pytest.mark.asyncio
async def test_rag_query_exposes_claim_verification_fields() -> None:
    RAGQueryRequest, rag_query = _load_rag_symbols()
    retrieval_result = {
        "answer": "Method A improves F1 on SQuAD [Paper A, Results].",
        "sources": [
            {
                "paper_id": "paper-a",
                "paper_title": "Paper A",
                "score": 0.92,
                "page_num": 5,
                "source_id": "source-1",
                "section_path": "Results",
                "section": "Results",
                "content_subtype": "paragraph",
                "content_type": "text",
                "anchor_text": "Method A improves F1 on SQuAD",
                "text_preview": "Method A improves F1 on SQuAD",
                "text": "Method A improves F1 on SQuAD and outperforms the baseline.",
            }
        ],
        "metadata": {
            "claimVerification": {
                "totalClaims": 1,
                "supportedClaimCount": 1,
                "unsupportedClaimCount": 0,
                "weaklySupportedClaimCount": 0,
                "unsupportedClaimRate": 0.0,
                "results": [
                    {
                        "claim_id": "claim-1",
                        "text": "Method A improves F1 on SQuAD",
                        "claim_type": "numeric",
                        "support_level": "supported",
                        "evidence_ids": ["source-1"],
                        "support_score": 0.9,
                    }
                ],
            },
            "supportedClaimCount": 1,
            "unsupportedClaimCount": 0,
            "abstained": False,
            "abstainReason": None,
            "answerMode": "full",
            "graph_retrieval_used": False,
            "graph_candidate_count": 0,
            "graph_vector_merged_evidence": 1,
            "retrieval_evaluator": {
                "is_weak": False,
                "weak_reasons": [],
                "metrics": {"score_coverage": 0.88},
            },
            "iterative_retrieval_triggered": False,
            "retrieval_trace": {"mode": "orchestrator_v2", "iterative_triggered": False, "rounds": []},
            "citation_aware_metadata": {"citation_expansion_applied": False},
            "scientific_synthesis_metrics": {
                "citation_faithfulness": 1.0,
                "unsupported_claim_rate": 0.0,
                "cross_paper_synthesis_quality": 0.9,
                "partial_abstain_quality": 1.0,
            },
        },
    }

    with (
        patch("app.api.rag.get_cached_response", new=AsyncMock(return_value=None)),
        patch("app.api.rag.set_cached_response", new=AsyncMock(return_value=None)),
        patch("app.api.rag.AgenticRetrievalOrchestrator.retrieve", new=AsyncMock(return_value=retrieval_result)),
        patch("app.api.rag.calculate_confidence", return_value=(0.88, {"score_coverage": 0.8}, 0.85, [])),
    ):
        response = await rag_query(
            RAGQueryRequest(question="What does Method A improve?", paper_ids=["paper-a"], query_type="fact", top_k=5),
            user_id="user-1",
        )

    assert response.claimVerification["supportedClaimCount"] == 1
    assert response.supportedClaimCount == 1
    assert response.unsupportedClaimCount == 0
    assert response.abstained is False
    assert response.answerMode == "full"
    assert response.retrievalEvaluator["is_weak"] is False
    assert response.iterativeRetrievalTriggered is False
    assert response.retrievalTrace["mode"] == "orchestrator_v2"
    assert response.citationAwareMetadata["citation_expansion_applied"] is False
