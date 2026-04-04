"""Tests for EmbeddingServiceFactory.

Tests verify:
- Factory creates correct service based on configuration
- Singleton caching works correctly
- ValueError raised for unknown model types
- Default model selection
- Configuration via environment variables
"""

import pytest
from unittest.mock import Mock, patch
from typing import Dict

from app.core.embedding.base import BaseEmbeddingService
from app.core.embedding.bge_embedding import BGEEmbeddingService
from app.core.embedding.qwen3vl_embedding import Qwen3VLEmbeddingService
from app.core.embedding.factory import EmbeddingServiceFactory, get_embedding_service


class TestEmbeddingServiceFactoryCreation:
    """Test factory creation logic."""

    def teardown_method(self):
        """Clear factory cache after each test."""
        EmbeddingServiceFactory.clear_cache()

    @patch('app.core.embedding.factory.settings')
    def test_create_bge_service_by_default(self, mock_settings):
        """Factory should create BGEEmbeddingService by default."""
        # Configure to use BGE-M3
        mock_settings.EMBEDDING_MODEL = "bge-m3"
        mock_settings.EMBEDDING_QUANTIZATION = "fp16"
        
        with patch('app.core.embedding.bge_embedding.get_bge_m3_service') as mock_get:
            mock_bge = Mock()
            mock_get.return_value = mock_bge
            
            service = EmbeddingServiceFactory.create()
            
            assert isinstance(service, BGEEmbeddingService)
            assert isinstance(service, BaseEmbeddingService)

    @patch('app.core.embedding.factory.settings')
    def test_create_qwen3vl_service_when_configured(self, mock_settings):
        """Factory should create Qwen3VLEmbeddingService when configured."""
        # Configure to use Qwen3-VL
        mock_settings.EMBEDDING_MODEL = "qwen3-vl-2b"
        mock_settings.EMBEDDING_QUANTIZATION = "int4"
        
        with patch('app.core.embedding.qwen3vl_embedding.get_qwen3vl_service') as mock_get:
            mock_qwen = Mock()
            mock_get.return_value = mock_qwen
            
            service = EmbeddingServiceFactory.create()
            
            assert isinstance(service, Qwen3VLEmbeddingService)
            assert isinstance(service, BaseEmbeddingService)

    @patch('app.core.embedding.factory.settings')
    def test_raises_valueerror_for_unknown_model(self, mock_settings):
        """Factory should raise ValueError for unknown model type."""
        # Configure with unknown model
        mock_settings.EMBEDDING_MODEL = "unknown-model"
        mock_settings.EMBEDDING_QUANTIZATION = "fp16"
        
        with pytest.raises(ValueError) as exc_info:
            EmbeddingServiceFactory.create()
        
        # Error should mention unknown model
        assert "unknown" in str(exc_info.value).lower()
        assert "unknown-model" in str(exc_info.value)


class TestEmbeddingServiceFactoryCaching:
    """Test singleton caching behavior."""

    def teardown_method(self):
        """Clear factory cache after each test."""
        EmbeddingServiceFactory.clear_cache()

    @patch('app.core.embedding.factory.settings')
    def test_caches_instances_by_model_type(self, mock_settings):
        """Factory should cache instances by model type."""
        mock_settings.EMBEDDING_MODEL = "bge-m3"
        mock_settings.EMBEDDING_QUANTIZATION = "fp16"
        
        with patch('app.core.embedding.bge_embedding.get_bge_m3_service') as mock_get:
            mock_bge = Mock()
            mock_get.return_value = mock_bge
            
            # Create twice
            service1 = EmbeddingServiceFactory.create()
            service2 = EmbeddingServiceFactory.create()
            
            # Should be same instance (cached)
            assert service1 is service2
            
            # Should call underlying get only once
            mock_get.assert_called_once()

    @patch('app.core.embedding.factory.settings')
    def test_different_models_different_instances(self, mock_settings):
        """Different model types should create different instances."""
        # Create BGE service
        mock_settings.EMBEDDING_MODEL = "bge-m3"
        mock_settings.EMBEDDING_QUANTIZATION = "fp16"
        
        with patch('app.core.embedding.bge_embedding.get_bge_m3_service') as mock_get_bge:
            mock_bge = Mock()
            mock_get_bge.return_value = mock_bge
            
            bge_service = EmbeddingServiceFactory.create()
        
        # Create Qwen3VL service
        mock_settings.EMBEDDING_MODEL = "qwen3-vl-2b"
        
        with patch('app.core.embedding.qwen3vl_embedding.get_qwen3vl_service') as mock_get_qwen:
            mock_qwen = Mock()
            mock_get_qwen.return_value = mock_qwen
            
            qwen_service = EmbeddingServiceFactory.create()
        
        # Should be different instances
        assert bge_service is not qwen_service
        assert isinstance(bge_service, BGEEmbeddingService)
        assert isinstance(qwen_service, Qwen3VLEmbeddingService)

    def test_clear_cache_removes_all_instances(self):
        """clear_cache() should remove all cached instances."""
        # Add some instances to cache
        EmbeddingServiceFactory._instances = {
            "bge-m3:auto:fp16": Mock(),
            "qwen3-vl-2b:auto:int4": Mock()
        }
        
        # Clear cache
        EmbeddingServiceFactory.clear_cache()
        
        # Should be empty
        assert len(EmbeddingServiceFactory._instances) == 0


