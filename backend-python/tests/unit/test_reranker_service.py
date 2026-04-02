"""Tests for ReRanker service.

Tests cover:
- Model loading
- Reranking functionality
- Singleton pattern
- FP16 mode when CUDA available
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from app.core.reranker_service import (
    ReRankerService,
    get_reranker_service,
)


class TestReRankerService:
    """Test ReRankerService class."""

    def test_init(self):
        """Test service initialization."""
        service = ReRankerService()
        assert service.MODEL_NAME == "BAAI/bge-reranker-large"
        assert not service._initialized
        assert service.device in ["cuda", "cpu"]

    @patch("app.core.reranker_service.FlagReranker")
    def test_load_model(self, mock_reranker_class):
        """Test 1: load_model() initializes FlagReranker with BAAI/bge-reranker-large."""
        # Setup mocks
        mock_model = MagicMock()
        mock_reranker_class.return_value = mock_model

        service = ReRankerService()
        service.load_model()

        # Verify model was loaded with correct name
        assert service._initialized
        assert service.model == mock_model
        mock_reranker_class.assert_called_once_with(
            "BAAI/bge-reranker-large",
            use_fp16=False  # CPU mode by default in test
        )

    @patch("app.core.reranker_service.FlagReranker")
    def test_load_model_already_loaded(self, mock_reranker_class):
        """Test model loading when already loaded."""
        service = ReRankerService()

        # Load once
        service.load_model()
        assert service._initialized

        # Clear mock call counts
        mock_reranker_class.reset_mock()

        # Load again - should not call constructor
        service.load_model()
        mock_reranker_class.assert_not_called()

    @patch("app.core.reranker_service.FlagReranker")
    def test_rerank_not_loaded_raises_error(self, mock_reranker_class):
        """Test reranking when model not loaded raises error."""
        service = ReRankerService()

        with pytest.raises(RuntimeError, match="Model not loaded"):
            service.rerank("test query", ["doc1", "doc2"])

    @patch("app.core.reranker_service.FlagReranker")
    def test_rerank_basic(self, mock_reranker_class):
        """Test 2: rerank() returns List[Tuple[str, float]] sorted by score descending."""
        # Setup mock
        mock_model = MagicMock()
        mock_reranker_class.return_value = mock_model

        # Mock compute_score return value - returns list of scores
        mock_model.compute_score.return_value = [0.9, 0.3, 0.7]

        service = ReRankerService()
        service.load_model()

        query = "test query"
        documents = ["doc1", "doc2", "doc3"]
        result = service.rerank(query, documents, top_k=10)

        # Should return sorted by score descending
        assert isinstance(result, list)
        assert len(result) == 3
        assert result[0][0] == "doc1"  # score 0.9
        assert result[0][1] == 0.9
        assert result[1][0] == "doc3"  # score 0.7
        assert result[1][1] == 0.7
        assert result[2][0] == "doc2"  # score 0.3
        assert result[2][1] == 0.3

    @patch("app.core.reranker_service.FlagReranker")
    def test_rerank_top_k(self, mock_reranker_class):
        """Test rerank respects top_k parameter."""
        # Setup mock
        mock_model = MagicMock()
        mock_reranker_class.return_value = mock_model

        # Mock compute_score return value
        mock_model.compute_score.return_value = [0.9, 0.8, 0.7, 0.6, 0.5]

        service = ReRankerService()
        service.load_model()

        query = "test query"
        documents = ["doc1", "doc2", "doc3", "doc4", "doc5"]
        result = service.rerank(query, documents, top_k=2)

        # Should return only top 2
        assert len(result) == 2
        assert result[0][0] == "doc1"
        assert result[1][0] == "doc2"

    def test_singleton(self):
        """Test 3: Singleton get_reranker_service() returns same instance."""
        # Reset singleton for test
        import app.core.reranker_service
        app.core.reranker_service._reranker_service = None

        service1 = get_reranker_service()
        service2 = get_reranker_service()
        assert service1 is service2

    @patch("app.core.reranker_service.FlagReranker")
    @patch("torch.cuda.is_available")
    def test_fp16_mode_cuda(self, mock_cuda_available, mock_reranker_class):
        """Test 4: FP16 mode enabled when CUDA available."""
        # Mock CUDA available
        mock_cuda_available.return_value = True

        mock_model = MagicMock()
        mock_reranker_class.return_value = mock_model

        # Reset singleton and create new instance
        import app.core.reranker_service
        app.core.reranker_service._reranker_service = None

        service = get_reranker_service()
        service.load_model()

        # Verify FP16 was enabled
        assert service.device == "cuda"
        mock_reranker_class.assert_called_once_with(
            "BAAI/bge-reranker-large",
            use_fp16=True
        )

    @patch("app.core.reranker_service.FlagReranker")
    @patch("torch.cuda.is_available")
    def test_fp16_mode_cpu(self, mock_cuda_available, mock_reranker_class):
        """Test FP16 mode disabled when CUDA not available."""
        # Mock CUDA not available
        mock_cuda_available.return_value = False

        mock_model = MagicMock()
        mock_reranker_class.return_value = mock_model

        # Reset singleton and create new instance
        import app.core.reranker_service
        app.core.reranker_service._reranker_service = None

        service = get_reranker_service()
        service.load_model()

        # Verify FP16 was disabled
        assert service.device == "cpu"
        mock_reranker_class.assert_called_once_with(
            "BAAI/bge-reranker-large",
            use_fp16=False
        )