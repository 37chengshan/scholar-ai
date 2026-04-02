"""Tests for ImageCaptionService."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from PIL import Image

from app.core.image_caption_service import (
    ImageCaptionService,
    get_image_caption_service,
    create_image_caption_service,
    _image_caption_service
)


class TestImageCaptionService:
    """Test ImageCaptionService class."""

    def test_init_default_model(self):
        """Test initialization with default model name."""
        service = ImageCaptionService()
        assert service.model_name == "Qwen/Qwen2-VL-2B-Instruct"
        assert service._initialized is False
        assert service.device in ["cuda", "cpu"]

    def test_init_custom_model(self):
        """Test initialization with custom model name."""
        service = ImageCaptionService(model_name="custom-model")
        assert service.model_name == "custom-model"

    def test_build_prompt(self):
        """Test prompt template construction."""
        service = ImageCaptionService()
        prompt = service._build_prompt()
        assert "学术图片" in prompt
        assert "图表类型" in prompt
        assert "80字" in prompt

    @patch('app.core.image_caption_service.AutoProcessor')
    @patch('app.core.image_caption_service.Qwen2VLForConditionalGeneration')
    @patch('app.core.image_caption_service.torch.cuda.is_available')
    def test_load_model_success(self, mock_cuda, mock_model_class, mock_processor_class):
        """Test successful model loading."""
        mock_cuda.return_value = False
        mock_processor = Mock()
        mock_processor_class.from_pretrained.return_value = mock_processor
        mock_model = Mock()
        mock_model_class.from_pretrained.return_value = mock_model

        service = ImageCaptionService()
        result = service._load_model()

        assert result is True
        assert service._initialized is True
        assert service.processor is not None
        assert service.model is not None

    @patch('app.core.image_caption_service.AutoProcessor')
    @patch('app.core.image_caption_service.Qwen2VLForConditionalGeneration')
    def test_load_model_failure(self, mock_model_class, mock_processor_class):
        """Test model loading failure handling."""
        mock_processor_class.from_pretrained.side_effect = Exception("Model not found")

        service = ImageCaptionService()
        result = service._load_model()

        assert result is False
        assert service._initialized is False

    @patch('app.core.image_caption_service.AutoProcessor')
    @patch('app.core.image_caption_service.Qwen2VLForConditionalGeneration')
    @pytest.mark.asyncio
    async def test_generate_caption_success(self, mock_model_class, mock_processor_class):
        """Test successful caption generation."""
        # Setup mocks
        mock_processor = Mock()
        mock_processor.apply_chat_template.return_value = "<|im_start|>user\n<image>\nPrompt<|im_end|>"
        mock_processor.return_value = {
            'input_ids': Mock(shape=(1, 10)),
            'pixel_values': Mock()
        }
        mock_processor.decode.return_value = "This is a bar chart showing experimental results with increasing trend."
        mock_processor_class.from_pretrained.return_value = mock_processor

        mock_model = Mock()
        mock_model.device = "cpu"
        mock_model.generate.return_value = [list(range(20))]  # Mock token IDs
        mock_model_class.from_pretrained.return_value = mock_model

        # Create service and test
        service = ImageCaptionService()
        service._initialized = True
        service.processor = mock_processor
        service.model = mock_model
        service.device = "cpu"

        # Create a test image
        test_image = Image.new('RGB', (100, 100), color='red')

        caption = await service.generate_caption(test_image)

        assert caption is not None
        assert len(caption) > 10
        assert "bar chart" in caption.lower() or "Figure" in caption

    @pytest.mark.asyncio
    async def test_generate_caption_model_not_loaded(self):
        """Test fallback when model fails to load."""
        service = ImageCaptionService()

        # Mock _load_model to return False (simulating load failure)
        service._load_model = Mock(return_value=False)

        test_image = Image.new('RGB', (100, 100), color='red')
        caption = await service.generate_caption(test_image)

        assert caption == "Academic figure from research paper"

    @patch('app.core.image_caption_service.AutoProcessor')
    @patch('app.core.image_caption_service.Qwen2VLForConditionalGeneration')
    @pytest.mark.asyncio
    async def test_generate_caption_too_short(self, mock_model_class, mock_processor_class):
        """Test fallback when generated caption is too short."""
        # Setup mocks
        mock_processor = Mock()
        mock_processor.apply_chat_template.return_value = "prompt"
        mock_processor.return_value = {'input_ids': Mock(shape=(1, 10))}
        mock_processor.decode.return_value = "Hi"  # Too short caption
        mock_processor_class.from_pretrained.return_value = mock_processor

        mock_model = Mock()
        mock_model.device = "cpu"
        mock_model.generate.return_value = [list(range(20))]
        mock_model_class.from_pretrained.return_value = mock_model

        service = ImageCaptionService()
        service._initialized = True
        service.processor = mock_processor
        service.model = mock_model

        test_image = Image.new('RGB', (100, 100), color='red')
        caption = await service.generate_caption(test_image)

        assert caption == "Figure showing research data"

    @patch('app.core.image_caption_service.AutoProcessor')
    @patch('app.core.image_caption_service.Qwen2VLForConditionalGeneration')
    @pytest.mark.asyncio
    async def test_generate_caption_exception(self, mock_model_class, mock_processor_class):
        """Test fallback when generation raises exception."""
        mock_processor = Mock()
        mock_processor.apply_chat_template.side_effect = Exception("Processing error")
        mock_processor_class.from_pretrained.return_value = mock_processor

        mock_model = Mock()
        mock_model_class.from_pretrained.return_value = mock_model

        service = ImageCaptionService()
        service._initialized = True
        service.processor = mock_processor
        service.model = mock_model

        test_image = Image.new('RGB', (100, 100), color='red')
        caption = await service.generate_caption(test_image)

        assert caption == "Figure showing research data"

    def test_is_loaded(self):
        """Test is_loaded method."""
        service = ImageCaptionService()
        assert service.is_loaded() is False
        service._initialized = True
        assert service.is_loaded() is True

    def test_get_device(self):
        """Test get_device method."""
        service = ImageCaptionService()
        device = service.get_device()
        assert device in ["cuda", "cpu"]


class TestSingleton:
    """Test singleton pattern."""

    def teardown_method(self):
        """Reset singleton after each test."""
        global _image_caption_service
        _image_caption_service = None

    def test_get_image_caption_service_singleton(self):
        """Test that get_image_caption_service returns singleton."""
        service1 = get_image_caption_service()
        service2 = get_image_caption_service()
        assert service1 is service2

    @pytest.mark.asyncio
    async def test_create_image_caption_service(self):
        """Test create_image_caption_service factory function."""
        service = await create_image_caption_service()
        assert isinstance(service, ImageCaptionService)


class TestCaptionLength:
    """Test caption length constraints."""

    @patch('app.core.image_caption_service.AutoProcessor')
    @patch('app.core.image_caption_service.Qwen2VLForConditionalGeneration')
    @pytest.mark.asyncio
    async def test_caption_truncated_if_too_long(self, mock_model_class, mock_processor_class):
        """Test that long captions are truncated."""
        # Setup mocks
        mock_processor = Mock()
        mock_processor.apply_chat_template.return_value = "prompt"
        mock_processor.return_value = {'input_ids': Mock(shape=(1, 10))}
        # Generate a caption longer than max_length
        long_caption = "This is a very long caption " * 10
        mock_processor.decode.return_value = long_caption
        mock_processor_class.from_pretrained.return_value = mock_processor

        mock_model = Mock()
        mock_model.device = "cpu"
        mock_model.generate.return_value = [list(range(20))]
        mock_model_class.from_pretrained.return_value = mock_model

        service = ImageCaptionService()
        service._initialized = True
        service.processor = mock_processor
        service.model = mock_model

        test_image = Image.new('RGB', (100, 100), color='red')
        caption = await service.generate_caption(test_image, max_length=50)

        assert len(caption) <= 53  # 50 + "..."
        assert caption.endswith("...")
