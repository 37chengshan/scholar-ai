"""
Tests for EmbeddingService refactored to use BGEM3Service (1024-dim) and Milvus.

Per 13-02-PLAN:
- Test 1: generate_embedding() returns 1024-dim vector
- Test 2: generate_embeddings_batch() returns list of 1024-dim vectors
- Test 3: store_chunks() inserts to Milvus, not PostgreSQL
- Test 4: No SentenceTransformer import present
"""
import pytest
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from typing import List, Dict, Any

from app.core.embedding_service import EmbeddingService


# Fixtures

@pytest.fixture
def mock_bge_m3_service():
    """Mock BGEM3Service for 1024-dim embeddings."""
    mock = Mock()
    mock.encode_text = Mock(return_value=[0.1] * 1024)
    mock.EMBEDDING_DIM = 1024
    return mock


@pytest.fixture
def mock_milvus_service():
    """Mock MilvusService for vector storage."""
    mock = Mock()
    # Return IDs based on input length
    def mock_insert(data):
        return list(range(1, len(data) + 1))
    mock.insert_contents = Mock(side_effect=mock_insert)
    return mock


@pytest.fixture
def sample_chunks():
    """Sample chunks for testing."""
    return [
        {
            "text": "We evaluated our model on three benchmarks.",
            "section": "Methodology",
            "page_start": 5,
        },
        {
            "text": "Table 1 shows the performance comparison.",
            "section": "Results",
            "page_start": 7,
        },
    ]


# Tests

class TestEmbeddingServiceBGE3Integration:
    """Test suite for EmbeddingService using BGEM3Service (1024-dim)."""

    def test_generate_embedding_returns_1024_dim(self, mock_bge_m3_service):
        """Test 1: generate_embedding() returns 1024-dim vector."""
        with patch('app.core.embedding_service.get_bge_m3_service', return_value=mock_bge_m3_service):
            service = EmbeddingService()
            embedding = service.generate_embedding("Test text")
            
            assert len(embedding) == 1024
            assert isinstance(embedding, list)
            assert all(isinstance(x, float) for x in embedding)

    def test_generate_embedding_empty_text_returns_zero_vector(self, mock_bge_m3_service):
        """Test that empty text returns zero vector."""
        with patch('app.core.embedding_service.get_bge_m3_service', return_value=mock_bge_m3_service):
            service = EmbeddingService()
            embedding = service.generate_embedding("")
            
            assert len(embedding) == 1024
            assert embedding == [0.0] * 1024

    def test_generate_embeddings_batch_returns_1024_dim(self, mock_bge_m3_service):
        """Test 2: generate_embeddings_batch() returns list of 1024-dim vectors."""
        with patch('app.core.embedding_service.get_bge_m3_service', return_value=mock_bge_m3_service):
            mock_bge_m3_service.encode_text = Mock(return_value=[[0.1] * 1024, [0.2] * 1024])
            
            service = EmbeddingService()
            texts = ["First text", "Second text"]
            embeddings = service.generate_embeddings_batch(texts)
            
            assert len(embeddings) == 2
            assert all(len(e) == 1024 for e in embeddings)

    def test_generate_embeddings_batch_empty_returns_empty_list(self, mock_bge_m3_service):
        """Test that empty input returns empty list."""
        with patch('app.core.embedding_service.get_bge_m3_service', return_value=mock_bge_m3_service):
            service = EmbeddingService()
            embeddings = service.generate_embeddings_batch([])
            
            assert embeddings == []

    def test_mock_mode_returns_1024_dim(self):
        """Test that mock_mode returns 1024-dim vectors."""
        service = EmbeddingService(mock_mode=True)
        embedding = service.generate_embedding("Test text")
        
        assert len(embedding) == 1024

    @pytest.mark.asyncio
    async def test_store_chunks_uses_milvus(self, mock_bge_m3_service, mock_milvus_service, sample_chunks):
        """Test 3: store_chunks() inserts to Milvus, not PostgreSQL."""
        with patch('app.core.embedding_service.get_bge_m3_service', return_value=mock_bge_m3_service):
            with patch('app.core.embedding_service.get_milvus_service', return_value=mock_milvus_service):
                service = EmbeddingService()
                
                # Store chunks (should use Milvus, not PostgreSQL)
                chunk_ids = await service.store_chunks(
                    paper_id="test-paper-id",
                    user_id="test-user-id",
                    chunks=sample_chunks,
                )
                
                # Verify Milvus insert_contents was called
                assert mock_milvus_service.insert_contents.called
                assert len(chunk_ids) == len(sample_chunks)

    @pytest.mark.asyncio
    async def test_store_chunks_with_contextual_embedding(self, mock_bge_m3_service, mock_milvus_service, sample_chunks):
        """Test store_chunks with contextual embedding (whole_document)."""
        with patch('app.core.embedding_service.get_bge_m3_service', return_value=mock_bge_m3_service):
            with patch('app.core.embedding_service.get_milvus_service', return_value=mock_milvus_service):
                service = EmbeddingService()
                
                # Mock create_contextual_embedding
                with patch.object(service, 'create_contextual_embedding', return_value=([0.1] * 1024, "Contextualized text")):
                    chunk_ids = await service.store_chunks(
                        paper_id="test-paper-id",
                        user_id="test-user-id",
                        chunks=sample_chunks,
                        whole_document="Full document text for context"
                    )
                    
                    assert mock_milvus_service.insert_contents.called
                    assert len(chunk_ids) == len(sample_chunks)

    @pytest.mark.asyncio
    async def test_store_chunks_empty_returns_empty_list(self, mock_bge_m3_service, mock_milvus_service):
        """Test store_chunks with empty input returns empty list."""
        with patch('app.core.embedding_service.get_bge_m3_service', return_value=mock_bge_m3_service):
            with patch('app.core.embedding_service.get_milvus_service', return_value=mock_milvus_service):
                service = EmbeddingService()
                
                chunk_ids = await service.store_chunks(
                    paper_id="test-paper-id",
                    user_id="test-user-id",
                    chunks=[],
                )
                
                assert chunk_ids == []


