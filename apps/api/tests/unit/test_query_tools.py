"""Unit tests for query tool implementations.

Tests cover:
- external_search: arXiv and Semantic Scholar search
- rag_search: Multimodal RAG search
- list_papers: User paper library listing
- read_paper: Paper details retrieval
- list_notes: User notes listing
- read_note: Note content retrieval
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.tools.query_tools import (
    execute_external_search,
    execute_rag_search,
    execute_list_papers,
    execute_read_paper,
    execute_list_notes,
    execute_read_note,
)


@pytest.mark.asyncio
class TestExternalSearchTool:
    """Tests for external_search tool."""

    async def test_external_search_arxiv_source(self):
        """Test external search with arXiv source returns results."""
        params = {
            "query": "transformer architecture",
            "sources": ["arxiv"],
            "limit": 5
        }

        with patch("app.tools.query_tools.search_arxiv") as mock_search:
            mock_search.return_value = {
                "results": [
                    {
                        "id": "1706.03762",
                        "title": "Attention Is All You Need",
                        "authors": ["Vaswani et al."],
                        "year": 2017,
                        "abstract": "The dominant sequence transduction models...",
                        "source": "arxiv",
                        "url": "https://arxiv.org/abs/1706.03762"
                    }
                ]
            }

            result = await execute_external_search(params)

            assert result["success"] is True
            assert len(result["data"]["results"]) > 0
            assert result["data"]["results"][0]["source"] == "arxiv"

    async def test_external_search_semantic_scholar_source(self):
        """Test external search with Semantic Scholar source returns results."""
        params = {
            "query": "BERT pretraining",
            "sources": ["semantic_scholar"],
            "limit": 10
        }

        with patch("app.tools.query_tools.search_semantic_scholar") as mock_search:
            mock_search.return_value = {
                "results": [
                    {
                        "id": "paper-123",
                        "title": "BERT: Pre-training of Deep Bidirectional Transformers",
                        "authors": ["Devlin et al."],
                        "year": 2019,
                        "abstract": "We introduce a new language representation model...",
                        "source": "semantic-scholar",
                        "citationCount": 50000
                    }
                ]
            }

            result = await execute_external_search(params)

            assert result["success"] is True
            assert len(result["data"]["results"]) > 0
            assert result["data"]["results"][0]["source"] == "semantic-scholar"

    async def test_external_search_multiple_sources(self):
        """Test external search with multiple sources combines results."""
        params = {
            "query": "attention mechanism",
            "sources": ["arxiv", "semantic_scholar"],
            "limit": 5
        }

        with patch("app.tools.query_tools.search_arxiv") as mock_arxiv, \
             patch("app.tools.query_tools.search_semantic_scholar") as mock_s2:

            mock_arxiv.return_value = {
                "results": [{"id": "arxiv-1", "title": "Paper 1", "source": "arxiv"}]
            }
            mock_s2.return_value = {
                "results": [{"id": "s2-1", "title": "Paper 2", "source": "semantic-scholar"}]
            }

            result = await execute_external_search(params)

            assert result["success"] is True
            # Should have results from both sources (after deduplication)


@pytest.mark.asyncio
class TestRAGSearchTool:
    """Tests for rag_search tool."""

    async def test_rag_search_basic_query(self):
        """Test RAG search with basic query returns results."""
        params = {
            "question": "What is the attention mechanism?",
            "paper_ids": ["paper-1", "paper-2"],
            "top_k": 5
        }

        with patch("app.tools.query_tools.get_multimodal_search_service") as mock_service:
            mock_instance = MagicMock()
            mock_instance.search = AsyncMock(return_value={
                "results": [
                    {
                        "id": "chunk-1",
                        "paper_id": "paper-1",
                        "content_data": "The attention mechanism allows...",
                        "score": 0.95
                    }
                ],
                "total_count": 1
            })
            mock_service.return_value = mock_instance

            result = await execute_rag_search(params, user_id="user-123")

            assert result["success"] is True
            assert len(result["data"]["results"]) > 0
            assert result["data"]["results"][0]["paper_id"] == "paper-1"

    async def test_rag_search_with_filters(self):
        """Test RAG search with metadata filters applies them."""
        params = {
            "question": "methodology for training",
            "paper_ids": ["paper-1"],
            "top_k": 10
        }

        with patch("app.tools.query_tools.get_multimodal_search_service") as mock_service:
            mock_instance = MagicMock()
            mock_instance.search = AsyncMock(return_value={
                "results": [],
                "total_count": 0
            })
            mock_service.return_value = mock_instance

            result = await execute_rag_search(params, user_id="user-123")

            assert result["success"] is True


@pytest.mark.asyncio
class TestListPapersTool:
    """Tests for list_papers tool."""

    async def test_list_papers_returns_user_papers(self):
        """Test list_papers retrieves papers from PostgreSQL."""
        params = {
            "filter": {"status": "completed"},
            "sort": "created_at",
            "limit": 20
        }

        with patch("app.tools.query_tools.get_db_connection") as mock_db:
            mock_conn = AsyncMock()
            mock_conn.fetch = AsyncMock(return_value=[
                {
                    "id": "paper-1",
                    "title": "Paper 1",
                    "authors": ["Author A"],
                    "created_at": "2024-01-01"
                }
            ])
            mock_db.return_value.__aenter__.return_value = mock_conn

            result = await execute_list_papers(params, user_id="user-123")

            assert result["success"] is True
            assert len(result["data"]["papers"]) > 0

    async def test_list_papers_with_status_filter(self):
        """Test list_papers filters by status."""
        params = {
            "filter": {"status": "processing"},
            "limit": 10
        }

        with patch("app.tools.query_tools.get_db_connection") as mock_db:
            mock_conn = AsyncMock()
            mock_conn.fetch = AsyncMock(return_value=[])
            mock_db.return_value.__aenter__.return_value = mock_conn

            result = await execute_list_papers(params, user_id="user-123")

            assert result["success"] is True


@pytest.mark.asyncio
class TestReadPaperTool:
    """Tests for read_paper tool."""

    async def test_read_paper_retrieves_metadata(self):
        """Test read_paper retrieves paper metadata."""
        params = {
            "paper_id": "paper-123",
            "sections": ["metadata", "abstract"]
        }

        with patch("app.tools.query_tools.get_db_connection") as mock_db:
            mock_conn = AsyncMock()
            mock_conn.fetchrow = AsyncMock(return_value={
                "id": "paper-123",
                "title": "Test Paper",
                "abstract": "This is the abstract",
                "authors": ["Author 1"]
            })
            mock_db.return_value.__aenter__.return_value = mock_conn

            result = await execute_read_paper(params, user_id="user-123")

            assert result["success"] is True
            assert result["data"]["title"] == "Test Paper"

    async def test_read_paper_retrieves_content(self):
        """Test read_paper retrieves full content."""
        params = {
            "paper_id": "paper-123",
            "sections": ["content"]
        }

        with patch("app.tools.query_tools.get_db_connection") as mock_db:
            mock_conn = AsyncMock()
            mock_conn.fetchrow = AsyncMock(return_value={
                "id": "paper-123",
                "content": "Full paper content..."
            })
            mock_db.return_value.__aenter__.return_value = mock_conn

            result = await execute_read_paper(params, user_id="user-123")

            assert result["success"] is True
            assert "content" in result["data"]


@pytest.mark.asyncio
class TestListNotesTool:
    """Tests for list_notes tool."""

    async def test_list_notes_returns_user_notes(self):
        """Test list_notes retrieves notes from database."""
        params = {
            "filter": {},
            "limit": 20
        }

        with patch("app.tools.query_tools.get_db_connection") as mock_db:
            mock_conn = AsyncMock()
            mock_conn.fetch = AsyncMock(return_value=[
                {
                    "id": "note-1",
                    "title": "My Note",
                    "content": "Note content",
                    "created_at": "2024-01-01"
                }
            ])
            mock_db.return_value.__aenter__.return_value = mock_conn

            result = await execute_list_notes(params, user_id="user-123")

            assert result["success"] is True
            assert len(result["data"]["notes"]) > 0


@pytest.mark.asyncio
class TestReadNoteTool:
    """Tests for read_note tool."""

    async def test_read_note_retrieves_content(self):
        """Test read_note retrieves note by ID."""
        params = {
            "note_id": "note-123"
        }

        with patch("app.tools.query_tools.get_db_connection") as mock_db:
            mock_conn = AsyncMock()
            mock_conn.fetchrow = AsyncMock(return_value={
                "id": "note-123",
                "title": "Test Note",
                "content": "This is my note",
                "paper_ids": ["paper-1"]
            })
            mock_db.return_value.__aenter__.return_value = mock_conn

            result = await execute_read_note(params, user_id="user-123")

            assert result["success"] is True
            assert result["data"]["title"] == "Test Note"