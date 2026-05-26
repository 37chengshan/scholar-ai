"""Integration tests for the canonical RAG query API."""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.middleware.auth import get_current_user_id


@pytest.fixture(autouse=True)
def override_auth():
    app.dependency_overrides[get_current_user_id] = lambda: "user-1"
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def retrieval_result():
    return {
        "answer": "YOLOv4 improves training efficiency.",
        "sources": [
            {
                "paper_id": "paper-1",
                "source_id": "chunk-1",
                "score": 0.95,
                "page_num": 5,
                "section_path": "Results",
                "content_subtype": "paragraph",
                "anchor_text": "YOLOv4 improves training efficiency.",
                "text_preview": "YOLOv4 improves training efficiency compared with YOLOv3.",
            }
        ],
        "metadata": {
            "claimVerification": {"supportedClaimCount": 1},
            "supportedClaimCount": 1,
            "unsupportedClaimCount": 0,
            "abstained": False,
            "answerMode": "full",
            "query_family": "compare",
            "decontextualized_query": "compare yolov3 yolov4 training efficiency",
            "rewrite_count": 2,
            "second_pass_used": True,
            "second_pass_gain": 0.25,
            "graph_retrieval_used": False,
            "graph_candidate_count": 0,
            "graph_vector_merged_evidence": 1,
            "retrieval_evaluator": {"is_weak": False},
            "iterative_retrieval_triggered": False,
            "retrieval_trace": {"mode": "orchestrator_v2"},
            "citation_aware_metadata": {"citation_expansion_applied": False},
            "scientific_synthesis_metrics": {"citation_faithfulness": 1.0},
            "recovery_actions": [],
            "phase6_runtime": {
                "answer_mode": "full",
                "confidence_level": "high-confidence",
                "degraded": False,
                "degraded_reasons": [],
                "corrective_retrieval_used": False,
                "corrective_actions": [],
                "fallback_used": False,
                "fallback_events": [],
                "unsupported_claim_count": 0,
                "recovery_outcome": "not_needed",
                "silent_fallback": False,
                "next_step_entry": {"entry_type": "read"},
                "raptor_lite_used": False,
                "raptor_lite_signals": [],
                "review_global_evidence_used": False,
                "review_global_evidence": {},
            },
        },
    }


