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
def answer_contract_payload():
    return {
        "response_type": "rag",
        "answer_mode": "full",
        "answer": "YOLOv4 improves training efficiency.",
        "claims": [],
        "citations": [
            {
                "paper_id": "paper-1",
                "source_chunk_id": "chunk-1",
                "source_id": "chunk-1",
                "score": 0.95,
                "page_num": 5,
                "section_path": "Results",
                "content_type": "paragraph",
                "anchor_text": "YOLOv4 improves training efficiency.",
                "text_preview": "YOLOv4 improves training efficiency compared with YOLOv3.",
            }
        ],
        "evidence_blocks": [],
        "quality": {},
        "trace": {
            "query_family": "compare",
            "trace_id": "trace-1",
            "run_id": "run-1",
        },
        "truthfulness_summary": {
            "supportedClaimCount": 1,
            "unsupportedClaimCount": 0,
        },
        "truthfulness_report": {
            "answerMode": "full",
            "summary": {
                "supportedClaimCount": 1,
                "unsupportedClaimCount": 0,
            },
        },
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
    }


class TestRAGAPIUnified:
    @pytest.mark.asyncio
    async def test_rag_query_route_returns_current_contract(self, answer_contract_payload):
        with (
            patch("app.api.rag.get_cached_response", new=AsyncMock(return_value=None)),
            patch("app.api.rag.set_cached_response", new=AsyncMock(return_value=None)),
            patch(
                "app.api.rag.build_answer_contract_payload",
                new=AsyncMock(return_value=answer_contract_payload),
            ),
            patch(
                "app.api.rag.build_academic_query_plan",
                return_value={
                    "query_family": "compare",
                    "planner_query_count": 2,
                    "decontextualized_query": "compare yolov3 yolov4 training efficiency",
                },
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
        assert data["second_pass_used"] is False
        assert data["second_pass_gain"] is None
        assert data["phase6_runtime"]["confidence_level"] == "high-confidence"
        assert data["sources"][0]["source_id"] == "chunk-1"

    @pytest.mark.asyncio
    async def test_rag_query_normalizes_partial_legacy_source_fields(self):
        answer_contract_payload = {
            "response_type": "rag",
            "answer_mode": "partial",
            "answer": "Test answer",
            "claims": [],
            "citations": [
                {
                    "paper_id": "paper-1",
                    "source_chunk_id": "legacy-1",
                    "score": 0.8,
                    "page_num": 2,
                    "section_path": "Methods",
                    "content_type": "text",
                    "text_preview": "Legacy source preview",
                }
            ],
            "evidence_blocks": [],
            "quality": {},
            "trace": {"query_family": "fact", "trace_id": "trace-2", "run_id": "run-2"},
            "truthfulness_summary": {"supportedClaimCount": 0, "unsupportedClaimCount": 0},
            "truthfulness_report": {"answerMode": "partial", "summary": {"supportedClaimCount": 0, "unsupportedClaimCount": 0}},
            "recovery_actions": [],
            "phase6_runtime": {"corrective_retrieval_used": False, "confidence_level": "medium-confidence"},
        }

        with (
            patch("app.api.rag.get_cached_response", new=AsyncMock(return_value=None)),
            patch("app.api.rag.set_cached_response", new=AsyncMock(return_value=None)),
            patch(
                "app.api.rag.build_answer_contract_payload",
                new=AsyncMock(return_value=answer_contract_payload),
            ),
            patch(
                "app.api.rag.build_academic_query_plan",
                return_value={
                    "query_family": "fact",
                    "planner_query_count": 1,
                    "decontextualized_query": "YOLO目标检测",
                },
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
            "answer_contract_payload": {
                "response_type": "rag",
                "answer_mode": "full",
                "answer": "cached answer",
                "claims": [],
                "citations": [],
                "evidence_blocks": [],
                "quality": {},
                "trace": {"query_family": "fact", "trace_id": "trace-cached", "run_id": "run-cached"},
                "truthfulness_summary": {"supportedClaimCount": 1, "unsupportedClaimCount": 0},
                "truthfulness_report": {"answerMode": "full", "summary": {"supportedClaimCount": 1, "unsupportedClaimCount": 0}},
                "recovery_actions": [],
                "phase6_runtime": {"confidence_level": "high-confidence", "corrective_retrieval_used": False},
            },
            "query_plan": {
                "query_family": "fact",
                "planner_query_count": 1,
                "decontextualized_query": "cached query",
            },
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
        assert data["phase6_runtime"]["confidence_level"] == "high-confidence"
        assert data["query_family"] == "fact"
