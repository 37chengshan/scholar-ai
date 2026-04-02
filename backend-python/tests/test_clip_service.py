"""Tests for CLIP embedding service."""

import pytest
import torch
from PIL import Image
from unittest.mock import Mock, patch, MagicMock
from io import BytesIO

from app.core.clip_service import CLIPService, get_clip_service, create_clip_service


class TestCLIPService:
    """Test CLIPService class."""

    def test_init(self):
        """Test service initialization."""
        service = CLIPService()
        assert service.MODEL_NAME == "google/siglip-base-patch16-256"
        assert service.EMBEDDING_DIM == 768
        assert not service.is_loaded()
        assert service.device in ["cuda", "cpu"]

    def test_get_embedding_dim(self):
        """Test getting embedding dimension."""
        service = CLIPService()
        assert service.get_embedding_dim() == 768

    def test_get_device(self):
        """Test getting device."""
        service = CLIPService()
        assert service.get_device() in ["cuda", "cpu"]

    @patch("app.core.clip_service.AutoProcessor")
    @patch("app.core.clip_service.AutoModel")
    def test_load_model(self, mock_model_class, mock_processor_class):
        """Test model loading."""
        # Setup mocks
        mock_processor = MagicMock()
        mock_processor_class.from_pretrained.return_value = mock_processor

        mock_model = MagicMock()
        mock_model_class.from_pretrained.return_value = mock_model

        service = CLIPService()
        service.load_model()

        # Verify model was loaded
        assert service.is_loaded()
        assert service.model == mock_model
        assert service.processor == mock_processor

    @patch("app.core.clip_service.AutoProcessor")
    @patch("app.core.clip_service.AutoModel")
    def test_load_model_already_loaded(self, mock_model_class, mock_processor_class):
        """Test model loading when already loaded."""
        service = CLIPService()

        # Load once
        service.load_model()
        assert service.is_loaded()

        # Clear mock call counts
        mock_model_class.from_pretrained.reset_mock()
        mock_processor_class.from_pretrained.reset_mock()

        # Load again - should not call from_pretrained
        service.load_model()
        mock_model_class.from_pretrained.assert_not_called()
        mock_processor_class.from_pretrained.assert_not_called()

    @patch("app.core.clip_service.AutoProcessor")
    @patch("app.core.clip_service.AutoModel")
    def test_encode_image_not_loaded(self, mock_model_class, mock_processor_class):
        """Test encoding when model not loaded raises error."""
        service = CLIPService()

        with pytest.raises(RuntimeError, match="Model not loaded"):
            service.encode_image("test.jpg")

    def test_singleton(self):
        """Test singleton pattern."""
        service1 = get_clip_service()
        service2 = get_clip_service()
        assert service1 is service2

    @pytest.mark.asyncio
    @patch("app.core.clip_service.get_clip_service")
    async def test_create_clip_service(self, mock_get_service):
        """Test async service creation."""
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service

        service = await create_clip_service()

        assert service == mock_service
        mock_service.load_model.assert_called_once()
