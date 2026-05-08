"""Unit tests for query tool implementations."""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.tools.query_tools import (
    execute_external_search,
    execute_list_notes,
    execute_list_papers,
    execute_rag_search,
    execute_read_note,
    execute_read_paper,
)


def _mock_scalar_result(items):
    result = MagicMock()
    result.scalars.return_value.all.return_value = items
    return result


def _mock_single_result(item):
    result = MagicMock()
    result.scalar_one_or_none.return_value = item
    return result


@asynccontextmanager
async def _session_ctx(session):
    yield session


@pytest.mark.asyncio
class TestExternalSearchTool:
    async def test_external_search_arxiv_source(self):
        params = {
            "query": "transformer architecture",
            "sources": ["arxiv"],
            "limit": 5,
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
                    }
                ]
            }

            result = await execute_external_search(params)

        assert result["success"] is True
        assert result["data"]["results"][0]["source"] == "arxiv"

    async def test_external_search_semantic_scholar_source(self):
        params = {
            "query": "BERT pretraining",
            "sources": ["semantic_scholar"],
            "limit": 10,
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
                        "citationCount": 50000,
                    }
                ]
            }

            result = await execute_external_search(params)

        assert result["success"] is True
        assert result["data"]["results"][0]["source"] == "semantic-scholar"

    async def test_external_search_multiple_sources(self):
        params = {
            "query": "attention mechanism",
            "sources": ["arxiv", "semantic_scholar"],
            "limit": 5,
        }

        with patch("app.tools.query_tools.search_arxiv") as mock_arxiv, patch(
            "app.tools.query_tools.search_semantic_scholar"
        ) as mock_s2:
            mock_arxiv.return_value = {
                "results": [{"id": "arxiv-1", "title": "Paper 1", "source": "arxiv"}]
            }
            mock_s2.return_value = {
                "results": [{"id": "s2-1", "title": "Paper 2", "source": "semantic-scholar"}]
            }

            result = await execute_external_search(params)

        assert result["success"] is True
        assert len(result["data"]["results"]) == 2


@pytest.mark.asyncio
class TestRAGSearchTool:
    async def test_rag_search_basic_query(self):
        params = {
            "question": "What is the attention mechanism?",
            "paper_ids": ["paper-1", "paper-2"],
            "top_k": 5,
        }

        with patch("app.tools.query_tools.get_multimodal_search_service") as mock_service:
            mock_instance = MagicMock()
            mock_instance.search = AsyncMock(
                return_value={
                    "results": [
                        {
                            "id": "chunk-1",
                            "paper_id": "paper-1",
                            "content_data": "The attention mechanism allows...",
                            "score": 0.95,
                        }
                    ],
                    "total_count": 1,
                }
            )
            mock_service.return_value = mock_instance

            result = await execute_rag_search(params, user_id="user-123")

        assert result["success"] is True
        mock_instance.search.assert_awaited_once()
        assert mock_instance.search.await_args.kwargs["paper_ids"] == ["paper-1", "paper-2"]

    async def test_rag_search_knowledge_base_scope_resolves_paper_ids(self):
        params = {
            "question": "methodology for training",
            "paper_ids": ["paper-1", "paper-3"],
            "top_k": 10,
        }
        session = AsyncMock()
        session.execute = AsyncMock(
            return_value=SimpleNamespace(fetchall=lambda: [("paper-1",), ("paper-2",)])
        )

        with patch("app.tools.query_tools.AsyncSessionLocal", return_value=_session_ctx(session)):
            with patch("app.tools.query_tools.get_multimodal_search_service") as mock_service:
                mock_instance = MagicMock()
                mock_instance.search = AsyncMock(return_value={"results": [], "total_count": 0})
                mock_service.return_value = mock_instance

                result = await execute_rag_search(
                    params,
                    user_id="user-123",
                    scope={"type": "knowledge_base", "knowledge_base_id": "kb-1"},
                )

        assert result["success"] is True
        assert mock_instance.search.await_args.kwargs["paper_ids"] == ["paper-1"]

    async def test_rag_search_compare_scope_prefers_scope_paper_ids(self):
        params = {
            "question": "compare training strategies",
            "paper_ids": ["paper-old"],
            "top_k": 10,
        }

        with patch("app.tools.query_tools.get_multimodal_search_service") as mock_service:
            mock_instance = MagicMock()
            mock_instance.search = AsyncMock(return_value={"results": [], "total_count": 0})
            mock_service.return_value = mock_instance

            result = await execute_rag_search(
                params,
                user_id="user-123",
                scope={"type": "compare", "paper_ids": ["paper-1", "paper-2"]},
            )

        assert result["success"] is True
        assert mock_instance.search.await_args.kwargs["paper_ids"] == ["paper-1", "paper-2"]