class TestEmbeddingServiceFactoryConfiguration:
    """Test configuration handling."""

    def teardown_method(self):
        """Clear factory cache after each test."""
        EmbeddingServiceFactory.clear_cache()

    @patch('app.core.embedding.factory.settings')
    def test_uses_embedding_model_config(self, mock_settings):
        """Factory should use EMBEDDING_MODEL from configuration."""
        mock_settings.EMBEDDING_MODEL = "qwen3-vl-2b"
        mock_settings.EMBEDDING_QUANTIZATION = "int4"
        
        with patch('app.core.embedding.qwen3vl_embedding.get_qwen3vl_service') as mock_get:
            mock_qwen = Mock()
            mock_get.return_value = mock_qwen
            
            service = EmbeddingServiceFactory.create()
            
            # Should create Qwen3VL service
            assert isinstance(service, Qwen3VLEmbeddingService)

    @patch('app.core.embedding.factory.settings')
    def test_uses_quantization_config(self, mock_settings):
        """Factory should pass quantization to Qwen3VL service."""
        mock_settings.EMBEDDING_MODEL = "qwen3-vl-2b"
        mock_settings.EMBEDDING_QUANTIZATION = "fp16"
        
        with patch('app.core.embedding.qwen3vl_embedding.get_qwen3vl_service') as mock_get:
            mock_qwen = Mock()
            mock_get.return_value = mock_qwen
            
            service = EmbeddingServiceFactory.create()
            
            # Should create Qwen3VLEmbeddingService with quantization
            assert isinstance(service, Qwen3VLEmbeddingService)
            assert service.quantization == "fp16"


class TestGetEmbeddingServiceFunction:
    """Test backward compatible get_embedding_service() function."""

    def teardown_method(self):
        """Clear factory cache after each test."""
        EmbeddingServiceFactory.clear_cache()

    @patch('app.core.embedding.factory.settings')
    def test_returns_factory_created_service(self, mock_settings):
        """get_embedding_service() should return service from factory."""
        mock_settings.EMBEDDING_MODEL = "bge-m3"
        mock_settings.EMBEDDING_QUANTIZATION = "fp16"
        
        with patch('app.core.embedding.bge_embedding.get_bge_m3_service') as mock_get:
            mock_bge = Mock()
            mock_get.return_value = mock_bge
            
            service = get_embedding_service()
            
            # Should return BGEEmbeddingService
            assert isinstance(service, BGEEmbeddingService)

    @patch('app.core.embedding.factory.settings')
    def test_is_backward_compatible(self, mock_settings):
        """Function should work like old API (backward compatibility)."""
        mock_settings.EMBEDDING_MODEL = "qwen3-vl-2b"
        mock_settings.EMBEDDING_QUANTIZATION = "int4"
        
        with patch('app.core.embedding.qwen3vl_embedding.get_qwen3vl_service') as mock_get:
            mock_qwen = Mock()
            mock_get.return_value = mock_qwen
            
            # Old API: just call get_embedding_service()
            service = get_embedding_service()
            
            # Should work without error
            assert service is not None
            assert isinstance(service, BaseEmbeddingService)


