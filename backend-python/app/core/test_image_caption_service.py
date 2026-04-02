"""Tests for ImageCaptionService."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from PIL import Image
import httpx

from app.core.image_caption_service import (
    ImageCaptionService,
    get_image_caption_service,
    create_image_caption_service,
    _image_caption_service
)


class TestImageCaptionService:
    """Test ImageCaptionService class."""

    def test_init_default_api_key(self):
        """Test initialization with default API key from settings."""
        with patch('app.core.image_caption_service.settings') as mock_settings:
            mock_settings.ZHIPU_API_KEY = "test-key"
            service = ImageCaptionService()
            assert service.api_key == "test-key"
            assert service.MODEL_NAME == "glm-4v"
            assert service.API_URL == "https://open.bigmodel.cn/api/paas/v4/chat/completions"

    def test_init_custom_api_key(self):
        """Test initialization with custom API key."""
        service = ImageCaptionService(api_key="custom-key")
        assert service.api_key == "custom-key"

    def test_build_prompt(self):
        """Test prompt template construction."""
        service = ImageCaptionService(api_key="test-key")
        prompt = service._build_prompt()
        assert "学术图片" in prompt
        assert "图表类型" in prompt
        assert "80字" in prompt

    def test_encode_image(self):
        """Test image encoding to base64."""
        service = ImageCaptionService(api_key="test-key")
        test_image = Image.new('RGB', (100, 100), color='red')

        encoded = service._encode_image(test_image)

        assert isinstance(encoded, str)
        assert len(encoded) > 0

    def test_encode_image_rgba(self):
        """Test encoding RGBA image (converts to RGB)."""
        service = ImageCaptionService(api_key="test-key")
        test_image = Image.new('RGBA', (100, 100), color=(255, 0, 0, 128))

        encoded = service._encode_image(test_image)

        assert isinstance(encoded, str)
        assert len(encoded) > 0

    @pytest.mark.asyncio
    async def test_call_api_success(self):
        """Test successful API call."""
        service = ImageCaptionService(api_key="test-key")

        mock_response = Mock()
        mock_response.json.return_value = {
            "choices": [
                {"message": {"content": "This is a bar chart showing experimental results."}}
            ]
        }
        mock_response.raise_for_status = Mock()

        service.client = Mock()
        service.client.post = AsyncMock(return_value=mock_response)

        result = await service._call_api("base64encodedimage")

        assert result == "This is a bar chart showing experimental results."
        service.client.post.assert_called_once()

        # Verify payload structure
        call_args = service.client.post.call_args
        payload = call_args[1]['json']
        assert payload['model'] == 'glm-4v'
        assert len(payload['messages']) == 1
        assert len(payload['messages'][0]['content']) == 2  # text + image

    @pytest.mark.asyncio
    async def test_call_api_no_api_key(self):
        """Test API call without API key."""
        service = ImageCaptionService(api_key="")

        # The retry decorator will wrap the ValueError in RetryError
        from tenacity import RetryError
        with pytest.raises(RetryError) as exc_info:
            await service._call_api("base64encodedimage")

        # Check that the underlying error (from the last attempt) is about the API key
        # The RetryError's last exception is stored in the future
        retry_error = exc_info.value
        # Get the underlying exception from the retry error
        assert retry_error.last_attempt.exception() is not None
        assert "ZHIPU_API_KEY" in str(retry_error.last_attempt.exception())

    @pytest.mark.asyncio
    async def test_call_api_invalid_response(self):
        """Test API call with invalid response."""
        service = ImageCaptionService(api_key="test-key")

        mock_response = Mock()
        mock_response.json.return_value = {"error": "Invalid request"}
        mock_response.raise_for_status = Mock()

        service.client = Mock()
        service.client.post = AsyncMock(return_value=mock_response)

        # The retry decorator will wrap the ValueError in RetryError
        from tenacity import RetryError
        with pytest.raises(RetryError) as exc_info:
            await service._call_api("base64encodedimage")

        # Check that the underlying error is about the response
        retry_error = exc_info.value
        assert retry_error.last_attempt.exception() is not None
        assert "Unexpected API response" in str(retry_error.last_attempt.exception())

    @pytest.mark.asyncio
    async def test_generate_caption_success(self):
        """Test successful caption generation."""
        service = ImageCaptionService(api_key="test-key")

        mock_response = Mock()
        mock_response.json.return_value = {
            "choices": [
                {"message": {"content": "This is a bar chart showing increasing accuracy trends."}}
            ]
        }
        mock_response.raise_for_status = Mock()

        service.client = Mock()
        service.client.post = AsyncMock(return_value=mock_response)

        test_image = Image.new('RGB', (100, 100), color='red')
        caption = await service.generate_caption(test_image)

        assert caption is not None
        assert len(caption) > 10
        assert "bar chart" in caption.lower() or "Figure" in caption

    @pytest.mark.asyncio
    async def test_generate_caption_api_failure_fallback(self):
        """Test fallback when API fails."""
        service = ImageCaptionService(api_key="test-key")

        service.client = Mock()
        service.client.post = AsyncMock(side_effect=httpx.HTTPError("Connection failed"))

        test_image = Image.new('RGB', (100, 100), color='red')
        caption = await service.generate_caption(test_image)

        assert caption == "Figure showing research data"

    @pytest.mark.asyncio
    async def test_generate_caption_empty_response_fallback(self):
        """Test fallback when API returns empty response."""
        service = ImageCaptionService(api_key="test-key")

        mock_response = Mock()
        mock_response.json.return_value = {
            "choices": [
                {"message": {"content": ""}}
            ]
        }
        mock_response.raise_for_status = Mock()

        service.client = Mock()
        service.client.post = AsyncMock(return_value=mock_response)

        test_image = Image.new('RGB', (100, 100), color='red')
        caption = await service.generate_caption(test_image)

        assert caption == "Figure showing research data"

    @pytest.mark.asyncio
    async def test_generate_caption_short_response_fallback(self):
        """Test fallback when API returns too short response."""
        service = ImageCaptionService(api_key="test-key")

        mock_response = Mock()
        mock_response.json.return_value = {
            "choices": [
                {"message": {"content": "Hi"}}
            ]
        }
        mock_response.raise_for_status = Mock()

        service.client = Mock()
        service.client.post = AsyncMock(return_value=mock_response)

        test_image = Image.new('RGB', (100, 100), color='red')
        caption = await service.generate_caption(test_image)

        assert caption == "Figure showing research data"

    @pytest.mark.asyncio
    async def test_generate_caption_truncated(self):
        """Test caption truncation when too long."""
        service = ImageCaptionService(api_key="test-key")

        long_caption = "This is a very long caption " * 10
        mock_response = Mock()
        mock_response.json.return_value = {
            "choices": [
                {"message": {"content": long_caption}}
            ]
        }
        mock_response.raise_for_status = Mock()

        service.client = Mock()
        service.client.post = AsyncMock(return_value=mock_response)

        test_image = Image.new('RGB', (100, 100), color='red')
        caption = await service.generate_caption(test_image, max_length=50)

        assert len(caption) <= 53  # 50 + "..."
        assert caption.endswith("...")

    @pytest.mark.asyncio
    async def test_close(self):
        """Test client cleanup."""
        service = ImageCaptionService(api_key="test-key")
        service.client = Mock()
        service.client.aclose = AsyncMock()

        await service.close()
        service.client.aclose.assert_called_once()


class TestSingleton:
    """Test singleton pattern."""

    def teardown_method(self):
        """Reset singleton after each test."""
        global _image_caption_service
        _image_caption_service = None

    def test_get_image_caption_service_singleton(self):
        """Test that get_image_caption_service returns singleton."""
        with patch('app.core.image_caption_service.settings') as mock_settings:
            mock_settings.ZHIPU_API_KEY = "test-key"
            service1 = get_image_caption_service()
            service2 = get_image_caption_service()
            assert service1 is service2

    @pytest.mark.asyncio
    async def test_create_image_caption_service(self):
        """Test create_image_caption_service factory function."""
        with patch('app.core.image_caption_service.settings') as mock_settings:
            mock_settings.ZHIPU_API_KEY = "test-key"
            service = await create_image_caption_service()
            assert isinstance(service, ImageCaptionService)


class TestRetryLogic:
    """Test retry behavior."""

    @pytest.mark.asyncio
    async def test_retry_on_failure(self):
        """Test that API calls are retried on failure."""
        service = ImageCaptionService(api_key="test-key")

        # First 2 calls fail, 3rd succeeds
        mock_response = Mock()
        mock_response.json.return_value = {
            "choices": [
                {"message": {"content": "Success after retries"}}
            ]
        }
        mock_response.raise_for_status = Mock()

        service.client = Mock()
        service.client.post = AsyncMock(
            side_effect=[
                httpx.HTTPError("First failure"),
                httpx.HTTPError("Second failure"),
                mock_response
            ]
        )

        # Should succeed after retries
        result = await service._call_api("base64encodedimage")
        assert result == "Success after retries"
        assert service.client.post.call_count == 3
