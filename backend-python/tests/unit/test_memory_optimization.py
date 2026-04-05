"""Tests for memory optimization strategies.

Tests StreamingParser and EmbeddingObjectPool to verify:
- MAX_PAGES_PER_BATCH = 10 per D-08
- Memory released after each batch per D-09
- Peak memory under 3GB per D-10
- Object pool manages models per D-11
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from pathlib import Path

from app.workers.streaming_parser import StreamingParser
from app.utils.object_pool import ObjectPool, EmbeddingObjectPool


class TestStreamingParser:
    """Tests for StreamingParser."""
    
    def test_max_pages_per_batch(self):
        """Test batch size is 10 per D-08."""
        parser = StreamingParser()
        assert parser.MAX_PAGES_PER_BATCH == 10
    
    def test_memory_estimation(self):
        """Test memory estimation calculation."""
        parser = StreamingParser()
        
        # 50-page paper
        estimate = parser.estimate_memory_usage(50)
        
        assert estimate["total_pages"] == 50
        assert estimate["batch_size"] == 10
        assert estimate["num_batches"] == 5
        assert estimate["within_target"] == True  # Per D-10
    
    def test_memory_estimation_large_paper(self):
        """Test memory estimation for large papers."""
        parser = StreamingParser()
        
        # 100-page paper - should still be within target due to batching
        estimate = parser.estimate_memory_usage(100)
        
        assert estimate["total_pages"] == 100
        assert estimate["batch_size"] == 10
        assert estimate["num_batches"] == 10
        # Peak memory = batch_size * MB_PER_PAGE = 10 * 30 = 300MB
        assert estimate["estimated_peak_memory_mb"] == 300
        assert estimate["within_target"] == True
    
    def test_parser_initialization(self):
        """Test parser initialization."""
        parser = StreamingParser()
        assert parser.parser is not None
    
    def test_parser_with_custom_docling(self):
        """Test parser with custom DoclingParser instance."""
        mock_parser = Mock()
        parser = StreamingParser(parser=mock_parser)
        assert parser.parser == mock_parser
    
    @pytest.mark.asyncio
    async def test_batch_yields_progress(self):
        """Test that batches yield with progress."""
        # Create mock parser to avoid file I/O
        mock_docling = Mock()
        mock_docling.parse_pdf = AsyncMock(return_value={
            "items": [{"page": i} for i in range(1, 21)],
        })
        
        parser = StreamingParser(parser=mock_docling)
        
        # Mock Path.exists() to return True
        with patch.object(Path, 'exists', return_value=True):
            batches = []
            async for batch in parser.parse_large_pdf("test.pdf", 20):
                batches.append(batch)
        
        # 20 pages with batch size 10 = 2 batches
        assert len(batches) == 2
        assert batches[0]["progress"] == 0.5
        assert batches[1]["progress"] == 1.0
    
    @pytest.mark.asyncio
    async def test_batch_page_ranges(self):
        """Test that batches have correct page ranges."""
        mock_docling = Mock()
        mock_docling.parse_pdf = AsyncMock(return_value={
            "items": [{"page": i} for i in range(1, 31)],
        })
        
        parser = StreamingParser(parser=mock_docling)
        
        # Mock Path.exists() to return True
        with patch.object(Path, 'exists', return_value=True):
            batches = []
            async for batch in parser.parse_large_pdf("test.pdf", 30):
                batches.append(batch)
        
        # 3 batches: 1-10, 11-20, 21-30
        assert len(batches) == 3
        assert batches[0]["pages"] == "1-10"
        assert batches[1]["pages"] == "11-20"
        assert batches[2]["pages"] == "21-30"
    
    @pytest.mark.asyncio
    async def test_parse_pdf_range(self):
        """Test parse_pdf_range method."""
        mock_docling = Mock()
        mock_docling.parse_pdf = AsyncMock(return_value={
            "items": [{"page": i} for i in range(1, 51)],
        })
        
        parser = StreamingParser(parser=mock_docling)
        
        result = await parser.parse_pdf_range("test.pdf", 5, 15)
        
        assert result["pages"] == "5-15"
        # Should filter to pages 5-15
        filtered_pages = [item["page"] for item in result["items"]]
        assert all(5 <= p <= 15 for p in filtered_pages)


class TestObjectPool:
    """Tests for ObjectPool."""
    
    def test_pool_init(self):
        """Test pool initialization."""
        pool = ObjectPool(pool_size=3)
        assert pool._pool_size == 3
        assert pool._initialized == False
    
    def test_pool_set_factory(self):
        """Test factory setting."""
        pool = ObjectPool(pool_size=2)
        
        async def factory():
            return Mock()
        
        pool.set_factory(factory)
        assert pool._factory == factory
    
    @pytest.mark.asyncio
    async def test_pool_acquire_release(self):
        """Test object acquire and release."""
        pool = ObjectPool(pool_size=2)
        
        # Set factory
        async def factory():
            return Mock()
        
        pool.set_factory(factory)
        
        # Initialize first to check initial state
        await pool.initialize()
        assert pool.available == 2
        
        # Acquire - should reduce available count
        obj1 = await pool.acquire()
        assert pool.available == 1
        
        # Release - should restore available count
        await pool.release(obj1)
        assert pool.available == 2
        
        # Acquire again - verify pool still has objects
        obj2 = await pool.acquire()
        assert obj2 is not None
        assert pool.available == 1
    
    @pytest.mark.asyncio
    async def test_pool_creates_objects_on_initialize(self):
        """Test that pool creates objects on initialize."""
        pool = ObjectPool(pool_size=3)
        
        created_objects = []
        async def factory():
            obj = Mock()
            created_objects.append(obj)
            return obj
        
        pool.set_factory(factory)
        await pool.initialize()
        
        assert len(created_objects) == 3
        assert pool._initialized == True
        assert pool.available == 3
    
    @pytest.mark.asyncio
    async def test_pool_lazy_initialization(self):
        """Test that pool initializes on first acquire."""
        pool = ObjectPool(pool_size=2)
        
        async def factory():
            return Mock()
        
        pool.set_factory(factory)
        
        # Pool not initialized yet
        assert pool._initialized == False
        
        # First acquire should trigger initialization
        obj = await pool.acquire()
        assert pool._initialized == True
    
    @pytest.mark.asyncio
    async def test_pool_available_count(self):
        """Test available count after operations."""
        pool = ObjectPool(pool_size=2)
        
        async def factory():
            return Mock()
        
        pool.set_factory(factory)
        await pool.initialize()
        
        assert pool.available == 2
        
        obj1 = await pool.acquire()
        assert pool.available == 1
        
        obj2 = await pool.acquire()
        assert pool.available == 0
        
        await pool.release(obj1)
        assert pool.available == 1
        
        await pool.release(obj2)
        assert pool.available == 2


class TestEmbeddingObjectPool:
    """Tests for EmbeddingObjectPool."""
    
    def test_embedding_pool_init(self):
        """Test embedding pool initialization."""
        pool = EmbeddingObjectPool(pool_size=2)
        assert pool._initialized == False
    
    @pytest.mark.asyncio
    async def test_embedding_pool_creates_service(self):
        """Test that embedding pool creates service instances."""
        pool = EmbeddingObjectPool(pool_size=1)
        
        # Mock the Qwen3VLMultimodalEmbedding and settings at the correct import location
        with patch('app.core.qwen3vl_service.Qwen3VLMultimodalEmbedding') as MockService:
            mock_service = Mock()
            mock_service.load_model = Mock()
            MockService.return_value = mock_service
            
            with patch('app.core.config.settings') as mock_settings:
                mock_settings.EMBEDDING_QUANTIZATION = "int4"
                mock_settings.EMBEDDING_DEVICE = "auto"
                
                await pool.initialize()
                
                # Should have created service with correct config
                MockService.assert_called_once_with(
                    quantization="int4",
                    device="auto"
                )
                mock_service.load_model.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test context manager usage."""
        pool = EmbeddingObjectPool(pool_size=1)
        
        with patch('app.core.qwen3vl_service.Qwen3VLMultimodalEmbedding') as MockService:
            mock_service = Mock()
            mock_service.load_model = Mock()
            MockService.return_value = mock_service
            
            with patch('app.core.config.settings'):
                async with pool as service:
                    assert service is not None
                    assert service == mock_service
    
    @pytest.mark.asyncio
    async def test_context_manager_releases_on_exit(self):
        """Test that context manager releases service on exit."""
        pool = EmbeddingObjectPool(pool_size=1)
        
        with patch('app.core.qwen3vl_service.Qwen3VLMultimodalEmbedding') as MockService:
            mock_service = Mock()
            mock_service.load_model = Mock()
            MockService.return_value = mock_service
            
            with patch('app.core.config.settings'):
                async with pool as service:
                    pass
                
                # Service should be released back to pool
                assert pool._pool.available == 1


class TestGetEmbeddingPool:
    """Tests for get_embedding_pool singleton."""
    
    @pytest.mark.asyncio
    async def test_singleton_creation(self):
        """Test that singleton is created once."""
        from app.utils.object_pool import get_embedding_pool
        
        # Reset singleton for test
        import app.utils.object_pool
        app.utils.object_pool._embedding_pool = None
        
        pool1 = await get_embedding_pool()
        pool2 = await get_embedding_pool()
        
        assert pool1 == pool2
    
    @pytest.mark.asyncio
    async def test_singleton_pool_size(self):
        """Test default pool size."""
        from app.utils.object_pool import get_embedding_pool
        
        # Reset singleton for test
        import app.utils.object_pool
        app.utils.object_pool._embedding_pool = None
        
        pool = await get_embedding_pool()
        
        # Default pool size is 2
        assert pool._pool._pool_size == 2