@pytest.mark.asyncio
class TestListPapersTool:
    async def test_list_papers_returns_user_papers(self):
        params = {
            "filter": {"status": "completed"},
            "sort": "created_at",
            "limit": 20,
        }
        paper = SimpleNamespace(
            id="paper-1",
            title="Paper 1",
            authors=["Author A"],
            year=2024,
            status="completed",
            created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        )
        session = AsyncMock()
        session.execute = AsyncMock(return_value=_mock_scalar_result([paper]))

        with patch("app.tools.query_tools.AsyncSessionLocal", return_value=_session_ctx(session)):
            result = await execute_list_papers(params, user_id="user-123")

        assert result["success"] is True
        assert result["data"]["papers"][0]["id"] == "paper-1"

    async def test_list_papers_with_knowledge_base_scope_filters_results(self):
        params = {
            "filter": {},
            "limit": 10,
        }
        paper = SimpleNamespace(
            id="paper-1",
            title="Scoped Paper",
            authors=["Author A"],
            year=2024,
            status="completed",
            created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        )
        session = AsyncMock()
        session.execute = AsyncMock(return_value=_mock_scalar_result([paper]))

        with patch("app.tools.query_tools.AsyncSessionLocal", return_value=_session_ctx(session)):
            result = await execute_list_papers(
                params,
                user_id="user-123",
                scope={"type": "knowledge_base", "knowledge_base_id": "kb-1"},
            )

        assert result["success"] is True
        assert result["data"]["papers"][0]["title"] == "Scoped Paper"

    async def test_list_papers_with_compare_scope_filters_results(self):
        params = {
            "filter": {},
            "limit": 10,
        }
        paper = SimpleNamespace(
            id="paper-compare-1",
            title="Compare Scoped Paper",
            authors=["Author A"],
            year=2024,
            status="completed",
            created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        )
        session = AsyncMock()
        session.execute = AsyncMock(return_value=_mock_scalar_result([paper]))

        with patch("app.tools.query_tools.AsyncSessionLocal", return_value=_session_ctx(session)):
            result = await execute_list_papers(
                params,
                user_id="user-123",
                scope={"type": "compare", "paper_ids": ["paper-compare-1", "paper-compare-2"]},
            )

        assert result["success"] is True
        assert result["data"]["papers"][0]["id"] == "paper-compare-1"


@pytest.mark.asyncio
class TestReadPaperTool:
    async def test_read_paper_retrieves_metadata(self):
        params = {
            "paper_id": "paper-123",
            "sections": ["metadata", "abstract"],
        }
        paper = SimpleNamespace(
            id="paper-123",
            title="Test Paper",
            abstract="This is the abstract",
            authors=["Author 1"],
            year=2024,
            doi=None,
            keywords=["test"],
            content=None,
            reading_notes=None,
        )
        session = AsyncMock()
        session.execute = AsyncMock(return_value=_mock_single_result(paper))

        with patch("app.tools.query_tools.AsyncSessionLocal", return_value=_session_ctx(session)):
            result = await execute_read_paper(params, user_id="user-123")

        assert result["success"] is True
        assert result["data"]["title"] == "Test Paper"

    async def test_read_paper_retrieves_content(self):
        params = {
            "paper_id": "paper-123",
            "sections": ["content"],
        }
        paper = SimpleNamespace(
            id="paper-123",
            title="Test Paper",
            abstract=None,
            authors=[],
            year=None,
            doi=None,
            keywords=[],
            content="Full paper content...",
            reading_notes=None,
        )
        session = AsyncMock()
        session.execute = AsyncMock(return_value=_mock_single_result(paper))

        with patch("app.tools.query_tools.AsyncSessionLocal", return_value=_session_ctx(session)):
            result = await execute_read_paper(params, user_id="user-123")

        assert result["success"] is True
        assert result["data"]["content"] == "Full paper content..."


@pytest.mark.asyncio
class TestListNotesTool:
    async def test_list_notes_returns_user_notes(self):
        params = {
            "filter": {},
            "limit": 20,
        }
        note = SimpleNamespace(
            id="note-1",
            title="My Note",
            content="Note content",
            tags=["tag"],
            paper_ids=["paper-1"],
            created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
            updated_at=datetime(2024, 1, 2, tzinfo=timezone.utc),
        )
        session = AsyncMock()
        session.execute = AsyncMock(return_value=_mock_scalar_result([note]))

        with patch("app.tools.query_tools.AsyncSessionLocal", return_value=_session_ctx(session)):
            result = await execute_list_notes(params, user_id="user-123")

        assert result["success"] is True
        assert result["data"]["notes"][0]["title"] == "My Note"


@pytest.mark.asyncio
class TestReadNoteTool:
    async def test_read_note_retrieves_content(self):
        params = {"note_id": "note-123"}
        note = SimpleNamespace(
            id="note-123",
            title="Test Note",
            content="This is my note",
            tags=["tag"],
            paper_ids=["paper-1"],
            created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
            updated_at=datetime(2024, 1, 2, tzinfo=timezone.utc),
        )
        session = AsyncMock()
        session.execute = AsyncMock(return_value=_mock_single_result(note))

        with patch("app.tools.query_tools.AsyncSessionLocal", return_value=_session_ctx(session)):
            result = await execute_read_note(params, user_id="user-123")

        assert result["success"] is True
        assert result["data"]["title"] == "Test Note"
