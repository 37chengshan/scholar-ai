"""Tests for BGERerankerService adapter.

Tests verify:
- Implements BaseRerankerService interface
- Preserves existing ReRankerService behavior
- Returns structured results (document, score, rank)
- Supports text-only inputs (supports_multimodal=False)
- Works identically to old ReRankerService
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import List, Dict, Any


class TestBGERerankerService:
    """Tests for BGERerankerService adapter."""

    def test_bge_reranker_implements_base_interface(self):
        """Test that BGERerankerService implements BaseRerankerService."""
        from app.core.reranker.bge_reranker import BGERerankerService
        from app.core.reranker.base import BaseRerankerService

        # Create instance
        service = BGERerankerService()

        # Should be instance of BaseRerankerService
        assert isinstance(service, BaseRerankerService)

    def test_bge_reranker_supports_multimodal_returns_false(self):
        """Test that BGERerankerService.supports_multimodal() returns False."""
        from app.core.reranker.bge_reranker import BGERerankerService

        service = BGERerankerService()

        # Should return False (text-only)
        assert service.supports_multimodal() is False

    def test_bge_reranker_is_loaded_initially_false(self):
        """Test that BGERerankerService.is_loaded() returns False before load_model()."""
        from app.core.reranker.bge_reranker import BGERerankerService

        service = BGERerankerService()

        # Should return False initially
        assert service.is_loaded() is False

    def test_bge_reranker_get_model_info(self):
        """Test that BGERerankerService.get_model_info() returns correct info."""
        from app.core.reranker.bge_reranker import BGERerankerService

        service = BGERerankerService()

        info = service.get_model_info()

        # Should return dict with required keys
        assert isinstance(info, dict)
        assert "name" in info
        assert "version" in info
        assert "type" in info

        # Should indicate text-only
        assert info["type"] == "text-only"
        assert "bge" in info["name"].lower()

    @patch('app.core.reranker.bge_reranker.FlagReranker')
    def test_bge_reranker_load_model_success(self, mock_flag_reranker):
        """Test that BGERerankerService.load_model() loads FlagReranker successfully."""
        from app.core.reranker.bge_reranker import BGERerankerService

        service = BGERerankerService()

        # Mock FlagReranker
        mock_model = Mock()
        mock_flag_reranker.return_value = mock_model

        # Load model
        service.load_model()

        # Should set initialized flag
        assert service.is_loaded() is True

        # Should have called FlagReranker
        mock_flag_reranker.assert_called_once()

    def test_bge_reranker_rerank_before_load_raises(self):
        """Test that rerank() before load_model() raises RuntimeError."""
        from app.core.reranker.bge_reranker import BGERerankerService

        service = BGERerankerService()

        # Should raise RuntimeError
        with pytest.raises(RuntimeError) as exc_info:
            service.rerank("query", ["doc1", "doc2"])

        # Error message should mention load_model
        assert "load_model" in str(exc_info.value).lower()

    @patch('app.core.reranker.bge_reranker.FlagReranker')
    def test_bge_reranker_rerank_returns_structured_results(self, mock_flag_reranker):
        """Test that BGERerankerService.rerank() returns structured results."""
        from app.core.reranker.bge_reranker import BGERerankerService

        service = BGERerankerService()
        service.load_model()

        # Mock compute_score to return scores
        mock_flag_reranker.return_value.compute_score.return_value = [0.9, 0.7, 0.5]

        # Rerank
        query = "test query"
        documents = ["doc1", "doc2", "doc3"]
        results = service.rerank(query, documents, top_k=3)

        # Should return list of dicts
        assert isinstance(results, list)
        assert len(results) == 3

        # Each result should have document, score, rank
        for i, result in enumerate(results):
            assert isinstance(result, dict)
            assert "document" in result
            assert "score" in result
            assert "rank" in result

            # Rank should be 0-indexed
            assert result["rank"] == i

            # Score should be float
            assert isinstance(result["score"], float)

    @patch('app.core.reranker.bge_reranker.FlagReranker')
    def test_bge_reranker_rerank_sorts_by_score(self, mock_flag_reranker):
        """Test that BGERerankerService.rerank() sorts results by score descending."""
        from app.core.reranker.bge_reranker import BGERerankerService

        service = BGERerankerService()
        service.load_model()

        # Mock compute_score with unsorted scores
        mock_flag_reranker.return_value.compute_score.return_value = [0.5, 0.9, 0.7]

        # Rerank
        query = "test query"
        documents = ["doc1", "doc2", "doc3"]
        results = service.rerank(query, documents, top_k=3)

        # Should be sorted by score descending
        scores = [r["score"] for r in results]
        assert scores == sorted(scores, reverse=True)

        # Top result should have highest score
        assert results[0]["score"] == 0.9
        assert results[0]["document"] == "doc2"

    @patch('app.core.reranker.bge_reranker.FlagReranker')
    def test_bge_reranker_rerank_respects_top_k(self, mock_flag_reranker):
        """Test that BGERerankerService.rerank() respects top_k parameter."""
        from app.core.reranker.bge_reranker import BGERerankerService

        service = BGERerankerService()
        service.load_model()

        # Mock compute_score
        scores = [0.9, 0.8, 0.7, 0.6, 0.5]
        mock_flag_reranker.return_value.compute_score.return_value = scores

        # Rerank with top_k=2
        query = "test query"
        documents = ["doc1", "doc2", "doc3", "doc4", "doc5"]
        results = service.rerank(query, documents, top_k=2)

        # Should return only top_k results
        assert len(results) == 2

        # Should be top 2 scores
        assert results[0]["score"] == 0.9
        assert results[1]["score"] == 0.8

    @patch('app.core.reranker.bge_reranker.FlagReranker')
    def test_bge_reranker_rerank_single_document(self, mock_flag_reranker):
        """Test that BGERerankerService.rerank() handles single document case."""
        from app.core.reranker.bge_reranker import BGERerankerService

        service = BGERerankerService()
        service.load_model()

        # Mock compute_score to return float for single doc (not list)
        mock_flag_reranker.return_value.compute_score.return_value = 0.9

        # Rerank single document
        query = "test query"
        documents = ["doc1"]
        results = service.rerank(query, documents, top_k=10)

        # Should return single result
        assert len(results) == 1
        assert results[0]["score"] == 0.9

    @patch('app.core.reranker.bge_reranker.FlagReranker')
    def test_bge_reranker_accepts_dict_query_but_uses_text(self, mock_flag_reranker):
        """Test that BGERerankerService accepts dict query but uses text component."""
        from app.core.reranker.bge_reranker import BGERerankerService

        service = BGERerankerService()
        service.load_model()

        # Mock compute_score
        mock_flag_reranker.return_value.compute_score.return_value = [0.8]

        # Rerank with dict query (multimodal format)
        query = {"text": "test query", "image": "image_path.jpg"}
        documents = ["doc1"]
        results = service.rerank(query, documents, top_k=1)

        # Should extract text from dict
        # Verify compute_score was called with text
        call_args = mock_flag_reranker.return_value.compute_score.call_args
        pairs = call_args[0][0]  # First positional argument
        assert pairs[0][0] == "test query"  # Should use text from dict

    def test_bge_reranker_backward_compatible_get_service(self):
        """Test backward compatibility: get_reranker_service() function exists."""
        from app.core.reranker.bge_reranker import get_reranker_service

        # Should exist
        assert callable(get_reranker_service)

        # Should return BGERerankerService
        service = get_reranker_service()
        from app.core.reranker.bge_reranker import BGERerankerService
        assert isinstance(service, BGERerankerService)

    def test_bge_reranker_backward_compatible_singleton(self):
        """Test backward compatibility: get_reranker_service() returns singleton."""
        from app.core.reranker.bge_reranker import get_reranker_service

        # Get service twice
        service1 = get_reranker_service()
        service2 = get_reranker_service()

        # Should be same instance
        assert service1 is service2


class TestBGERerankerServiceIntegration:
    """Integration tests verifying identical behavior to old ReRankerService."""

    @patch('app.core.reranker.bge_reranker.FlagReranker')
    def test_bge_reranker_same_model_name_as_old_service(self, mock_flag_reranker):
        """Test that BGERerankerService uses same MODEL_NAME as old ReRankerService."""
        from app.core.reranker.bge_reranker import BGERerankerService

        service = BGERerankerService()
        service.load_model()

        # Should use BAAI/bge-reranker-large
        call_args = mock_flag_reranker.call_args
        model_name = call_args[0][0]  # First positional argument
        assert model_name == "BAAI/bge-reranker-large"

    @patch('app.core.reranker.bge_reranker.FlagReranker')
    def test_bge_reranker_fp16_on_cuda(self, mock_flag_reranker):
        """Test that BGERerankerService uses FP16 when device=cuda."""
        from app.core.reranker.bge_reranker import BGERerankerService

        service = BGERerankerService()
        
        # Mock CUDA detection
        service.device = "cuda"
        service.load_model()

        # Should pass use_fp16=True
        call_kwargs = mock_flag_reranker.call_args[1]
        assert call_kwargs.get("use_fp16") is True

    @patch('app.core.reranker.bge_reranker.FlagReranker')
    def test_bge_reranker_fp16_false_on_cpu(self, mock_flag_reranker):
        """Test that BGERerankerService uses FP16=False when device=cpu."""
        from app.core.reranker.bge_reranker import BGERerankerService

        service = BGERerankerService()
        
        # Mock CPU device
        service.device = "cpu"
        service.load_model()

        # Should pass use_fp16=False
        call_kwargs = mock_flag_reranker.call_args[1]
        assert call_kwargs.get("use_fp16") is False