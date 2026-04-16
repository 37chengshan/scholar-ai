"""Unit tests for MemorySearch service.

Tests vector-based memory retrieval and storage:
- Search memories using vector similarity
- Store memories with embeddings
- Filter by memory types

Per D-11, D-12: Long-term memory with vector retrieval.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.core.memory_search import MemorySearch, Memory


class TestMemorySearchBasic:
    """Test basic MemorySearch functionality."""

    @pytest.mark.asyncio
    async def test_search_memories_returns_results(self):
        """Test 1: search_memories() returns top-k relevant memories"""
        mock_embedding = MagicMock()
        mock_embedding.encode = AsyncMock(return_value=[0.1] * 1024)

        mock_milvus = MagicMock()
        mock_milvus.search = AsyncMock(return_value=[{"id": "mem-1", "distance": 0.95}])
        mock_milvus.connect = AsyncMock()

        mock_row = {"id": "mem-1", "content": "Test", "memory_type": "preference", "metadata": None, "created_at": "2026-04-08"}
        mock_conn = MagicMock()
        mock_conn.fetch = AsyncMock(return_value=[mock_row])

        memory_search = MemorySearch(embedding_service=mock_embedding, milvus_service=mock_milvus)

        with patch("app.core.memory_search.get_db_connection") as mock_db:
            mock_db.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
            mock_db.return_value.__aexit__ = AsyncMock()
            results = await memory_search.search_memories(query="test", user_id="user-123", top_k=2)
            assert len(results) == 1

    @pytest.mark.asyncio
    async def test_search_memories_filters_by_type(self):
        """Test 2: search_memories() filters by memory_types"""
        mock_embedding = MagicMock()
        mock_embedding.encode = AsyncMock(return_value=[0.1] * 1024)

        mock_milvus = MagicMock()
        mock_milvus.search = AsyncMock(return_value=[])
        mock_milvus.connect = AsyncMock()

        memory_search = MemorySearch(embedding_service=mock_embedding, milvus_service=mock_milvus)

        with patch("app.core.memory_search.get_db_connection") as mock_db:
            mock_conn = MagicMock()
            mock_conn.fetch = AsyncMock(return_value=[])
            mock_db.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
            mock_db.return_value.__aexit__ = AsyncMock()
            await memory_search.search_memories(query="test", user_id="user-123", top_k=5, memory_types=["preference"])
            call_args = mock_milvus.search.call_args
            filter_expr = call_args[1]["filter_expr"]
            assert "memory_type in" in filter_expr


class TestMemorySearchStorage:
    """Test memory storage functionality."""

    @pytest.mark.asyncio
    async def test_store_memory_returns_id(self):
        """Test 4: store_memory() returns memory ID"""
        mock_embedding = MagicMock()
        mock_embedding.encode = AsyncMock(return_value=[0.1] * 1024)

        mock_milvus = MagicMock()
        mock_milvus.insert = AsyncMock()
        mock_milvus.connect = AsyncMock()

        mock_conn = MagicMock()
        mock_conn.fetchrow = AsyncMock(return_value={"id": "new-mem-id"})

        memory_search = MemorySearch(embedding_service=mock_embedding, milvus_service=mock_milvus)

        with patch("app.core.memory_search.get_db_connection") as mock_db:
            mock_db.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
            mock_db.return_value.__aexit__ = AsyncMock()
            memory_id = await memory_search.store_memory(user_id="user-123", content="Test", memory_type="preference")
            assert memory_id == "new-mem-id"


class TestMemoryDataclass:
    """Test Memory dataclass."""

    def test_memory_creation(self):
        """Test Memory dataclass instantiation"""
        memory = Memory(id="mem-123", content="Test content", memory_type="preference")
        assert memory.id == "mem-123"
        assert memory.similarity == 0.0
