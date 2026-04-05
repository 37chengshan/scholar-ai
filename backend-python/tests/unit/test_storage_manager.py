"""Unit tests for StorageManager and Milvus batch insert.

Tests for:
- Milvus batch insert with retry logic
- StorageManager batch storage operations
- Paper metadata storage
- Vector storage
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.workers.storage_manager import StorageManager, get_storage_manager
from app.core.milvus_service import MilvusService
from app.workers.pipeline_context import PipelineContext


class TestMilvusBatchInsert:
    """Tests for Milvus batch insert with retry."""

    def test_batch_size_constant(self):
        """Test that batch size is 50 per D-27."""
        milvus = MilvusService()
        
        # Verify batch size is 50 per D-27
        assert milvus.MILVUS_BATCH_SIZE == 50

    def test_max_retries_constant(self):
        """Test that max retries is 3 per D-29."""
        milvus = MilvusService()
        
        # Verify retry settings per D-29
        assert milvus.MAX_RETRIES == 3

    def test_insert_contents_batched_exists(self):
        """Test that insert_contents_batched method exists."""
        milvus = MilvusService()
        
        assert hasattr(milvus, 'insert_contents_batched')
        assert callable(milvus.insert_contents_batched)


class TestStorageManager:
    """Tests for StorageManager class."""

    def test_storage_manager_init(self):
        """Test storage manager initialization."""
        mock_pool = MagicMock()
        manager = StorageManager(mock_pool)
        
        assert manager.db_pool is mock_pool
        assert manager.milvus is not None
        assert manager.neo4j is not None
        assert manager.notes_generator is not None
        assert manager.parser is not None

    def test_embedding_dimension(self):
        """Test embedding dimension is 2048 for Qwen3VL."""
        mock_pool = MagicMock()
        manager = StorageManager(mock_pool)
        
        assert manager.EMBEDDING_DIM == 2048

    def test_singleton_with_pool(self):
        """Test singleton pattern with pool."""
        mock_pool = MagicMock()
        manager = get_storage_manager(mock_pool)
        
        assert manager is not None
        assert isinstance(manager, StorageManager)

    @pytest.mark.asyncio
    async def test_store_paper_metadata(self):
        """Test paper metadata storage."""
        mock_pool = MagicMock()
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        manager = StorageManager(mock_pool)
        
        # Create context with metadata
        ctx = PipelineContext(
            task_id="test",
            paper_id="test-paper",
            user_id="test-user",
            storage_key="test-key"
        )
        ctx.metadata = {"title": "Test Paper", "authors": ["Author 1"]}
        ctx.imrad = {"introduction": {"content": "intro"}}
        ctx.parse_result = {"markdown": "# Test", "page_count": 10, "items": []}
        
        await manager._store_paper_metadata(mock_conn, ctx)
        
        # Verify execute was called
        mock_conn.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_store_notes_success(self):
        """Test reading notes generation and storage."""
        mock_pool = MagicMock()
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        manager = StorageManager(mock_pool)
        
        ctx = PipelineContext(
            task_id="test",
            paper_id="test-paper",
            user_id="test-user",
            storage_key="test-key"
        )
        ctx.metadata = {"title": "Test Paper", "authors": ["Author 1"]}
        ctx.imrad = {"introduction": {}}
        
        # Mock notes generator
        with patch.object(manager.notes_generator, 'generate_notes', new_callable=AsyncMock, return_value="Test notes"):
            await manager._store_notes(mock_conn, ctx)
            
            # Verify notes were stored
            assert ctx.notes == "Test notes"
            mock_conn.execute.assert_called()

    @pytest.mark.asyncio
    async def test_store_notes_failure_graceful(self):
        """Test that notes failure doesn't block pipeline."""
        mock_pool = MagicMock()
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        manager = StorageManager(mock_pool)
        
        ctx = PipelineContext(
            task_id="test",
            paper_id="test-paper",
            user_id="test-user",
            storage_key="test-key"
        )
        ctx.metadata = {"title": "Test Paper"}
        ctx.imrad = {}
        
        # Mock notes generator to fail
        with patch.object(manager.notes_generator, 'generate_notes', new_callable=AsyncMock, side_effect=Exception("Notes failed")):
            # Should not raise exception
            await manager._store_notes(mock_conn, ctx)
            
            # Notes should remain None
            assert ctx.notes is None

    @pytest.mark.asyncio
    async def test_store_vectors_with_images(self):
        """Test batch vector storage with images and tables."""
        mock_pool = MagicMock()
        manager = StorageManager(mock_pool)
        
        ctx = PipelineContext(
            task_id="test",
            paper_id="test-paper",
            user_id="test-user",
            storage_key="test-key"
        )
        ctx.parse_result = {"items": [], "markdown": "# Test"}
        ctx.imrad = None
        ctx.image_results = [
            {
                "paper_id": "test-paper",
                "user_id": "test-user",
                "embedding": [0.1] * 2048,
                "content_type": "image",
                "page_num": 1,
                "content_data": "Figure 1"
            }
        ]
        ctx.table_results = []
        
        # Mock parser and embedding service
        with patch.object(manager.parser, 'chunk_by_semantic', return_value=[]):
            with patch.object(manager.milvus, 'insert_contents_batched', return_value=[1]):
                ids = await manager._store_vectors(ctx)
                
                # Should include the image
                assert len(ids) == 1

    @pytest.mark.asyncio
    async def test_store_graph_nodes_success(self):
        """Test Neo4j graph node storage."""
        mock_pool = MagicMock()
        manager = StorageManager(mock_pool)
        
        ctx = PipelineContext(
            task_id="test",
            paper_id="test-paper",
            user_id="test-user",
            storage_key="test-key"
        )
        ctx.parse_result = {"items": [{"text": "chunk1"}]}
        ctx.metadata = {"title": "Test Paper", "authors": ["Author 1"]}
        ctx.imrad = {"introduction": {"page_start": 1, "page_end": 5}}
        
        chunk_ids = [1, 2, 3]
        
        # Mock Neo4j service
        with patch.object(manager.neo4j, 'create_chunk_nodes', new_callable=AsyncMock):
            with patch.object(manager.neo4j, 'create_section_nodes', new_callable=AsyncMock):
                with patch.object(manager.neo4j, 'create_paper_node', new_callable=AsyncMock):
                    await manager._store_graph_nodes(ctx, chunk_ids)

    @pytest.mark.asyncio
    async def test_store_graph_nodes_failure_graceful(self):
        """Test that Neo4j failure doesn't block pipeline."""
        mock_pool = MagicMock()
        manager = StorageManager(mock_pool)
        
        ctx = PipelineContext(
            task_id="test",
            paper_id="test-paper",
            user_id="test-user",
            storage_key="test-key"
        )
        ctx.parse_result = {"items": []}
        ctx.metadata = {}
        ctx.imrad = {}
        
        chunk_ids = [1]
        
        # Mock Neo4j to fail
        with patch.object(manager.neo4j, 'create_chunk_nodes', new_callable=AsyncMock, side_effect=Exception("Neo4j error")):
            # Should not raise exception
            await manager._store_graph_nodes(ctx, chunk_ids)

    @pytest.mark.asyncio
    async def test_full_store_workflow(self):
        """Test full store() workflow."""
        mock_pool = MagicMock()
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        manager = StorageManager(mock_pool)
        
        ctx = PipelineContext(
            task_id="test",
            paper_id="test-paper",
            user_id="test-user",
            storage_key="test-key"
        )
        ctx.parse_result = {"markdown": "# Test", "page_count": 10, "items": []}
        ctx.metadata = {"title": "Test Paper"}
        ctx.imrad = {}
        ctx.image_results = []
        ctx.table_results = []
        
        # Mock all storage operations
        with patch.object(manager.parser, 'chunk_by_semantic', return_value=[]):
            with patch.object(manager.milvus, 'insert_contents_batched', return_value=[]):
                with patch.object(manager.notes_generator, 'generate_notes', new_callable=AsyncMock, return_value=None):
                    with patch.object(manager.neo4j, 'create_chunk_nodes', new_callable=AsyncMock):
                        with patch.object(manager.neo4j, 'create_section_nodes', new_callable=AsyncMock):
                            with patch.object(manager.neo4j, 'create_paper_node', new_callable=AsyncMock):
                                result = await manager.store(ctx)
                                
                                # Verify context is returned
                                assert result is ctx