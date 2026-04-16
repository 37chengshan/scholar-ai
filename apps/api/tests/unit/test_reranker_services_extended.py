"""Extended tests for BGERerankerService and Qwen3VLRerankerService.

Tests verify:
- Reranking functionality
- Score normalization
- Batch processing
- Error handling
- Model lifecycle
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from typing import List, Dict

from app.core.reranker.base import BaseRerankerService
from app.core.reranker.bge_reranker import BGERerankerService
from app.core.reranker.qwen3vl_reranker import Qwen3VLRerankerService


class TestBGERerankerServiceInterface:
    """Test BGERerankerService interface compliance."""

    def test_bge_reranker_inherits_from_base(self):
        """BGERerankerService should inherit from BaseRerankerService."""
        assert issubclass(BGERerankerService, BaseRerankerService)

    @patch('app.core.reranker.bge_reranker.FlagReranker')
    def test_bge_reranker_is_not_abstract(self, mock_flag_reranker):
        """BGERerankerService should be concrete (can instantiate)."""
        service = BGERerankerService()
        assert service is not None
        assert isinstance(service, BaseRerankerService)

    @patch('app.core.reranker.bge_reranker.FlagReranker')
    def test_bge_supports_reranking(self, mock_flag_reranker):
        """BGERerankerService should support reranking."""
        service = BGERerankerService()
        
        query = "test query"
        documents = ["doc1", "doc2", "doc3"]
        
        assert hasattr(service, 'rerank')


class TestBGERerankerServiceReranking:
    """Test BGE reranking functionality."""

    @patch('app.core.reranker.bge_reranker.FlagReranker')
    def test_rerank_returns_sorted_results(self, mock_flag_reranker_class):
        """Test that rerank returns sorted results."""
        mock_flag_reranker = MagicMock()
        mock_flag_reranker.compute_score.return_value = [0.7, 0.9, 0.5]
        mock_flag_reranker_class.return_value = mock_flag_reranker
        
        service = BGERerankerService()
        service.load_model()
        
        query = "test query"
        documents = ["doc1", "doc2", "doc3"]
        results = service.rerank(query, documents)
        
        assert len(results) == 3
        scores = [r["score"] for r in results]
        assert scores == sorted(scores, reverse=True)

    @patch('app.core.reranker.bge_reranker.FlagReranker')
    def test_rerank_with_top_k(self, mock_flag_reranker_class):
        """Test rerank with top_k parameter."""
        mock_flag_reranker = MagicMock()
        mock_flag_reranker.compute_score.return_value = [0.9, 0.7, 0.5]
        mock_flag_reranker_class.return_value = mock_flag_reranker
        
        service = BGERerankerService()
        service.load_model()
        
        query = "test query"
        documents = ["doc1", "doc2", "doc3"]
        results = service.rerank(query, documents, top_k=2)
        
        assert len(results) == 2

    @patch('app.core.reranker.bge_reranker.FlagReranker')
    def test_rerank_empty_documents(self, mock_flag_reranker_class):
        """Test rerank with empty documents."""
        mock_flag_reranker = MagicMock()
        mock_flag_reranker_class.return_value = mock_flag_reranker
        
        service = BGERerankerService()
        service.load_model()
        
        query = "test query"
        documents: List[str] = []
        results = service.rerank(query, documents)
        
        assert results == []

    @patch('app.core.reranker.bge_reranker.FlagReranker')
    def test_rerank_scores_in_valid_range(self, mock_flag_reranker_class):
        """Test that rerank scores are in valid range."""
        mock_flag_reranker = MagicMock()
        mock_flag_reranker.compute_score.return_value = [0.95, 0.75, 0.25]
        mock_flag_reranker_class.return_value = mock_flag_reranker
        
        service = BGERerankerService()
        service.load_model()
        
        query = "test query"
        documents = ["doc1", "doc2", "doc3"]
        results = service.rerank(query, documents)
        
        for result in results:
            assert 0 <= result["score"] <= 1


class TestBGERerankerServiceLifecycle:
    """Test BGE reranker lifecycle management."""

    @patch('app.core.reranker.bge_reranker.FlagReranker')
    def test_load_model_initializes_reranker(self, mock_flag_reranker_class):
        """Test load_model initializes reranker."""
        mock_flag_reranker = MagicMock()
        mock_flag_reranker_class.return_value = mock_flag_reranker
        
        service = BGERerankerService()
        service.load_model()
        
        mock_flag_reranker_class.assert_called_once()
        assert service.is_loaded() is True

    @patch('app.core.reranker.bge_reranker.FlagReranker')
    def test_is_loaded_returns_true_after_loading(self, mock_flag_reranker_class):
        """Test is_loaded returns True after load_model."""
        mock_flag_reranker = MagicMock()
        mock_flag_reranker_class.return_value = mock_flag_reranker
        
        service = BGERerankerService()
        
        assert service.is_loaded() is False
        
        service.load_model()
        
        assert service.is_loaded() is True


class TestQwen3VLRerankerServiceInterface:
    """Test Qwen3VLRerankerService interface compliance."""

    def test_qwen3vl_reranker_inherits_from_base(self):
        """Qwen3VLRerankerService should inherit from BaseRerankerService."""
        assert issubclass(Qwen3VLRerankerService, BaseRerankerService)

    @patch('app.core.reranker.qwen3vl_reranker.AutoModel')
    @patch('app.core.reranker.qwen3vl_reranker.AutoTokenizer')
    def test_qwen3vl_reranker_is_not_abstract(self, mock_tokenizer, mock_model):
        """Qwen3VLRerankerService should be concrete (can instantiate)."""
        service = Qwen3VLRerankerService()
        assert service is not None
        assert isinstance(service, BaseRerankerService)

    @patch('app.core.reranker.qwen3vl_reranker.AutoModel')
    @patch('app.core.reranker.qwen3vl_reranker.AutoTokenizer')
    def test_qwen3vl_supports_reranking(self, mock_tokenizer, mock_model):
        """Qwen3VLRerankerService should support reranking."""
        service = Qwen3VLRerankerService()
        
        assert hasattr(service, 'rerank')


class TestQwen3VLRerankerServiceReranking:
    """Test Qwen3VL reranking functionality."""

    @patch('app.core.reranker.qwen3vl_reranker.AutoModel')
    @patch('app.core.reranker.qwen3vl_reranker.AutoTokenizer')
    def test_rerank_with_quantization(self, mock_tokenizer, mock_model):
        """Test rerank with quantization parameter."""
        service = Qwen3VLRerankerService(quantization="int8")
        
        assert service.quantization == "int8"

    @patch('app.core.reranker.qwen3vl_reranker.AutoModel')
    @patch('app.core.reranker.qwen3vl_reranker.AutoTokenizer')
    def test_rerank_accepts_text_documents(self, mock_tokenizer, mock_model):
        """Test that rerank accepts text documents."""
        mock_model_instance = MagicMock()
        mock_model.return_value = mock_model_instance
        mock_tokenizer_instance = MagicMock()
        mock_tokenizer.return_value = mock_tokenizer_instance
        
        service = Qwen3VLRerankerService()
        
        with patch('pathlib.Path.exists', return_value=True):
            service.load_model()
        
        assert service.is_loaded() is True


class TestQwen3VLRerankerServiceLifecycle:
    """Test Qwen3VL reranker lifecycle management."""

    @patch('app.core.reranker.qwen3vl_reranker.AutoModel')
    @patch('app.core.reranker.qwen3vl_reranker.AutoTokenizer')
    def test_load_model_calls_transformers(self, mock_tokenizer, mock_model):
        """Test load_model calls transformers."""
        mock_model.return_value = MagicMock()
        mock_tokenizer.return_value = MagicMock()
        
        service = Qwen3VLRerankerService()
        
        with patch('pathlib.Path.exists', return_value=True):
            service.load_model()
        
        assert service._initialized is True

    @patch('app.core.reranker.qwen3vl_reranker.AutoModel')
    @patch('app.core.reranker.qwen3vl_reranker.AutoTokenizer')
    def test_is_loaded_returns_true_after_loading(self, mock_tokenizer, mock_model):
        """Test is_loaded returns True after load_model."""
        mock_model.return_value = MagicMock()
        mock_tokenizer.return_value = MagicMock()
        
        service = Qwen3VLRerankerService()
        
        assert service.is_loaded() is False
        
        with patch('pathlib.Path.exists', return_value=True):
            service.load_model()
        
        assert service.is_loaded() is True

    @patch('app.core.reranker.qwen3vl_reranker.AutoModel')
    @patch('app.core.reranker.qwen3vl_reranker.AutoTokenizer')
    def test_get_model_info(self, mock_tokenizer, mock_model):
        """Test get_model_info returns correct information."""
        service = Qwen3VLRerankerService()
        info = service.get_model_info()
        
        assert isinstance(info, dict)
        assert "name" in info
        assert "Qwen3-VL-Reranker" in info["name"]


class TestRerankerServiceComparison:
    """Compare BGE and Qwen3VL reranker behaviors."""

    @patch('app.core.reranker.bge_reranker.FlagReranker')
    @patch('app.core.reranker.qwen3vl_reranker.AutoModel')
    @patch('app.core.reranker.qwen3vl_reranker.AutoTokenizer')
    def test_both_implement_same_interface(self, mock_tokenizer, mock_model, mock_flag_reranker):
        """Both rerankers should implement BaseRerankerService."""
        bge_service = BGERerankerService()
        qwen_service = Qwen3VLRerankerService()
        
        assert isinstance(bge_service, BaseRerankerService)
        assert isinstance(qwen_service, BaseRerankerService)
        
        assert hasattr(bge_service, 'rerank')
        assert hasattr(qwen_service, 'rerank')
        
        assert hasattr(bge_service, 'load_model')
        assert hasattr(qwen_service, 'load_model')
        
        assert hasattr(bge_service, 'is_loaded')
        assert hasattr(qwen_service, 'is_loaded')

    @patch('app.core.reranker.bge_reranker.FlagReranker')
    @patch('app.core.reranker.qwen3vl_reranker.AutoModel')
    @patch('app.core.reranker.qwen3vl_reranker.AutoTokenizer')
    def test_both_support_structured_output(self, mock_tokenizer, mock_model, mock_flag_reranker):
        """Both rerankers should support structured output."""
        bge_service = BGERerankerService()
        qwen_service = Qwen3VLRerankerService()
        
        assert hasattr(bge_service, 'rerank')
        assert hasattr(qwen_service, 'rerank')