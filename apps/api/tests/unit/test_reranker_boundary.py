"""Boundary tests for Reranker services.

Tests verify edge cases and boundary conditions:
- Large batch sizes (1000+ documents)
- Very long text inputs
- Special characters and Unicode
- Empty/whitespace inputs
- top_k boundary values
- Single document
- Duplicate documents
- None/null inputs
- Text length limits
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from typing import List, Dict, Any
import string

from app.core.reranker.base import BaseRerankerService
from app.core.reranker.bge_reranker import BGERerankerService
from app.core.reranker.qwen3vl_reranker import Qwen3VLRerankerService


class TestBGERerankerBoundaryConditions:
    """Test BGE reranker boundary conditions."""

    @patch('app.core.reranker.bge_reranker.FlagReranker')
    def test_rerank_large_batch_size(self, mock_flag_reranker_class):
        """Test reranking with 1000+ documents."""
        mock_flag_reranker = MagicMock()
        scores = [0.9 - i * 0.0001 for i in range(1000)]
        mock_flag_reranker.compute_score.return_value = scores
        mock_flag_reranker_class.return_value = mock_flag_reranker
        
        service = BGERerankerService()
        service.load_model()
        
        query = "test query"
        documents = [f"document {i}" for i in range(1000)]
        results = service.rerank(query, documents, top_k=10)
        
        assert len(results) == 10
        assert results[0]["score"] >= results[-1]["score"]

    @patch('app.core.reranker.bge_reranker.FlagReranker')
    def test_rerank_very_long_text(self, mock_flag_reranker_class):
        """Test reranking with very long text (10000 chars)."""
        mock_flag_reranker = MagicMock()
        mock_flag_reranker.compute_score.return_value = [0.8, 0.6]
        mock_flag_reranker_class.return_value = mock_flag_reranker
        
        service = BGERerankerService()
        service.load_model()
        
        long_query = "test query " * 1000
        long_doc = "document content " * 500
        
        results = service.rerank(long_query, [long_doc, "short doc"])
        
        assert len(results) == 2
        assert "score" in results[0]

    @patch('app.core.reranker.bge_reranker.FlagReranker')
    def test_rerank_special_characters(self, mock_flag_reranker_class):
        """Test reranking with special characters."""
        mock_flag_reranker = MagicMock()
        mock_flag_reranker.compute_score.return_value = [0.8, 0.7]
        mock_flag_reranker_class.return_value = mock_flag_reranker
        
        service = BGERerankerService()
        service.load_model()
        
        query = "test!@#$%^&*()_+-=[]{}|;':\",./<>?"
        documents = [
            "doc with \n newlines \t tabs",
            "doc with unicode: 你好世界 🎉"
        ]
        
        results = service.rerank(query, documents)
        
        assert len(results) == 2

    @patch('app.core.reranker.bge_reranker.FlagReranker')
    def test_rerank_unicode_characters(self, mock_flag_reranker_class):
        """Test reranking with various Unicode characters."""
        mock_flag_reranker = MagicMock()
        mock_flag_reranker.compute_score.return_value = [0.8, 0.7, 0.6]
        mock_flag_reranker_class.return_value = mock_flag_reranker
        
        service = BGERerankerService()
        service.load_model()
        
        documents = [
            "中文测试",
            "日本語テスト",
            "한국어 테스트"
        ]
        
        results = service.rerank("多语言查询", documents)
        
        assert len(results) == 3

    @patch('app.core.reranker.bge_reranker.FlagReranker')
    def test_rerank_empty_query(self, mock_flag_reranker_class):
        """Test reranking with empty query string."""
        mock_flag_reranker = MagicMock()
        mock_flag_reranker.compute_score.return_value = [0.5]
        mock_flag_reranker_class.return_value = mock_flag_reranker
        
        service = BGERerankerService()
        service.load_model()
        
        results = service.rerank("", ["doc1"])
        
        assert len(results) == 1

    @patch('app.core.reranker.bge_reranker.FlagReranker')
    def test_rerank_whitespace_only(self, mock_flag_reranker_class):
        """Test reranking with whitespace-only inputs."""
        mock_flag_reranker = MagicMock()
        mock_flag_reranker.compute_score.return_value = [0.5, 0.3]
        mock_flag_reranker_class.return_value = mock_flag_reranker
        
        service = BGERerankerService()
        service.load_model()
        
        results = service.rerank("   ", ["   ", "doc1"])
        
        assert len(results) == 2

    @patch('app.core.reranker.bge_reranker.FlagReranker')
    def test_rerank_top_k_zero(self, mock_flag_reranker_class):
        """Test reranking with top_k=0."""
        mock_flag_reranker = MagicMock()
        mock_flag_reranker.compute_score.return_value = [0.9, 0.7]
        mock_flag_reranker_class.return_value = mock_flag_reranker
        
        service = BGERerankerService()
        service.load_model()
        
        results = service.rerank("query", ["doc1", "doc2"], top_k=0)
        
        assert len(results) == 0

    @patch('app.core.reranker.bge_reranker.FlagReranker')
    def test_rerank_top_k_exceeds_documents(self, mock_flag_reranker_class):
        """Test reranking with top_k > number of documents."""
        mock_flag_reranker = MagicMock()
        mock_flag_reranker.compute_score.return_value = [0.9]
        mock_flag_reranker_class.return_value = mock_flag_reranker
        
        service = BGERerankerService()
        service.load_model()
        
        results = service.rerank("query", ["doc1"], top_k=100)
        
        assert len(results) == 1

    @patch('app.core.reranker.bge_reranker.FlagReranker')
    def test_rerank_single_document(self, mock_flag_reranker_class):
        """Test reranking with single document."""
        mock_flag_reranker = MagicMock()
        mock_flag_reranker.compute_score.return_value = 0.85
        mock_flag_reranker_class.return_value = mock_flag_reranker
        
        service = BGERerankerService()
        service.load_model()
        
        results = service.rerank("query", ["single doc"])
        
        assert len(results) == 1
        assert results[0]["rank"] == 0

    @patch('app.core.reranker.bge_reranker.FlagReranker')
    def test_rerank_duplicate_documents(self, mock_flag_reranker_class):
        """Test reranking with duplicate documents."""
        mock_flag_reranker = MagicMock()
        mock_flag_reranker.compute_score.return_value = [0.9, 0.9, 0.8]
        mock_flag_reranker_class.return_value = mock_flag_reranker
        
        service = BGERerankerService()
        service.load_model()
        
        documents = ["duplicate", "duplicate", "unique"]
        results = service.rerank("query", documents)
        
        assert len(results) == 3

    @patch('app.core.reranker.bge_reranker.FlagReranker')
    def test_rerank_all_duplicate_documents(self, mock_flag_reranker_class):
        """Test reranking with all duplicate documents."""
        mock_flag_reranker = MagicMock()
        mock_flag_reranker.compute_score.return_value = [0.9, 0.9, 0.9]
        mock_flag_reranker_class.return_value = mock_flag_reranker
        
        service = BGERerankerService()
        service.load_model()
        
        documents = ["same", "same", "same"]
        results = service.rerank("query", documents)
        
        assert len(results) == 3

    @patch('app.core.reranker.bge_reranker.FlagReranker')
    def test_rerank_dict_input_empty_text(self, mock_flag_reranker_class):
        """Test reranking with dict input containing empty text."""
        mock_flag_reranker = MagicMock()
        mock_flag_reranker.compute_score.return_value = [0.7, 0.6]
        mock_flag_reranker_class.return_value = mock_flag_reranker
        
        service = BGERerankerService()
        service.load_model()
        
        query = {"text": "", "extra": "data"}
        documents = [{"text": "", "id": 1}, {"text": "content", "id": 2}]
        
        results = service.rerank(query, documents)
        
        assert len(results) == 2

    @patch('app.core.reranker.bge_reranker.FlagReranker')
    def test_rerank_dict_input_missing_text_key(self, mock_flag_reranker_class):
        """Test reranking with dict input missing text key."""
        mock_flag_reranker = MagicMock()
        mock_flag_reranker.compute_score.return_value = [0.7, 0.6]
        mock_flag_reranker_class.return_value = mock_flag_reranker
        
        service = BGERerankerService()
        service.load_model()
        
        query = {"content": "query"}
        documents = [{"content": "doc1"}, {"text": "doc2"}]
        
        results = service.rerank(query, documents)
        
        assert len(results) == 2

    @patch('app.core.reranker.bge_reranker.FlagReranker')
    def test_rerank_negative_top_k(self, mock_flag_reranker_class):
        """Test reranking with negative top_k value returns all but last."""
        mock_flag_reranker = MagicMock()
        mock_flag_reranker.compute_score.return_value = [0.9, 0.7]
        mock_flag_reranker_class.return_value = mock_flag_reranker
        
        service = BGERerankerService()
        service.load_model()
        
        results = service.rerank("query", ["doc1", "doc2"], top_k=-1)
        
        assert len(results) == 1


class TestQwen3VLRerankerBoundaryConditions:
    """Test Qwen3VL reranker boundary conditions."""

    @patch('app.core.reranker.qwen3vl_reranker.AutoModel')
    @patch('app.core.reranker.qwen3vl_reranker.AutoTokenizer')
    def test_rerank_large_batch_multimodal(self, mock_tokenizer, mock_model):
        """Test multimodal reranking with large batch."""
        mock_model_instance = MagicMock()
        mock_model_instance.rerank = MagicMock(return_value=[0.9 - i * 0.001 for i in range(100)])
        mock_model.return_value = mock_model_instance
        
        service = Qwen3VLRerankerService()
        service.load_model()
        
        query = {"text": "query", "image": "fake_image.jpg"}
        documents = [{"text": f"doc {i}", "image": f"img{i}.jpg"} for i in range(100)]
        
        results = service.rerank(query, documents, top_k=20)
        
        assert len(results) == 20

    @patch('app.core.reranker.qwen3vl_reranker.AutoModel')
    @patch('app.core.reranker.qwen3vl_reranker.AutoTokenizer')
    def test_rerank_mixed_text_and_multimodal(self, mock_tokenizer, mock_model):
        """Test reranking with mixed text-only and multimodal documents."""
        mock_model_instance = MagicMock()
        mock_model_instance.rerank = MagicMock(return_value=[0.8, 0.7, 0.6])
        mock_model.return_value = mock_model_instance
        
        service = Qwen3VLRerankerService()
        service.load_model()
        
        documents = [
            "text only doc",
            {"text": "multimodal doc", "image": "img.jpg"},
            "another text doc"
        ]
        
        results = service.rerank("query", documents)
        
        assert len(results) == 3

    @patch('app.core.reranker.qwen3vl_reranker.AutoModel')
    @patch('app.core.reranker.qwen3vl_reranker.AutoTokenizer')
    def test_rerank_unicode_multimodal(self, mock_tokenizer, mock_model):
        """Test multimodal reranking with Unicode text."""
        mock_model_instance = MagicMock()
        mock_model_instance.rerank = MagicMock(return_value=[0.9, 0.8])
        mock_model.return_value = mock_model_instance
        
        service = Qwen3VLRerankerService()
        service.load_model()
        
        query = {"text": "中文查询 🎉", "image": "img.jpg"}
        documents = [{"text": "中文文档", "image": "doc.jpg"}]
        
        results = service.rerank(query, documents)
        
        assert len(results) == 1

    @patch('app.core.reranker.qwen3vl_reranker.AutoModel')
    @patch('app.core.reranker.qwen3vl_reranker.AutoTokenizer')
    def test_rerank_empty_image_field(self, mock_tokenizer, mock_model):
        """Test reranking with empty image field in dict."""
        mock_model_instance = MagicMock()
        mock_model_instance.rerank = MagicMock(return_value=[0.8, 0.7])
        mock_model.return_value = mock_model_instance
        
        service = Qwen3VLRerankerService()
        service.load_model()
        
        query = {"text": "query", "image": ""}
        documents = [{"text": "doc1", "image": None}, {"text": "doc2", "image": ""}]
        
        results = service.rerank(query, documents)
        
        assert len(results) == 2

    @patch('app.core.reranker.qwen3vl_reranker.AutoModel')
    @patch('app.core.reranker.qwen3vl_reranker.AutoTokenizer')
    def test_rerank_long_multimodal_text(self, mock_tokenizer, mock_model):
        """Test reranking with very long text in multimodal input."""
        mock_model_instance = MagicMock()
        mock_model_instance.rerank = MagicMock(return_value=[0.9])
        mock_model.return_value = mock_model_instance
        
        service = Qwen3VLRerankerService()
        service.load_model()
        
        long_text = "content " * 1000
        query = {"text": long_text, "image": "img.jpg"}
        
        results = service.rerank(query, ["short doc"])
        
        assert len(results) == 1

    @patch('app.core.reranker.qwen3vl_reranker.AutoModel')
    @patch('app.core.reranker.qwen3vl_reranker.AutoTokenizer')
    def test_rerank_invalid_quantization(self, mock_tokenizer, mock_model):
        """Test initialization with invalid quantization type."""
        service = Qwen3VLRerankerService(quantization="invalid")
        
        assert service.quantization == "invalid"

    @patch('app.core.reranker.qwen3vl_reranker.AutoModel')
    @patch('app.core.reranker.qwen3vl_reranker.AutoTokenizer')
    def test_rerank_invalid_device(self, mock_tokenizer, mock_model):
        """Test initialization with invalid device type."""
        service = Qwen3VLRerankerService(device="invalid_device")
        
        assert service.device == "invalid_device"


class TestRerankerCommonBoundaryConditions:
    """Test boundary conditions common to both rerankers."""

    @patch('app.core.reranker.bge_reranker.FlagReranker')
    def test_both_handle_empty_documents_list(self, mock_flag_reranker):
        """Both rerankers should handle empty documents list."""
        service = BGERerankerService()
        service.load_model()
        
        results = service.rerank("query", [])
        
        assert results == []

    @patch('app.core.reranker.qwen3vl_reranker.AutoModel')
    @patch('app.core.reranker.qwen3vl_reranker.AutoTokenizer')
    def test_qwen3vl_handles_empty_documents_list(self, mock_tokenizer, mock_model):
        """Qwen3VL reranker should handle empty documents list."""
        service = Qwen3VLRerankerService()
        service.load_model()
        
        results = service.rerank("query", [])
        
        assert results == []

    @patch('app.core.reranker.bge_reranker.FlagReranker')
    def test_both_return_correct_rank_sequence(self, mock_flag_reranker):
        """Both rerankers should return correct rank sequence."""
        mock_flag_reranker_instance = MagicMock()
        mock_flag_reranker_instance.compute_score.return_value = [0.9, 0.7, 0.5, 0.3]
        mock_flag_reranker.return_value = mock_flag_reranker_instance
        
        service = BGERerankerService()
        service.load_model()
        
        results = service.rerank("query", ["d1", "d2", "d3", "d4"])
        
        ranks = [r["rank"] for r in results]
        assert ranks == [0, 1, 2, 3]

    @patch('app.core.reranker.bge_reranker.FlagReranker')
    def test_scores_always_between_zero_and_one(self, mock_flag_reranker):
        """All scores should be normalized between 0 and 1."""
        mock_flag_reranker_instance = MagicMock()
        mock_flag_reranker_instance.compute_score.return_value = [0.99, 0.01, 0.5]
        mock_flag_reranker.return_value = mock_flag_reranker_instance
        
        service = BGERerankerService()
        service.load_model()
        
        results = service.rerank("query", ["d1", "d2", "d3"])
        
        for result in results:
            assert 0 <= result["score"] <= 1

    @patch('app.core.reranker.bge_reranker.FlagReranker')
    def test_top_k_one_returns_single_result(self, mock_flag_reranker):
        """top_k=1 should return single highest-score result."""
        mock_flag_reranker_instance = MagicMock()
        mock_flag_reranker_instance.compute_score.return_value = [0.5, 0.9, 0.7]
        mock_flag_reranker.return_value = mock_flag_reranker_instance
        
        service = BGERerankerService()
        service.load_model()
        
        results = service.rerank("query", ["d1", "d2", "d3"], top_k=1)
        
        assert len(results) == 1
        assert results[0]["score"] == 0.9


class TestRerankerInputValidation:
    """Test input validation for rerankers."""

    @patch('app.core.reranker.bge_reranker.FlagReranker')
    def test_query_can_be_dict_with_extra_keys(self, mock_flag_reranker):
        """Query dict can contain extra keys beyond 'text'."""
        mock_flag_reranker_instance = MagicMock()
        mock_flag_reranker_instance.compute_score.return_value = [0.8]
        mock_flag_reranker.return_value = mock_flag_reranker_instance
        
        service = BGERerankerService()
        service.load_model()
        
        query = {"text": "query", "metadata": {"id": 1}, "tags": ["tag1"]}
        results = service.rerank(query, ["doc"])
        
        assert len(results) == 1

    @patch('app.core.reranker.bge_reranker.FlagReranker')
    def test_document_can_be_dict_with_nested_structure(self, mock_flag_reranker):
        """Document dict can contain nested structure."""
        mock_flag_reranker_instance = MagicMock()
        mock_flag_reranker_instance.compute_score.return_value = [0.8, 0.7]
        mock_flag_reranker.return_value = mock_flag_reranker_instance
        
        service = BGERerankerService()
        service.load_model()
        
        documents = [
            {"text": "doc1", "metadata": {"author": "A", "date": "2024"}},
            {"text": "doc2", "sections": [{"title": "intro"}]}
        ]
        
        results = service.rerank("query", documents)
        
        assert len(results) == 2

    @patch('app.core.reranker.bge_reranker.FlagReranker')
    def test_extreme_score_values(self, mock_flag_reranker):
        """Test handling of extreme score values (near 0 and 1)."""
        mock_flag_reranker_instance = MagicMock()
        mock_flag_reranker_instance.compute_score.return_value = [0.999999, 0.000001, 0.5]
        mock_flag_reranker.return_value = mock_flag_reranker_instance
        
        service = BGERerankerService()
        service.load_model()
        
        results = service.rerank("query", ["d1", "d2", "d3"])
        
        assert results[0]["score"] >= results[-1]["score"]