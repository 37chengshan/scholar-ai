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

        assert hasattr(milvus, "insert_contents_batched")
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
            storage_key="test-key",
        )
        ctx.metadata = {"title": "Test Paper", "authors": ["Author 1"]}
        ctx.imrad = {"introduction": {"content": "intro"}}
        ctx.parse_result = {"markdown": "# Test", "page_count": 10, "items": []}

        await manager._store_paper_metadata(mock_conn, ctx)

        # Verify execute was called
        mock_conn.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_store_paper_metadata_title_update(self):
        """Test that title is ALWAYS updated when metadata has valid title (per D-04)."""
        mock_pool = MagicMock()
        mock_conn = AsyncMock()

        manager = StorageManager(mock_pool)

        # Case 1: Metadata has title - should update (overwrite filename-based title)
        ctx = PipelineContext(
            task_id="test",
            paper_id="test-paper",
            user_id="test-user",
            storage_key="test-key",
        )
        ctx.metadata = {"title": "Extracted Title from PDF"}
        ctx.imrad = {}
        ctx.parse_result = {"markdown": "# Test", "page_count": 10, "items": []}

        await manager._store_paper_metadata(mock_conn, ctx)

        # Verify the SQL contains "title = $4" (not "title = title")
        call_args = mock_conn.execute.call_args
        sql = call_args[0][0]
        assert "title = $4" in sql, (
            "Title should be updated when metadata has valid title"
        )

        # Verify title parameter is the extracted title
        title_param = call_args[0][4]  # $4 is the title parameter
        assert title_param == "Extracted Title from PDF"

    @pytest.mark.asyncio
    async def test_store_paper_metadata_title_preserved_when_empty(self):
        """Test that title is preserved when metadata extraction fails (empty title)."""
        mock_pool = MagicMock()
        mock_conn = AsyncMock()

        manager = StorageManager(mock_pool)

        # Case 2: Metadata has empty/None title - should preserve existing
        ctx = PipelineContext(
            task_id="test",
            paper_id="test-paper",
            user_id="test-user",
            storage_key="test-key",
        )
        ctx.metadata = {"title": None}  # Extraction failed
        ctx.imrad = {}
        ctx.parse_result = {"markdown": "# Test", "page_count": 10, "items": []}

        await manager._store_paper_metadata(mock_conn, ctx)

        # Verify the SQL contains "title = title" (preserve existing)
        call_args = mock_conn.execute.call_args
        sql = call_args[0][0]
        assert "title = title" in sql, "Title should be preserved when extraction fails"

    @pytest.mark.asyncio
    async def test_store_paper_metadata_title_whitespace_handling(self):
        """Test that whitespace-only titles are treated as empty."""
        mock_pool = MagicMock()
        mock_conn = AsyncMock()

        manager = StorageManager(mock_pool)

        # Whitespace-only title should be treated as empty
        ctx = PipelineContext(
            task_id="test",
            paper_id="test-paper",
            user_id="test-user",
            storage_key="test-key",
        )
        ctx.metadata = {"title": "   "}  # Whitespace only
        ctx.imrad = {}
        ctx.parse_result = {"markdown": "# Test", "page_count": 10, "items": []}

        await manager._store_paper_metadata(mock_conn, ctx)

        # Verify the SQL preserves existing title
        call_args = mock_conn.execute.call_args
        sql = call_args[0][0]
        assert "title = title" in sql, "Whitespace-only title should preserve existing"

    @pytest.mark.asyncio
    async def test_store_paper_metadata_normalizes_oversized_title(self):
        """Multiline oversized title should be normalized to first line and capped."""
        mock_pool = MagicMock()
        mock_conn = AsyncMock()

        manager = StorageManager(mock_pool)

        ctx = PipelineContext(
            task_id="test",
            paper_id="test-paper",
            user_id="test-user",
            storage_key="test-key",
        )
        very_long = "A" * 500
        ctx.metadata = {"title": f"  Candidate title line  \n{very_long}"}
        ctx.imrad = {}
        ctx.parse_result = {"markdown": "# Test", "page_count": 10, "items": []}

        await manager._store_paper_metadata(mock_conn, ctx)

        call_args = mock_conn.execute.call_args[0]
        normalized_title = call_args[4]  # $4 title param
        assert normalized_title == "Candidate title line"
        assert len(normalized_title) <= manager.MAX_INDEXED_TITLE_LEN

    @pytest.mark.asyncio
    async def test_store_paper_metadata_resolves_duplicate_title(self):
        """Duplicate extracted titles should be suffixed to satisfy unique_user_title."""
        mock_pool = MagicMock()
        mock_conn = AsyncMock()
        mock_conn.fetchval = AsyncMock(side_effect=["existing-paper-id", None])

        manager = StorageManager(mock_pool)

        ctx = PipelineContext(
            task_id="test",
            paper_id="test-paper",
            user_id="test-user",
            storage_key="test-key",
        )
        ctx.metadata = {"title": "Duplicate Title"}
        ctx.imrad = {}
        ctx.parse_result = {"markdown": "# Test", "page_count": 10, "items": []}

        await manager._store_paper_metadata(mock_conn, ctx)

        call_args = mock_conn.execute.call_args[0]
        stored_title = call_args[4]
        assert stored_title == "Duplicate Title (v2)"

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
            storage_key="test-key",
        )
        ctx.metadata = {"title": "Test Paper", "authors": ["Author 1"]}
        ctx.imrad = {"introduction": {}}

        # Mock notes generator
        with patch.object(
            manager.notes_generator,
            "generate_notes",
            new_callable=AsyncMock,
            return_value="Test notes",
        ):
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
            storage_key="test-key",
        )
        ctx.metadata = {"title": "Test Paper"}
        ctx.imrad = {}

        # Mock notes generator to fail
        with patch.object(
            manager.notes_generator,
            "generate_notes",
            new_callable=AsyncMock,
            side_effect=Exception("Notes failed"),
        ):
            # Should not raise exception
            await manager._store_notes(mock_conn, ctx)

            # Notes should remain None
            assert ctx.notes is None

    @pytest.mark.asyncio
    async def test_store_notes_generates_for_fallback_parse(self):
        """Fallback parse mode should still attempt notes generation."""
        mock_pool = MagicMock()
        mock_conn = AsyncMock()

        manager = StorageManager(mock_pool)

        ctx = PipelineContext(
            task_id="test",
            paper_id="test-paper",
            user_id="test-user",
            storage_key="test-key",
        )
        ctx.metadata = {"title": "Fallback Paper"}
        ctx.imrad = {"introduction": {"content": "intro"}}
        ctx.parse_result = {"metadata": {"parse_mode": "pypdf_fallback"}}

        with patch.object(
            manager,
            "_generate_notes_with_retry",
            new_callable=AsyncMock,
            return_value="Fallback notes",
        ) as mock_generate:
            await manager._store_notes(mock_conn, ctx)
            mock_generate.assert_called_once()
            assert ctx.notes == "Fallback notes"

    @pytest.mark.asyncio
    async def test_store_paper_metadata_strips_null_bytes(self):
        """Metadata/content strings containing NUL should be sanitized before DB write."""
        mock_pool = MagicMock()
        mock_conn = AsyncMock()

        manager = StorageManager(mock_pool)

        ctx = PipelineContext(
            task_id="test",
            paper_id="test-paper",
            user_id="test-user",
            storage_key="test-key",
        )
        ctx.metadata = {
            "title": "Hello\x00World",
            "authors": ["A\x00B"],
            "abstract": "Abs\x00tract",
            "doi": "10.1\x00/xyz",
            "keywords": ["k\x001"],
        }
        ctx.imrad = {"introduction": {"content": "Intro\x00Text"}}
        ctx.parse_result = {"markdown": "Body\x00Text", "page_count": 1, "items": []}

        await manager._store_paper_metadata(mock_conn, ctx)

        call_args = mock_conn.execute.call_args[0]
        assert "\x00" not in call_args[1]  # content
        assert "\x00" not in call_args[3]  # extracted title
        assert "\x00" not in call_args[5]  # abstract
        assert "\x00" not in call_args[6]  # doi

    @pytest.mark.asyncio
    async def test_store_notes_strips_null_bytes(self):
        """Generated reading notes with NUL should be sanitized before persistence."""
        mock_pool = MagicMock()
        mock_conn = AsyncMock()

        manager = StorageManager(mock_pool)

        ctx = PipelineContext(
            task_id="test",
            paper_id="test-paper",
            user_id="test-user",
            storage_key="test-key",
        )
        ctx.metadata = {"title": "Test"}
        ctx.imrad = {"introduction": {"content": "x"}}

        with patch.object(
            manager,
            "_generate_notes_with_retry",
            new_callable=AsyncMock,
            return_value="Line1\x00Line2",
        ):
            await manager._store_notes(mock_conn, ctx)

        call_args = mock_conn.execute.call_args[0]
        assert "\x00" not in call_args[1]

    @pytest.mark.asyncio
    async def test_store_vectors_with_images(self):
        """Test batch vector storage with images and tables."""
        mock_pool = MagicMock()
        manager = StorageManager(mock_pool)

        ctx = PipelineContext(
            task_id="test",
            paper_id="test-paper",
            user_id="test-user",
            storage_key="test-key",
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
                "content_data": "Figure 1",
            }
        ]
        ctx.table_results = []

        # Mock parser and embedding service
        with patch.object(manager.parser, "chunk_by_semantic", return_value=[]):
            with patch.object(
                manager.milvus, "insert_contents_batched", return_value=[1]
            ):
                ids = await manager._store_vectors(ctx)

                # Should include the image
                assert len(ids) == 1

    @pytest.mark.asyncio
    async def test_store_vectors_raises_when_embedding_fails(self):
        """Embedding failures should fail hard instead of silently using zero vectors."""
        mock_pool = MagicMock()
        manager = StorageManager(mock_pool)

        ctx = PipelineContext(
            task_id="test",
            paper_id="test-paper",
            user_id="test-user",
            storage_key="test-key",
        )
        ctx.parse_result = {
            "items": [{"text": "chunk text", "page_start": 1}],
            "metadata": {},
        }
        ctx.imrad = {}
        ctx.image_results = []
        ctx.table_results = []

        with patch.object(
            manager.parser,
            "chunk_by_semantic",
            return_value=[{"text": "chunk text", "page_start": 1, "section": ""}],
        ):
            with patch.object(manager.qwen3vl_service, "is_loaded", return_value=True):
                with patch.object(
                    manager.qwen3vl_service,
                    "encode_text",
                    side_effect=RuntimeError("qwen failed"),
                ):
                    with pytest.raises(RuntimeError):
                        await manager._store_vectors(ctx)

    @pytest.mark.asyncio
    async def test_store_graph_nodes_success(self):
        """Test Neo4j graph node storage."""
        mock_pool = MagicMock()
        manager = StorageManager(mock_pool)

        ctx = PipelineContext(
            task_id="test",
            paper_id="test-paper",
            user_id="test-user",
            storage_key="test-key",
        )
        ctx.parse_result = {"items": [{"text": "chunk1"}]}
        ctx.metadata = {"title": "Test Paper", "authors": ["Author 1"]}
        ctx.imrad = {"introduction": {"page_start": 1, "page_end": 5}}

        chunk_ids = [1, 2, 3]

        # Mock Neo4j service
        with patch.object(manager.neo4j, "create_chunk_nodes", new_callable=AsyncMock):
            with patch.object(
                manager.neo4j, "create_section_nodes", new_callable=AsyncMock
            ):
                with patch.object(
                    manager.neo4j, "create_paper_node", new_callable=AsyncMock
                ):
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
            storage_key="test-key",
        )
        ctx.parse_result = {"items": []}
        ctx.metadata = {}
        ctx.imrad = {}

        chunk_ids = [1]

        # Mock Neo4j to fail
        with patch.object(
            manager.neo4j,
            "create_chunk_nodes",
            new_callable=AsyncMock,
            side_effect=Exception("Neo4j error"),
        ):
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
            storage_key="test-key",
        )
        ctx.parse_result = {"markdown": "# Test", "page_count": 10, "items": []}
        ctx.metadata = {"title": "Test Paper"}
        ctx.imrad = {}
        ctx.image_results = []
        ctx.table_results = []

        # Mock all storage operations
        with patch.object(manager.parser, "chunk_by_semantic", return_value=[]):
            with patch.object(
                manager.milvus, "insert_contents_batched", return_value=[]
            ):
                with patch.object(
                    manager.notes_generator,
                    "generate_notes",
                    new_callable=AsyncMock,
                    return_value=None,
                ):
                    with patch.object(
                        manager.neo4j, "create_chunk_nodes", new_callable=AsyncMock
                    ):
                        with patch.object(
                            manager.neo4j,
                            "create_section_nodes",
                            new_callable=AsyncMock,
                        ):
                            with patch.object(
                                manager.neo4j,
                                "create_paper_node",
                                new_callable=AsyncMock,
                            ):
                                result = await manager.store(ctx)

                                # Verify context is returned
                                assert result is ctx
