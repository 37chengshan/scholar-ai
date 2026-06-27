"""Unit tests for MemorySearch against the current SQLAlchemy + Milvus contract."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.memory_search import Memory, MemorySearch


class _SessionContext:
    def __init__(self, session):
        self._session = session

    async def __aenter__(self):
        return self._session

    async def __aexit__(self, exc_type, exc, tb):
        return False


class TestMemorySearchBasic:
    @pytest.mark.asyncio
    async def test_search_memories_returns_results(self):
        embedding_service = MagicMock()
        embedding_service.encode_text.return_value = [0.1] * 1024

        milvus_service = MagicMock()
        milvus_service.search = AsyncMock(
            return_value=[{"id": "mem-1", "distance": 0.95}]
        )

        memory_row = SimpleNamespace(
            id="mem-1",
            content="Test memory",
            memory_type="preference",
            extra_data={"topic": "rag"},
            created_at="2026-04-08T00:00:00Z",
        )
        result_proxy = MagicMock()
        result_proxy.scalars.return_value.all.return_value = [memory_row]

        session = MagicMock()
        session.execute = AsyncMock(return_value=result_proxy)
        session.commit = AsyncMock()
        session.refresh = AsyncMock()

        with patch(
            "app.core.memory_search.AsyncSessionLocal",
            return_value=_SessionContext(session),
        ):
            memory_search = MemorySearch(
                embedding_service=embedding_service,
                milvus_service=milvus_service,
            )
            results = await memory_search.search_memories(
                query="test",
                user_id="user-123",
                top_k=2,
            )

        assert len(results) == 1
        assert results[0].id == "mem-1"
        assert results[0].content == "Test memory"
        assert results[0].similarity == 0.95
        milvus_service.search.assert_awaited_once()
        embedding_service.encode_text.assert_called_once_with("test")

    @pytest.mark.asyncio
    async def test_search_memories_filters_by_type(self):
        embedding_service = MagicMock()
        embedding_service.encode_text.return_value = [0.1] * 1024

        milvus_service = MagicMock()
        milvus_service.search = AsyncMock(return_value=[])

        memory_search = MemorySearch(
            embedding_service=embedding_service,
            milvus_service=milvus_service,
        )

        results = await memory_search.search_memories(
            query="test",
            user_id="user-123",
            top_k=5,
            memory_types=["preference"],
        )

        assert results == []
        filter_expr = milvus_service.search.await_args.kwargs["filter_expr"]
        assert 'user_id == "user-123"' in filter_expr
        assert 'memory_type in ["preference"]' in filter_expr


class TestMemorySearchStorage:
    @pytest.mark.asyncio
    async def test_store_memory_returns_id(self):
        embedding_service = MagicMock()
        embedding_service.encode_text.return_value = [0.1] * 1024

        milvus_service = MagicMock()
        milvus_service.insert = AsyncMock()

        session = MagicMock()
        session.add = MagicMock()
        session.commit = AsyncMock()
        session.refresh = AsyncMock()

        async def _refresh(instance):
            instance.id = "new-mem-id"

        session.refresh.side_effect = _refresh

        with patch(
            "app.core.memory_search.AsyncSessionLocal",
            return_value=_SessionContext(session),
        ):
            memory_search = MemorySearch(
                embedding_service=embedding_service,
                milvus_service=milvus_service,
            )
            memory_id = await memory_search.store_memory(
                user_id="user-123",
                content="Test",
                memory_type="preference",
            )

        assert memory_id == "new-mem-id"
        session.add.assert_called_once()
        session.commit.assert_awaited_once()
        milvus_service.insert.assert_awaited_once()
        assert milvus_service.insert.await_args.kwargs["data"][0]["id"] == "new-mem-id"


class TestMemoryDataclass:
    def test_memory_creation(self):
        memory = Memory(id="mem-123", content="Test content", memory_type="preference")
        assert memory.id == "mem-123"
        assert memory.similarity == 0.0