class TestRAGAPIUnified:
    @pytest.mark.asyncio
    async def test_rag_query_route_returns_current_contract(self, retrieval_result):
        with (
            patch("app.api.rag.get_cached_response", new=AsyncMock(return_value=None)),
            patch("app.api.rag.set_cached_response", new=AsyncMock(return_value=None)),
            patch(
                "app.api.rag.AgenticRetrievalOrchestrator.retrieve",
                new=AsyncMock(return_value=retrieval_result),
            ),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as ac:
                response = await ac.post(
                    "/api/v1/queries/query",
                    json={
                        "question": "YOLOv3和YOLOv4的区别",
                        "paper_ids": ["paper-1", "paper-2"],
                        "query_type": "compare",
                        "top_k": 5,
                    },
                )

        assert response.status_code == 200
        data = response.json()
        assert data["answer"] == "YOLOv4 improves training efficiency."
        assert data["intent"] == "compare"
        assert data["confidence"] >= 0
        assert data["supportedClaimCount"] == 1
        assert data["unsupportedClaimCount"] == 0
        assert data["answerMode"] == "full"
        assert data["query_family"] == "compare"
        assert data["planner_query_count"] == 2
        assert data["decontextualized_query"] == "compare yolov3 yolov4 training efficiency"
        assert data["second_pass_used"] is True
        assert data["second_pass_gain"] == 0.25
        assert data["phase6_runtime"]["confidence_level"] == "high-confidence"
        assert data["sources"][0]["source_id"] == "chunk-1"

    @pytest.mark.asyncio
    async def test_rag_query_normalizes_partial_legacy_source_fields(self):
        retrieval_result = {
            "answer": "Test answer",
            "sources": [
                {
                    "paper_id": "paper-1",
                    "chunk_id": "legacy-1",
                    "score": 0.8,
                    "page_num": 2,
                    "section": "Methods",
                    "content_type": "text",
                    "text_preview": "Legacy source preview",
                }
            ],
            "metadata": {},
        }

        with (
            patch("app.api.rag.get_cached_response", new=AsyncMock(return_value=None)),
            patch("app.api.rag.set_cached_response", new=AsyncMock(return_value=None)),
            patch(
                "app.api.rag.AgenticRetrievalOrchestrator.retrieve",
                new=AsyncMock(return_value=retrieval_result),
            ),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as ac:
                response = await ac.post(
                    "/api/v1/queries/query",
                    json={"question": "YOLO目标检测", "paper_ids": ["paper-1"]},
                )

        assert response.status_code == 200
        data = response.json()
        assert data["sources"][0]["source_id"] == "legacy-1"
        assert data["sources"][0]["section_path"] == "Methods"
        assert data["sources"][0]["content_subtype"] == "text"
        assert data["sources"][0]["anchor_text"] == "Legacy source preview"

    def test_rag_query_request_model_uses_current_fields(self):
        from app.api.rag import RAGQueryRequest

        req = RAGQueryRequest(
            question="test",
            paper_ids=["paper-1"],
            query_type="fact",
            top_k=3,
        )

        assert req.question == "test"
        assert req.paper_ids == ["paper-1"]
        assert not hasattr(req, "user_id")

    def test_rag_query_response_model_exposes_current_runtime_fields(self):
        from app.api.rag import RAGQueryResponse

        resp = RAGQueryResponse(
            answer="test answer",
            query="test query",
            query_family="fact",
            planner_query_count=1,
            decontextualized_query="test query",
            second_pass_used=False,
            intent="question",
            sources=[],
            confidence=0.85,
            answerEvidenceConsistency=0.5,
            lowConfidenceReasons=["retrieval_weak"],
            supportedClaimCount=0,
            unsupportedClaimCount=0,
            answerMode="partial",
            phase6_runtime={"confidence_level": "medium-confidence"},
        )

        assert resp.intent == "question"
        assert resp.answerMode == "partial"
        assert resp.lowConfidenceReasons == ["retrieval_weak"]
        assert resp.query_family == "fact"
        assert resp.phase6_runtime == {"confidence_level": "medium-confidence"}

    @pytest.mark.asyncio
    async def test_rag_query_cached_response_preserves_phase6_runtime(self):
        cached_payload = {
            "answer": "cached answer",
            "query_family": "fact",
            "planner_query_count": 1,
            "decontextualized_query": "cached query",
            "second_pass_used": False,
            "second_pass_gain": None,
            "sources": [],
            "confidence": 0.9,
            "confidence_explain": None,
            "answerEvidenceConsistency": 0.8,
            "lowConfidenceReasons": [],
            "claimVerification": None,
            "supportedClaimCount": 1,
            "unsupportedClaimCount": 0,
            "abstained": False,
            "abstainReason": None,
            "answerMode": "full",
            "graphRetrievalUsed": False,
            "graphCandidateCount": 0,
            "graphVectorMergedEvidence": 0,
            "retrievalEvaluator": None,
            "iterativeRetrievalTriggered": False,
            "retrievalTrace": {"mode": "cached"},
            "citationAwareMetadata": None,
            "scientificSynthesisMetrics": None,
            "recoveryActions": [],
            "phase6_runtime": {"confidence_level": "high-confidence"},
        }

        with (
            patch("app.api.rag.get_cached_response", new=AsyncMock(return_value=cached_payload)),
            patch("app.api.rag.set_cached_response", new=AsyncMock(return_value=None)),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as ac:
                response = await ac.post(
                    "/api/v1/queries/query",
                    json={"question": "cached question", "paper_ids": ["paper-1"]},
                )

        assert response.status_code == 200
        data = response.json()
        assert data["cached"] is True
        assert data["phase6_runtime"] == {"confidence_level": "high-confidence"}
        assert data["query_family"] == "fact"
