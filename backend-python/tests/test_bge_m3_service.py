"""Tests for BGE-M3 unified embedding service.

Tests cover:
- Text encoding (single and batch)
- Table encoding
- Singleton pattern
- Empty text handling
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from app.core.bge_m3_service import (
    BGEM3Service,
    get_bge_m3_service,
    create_bge_m3_service,
)


class TestBGEM3Service:
    """Test BGEM3Service class."""

    def test_init(self):
        """Test service initialization."""
        service = BGEM3Service()
        assert service.MODEL_NAME == "BAAI/bge-m3"
        assert service.EMBEDDING_DIM == 1024
        assert service.MAX_SEQ_LENGTH == 8192
        assert not service.is_loaded()
        assert service.device in ["cuda", "cpu"]

    def test_get_embedding_dim(self):
        """Test getting embedding dimension."""
        service = BGEM3Service()
        assert service.get_embedding_dim() == 1024

    def test_get_device(self):
        """Test getting device."""
        service = BGEM3Service()
        assert service.get_device() in ["cuda", "cpu"]

    @patch("app.core.bge_m3_service.BGEM3FlagModel")
    def test_load_model(self, mock_model_class):
        """Test model loading."""
        # Setup mocks
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model

        service = BGEM3Service()
        service.load_model()

        # Verify model was loaded
        assert service.is_loaded()
        assert service.model == mock_model

    @patch("app.core.bge_m3_service.BGEM3FlagModel")
    def test_load_model_already_loaded(self, mock_model_class):
        """Test model loading when already loaded."""
        service = BGEM3Service()

        # Load once
        service.load_model()
        assert service.is_loaded()

        # Clear mock call counts
        mock_model_class.reset_mock()

        # Load again - should not call constructor
        service.load_model()
        mock_model_class.assert_not_called()

    @patch("app.core.bge_m3_service.BGEM3FlagModel")
    def test_encode_text_not_loaded(self, mock_model_class):
        """Test encoding when model not loaded raises error."""
        service = BGEM3Service()

        with pytest.raises(RuntimeError, match="Model not loaded"):
            service.encode_text("test query")

    @patch("app.core.bge_m3_service.BGEM3FlagModel")
    def test_encode_text_returns_1024_dim(self, mock_model_class):
        """Test 1: encode_text returns list of 1024 floats."""
        # Setup mock
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model

        # Mock encode return value - BGEM3FlagModel returns dict with 'dense_vecs'
        import numpy as np
        mock_model.encode.return_value = {"dense_vecs": np.array([[0.1] * 1024, [0.2] * 1024])}

        service = BGEM3Service()
        service.load_model()
        result = service.encode_text("test query")

        # Should return 1024-dim vector
        assert isinstance(result, list)
        assert len(result) == 1024

    @patch("app.core.bge_m3_service.BGEM3FlagModel")
    def test_encode_text_batch_returns_multiple(self, mock_model_class):
        """Test 2: encode_text with batch returns list of lists, each 1024-dim."""
        # Setup mock
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model

        # Mock encode return value - BGEM3FlagModel returns dict with 'dense_vecs'
        import numpy as np
        mock_model.encode.return_value = {"dense_vecs": np.array([[0.1] * 1024, [0.2] * 1024, [0.3] * 1024])}

        service = BGEM3Service()
        service.load_model()
        texts = ["text 1", "text 2", "text 3"]
        result = service.encode_text(texts)

        # Should return list of 1024-dim vectors
        assert isinstance(result, list)
        assert len(result) == 3
        for embedding in result:
            assert len(embedding) == 1024

    @patch("app.core.bge_m3_service.BGEM3FlagModel")
    def test_encode_table_returns_1024_dim(self, mock_model_class):
        """Test 3: encode_table returns 1024-dim vector."""
        # Setup mock
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model

        # Mock encode return value - BGEM3FlagModel returns dict with 'dense_vecs'
        import numpy as np
        mock_model.encode.return_value = {"dense_vecs": np.array([[0.1] * 1024])}

        service = BGEM3Service()
        service.load_model()

        result = service.encode_table(
            caption="Table 1: Results",
            description="Performance metrics",
            headers=["Model", "Accuracy", "F1"],
            sample_rows=[
                {"Model": "BERT", "Accuracy": "0.95", "F1": "0.94"},
                {"Model": "GPT", "Accuracy": "0.97", "F1": "0.96"},
            ],
        )

        # Should return 1024-dim vector
        assert isinstance(result, list)
        assert len(result) == 1024

    def test_serialize_table_format(self):
        """Test table serialization format."""
        service = BGEM3Service()

        text = service._serialize_table(
            caption="Table 1: Results",
            description="Performance metrics",
            headers=["Model", "Accuracy"],
            sample_rows=[{"Model": "BERT", "Accuracy": "0.95"}],
        )

        assert "Table: Table 1: Results" in text
        assert "Description: Performance metrics" in text
        assert "Columns: Model, Accuracy" in text
        assert "Sample data:" in text

    def test_serialize_table_truncate_rows(self):
        """Test table serialization truncates to max 3 rows."""
        service = BGEM3Service()

        text = service._serialize_table(
            caption="Test Table",
            description="Test",
            headers=["Col"],
            sample_rows=[
                {"Col": "row1"},
                {"Col": "row2"},
                {"Col": "row3"},
                {"Col": "row4"},
                {"Col": "row5"},
            ],
        )

        # Should only include first 3 rows
        assert "row1" in text
        assert "row2" in text
        assert "row3" in text
        assert "row4" not in text  # Row 4 should be truncated
        assert "row5" not in text  # Row 5 should be truncated

    @patch("app.core.bge_m3_service.BGEM3FlagModel")
    def test_empty_text_returns_zero_vector(self, mock_model_class):
        """Test 5: Empty text returns zero vector of 1024 dims."""
        # Setup mock
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model

        # Mock encode return value - empty text should return zero vector directly
        # The implementation returns zero vector without calling encode for empty strings
        import numpy as np
        mock_model.encode.return_value = {"dense_vecs": np.array([[0.1] * 1024])}

        service = BGEM3Service()
        service.load_model()

        # Empty string should return zero vector
        result = service.encode_text("")

        assert isinstance(result, list)
        assert len(result) == 1024
        assert all(x == 0.0 for x in result)

    def test_singleton(self):
        """Test 4: Service loads model only once (singleton pattern)."""
        service1 = get_bge_m3_service()
        service2 = get_bge_m3_service()
        assert service1 is service2

    @pytest.mark.asyncio
    @patch("app.core.bge_m3_service.get_bge_m3_service")
    async def test_create_bge_m3_service(self, mock_get_service):
        """Test async service creation."""
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service

        service = await create_bge_m3_service()

        assert service == mock_service
        mock_service.load_model.assert_called_once()
