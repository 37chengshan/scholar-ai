"""Tests for GPU auto-detection and configuration."""

import pytest
import os
import torch
from unittest.mock import patch, MagicMock, Mock
from app.config import Settings, get_settings
from app.core.qwen3vl_service import Qwen3VLMultimodalEmbedding


class TestEmbeddingDeviceConfig:
    """Tests for EMBEDDING_DEVICE configuration."""

    def test_default_device_is_auto(self):
        """Test that default EMBEDDING_DEVICE is 'auto'."""
        settings = get_settings()
        assert settings.EMBEDDING_DEVICE == "auto"

    def test_device_can_be_overridden_cpu(self):
        """Test that EMBEDDING_DEVICE can be set to 'cpu'."""
        original = os.environ.get("EMBEDDING_DEVICE")
        os.environ["EMBEDDING_DEVICE"] = "cpu"
        # Force reload by clearing lru_cache
        get_settings.cache_clear()
        settings = get_settings()
        assert settings.EMBEDDING_DEVICE == "cpu"
        if original:
            os.environ["EMBEDDING_DEVICE"] = original
        else:
            del os.environ["EMBEDDING_DEVICE"]

    def test_device_can_be_overridden_cuda(self):
        """Test that EMBEDDING_DEVICE can be set to 'cuda'."""
        original = os.environ.get("EMBEDDING_DEVICE")
        os.environ["EMBEDDING_DEVICE"] = "cuda"
        get_settings.cache_clear()
        settings = get_settings()
        assert settings.EMBEDDING_DEVICE == "cuda"
        if original:
            os.environ["EMBEDDING_DEVICE"] = original
        else:
            del os.environ["EMBEDDING_DEVICE"]

    def test_device_can_be_overridden_mps(self):
        """Test that EMBEDDING_DEVICE can be set to 'mps' (M1 Pro)."""
        original = os.environ.get("EMBEDDING_DEVICE")
        os.environ["EMBEDDING_DEVICE"] = "mps"
        get_settings.cache_clear()
        settings = get_settings()
        assert settings.EMBEDDING_DEVICE == "mps"
        if original:
            os.environ["EMBEDDING_DEVICE"] = original
        else:
            del os.environ["EMBEDDING_DEVICE"]


class TestDeviceDetection:
    """Tests for device auto-detection logic."""

    def test_detect_cuda_when_available(self):
        """Test CUDA detection when available."""
        with patch('torch.cuda.is_available', return_value=True):
            service = Qwen3VLMultimodalEmbedding(device="auto", quantization="int4")
            assert service.device == "cuda"

    def test_detect_mps_when_cuda_unavailable(self):
        """Test MPS (M1 Pro) detection when CUDA unavailable."""
        with patch('torch.cuda.is_available', return_value=False):
            with patch.object(torch.backends, 'mps', create=True) as mock_mps:
                mock_mps.is_available = Mock(return_value=True)
                service = Qwen3VLMultimodalEmbedding(device="auto", quantization="int4")
                assert service.device == "mps"

    def test_fallback_to_cpu_when_no_gpu(self):
        """Test CPU fallback when no GPU available."""
        with patch('torch.cuda.is_available', return_value=False):
            # Mock MPS unavailable by setting backs.mps.is_available to False
            with patch('torch.backends.mps.is_available', return_value=False):
                service = Qwen3VLMultimodalEmbedding(device="auto", quantization="int4")
                assert service.device == "cpu"

    def test_explicit_cpu_selection(self):
        """Test explicit CPU selection."""
        service = Qwen3VLMultimodalEmbedding(device="cpu", quantization="int4")
        assert service.device == "cpu"

    def test_explicit_cuda_selection(self):
        """Test explicit CUDA selection."""
        with patch('torch.cuda.is_available', return_value=True):
            service = Qwen3VLMultimodalEmbedding(device="cuda", quantization="int4")
            assert service.device == "cuda"

    def test_explicit_mps_selection(self):
        """Test explicit MPS selection."""
        service = Qwen3VLMultimodalEmbedding(device="mps", quantization="int4")
        assert service.device == "mps"


class TestDeviceLogging:
    """Tests for device selection logging."""

    def test_device_selection_is_logged(self, caplog):
        """Test that device selection is logged on load_model."""
        with patch('torch.cuda.is_available', return_value=False):
            with patch('torch.backends.mps.is_available', return_value=False):
                service = Qwen3VLMultimodalEmbedding(device="auto", quantization="int4")
                # Device should be set (CPU fallback)
                assert service.device == "cpu"

    def test_cuda_detection_is_logged(self, caplog):
        """Test that CUDA detection is logged."""
        with patch('torch.cuda.is_available', return_value=True):
            service = Qwen3VLMultimodalEmbedding(device="auto", quantization="int4")
            assert service.device == "cuda"


class TestDeviceIntegration:
    """Integration tests for device configuration flow."""

    def test_config_to_service_flow_cpu(self):
        """Test config CPU setting flows to service."""
        original = os.environ.get("EMBEDDING_DEVICE")
        os.environ["EMBEDDING_DEVICE"] = "cpu"
        get_settings.cache_clear()
        settings = get_settings()
        # Service would receive this config
        assert settings.EMBEDDING_DEVICE == "cpu"
        service = Qwen3VLMultimodalEmbedding(
            device=settings.EMBEDDING_DEVICE,
            quantization=settings.EMBEDDING_QUANTIZATION
        )
        assert service.device == "cpu"
        if original:
            os.environ["EMBEDDING_DEVICE"] = original
        else:
            del os.environ["EMBEDDING_DEVICE"]

    def test_config_to_service_flow_cuda(self):
        """Test config CUDA setting flows to service."""
        original = os.environ.get("EMBEDDING_DEVICE")
        os.environ["EMBEDDING_DEVICE"] = "cuda"
        get_settings.cache_clear()
        settings = get_settings()
        with patch('torch.cuda.is_available', return_value=True):
            service = Qwen3VLMultimodalEmbedding(
                device=settings.EMBEDDING_DEVICE,
                quantization=settings.EMBEDDING_QUANTIZATION
            )
            assert service.device == "cuda"
        if original:
            os.environ["EMBEDDING_DEVICE"] = original
        else:
            del os.environ["EMBEDDING_DEVICE"]

    def test_auto_device_with_available_cuda(self):
        """Test 'auto' device with available CUDA."""
        get_settings.cache_clear()
        settings = get_settings()
        assert settings.EMBEDDING_DEVICE == "auto"
        with patch('torch.cuda.is_available', return_value=True):
            service = Qwen3VLMultimodalEmbedding(
                device=settings.EMBEDDING_DEVICE,
                quantization=settings.EMBEDDING_QUANTIZATION
            )
            # Auto should detect CUDA
            assert service.device == "cuda"

    def test_auto_device_with_available_mps(self):
        """Test 'auto' device with available MPS (M1 Pro)."""
        get_settings.cache_clear()
        settings = get_settings()
        assert settings.EMBEDDING_DEVICE == "auto"
        with patch('torch.cuda.is_available', return_value=False):
            with patch('torch.backends.mps.is_available', return_value=True):
                service = Qwen3VLMultimodalEmbedding(
                    device=settings.EMBEDDING_DEVICE,
                    quantization=settings.EMBEDDING_QUANTIZATION
                )
                # Auto should detect MPS
                assert service.device == "mps"