class TestEmbeddingServiceFactoryEdgeCases:
    """Test edge cases and error handling."""

    def teardown_method(self):
        """Clear factory cache after each test."""
        EmbeddingServiceFactory.clear_cache()

    @patch('app.core.embedding.factory.settings')
    def test_handles_empty_model_name(self, mock_settings):
        """Factory should handle empty model name."""
        mock_settings.EMBEDDING_MODEL = ""
        mock_settings.EMBEDDING_QUANTIZATION = "fp16"
        
        with pytest.raises(ValueError):
            EmbeddingServiceFactory.create()

    @patch('app.core.embedding.factory.settings')
    def test_case_sensitive_model_names(self, mock_settings):
        """Model names should be case-sensitive."""
        mock_settings.EMBEDDING_MODEL = "BGE-M3"  # Wrong case
        mock_settings.EMBEDDING_QUANTIZATION = "fp16"
        
        with pytest.raises(ValueError):
            EmbeddingServiceFactory.create()

    @patch('app.core.embedding.factory.settings')
    def test_cache_key_includes_all_params(self, mock_settings):
        """Cache key should include model type, device, and quantization."""
        mock_settings.EMBEDDING_MODEL = "bge-m3"
        mock_settings.EMBEDDING_QUANTIZATION = "fp16"
        
        with patch('app.core.embedding.bge_embedding.get_bge_m3_service') as mock_get:
            mock_bge = Mock()
            mock_get.return_value = mock_bge
            
            # Create service
            EmbeddingServiceFactory.create()
            
            # Check cache has entry with expected key format
            assert len(EmbeddingServiceFactory._instances) == 1
            cache_key = list(EmbeddingServiceFactory._instances.keys())[0]
            assert "bge-m3" in cache_key
            assert "fp16" in cache_key


class TestEmbeddingServiceFactorySupportedModels:
    """Test all supported model types."""

    def teardown_method(self):
        """Clear factory cache after each test."""
        EmbeddingServiceFactory.clear_cache()

    @patch('app.core.embedding.factory.settings')
    def test_supports_bge_m3(self, mock_settings):
        """Factory should support BGE-M3 model."""
        mock_settings.EMBEDDING_MODEL = "bge-m3"
        mock_settings.EMBEDDING_QUANTIZATION = "fp16"
        
        with patch('app.core.embedding.bge_embedding.get_bge_m3_service') as mock_get:
            mock_bge = Mock()
            mock_get.return_value = mock_bge
            
            service = EmbeddingServiceFactory.create()
            
            assert isinstance(service, BGEEmbeddingService)
            assert service.supports_multimodal() is False

    @patch('app.core.embedding.factory.settings')
    def test_supports_qwen3_vl_2b(self, mock_settings):
        """Factory should support Qwen3-VL-2B model."""
        mock_settings.EMBEDDING_MODEL = "qwen3-vl-2b"
        mock_settings.EMBEDDING_QUANTIZATION = "int4"
        
        with patch('app.core.embedding.qwen3vl_embedding.get_qwen3vl_service') as mock_get:
            mock_qwen = Mock()
            mock_get.return_value = mock_qwen
            
            service = EmbeddingServiceFactory.create()
            
            assert isinstance(service, Qwen3VLEmbeddingService)
            assert service.supports_multimodal() is True

    @patch('app.core.embedding.factory.settings')
    def test_model_info_reflects_actual_model(self, mock_settings):
        """Created service should return correct model info."""
        mock_settings.EMBEDDING_MODEL = "qwen3-vl-2b"
        mock_settings.EMBEDDING_QUANTIZATION = "int4"
        
        with patch('app.core.embedding.qwen3vl_embedding.get_qwen3vl_service') as mock_get:
            mock_qwen = Mock()
            mock_get.return_value = mock_qwen
            
            service = EmbeddingServiceFactory.create()
            info = service.get_model_info()
            
            # Should match Qwen3-VL
            assert "Qwen3-VL" in info["name"]
            assert info["type"] == "multimodal"
            assert info["dimension"] == "2048"