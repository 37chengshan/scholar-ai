"""Tests for RerankerServiceFactory.

Tests verify:
- Factory creates BGERerankerService by default
- Factory creates Qwen3VLRerankerService when configured
- Factory caches instances (singleton per model type)
- Factory raises ValueError for unknown model type
- Backward compatible get_reranker_service() function
"""

import pytest
from unittest.mock import Mock, patch
import os


class TestRerankerServiceFactory:
    """Tests for RerankerServiceFactory."""

    def test_factory_creates_bge_reranker_by_default(self):
        """Test that Factory creates BGERerankerService by default."""
        from app.core.reranker.factory import RerankerServiceFactory
        from app.core.reranker.bge_reranker import BGERerankerService

        # Clear cache
        RerankerServiceFactory._instances = {}

        with patch('app.core.reranker.factory.settings') as mock_settings:
            mock_settings.RERANKER_MODEL = "bge-reranker"
            mock_settings.RERANKER_QUANTIZATION = "fp16"

            # Create with explicit default config
            service = RerankerServiceFactory.create()

        # Should be BGERerankerService
        assert isinstance(service, BGERerankerService)

    def test_factory_creates_bge_reranker_when_configured(self):
        """Test that Factory creates BGERerankerService when RERANKER_MODEL=bge-reranker."""
        from app.core.reranker.factory import RerankerServiceFactory
        from app.core.reranker.bge_reranker import BGERerankerService

        # Clear cache
        RerankerServiceFactory._instances = {}

        with patch('app.core.reranker.factory.settings') as mock_settings:
            mock_settings.RERANKER_MODEL = "bge-reranker"
            mock_settings.RERANKER_QUANTIZATION = "fp16"

            service = RerankerServiceFactory.create()

        # Should be BGERerankerService
        assert isinstance(service, BGERerankerService)

    def test_factory_creates_qwen3vl_reranker_when_configured(self):
        """Test that Factory creates Qwen3VLRerankerService when RERANKER_MODEL=qwen3-vl-reranker."""
        from app.core.reranker.factory import RerankerServiceFactory
        from app.core.reranker.qwen3vl_reranker import Qwen3VLRerankerService

        # Clear cache
        RerankerServiceFactory._instances = {}

        # Mock settings to return qwen3-vl-reranker
        with patch('app.core.reranker.factory.settings') as mock_settings:
            mock_settings.RERANKER_MODEL = "qwen3-vl-reranker"
            mock_settings.RERANKER_QUANTIZATION = "fp16"
            
            service = RerankerServiceFactory.create()

            # Should be Qwen3VLRerankerService
            assert isinstance(service, Qwen3VLRerankerService)

    def test_factory_raises_value_error_for_unknown_model(self):
        """Test that Factory raises ValueError for unknown model type."""
        from app.core.reranker.factory import RerankerServiceFactory

        # Clear cache
        RerankerServiceFactory._instances = {}

        # Mock settings to return unknown model
        with patch('app.core.reranker.factory.settings') as mock_settings:
            mock_settings.RERANKER_MODEL = "unknown-model"
            mock_settings.RERANKER_QUANTIZATION = "fp16"

            # Should raise ValueError
            with pytest.raises(ValueError) as exc_info:
                RerankerServiceFactory.create()

            # Error message should mention unknown model
            assert "unknown" in str(exc_info.value).lower()

    def test_factory_caches_instances(self):
        """Test that Factory caches instances (singleton per model type)."""
        from app.core.reranker.factory import RerankerServiceFactory

        # Clear cache
        RerankerServiceFactory._instances = {}

        with patch('app.core.reranker.factory.settings') as mock_settings:
            mock_settings.RERANKER_MODEL = "bge-reranker"
            mock_settings.RERANKER_QUANTIZATION = "fp16"

            # Create service twice
            service1 = RerankerServiceFactory.create()
            service2 = RerankerServiceFactory.create()

        # Should be same instance
        assert service1 is service2

    def test_factory_caches_per_configuration(self):
        """Test that Factory caches instances per configuration."""
        from app.core.reranker.factory import RerankerServiceFactory

        # Clear cache
        RerankerServiceFactory._instances = {}

        with patch('app.core.reranker.factory.settings') as mock_settings:
            mock_settings.RERANKER_MODEL = "bge-reranker"
            mock_settings.RERANKER_QUANTIZATION = "fp16"

            # Create service
            service1 = RerankerServiceFactory.create()

            # Clear cache
            RerankerServiceFactory._instances = {}

            # Create service again
            service2 = RerankerServiceFactory.create()

        # Should be different instances (different cache keys)
        assert service1 is not service2

    def test_factory_get_reranker_service_function(self):
        """Test backward compatible get_reranker_service() function."""
        from app.core.reranker.factory import get_reranker_service
        from app.core.reranker.base import BaseRerankerService

        # Clear cache
        from app.core.reranker.factory import RerankerServiceFactory
        RerankerServiceFactory._instances = {}

        with patch('app.core.reranker.factory.settings') as mock_settings:
            mock_settings.RERANKER_MODEL = "bge-reranker"
            mock_settings.RERANKER_QUANTIZATION = "fp16"

            # Get service
            service = get_reranker_service()

        # Should implement BaseRerankerService
        assert isinstance(service, BaseRerankerService)

    def test_factory_get_reranker_service_returns_singleton(self):
        """Test that get_reranker_service() returns singleton."""
        from app.core.reranker.factory import get_reranker_service

        # Clear cache
        from app.core.reranker.factory import RerankerServiceFactory
        RerankerServiceFactory._instances = {}

        with patch('app.core.reranker.factory.settings') as mock_settings:
            mock_settings.RERANKER_MODEL = "bge-reranker"
            mock_settings.RERANKER_QUANTIZATION = "fp16"

            # Get service twice
            service1 = get_reranker_service()
            service2 = get_reranker_service()

        # Should be same instance
        assert service1 is service2


