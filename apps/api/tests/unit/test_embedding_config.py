"""Tests for embedding configuration.

Verifies configuration settings from Plan 18-01.
"""

import pytest
from app.config import settings


class TestEmbeddingConfiguration:
    """Test embedding configuration settings."""

    def test_embedding_model_configured(self):
        """EMBEDDING_MODEL should be configured."""
        assert hasattr(settings, "EMBEDDING_MODEL")
        assert len(settings.EMBEDDING_MODEL) > 0

    def test_embedding_quantization_configured(self):
        """EMBEDDING_QUANTIZATION should be configured."""
        assert hasattr(settings, "EMBEDDING_QUANTIZATION")
        assert settings.EMBEDDING_QUANTIZATION in ["int4", "fp16"]

    def test_embedding_dimension_configured(self):
        """EMBEDDING_DIMENSION should be configured."""
        assert hasattr(settings, "EMBEDDING_DIMENSION")
        assert settings.EMBEDDING_DIMENSION in [1024, 2048]

    def test_qwen3vl_embedding_model_path_configured(self):
        """QWEN3VL_EMBEDDING_MODEL_PATH should be configured."""
        assert hasattr(settings, "QWEN3VL_EMBEDDING_MODEL_PATH")
        assert len(settings.QWEN3VL_EMBEDDING_MODEL_PATH) > 0

    def test_reranker_model_configured(self):
        """RERANKER_MODEL should be configured."""
        assert hasattr(settings, "RERANKER_MODEL")
        assert settings.RERANKER_MODEL in ["bge-reranker", "qwen3-vl-reranker"]

    def test_reranker_quantization_configured(self):
        """RERANKER_QUANTIZATION should be configured."""
        assert hasattr(settings, "RERANKER_QUANTIZATION")
        assert settings.RERANKER_QUANTIZATION in ["fp16", "int8"]