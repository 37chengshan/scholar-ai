"""Additional tests for base classes and edge cases.

Tests verify:
- Base class abstract methods
- Error handling
- Edge cases
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from abc import ABC, abstractmethod

from app.core.embedding.base import BaseEmbeddingService
from app.core.reranker.base import BaseRerankerService


class TestBaseEmbeddingService:
    """Test BaseEmbeddingService abstract methods."""

    def test_base_embedding_is_abstract(self):
        """BaseEmbeddingService should be abstract."""
        assert ABC in BaseEmbeddingService.__bases__

    def test_base_embedding_has_required_methods(self):
        """BaseEmbeddingService should have required abstract methods."""
        assert hasattr(BaseEmbeddingService, 'load_model')
        assert hasattr(BaseEmbeddingService, 'encode_text')
        assert hasattr(BaseEmbeddingService, 'is_loaded')
        assert hasattr(BaseEmbeddingService, 'get_model_info')
        assert hasattr(BaseEmbeddingService, 'supports_multimodal')

    def test_cannot_instantiate_base_embedding_directly(self):
        """Cannot instantiate BaseEmbeddingService directly."""
        with pytest.raises(TypeError):
            BaseEmbeddingService()


class TestBaseRerankerService:
    """Test BaseRerankerService abstract methods."""

    def test_base_reranker_is_abstract(self):
        """BaseRerankerService should be abstract."""
        assert ABC in BaseRerankerService.__bases__

    def test_base_reranker_has_required_methods(self):
        """BaseRerankerService should have required abstract methods."""
        assert hasattr(BaseRerankerService, 'load_model')
        assert hasattr(BaseRerankerService, 'rerank')
        assert hasattr(BaseRerankerService, 'is_loaded')
        assert hasattr(BaseRerankerService, 'get_model_info')
        assert hasattr(BaseRerankerService, 'supports_multimodal')

    def test_cannot_instantiate_base_reranker_directly(self):
        """Cannot instantiate BaseRerankerService directly."""
        with pytest.raises(TypeError):
            BaseRerankerService()


class TestEmbeddingServiceEdgeCases:
    """Test edge cases for embedding services."""

    @patch('app.core.embedding.bge_embedding.get_bge_m3_service')
    def test_bge_embedding_handles_whitespace_text(self, mock_get_bge):
        """Test BGE embedding handles whitespace text."""
        mock_bge = MagicMock()
        mock_bge.encode_text.return_value = [0.0] * 1024
        mock_get_bge.return_value = mock_bge
        
        from app.core.embedding.bge_embedding import BGEEmbeddingService
        service = BGEEmbeddingService()
        
        embedding = service.encode_text("   ")
        
        assert len(embedding) == 1024

    @patch('app.core.embedding.qwen3vl_embedding.get_qwen3vl_service')
    def test_qwen3vl_embedding_handles_newlines(self, mock_get_qwen):
        """Test Qwen3VL embedding handles text with newlines."""
        mock_qwen = MagicMock()
        mock_qwen.encode_text.return_value = [0.1] * 2048
        mock_get_qwen.return_value = mock_qwen
        
        from app.core.embedding.qwen3vl_embedding import Qwen3VLEmbeddingService
        service = Qwen3VLEmbeddingService()
        
        embedding = service.encode_text("line1\nline2\nline3")
        
        assert len(embedding) == 2048

    @patch('app.core.embedding.qwen3vl_embedding.get_qwen3vl_service')
    def test_qwen3vl_embedding_handles_special_characters(self, mock_get_qwen):
        """Test Qwen3VL embedding handles special characters."""
        mock_qwen = MagicMock()
        mock_qwen.encode_text.return_value = [0.2] * 2048
        mock_get_qwen.return_value = mock_qwen
        
        from app.core.embedding.qwen3vl_embedding import Qwen3VLEmbeddingService
        service = Qwen3VLEmbeddingService()
        
        embedding = service.encode_text("Special chars: @#$%^&*(){}[]|\\:;\"'<>,.?/~`")
        
        assert len(embedding) == 2048

    @patch('app.core.embedding.qwen3vl_embedding.get_qwen3vl_service')
    def test_qwen3vl_embedding_handles_unicode(self, mock_get_qwen):
        """Test Qwen3VL embedding handles unicode text."""
        mock_qwen = MagicMock()
        mock_qwen.encode_text.return_value = [0.3] * 2048
        mock_get_qwen.return_value = mock_qwen
        
        from app.core.embedding.qwen3vl_embedding import Qwen3VLEmbeddingService
        service = Qwen3VLEmbeddingService()
        
        embedding = service.encode_text("中文 日本語 한국어 العربية עברית")
        
        assert len(embedding) == 2048


class TestRerankerServiceEdgeCases:
    """Test edge cases for reranker services."""

    @patch('app.core.reranker.bge_reranker.FlagReranker')
    def test_bge_reranker_handles_single_document(self, mock_flag_reranker_class):
        """Test BGE reranker handles single document."""
        mock_flag_reranker = MagicMock()
        mock_flag_reranker.compute_score.return_value = 0.95
        mock_flag_reranker_class.return_value = mock_flag_reranker
        
        from app.core.reranker.bge_reranker import BGERerankerService
        service = BGERerankerService()
        service.load_model()
        
        query = "test query"
        documents = ["single doc"]
        results = service.rerank(query, documents)
        
        assert len(results) == 1
        assert results[0]["score"] == 0.95

    @patch('app.core.reranker.bge_reranker.FlagReranker')
    def test_bge_reranker_handles_duplicate_documents(self, mock_flag_reranker_class):
        """Test BGE reranker handles duplicate documents."""
        mock_flag_reranker = MagicMock()
        mock_flag_reranker.compute_score.return_value = [0.9, 0.9, 0.8]
        mock_flag_reranker_class.return_value = mock_flag_reranker
        
        from app.core.reranker.bge_reranker import BGERerankerService
        service = BGERerankerService()
        service.load_model()
        
        query = "test query"
        documents = ["doc1", "doc1", "doc2"]
        results = service.rerank(query, documents)
        
        assert len(results) == 3

    @patch('app.core.reranker.bge_reranker.FlagReranker')
    def test_bge_reranker_handles_long_query(self, mock_flag_reranker_class):
        """Test BGE reranker handles long query."""
        mock_flag_reranker = MagicMock()
        mock_flag_reranker.compute_score.return_value = [0.85]
        mock_flag_reranker_class.return_value = mock_flag_reranker
        
        from app.core.reranker.bge_reranker import BGERerankerService
        service = BGERerankerService()
        service.load_model()
        
        long_query = "This is a very long query " * 100
        documents = ["doc1"]
        results = service.rerank(long_query, documents)
        
        assert len(results) == 1


class TestFactoryCachingEdgeCases:
    """Test factory caching edge cases."""

    def test_embedding_factory_clear_cache(self):
        """Test EmbeddingServiceFactory clear_cache works."""
        from app.core.embedding.factory import EmbeddingServiceFactory
        
        # Add some entries
        EmbeddingServiceFactory._instances = {"key1": Mock(), "key2": Mock()}
        
        # Clear cache
        EmbeddingServiceFactory.clear_cache()
        
        assert len(EmbeddingServiceFactory._instances) == 0

    def test_reranker_factory_clear_cache(self):
        """Test RerankerServiceFactory clear_cache works."""
        from app.core.reranker.factory import RerankerServiceFactory
        
        # Add some entries
        RerankerServiceFactory._instances = {"key1": Mock(), "key2": Mock()}
        
        # Clear cache
        RerankerServiceFactory.clear_cache()
        
        assert len(RerankerServiceFactory._instances) == 0

    @patch('app.core.embedding.factory.settings')
    def test_embedding_factory_cache_key_format(self, mock_settings):
        """Test EmbeddingServiceFactory cache key format."""
        from app.core.embedding.factory import EmbeddingServiceFactory
        
        mock_settings.EMBEDDING_MODEL = "bge-m3"
        mock_settings.EMBEDDING_QUANTIZATION = "fp16"
        
        with patch('app.core.embedding.bge_embedding.get_bge_m3_service') as mock_get:
            mock_bge = Mock()
            mock_get.return_value = mock_bge
            
            EmbeddingServiceFactory.clear_cache()
            EmbeddingServiceFactory.create()
            
            cache_key = list(EmbeddingServiceFactory._instances.keys())[0]
            
            assert "bge-m3" in cache_key
            assert "fp16" in cache_key

    @patch('app.core.reranker.factory.settings')
    def test_reranker_factory_cache_key_format(self, mock_settings):
        """Test RerankerServiceFactory cache key format."""
        from app.core.reranker.factory import RerankerServiceFactory
        
        mock_settings.RERANKER_MODEL = "bge-reranker"
        mock_settings.RERANKER_QUANTIZATION = "fp16"
        
        RerankerServiceFactory.clear_cache()
        RerankerServiceFactory.create()
        
        cache_key = list(RerankerServiceFactory._instances.keys())[0]
        
        assert "bge-reranker" in cache_key
        assert "fp16" in cache_key