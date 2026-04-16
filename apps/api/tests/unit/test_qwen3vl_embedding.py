"""Tests for Qwen3VLEmbeddingService adapter.

Tests verify:
- Implements BaseEmbeddingService interface
- Multimodal embedding (supports_multimodal() == True)
- 2048-dim embeddings
- Text, image, and table encoding
- Singleton pattern preserved
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from typing import List, Dict
from PIL import Image

from app.core.embedding.base import BaseEmbeddingService
from app.core.embedding.qwen3vl_embedding import Qwen3VLEmbeddingService


class TestQwen3VLEmbeddingServiceInterface:
    """Test interface compliance."""

    def test_qwen3vl_embedding_inherits_from_base(self):
        """Qwen3VLEmbeddingService should inherit from BaseEmbeddingService."""
        assert issubclass(Qwen3VLEmbeddingService, BaseEmbeddingService)

    @patch('app.core.embedding.qwen3vl_embedding.get_qwen3vl_service')
    def test_qwen3vl_embedding_is_not_abstract(self, mock_get_service):
        """Qwen3VLEmbeddingService should be concrete (can instantiate)."""
        # Mock underlying service
        mock_qwen = Mock()
        mock_get_service.return_value = mock_qwen
        
        # Should instantiate without error
        service = Qwen3VLEmbeddingService()
        assert service is not None
        assert isinstance(service, BaseEmbeddingService)

    @patch('app.core.embedding.qwen3vl_embedding.get_qwen3vl_service')
    def test_supports_multimodal_returns_true(self, mock_get_service):
        """Qwen3VLEmbeddingService should return True for supports_multimodal()."""
        mock_qwen = Mock()
        mock_get_service.return_value = mock_qwen
        
        service = Qwen3VLEmbeddingService()
        assert service.supports_multimodal() is True

    @patch('app.core.embedding.qwen3vl_embedding.get_qwen3vl_service')
    def test_get_model_info_returns_correct_format(self, mock_get_service):
        """get_model_info() should return dict with required keys."""
        mock_qwen = Mock()
        mock_get_service.return_value = mock_qwen
        
        service = Qwen3VLEmbeddingService()
        info = service.get_model_info()
        
        assert isinstance(info, dict)
        assert "name" in info
        assert "version" in info
        assert "type" in info
        assert "dimension" in info
        
        # Verify values
        assert "Qwen3-VL-Embedding" in info["name"]
        assert info["type"] == "multimodal"
        assert info["dimension"] == "2048"


class TestQwen3VLEmbeddingServiceTextEncoding:
    """Test text encoding functionality."""

    @patch('app.core.embedding.qwen3vl_embedding.get_qwen3vl_service')
    def test_encode_text_single_string(self, mock_get_service):
        """encode_text() should handle single string input."""
        # Mock underlying service
        mock_qwen = Mock()
        mock_qwen.encode_text.return_value = [0.1] * 2048
        mock_get_service.return_value = mock_qwen
        
        service = Qwen3VLEmbeddingService()
        result = service.encode_text("test text")
        
        # Should return 2048-dim vector
        assert isinstance(result, list)
        assert len(result) == 2048
        
        # Should call underlying service
        mock_qwen.encode_text.assert_called_once_with("test text")

    @patch('app.core.embedding.qwen3vl_embedding.get_qwen3vl_service')
    def test_encode_text_list_of_strings(self, mock_get_service):
        """encode_text() should handle batch input."""
        # Mock underlying service
        mock_qwen = Mock()
        mock_qwen.encode_text.return_value = [[0.1] * 2048, [0.2] * 2048]
        mock_get_service.return_value = mock_qwen
        
        service = Qwen3VLEmbeddingService()
        result = service.encode_text(["text1", "text2"])
        
        # Should return list of 2048-dim vectors
        assert isinstance(result, list)
        assert len(result) == 2
        assert all(len(vec) == 2048 for vec in result)
        
        # Should call underlying service
        mock_qwen.encode_text.assert_called_once_with(["text1", "text2"])

    @patch('app.core.embedding.qwen3vl_embedding.get_qwen3vl_service')
    def test_encode_text_empty_string(self, mock_get_service):
        """encode_text() should handle empty string."""
        # Mock underlying service
        mock_qwen = Mock()
        mock_qwen.encode_text.return_value = [0.0] * 2048
        mock_get_service.return_value = mock_qwen
        
        service = Qwen3VLEmbeddingService()
        result = service.encode_text("")
        
        # Should return zero vector
        assert isinstance(result, list)
        assert len(result) == 2048
        assert all(v == 0.0 for v in result)


class TestQwen3VLEmbeddingServiceImageEncoding:
    """Test image encoding functionality."""

    @patch('app.core.embedding.qwen3vl_embedding.get_qwen3vl_service')
    def test_encode_image_single_path(self, mock_get_service):
        """encode_image() should handle image path."""
        # Mock underlying service
        mock_qwen = Mock()
        mock_qwen.encode_image.return_value = [0.2] * 2048
        mock_get_service.return_value = mock_qwen
        
        service = Qwen3VLEmbeddingService()
        result = service.encode_image("test.jpg")
        
        # Should return 2048-dim vector
        assert isinstance(result, list)
        assert len(result) == 2048
        
        # Should call underlying service
        mock_qwen.encode_image.assert_called_once_with("test.jpg")

    @patch('app.core.embedding.qwen3vl_embedding.get_qwen3vl_service')
    def test_encode_image_pil_image(self, mock_get_service):
        """encode_image() should handle PIL.Image."""
        # Mock underlying service
        mock_qwen = Mock()
        mock_qwen.encode_image.return_value = [0.3] * 2048
        mock_get_service.return_value = mock_qwen
        
        service = Qwen3VLEmbeddingService()
        img = Image.new('RGB', (100, 100))
        result = service.encode_image(img)
        
        # Should return 2048-dim vector
        assert isinstance(result, list)
        assert len(result) == 2048

    @patch('app.core.embedding.qwen3vl_embedding.get_qwen3vl_service')
    def test_encode_image_list_of_images(self, mock_get_service):
        """encode_image() should handle batch of images."""
        # Mock underlying service
        mock_qwen = Mock()
        mock_qwen.encode_image.return_value = [[0.1] * 2048, [0.2] * 2048]
        mock_get_service.return_value = mock_qwen
        
        service = Qwen3VLEmbeddingService()
        img1 = Image.new('RGB', (100, 100))
        img2 = Image.new('RGB', (200, 200))
        result = service.encode_image([img1, img2])
        
        # Should return list of 2048-dim vectors
        assert isinstance(result, list)
        assert len(result) == 2
        assert all(len(vec) == 2048 for vec in result)


class TestQwen3VLEmbeddingServiceTableEncoding:
    """Test table encoding functionality."""

    @patch('app.core.embedding.qwen3vl_embedding.get_qwen3vl_service')
    def test_encode_table_basic(self, mock_get_service):
        """encode_table() should serialize and encode table."""
        # Mock underlying service
        mock_qwen = Mock()
        mock_qwen.encode_table.return_value = [0.4] * 2048
        mock_get_service.return_value = mock_qwen
        
        service = Qwen3VLEmbeddingService()
        result = service.encode_table(
            caption="Test Table",
            headers=["Col1", "Col2"],
            rows=[{"Col1": "Val1", "Col2": "Val2"}]
        )
        
        # Should return 2048-dim vector
        assert isinstance(result, list)
        assert len(result) == 2048
        
        # Should call underlying service
        mock_qwen.encode_table.assert_called_once()

    @patch('app.core.embedding.qwen3vl_embedding.get_qwen3vl_service')
    def test_encode_table_empty_parameters(self, mock_get_service):
        """encode_table() should handle empty parameters."""
        # Mock underlying service
        mock_qwen = Mock()
        mock_qwen.encode_table.return_value = [0.0] * 2048
        mock_get_service.return_value = mock_qwen
        
        service = Qwen3VLEmbeddingService()
        result = service.encode_table()
        
        # Should return zero vector
        assert isinstance(result, list)
        assert len(result) == 2048


class TestQwen3VLEmbeddingServiceLifecycle:
    """Test model lifecycle management."""

    @patch('app.core.embedding.qwen3vl_embedding.get_qwen3vl_service')
    def test_load_model_calls_underlying_service(self, mock_get_service):
        """load_model() should call underlying service."""
        # Mock underlying service
        mock_qwen = Mock()
        mock_qwen.load_model.return_value = None
        mock_get_service.return_value = mock_qwen
        
        service = Qwen3VLEmbeddingService()
        service.load_model()
        
        # Should call underlying service
        mock_qwen.load_model.assert_called_once()

    @patch('app.core.embedding.qwen3vl_embedding.get_qwen3vl_service')
    def test_is_loaded_checks_underlying_service(self, mock_get_service):
        """is_loaded() should check underlying service."""
        # Mock underlying service
        mock_qwen = Mock()
        mock_qwen.is_loaded.return_value = True
        mock_get_service.return_value = mock_qwen
        
        service = Qwen3VLEmbeddingService()
        result = service.is_loaded()
        
        # Should return True
        assert result is True
        
        # Should call underlying service
        mock_qwen.is_loaded.assert_called_once()


class TestQwen3VLEmbeddingServiceMultimodal:
    """Test multimodal capabilities."""

    @patch('app.core.embedding.qwen3vl_embedding.get_qwen3vl_service')
    def test_all_modalities_supported(self, mock_get_service):
        """Should support text, image, and table encoding."""
        # Mock underlying service
        mock_qwen = Mock()
        mock_qwen.encode_text.return_value = [0.1] * 2048
        mock_qwen.encode_image.return_value = [0.2] * 2048
        mock_qwen.encode_table.return_value = [0.3] * 2048
        mock_get_service.return_value = mock_qwen
        
        service = Qwen3VLEmbeddingService()
        
        # Text
        text_emb = service.encode_text("query")
        assert len(text_emb) == 2048
        
        # Image
        img_emb = service.encode_image("test.jpg")
        assert len(img_emb) == 2048
        
        # Table
        table_emb = service.encode_table(
            caption="Data",
            headers=["A", "B"],
            rows=[{"A": "1", "B": "2"}]
        )
        assert len(table_emb) == 2048

    @patch('app.core.embedding.qwen3vl_embedding.get_qwen3vl_service')
    def test_2048_dim_consistency(self, mock_get_service):
        """All encodings should return 2048-dim vectors."""
        # Mock underlying service
        mock_qwen = Mock()
        mock_qwen.encode_text.return_value = [0.5] * 2048
        mock_qwen.encode_image.return_value = [0.6] * 2048
        mock_qwen.encode_table.return_value = [0.7] * 2048
        mock_get_service.return_value = mock_qwen
        
        service = Qwen3VLEmbeddingService()
        
        # All should be 2048-dim
        assert len(service.encode_text("test")) == 2048
        assert len(service.encode_image("img.jpg")) == 2048
        assert len(service.encode_table("T", [], [])) == 2048


class TestQwen3VLEmbeddingServiceIntegration:
    """Integration tests with real (mocked) underlying service."""

    @patch('app.core.qwen3vl_service.Qwen3VLMultimodalEmbedding')
    def test_full_workflow(self, mock_qwen_class):
        """Test complete workflow: load → encode all modalities."""
        # Create mock instance
        mock_instance = MagicMock()
        mock_instance.encode_text.return_value = [0.8] * 2048
        mock_instance.encode_image.return_value = [0.9] * 2048
        mock_instance.encode_table.return_value = [1.0] * 2048
        mock_instance.is_loaded.return_value = True
        mock_qwen_class.return_value = mock_instance
        
        with patch('app.core.embedding.qwen3vl_embedding.get_qwen3vl_service', return_value=mock_instance):
            service = Qwen3VLEmbeddingService()
            
            # Load model
            service.load_model()
            
            # Check loaded
            assert service.is_loaded() is True
            
            # Encode text
            text_embedding = service.encode_text("search query")
            assert len(text_embedding) == 2048
            
            # Encode image
            image_embedding = service.encode_image("image.png")
            assert len(image_embedding) == 2048
            
            # Encode table
            table_embedding = service.encode_table(
                caption="Results",
                headers=["Metric", "Value"],
                rows=[{"Metric": "Accuracy", "Value": "95%"}]
            )
            assert len(table_embedding) == 2048
            
            # Verify model info
            info = service.get_model_info()
            assert info["dimension"] == "2048"
            assert info["type"] == "multimodal"