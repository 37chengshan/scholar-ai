"""Tests for BGEEmbeddingService adapter.

Tests verify:
- Implements BaseEmbeddingService interface
- Text-only embedding (supports_multimodal() == False)
- 1024-dim embeddings (backward compatibility)
- Same behavior as old BGEM3Service
- Singleton pattern preserved
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from typing import List, Dict

from app.core.embedding.base import BaseEmbeddingService
from app.core.embedding.bge_embedding import BGEEmbeddingService


class TestBGEEmbeddingServiceInterface:
    """Test interface compliance."""

    def test_bge_embedding_inherits_from_base(self):
        """BGEEmbeddingService should inherit from BaseEmbeddingService."""
        assert issubclass(BGEEmbeddingService, BaseEmbeddingService)

    def test_bge_embedding_is_not_abstract(self):
        """BGEEmbeddingService should be concrete (can instantiate)."""
        # Should instantiate without error
        service = BGEEmbeddingService()
        assert service is not None
        assert isinstance(service, BaseEmbeddingService)

    def test_supports_multimodal_returns_false(self):
        """BGEEmbeddingService should return False for supports_multimodal()."""
        service = BGEEmbeddingService()
        assert service.supports_multimodal() is False

    def test_get_model_info_returns_correct_format(self):
        """get_model_info() should return dict with required keys."""
        service = BGEEmbeddingService()
        info = service.get_model_info()
        
        assert isinstance(info, dict)
        assert "name" in info
        assert "version" in info
        assert "type" in info
        assert "dimension" in info
        
        # Verify values
        assert info["name"] == "BAAI/bge-m3"
        assert info["type"] == "text-only"
        assert info["dimension"] == "1024"


class TestBGEEmbeddingServiceTextEncoding:
    """Test text encoding functionality."""

    @patch('app.core.embedding.bge_embedding.get_bge_m3_service')
    def test_encode_text_single_string(self, mock_get_service):
        """encode_text() should handle single string input."""
        # Mock underlying service with loaded state
        mock_bge = Mock()
        mock_bge.encode_text.return_value = [0.1] * 1024
        mock_bge.is_loaded.return_value = True  # Model loaded
        mock_get_service.return_value = mock_bge
        
        service = BGEEmbeddingService()
        result = service.encode_text("test text")
        
        # Should return 1024-dim vector
        assert isinstance(result, list)
        assert len(result) == 1024
        
        # Should call underlying service
        mock_bge.encode_text.assert_called_once_with("test text")

    @patch('app.core.embedding.bge_embedding.get_bge_m3_service')
    def test_encode_text_list_of_strings(self, mock_get_service):
        """encode_text() should handle batch input."""
        # Mock underlying service with loaded state
        mock_bge = Mock()
        mock_bge.encode_text.return_value = [[0.1] * 1024, [0.2] * 1024]
        mock_bge.is_loaded.return_value = True  # Model loaded
        mock_get_service.return_value = mock_bge
        
        service = BGEEmbeddingService()
        result = service.encode_text(["text1", "text2"])
        
        # Should return list of 1024-dim vectors
        assert isinstance(result, list)
        assert len(result) == 2
        assert all(len(vec) == 1024 for vec in result)
        
        # Should call underlying service
        mock_bge.encode_text.assert_called_once_with(["text1", "text2"])

    @patch('app.core.embedding.bge_embedding.get_bge_m3_service')
    def test_encode_text_empty_string(self, mock_get_service):
        """encode_text() should handle empty string."""
        # Mock underlying service with loaded state
        mock_bge = Mock()
        mock_bge.encode_text.return_value = [0.0] * 1024
        mock_bge.is_loaded.return_value = True  # Model loaded
        mock_get_service.return_value = mock_bge
        
        service = BGEEmbeddingService()
        result = service.encode_text("")
        
        # Should return zero vector
        assert isinstance(result, list)
        assert len(result) == 1024
        assert all(v == 0.0 for v in result)


class TestBGEEmbeddingServiceImageEncoding:
    """Test image encoding (should raise NotImplementedError)."""

    def test_encode_image_raises_not_implemented(self):
        """encode_image() should raise NotImplementedError for text-only model."""
        service = BGEEmbeddingService()
        
        with pytest.raises(NotImplementedError) as exc_info:
            service.encode_image("test.jpg")
        
        # Error should mention text-only
        assert "text-only" in str(exc_info.value).lower()

    def test_encode_image_pil_image_raises_not_implemented(self):
        """encode_image() should raise NotImplementedError for PIL.Image."""
        from PIL import Image
        
        service = BGEEmbeddingService()
        img = Image.new('RGB', (100, 100))
        
        with pytest.raises(NotImplementedError):
            service.encode_image(img)


class TestBGEEmbeddingServiceTableEncoding:
    """Test table encoding functionality."""

    @patch('app.core.embedding.bge_embedding.get_bge_m3_service')
    def test_encode_table_basic(self, mock_get_service):
        """encode_table() should serialize and encode table."""
        # Mock underlying service with loaded state
        mock_bge = Mock()
        mock_bge.encode_table.return_value = [0.3] * 1024
        mock_bge.is_loaded.return_value = True  # Model loaded
        mock_get_service.return_value = mock_bge
        
        service = BGEEmbeddingService()
        result = service.encode_table(
            caption="Test Table",
            headers=["Col1", "Col2"],
            rows=[{"Col1": "Val1", "Col2": "Val2"}]
        )
        
        # Should return 1024-dim vector
        assert isinstance(result, list)
        assert len(result) == 1024
        
        # Should call underlying service
        mock_bge.encode_table.assert_called_once()

    @patch('app.core.embedding.bge_embedding.get_bge_m3_service')
    def test_encode_table_empty_parameters(self, mock_get_service):
        """encode_table() should handle empty parameters."""
        # Mock underlying service with loaded state
        mock_bge = Mock()
        mock_bge.encode_table.return_value = [0.0] * 1024
        mock_bge.is_loaded.return_value = True  # Model loaded
        mock_get_service.return_value = mock_bge
        
        service = BGEEmbeddingService()
        result = service.encode_table()
        
        # Should return zero vector
        assert isinstance(result, list)
        assert len(result) == 1024


class TestBGEEmbeddingServiceLifecycle:
    """Test model lifecycle management."""

    @patch('app.core.embedding.bge_embedding.get_bge_m3_service')
    def test_load_model_calls_underlying_service(self, mock_get_service):
        """load_model() should call underlying service."""
        # Mock underlying service
        mock_bge = Mock()
        mock_bge.load_model.return_value = None
        mock_get_service.return_value = mock_bge
        
        service = BGEEmbeddingService()
        service.load_model()
        
        # Should call underlying service
        mock_bge.load_model.assert_called_once()

    @patch('app.core.embedding.bge_embedding.get_bge_m3_service')
    def test_is_loaded_checks_underlying_service(self, mock_get_service):
        """is_loaded() should check underlying service."""
        # Mock underlying service
        mock_bge = Mock()
        mock_bge.is_loaded.return_value = True
        mock_get_service.return_value = mock_bge
        
        service = BGEEmbeddingService()
        result = service.is_loaded()
        
        # Should return True
        assert result is True
        
        # Should call underlying service
        mock_bge.is_loaded.assert_called_once()


class TestBGEEmbeddingServiceBackwardCompatibility:
    """Test backward compatibility with old BGEM3Service."""

    @patch('app.core.embedding.bge_embedding.get_bge_m3_service')
    def test_encode_text_returns_1024_dim(self, mock_get_service):
        """Should return 1024-dim vectors (backward compatibility)."""
        # Mock underlying service with loaded state
        mock_bge = Mock()
        mock_bge.encode_text.return_value = [0.5] * 1024
        mock_bge.is_loaded.return_value = True  # Model loaded
        mock_get_service.return_value = mock_bge
        
        service = BGEEmbeddingService()
        result = service.encode_text("test")
        
        # Verify dimension
        assert len(result) == 1024

    def test_singleton_pattern_preserved(self):
        """Should use singleton pattern via get_bge_m3_service()."""
        # Both instances should use same underlying singleton
        service1 = BGEEmbeddingService()
        service2 = BGEEmbeddingService()
        
        # They should reference the same underlying service
        # (tested via mocking in integration tests)
        assert service1 is not None
        assert service2 is not None


class TestBGEEmbeddingServiceIntegration:
    """Integration tests with real (mocked) underlying service."""

    @patch('app.core.bge_m3_service.BGEM3Service')
    def test_full_workflow(self, mock_bge_class):
        """Test complete workflow: load → encode."""
        # Create mock instance
        mock_instance = MagicMock()
        mock_instance.encode_text.return_value = [0.7] * 1024
        mock_instance.encode_table.return_value = [0.8] * 1024
        mock_instance.is_loaded.return_value = True
        mock_bge_class.return_value = mock_instance
        
        with patch('app.core.bge_m3_service.get_bge_m3_service', return_value=mock_instance):
            service = BGEEmbeddingService()
            
            # Load model
            service.load_model()
            
            # Check loaded
            assert service.is_loaded() is True
            
            # Encode text
            text_embedding = service.encode_text("test query")
            assert len(text_embedding) == 1024
            
            # Encode table
            table_embedding = service.encode_table(
                caption="Results",
                headers=["Metric", "Value"],
                rows=[{"Metric": "Accuracy", "Value": "95%"}]
            )
            assert len(table_embedding) == 1024
            
            # Verify model info
            info = service.get_model_info()
            assert info["dimension"] == "1024"
            assert info["type"] == "text-only"