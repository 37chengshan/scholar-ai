"""Integration tests for unified RAG API using MultimodalSearchService.

Tests verify:
1. RAG API endpoint uses MultimodalSearchService
2. Query understanding features (intent, expansion, metadata) in responses
3. Backward compatibility maintained
4. Response structure matches D-15 specification

Per Plan 04-03: Update API routes to use unified MultimodalSearchService.
"""

import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, MagicMock, patch

from app.main import app


@pytest.fixture
async def client():
    """Create async test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def mock_multimodal_service():
    """Mock MultimodalSearchService for testing."""
    service = MagicMock()

    # Mock search response with query understanding fields
    service.search = AsyncMock(return_value={
        "query": "YOLOv3和YOLOv4的区别",
        "expanded_query": "YOLOv3 OR object detection OR real-time detection 和 YOLOv4 OR object detection OR real-time detection 的区别 OR 对比 OR 比较",
        "intent": "compare",
        "metadata_filters": {},
        "weights": {"text": 0.5, "image": 0.3, "table": 0.2},
        "results": [
            {
                "id": "chunk-1",
                "paper_id": "paper-1",
                "content_type": "text",
                "content_data": "YOLOv3 uses Darknet-53 backbone...",
                "score": 0.95,
                "page_num": 5,
            },
            {
                "id": "chunk-2",
                "paper_id": "paper-2",
                "content_type": "text",
                "content_data": "YOLOv4 introduces CSPDarknet53...",
                "score": 0.92,
                "page_num": 3,
            },
        ],
        "total_count": 2,
    })

    return service


class TestRAGAPIUnified:
    """Test unified RAG API integration."""

    @pytest.mark.asyncio
    async def test_rag_query_endpoint_imports_multimodal_service(self):
        """Test that rag.py imports MultimodalSearchService."""
        # Verify import exists in rag.py
        import app.api.rag as rag_module
        # Check if import statement exists in module
        import inspect
        source = inspect.getsource(rag_module)
        assert "get_multimodal_search_service" in source or "MultimodalSearchService" in source

    @pytest.mark.asyncio
    async def test_rag_query_with_intent(self, client, mock_multimodal_service):
        """Test RAG query endpoint returns intent field.

        Per Plan 04-03 Task 1: API response includes intent.
        """
        with patch("app.api.rag.get_multimodal_search_service", return_value=mock_multimodal_service):
            response = await client.post(
                "/rag/query",
                json={
                    "question": "YOLOv3和YOLOv4的区别",
                    "paper_ids": ["paper-1", "paper-2"],
                    "user_id": "user-1",
                }
            )

            assert response.status_code == 200
            data = response.json()

            # Check intent field in response (D-15 requirement)
            assert "intent" in data
            assert data["intent"] == "compare"

    @pytest.mark.asyncio
    async def test_rag_query_expansion(self, client, mock_multimodal_service):
        """Test RAG query endpoint returns expanded_query field.

        Per Plan 04-03 Task 1: API response includes expanded query.
        """
        with patch("app.api.rag.get_multimodal_search_service", return_value=mock_multimodal_service):
            response = await client.post(
                "/rag/query",
                json={
                    "question": "YOLO目标检测",
                    "paper_ids": ["paper-1"],
                    "user_id": "user-1",
                }
            )

            assert response.status_code == 200
            data = response.json()

            # Check expanded_query field (D-04 requirement)
            assert "expanded_query" in data
            assert "object detection" in data["expanded_query"] or "OR" in data["expanded_query"]

    @pytest.mark.asyncio
    async def test_rag_query_metadata_filters(self, client, mock_multimodal_service):
        """Test RAG query endpoint returns metadata_filters field.

        Per Plan 04-03 Task 1: API response includes metadata filters.
        """
        # Create service mock with metadata filters
        service_with_filters = MagicMock()
        service_with_filters.search = AsyncMock(return_value={
            "query": "2023年的论文",
            "expanded_query": "2023 年的论文",
            "intent": "question",
            "metadata_filters": {"year_range": (2023, 2023)},
            "weights": {"text": 0.5, "image": 0.3, "table": 0.2},
            "results": [],
            "total_count": 0,
        })

        with patch("app.api.rag.get_multimodal_search_service", return_value=service_with_filters):
            response = await client.post(
                "/rag/query",
                json={
                    "question": "2023年的论文",
                    "paper_ids": ["paper-1"],
                    "user_id": "user-1",
                }
            )

            assert response.status_code == 200
            data = response.json()

            # Check metadata_filters field (D-07 requirement)
            assert "metadata_filters" in data
            assert data["metadata_filters"]["year_range"] == (2023, 2023)

    @pytest.mark.asyncio
    async def test_rag_query_backward_compat(self, client, mock_multimodal_service):
        """Test backward compatibility - old clients still work.

        Per Plan 04-03: Maintain backward compatibility with existing clients.
        """
        with patch("app.api.rag.get_multimodal_search_service", return_value=mock_multimodal_service):
            response = await client.post(
                "/rag/query",
                json={
                    "question": "What is attention?",
                    "paper_ids": ["paper-1"],
                    "user_id": "user-1",
                }
            )

            assert response.status_code == 200
            data = response.json()

            # Old fields should still exist
            assert "answer" in data or "results" in data
            assert "sources" in data

    @pytest.mark.asyncio
    async def test_rag_query_request_model_has_user_id(self):
        """Test RAGQueryRequest model includes user_id field.

        Per Plan 04-03 Task 1: Add user_id to request model.
        """
        from app.api.rag import RAGQueryRequest

        # Should have user_id field
        req = RAGQueryRequest(
            question="test",
            paper_ids=["paper-1"],
            user_id="user-1"
        )
        assert req.user_id == "user-1"

    @pytest.mark.asyncio
    async def test_rag_query_response_model_has_new_fields(self):
        """Test RAGQueryResponse model includes new fields.

        Per Plan 04-03 Task 1: Add intent, expanded_query, metadata_filters to response.
        """
        from app.api.rag import RAGQueryResponse
        from typing import Dict

        # Should accept new optional fields
        resp = RAGQueryResponse(
            answer="test answer",
            query="test query",
            expanded_query="expanded test",
            intent="question",
            metadata_filters={"year_range": (2023, 2023)},
            sources=[],
        )
        assert resp.expanded_query == "expanded test"
        assert resp.intent == "question"
        assert resp.metadata_filters == {"year_range": (2023, 2023)}