class TestRerankerServiceFactoryConfiguration:
    """Tests for configuration-driven model selection."""

    def test_factory_uses_reranker_model_config(self):
        """Test that Factory uses RERANKER_MODEL configuration."""
        from app.core.reranker.factory import RerankerServiceFactory
        from app.core.reranker.bge_reranker import BGERerankerService

        # Clear cache
        RerankerServiceFactory._instances = {}

        with patch('app.core.reranker.factory.settings') as mock_settings:
            mock_settings.RERANKER_MODEL = "bge-reranker"
            mock_settings.RERANKER_QUANTIZATION = "fp16"

            service = RerankerServiceFactory.create()

        # Should create BGERerankerService based on config
        assert isinstance(service, BGERerankerService)

    def test_factory_passes_quantization_to_qwen3vl(self):
        """Test that Factory passes quantization config to Qwen3VLRerankerService."""
        from app.core.reranker.factory import RerankerServiceFactory
        from app.core.reranker.qwen3vl_reranker import Qwen3VLRerankerService

        # Clear cache
        RerankerServiceFactory._instances = {}

        # Mock settings
        with patch('app.core.reranker.factory.settings') as mock_settings:
            mock_settings.RERANKER_MODEL = "qwen3-vl-reranker"
            mock_settings.RERANKER_QUANTIZATION = "int8"

            service = RerankerServiceFactory.create()

            # Should create Qwen3VLRerankerService with quantization
            assert isinstance(service, Qwen3VLRerankerService)
            assert service.quantization == "int8"

    def test_factory_create_accepts_explicit_model_override(self):
        """Factory should honor explicit model arguments for A/B benchmark runs."""
        from app.core.reranker.factory import RerankerServiceFactory
        from app.core.reranker.bge_reranker import BGERerankerService

        RerankerServiceFactory._instances = {}

        with patch('app.core.reranker.factory.settings') as mock_settings:
            mock_settings.RERANKER_MODEL = "qwen3-vl-reranker"
            mock_settings.RERANKER_QUANTIZATION = "fp16"
            service = RerankerServiceFactory.create(model_type="bge-reranker", quantization="fp16")

        assert isinstance(service, BGERerankerService)

    def test_get_reranker_service_for_experiment(self):
        """Benchmark helper should return requested reranker model."""
        from app.core.reranker.factory import (
            RerankerServiceFactory,
            get_reranker_service_for_experiment,
        )
        from app.core.reranker.qwen3vl_reranker import Qwen3VLRerankerService

        RerankerServiceFactory._instances = {}

        service = get_reranker_service_for_experiment(
            model_type="qwen3-vl-reranker",
            quantization="fp16",
        )
        assert isinstance(service, Qwen3VLRerankerService)