class TestNoSentenceTransformerImport:
    """Test 4: Verify no SentenceTransformer imports."""

    def test_no_sentence_transformer_import(self):
        """Test that EmbeddingService module does not import SentenceTransformer."""
        import app.core.embedding_service as module
        import inspect
        
        source = inspect.getsource(module)
        
        # Should not have sentence_transformers import
        assert "from sentence_transformers import" not in source
        assert "SentenceTransformer" not in source

    def test_embedding_service_uses_bge_m3(self):
        """Test that EmbeddingService uses BGEM3Service."""
        with patch('app.core.embedding_service.get_bge_m3_service') as mock_get_bge:
            mock_bge = Mock()
            mock_bge.encode_text = Mock(return_value=[0.1] * 1024)
            mock_get_bge.return_value = mock_bge
            
            service = EmbeddingService()
            embedding = service.generate_embedding("Test")
            
            # Should call BGEM3Service.encode_text
            mock_bge.encode_text.assert_called()


class TestEmbeddingServiceDimension:
    """Test embedding dimension is 1024."""

    def test_dimension_property_returns_1024(self, mock_bge_m3_service):
        """Test that dimension property returns 1024."""
        with patch('app.core.embedding_service.get_bge_m3_service', return_value=mock_bge_m3_service):
            service = EmbeddingService()
            
            assert service.dimension == 1024

    def test_mock_embedding_is_1024_dim(self):
        """Test that mock embeddings are 1024-dim."""
        service = EmbeddingService(mock_mode=True)
        
        embedding = service._generate_mock_embedding("Test text")
        
        assert len(embedding) == 1024


class TestRemovedMethods:
    """Test that deprecated methods are removed."""

    def test_search_similar_removed(self):
        """Test that search_similar() method is removed (use MilvusService.search_contents())."""
        service = EmbeddingService()
        
        # search_similar should not exist
        assert not hasattr(service, 'search_similar')