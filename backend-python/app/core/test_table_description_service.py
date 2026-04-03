"""Tests for TableDescriptionService."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
import httpx

from app.core.table_description_service import (
    TableDescriptionService,
    get_table_description_service,
    create_table_description_service,
    _table_description_service
)


class TestTableDescriptionService:
    """Test TableDescriptionService class."""

    def test_init_default(self):
        """Test initialization with default settings."""
        with patch('app.core.table_description_service.settings') as mock_settings:
            mock_settings.ZHIPU_API_KEY = "test-key"
            service = TableDescriptionService()
            assert service.api_key == "test-key"
            assert service.MODEL_NAME == "glm-4-flash"
            assert service.API_URL == "https://open.bigmodel.cn/api/paas/v4/chat/completions"

    def test_init_custom_api_key(self):
        """Test initialization with custom API key."""
        service = TableDescriptionService(api_key="custom-key")
        assert service.api_key == "custom-key"

    def test_build_prompt(self):
        """Test prompt template construction."""
        service = TableDescriptionService(api_key="test-key")
        caption = "Table 1: Experimental Results"
        headers = ["Method", "Accuracy", "Time"]
        sample_rows = [
            {"Method": "A", "Accuracy": "95%", "Time": "10s"},
            {"Method": "B", "Accuracy": "92%", "Time": "8s"},
            {"Method": "C", "Accuracy": "98%", "Time": "15s"}
        ]

        prompt = service._build_prompt(caption, headers, sample_rows)

        assert "Table 1: Experimental Results" in prompt
        assert "Method, Accuracy, Time" in prompt
        assert "第1行" in prompt
        assert "第2行" in prompt
        assert "第3行" in prompt
        assert "一句话概括" in prompt
        assert "不超过100字" in prompt

    def test_format_sample_rows(self):
        """Test sample rows formatting."""
        service = TableDescriptionService(api_key="test-key")
        rows = [
            {"Method": "A", "Accuracy": "95%"},
            {"Method": "B", "Accuracy": "92%"}
        ]

        formatted = service._format_sample_rows(rows)

        assert "第1行" in formatted
        assert "第2行" in formatted
        assert "Method=A" in formatted
        assert "Accuracy=95%" in formatted

    def test_format_sample_rows_empty(self):
        """Test formatting empty rows."""
        service = TableDescriptionService(api_key="test-key")
        formatted = service._format_sample_rows([])
        assert formatted == "(无数据)"

    def test_format_sample_rows_more_than_3(self):
        """Test that only first 3 rows are formatted."""
        service = TableDescriptionService(api_key="test-key")
        rows = [
            {"id": 1}, {"id": 2}, {"id": 3}, {"id": 4}, {"id": 5}
        ]

        formatted = service._format_sample_rows(rows)

        assert "第1行" in formatted
        assert "第2行" in formatted
        assert "第3行" in formatted
        assert "第4行" not in formatted
        assert "第5行" not in formatted

    @pytest.mark.asyncio
    async def test_call_api_success(self):
        """Test successful API call."""
        service = TableDescriptionService(api_key="test-key")

        mock_response = Mock()
        mock_response.json.return_value = {
            "choices": [
                {"message": {"content": "This is a test description."}}
            ]
        }
        mock_response.raise_for_status = Mock()

        service.client = Mock()
        service.client.post = AsyncMock(return_value=mock_response)

        result = await service._call_api("test prompt")

        assert result == "This is a test description."
        service.client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_call_api_no_api_key(self):
        """Test API call without API key."""
        service = TableDescriptionService(api_key="")

        with pytest.raises(ValueError, match="ZHIPU_API_KEY not configured"):
            await service._call_api("test prompt")

    @pytest.mark.asyncio
    async def test_call_api_invalid_response(self):
        """Test API call with invalid response."""
        service = TableDescriptionService(api_key="test-key")

        mock_response = Mock()
        mock_response.json.return_value = {"error": "Invalid request"}
        mock_response.raise_for_status = Mock()

        service.client = Mock()
        service.client.post = AsyncMock(return_value=mock_response)

        with pytest.raises(ValueError):
            await service._call_api("test prompt")

    @pytest.mark.asyncio
    async def test_generate_description_success(self):
        """Test successful description generation."""
        service = TableDescriptionService(api_key="test-key")

        mock_response = Mock()
        mock_response.json.return_value = {
            "choices": [
                {"message": {"content": "This table compares methods by accuracy and time."}}
            ]
        }
        mock_response.raise_for_status = Mock()

        service.client = Mock()
        service.client.post = AsyncMock(return_value=mock_response)

        result = await service.generate_description(
            caption="Table 1: Results",
            headers=["Method", "Accuracy", "Time"],
            sample_rows=[
                {"Method": "A", "Accuracy": "95%", "Time": "10s"},
                {"Method": "B", "Accuracy": "92%", "Time": "8s"},
                {"Method": "C", "Accuracy": "98%", "Time": "15s"}
            ]
        )

        assert result == "This table compares methods by accuracy and time."

    @pytest.mark.asyncio
    async def test_generate_description_skipped_too_few_rows(self):
        """Test that tables with <= 2 rows are skipped."""
        service = TableDescriptionService(api_key="test-key")

        result = await service.generate_description(
            caption="Table 1: Results",
            headers=["Name", "Value"],
            sample_rows=[
                {"Name": "A", "Value": "1"},
                {"Name": "B", "Value": "2"}
            ],
            min_rows=2
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_generate_description_custom_min_rows(self):
        """Test custom min_rows threshold."""
        service = TableDescriptionService(api_key="test-key")

        # With min_rows=3, 3 rows should be processed (len > min_rows is False)
        # Actually len=3 <= min_rows=3, so it should be skipped
        result = await service.generate_description(
            caption="Table 1: Results",
            headers=["Name", "Value"],
            sample_rows=[
                {"Name": "A", "Value": "1"},
                {"Name": "B", "Value": "2"},
                {"Name": "C", "Value": "3"}
            ],
            min_rows=3
        )

        # len(sample_rows) = 3, min_rows = 3, so 3 <= 3 is True, should return None
        assert result is None

    @pytest.mark.asyncio
    async def test_generate_description_api_failure_fallback(self):
        """Test fallback to caption on API failure."""
        service = TableDescriptionService(api_key="test-key")

        service.client = Mock()
        service.client.post = AsyncMock(side_effect=httpx.HTTPError("Connection failed"))

        result = await service.generate_description(
            caption="Table 1: Experimental Results",
            headers=["Method", "Accuracy"],
            sample_rows=[
                {"Method": "A", "Accuracy": "95%"},
                {"Method": "B", "Accuracy": "92%"},
                {"Method": "C", "Accuracy": "98%"}
            ]
        )

        # Should fallback to caption
        assert result == "Table 1: Experimental Results"

    @pytest.mark.asyncio
    async def test_generate_description_empty_response_fallback(self):
        """Test fallback when API returns empty response."""
        service = TableDescriptionService(api_key="test-key")

        mock_response = Mock()
        mock_response.json.return_value = {
            "choices": [
                {"message": {"content": ""}}
            ]
        }
        mock_response.raise_for_status = Mock()

        service.client = Mock()
        service.client.post = AsyncMock(return_value=mock_response)

        result = await service.generate_description(
            caption="Table 1: Results",
            headers=["Name", "Value"],
            sample_rows=[
                {"Name": "A", "Value": "1"},
                {"Name": "B", "Value": "2"},
                {"Name": "C", "Value": "3"}
            ]
        )

        assert result == "Table 1: Results"

    @pytest.mark.asyncio
    async def test_generate_description_short_response_fallback(self):
        """Test fallback when API returns too short response."""
        service = TableDescriptionService(api_key="test-key")

        mock_response = Mock()
        mock_response.json.return_value = {
            "choices": [
                {"message": {"content": "Hi"}}
            ]
        }
        mock_response.raise_for_status = Mock()

        service.client = Mock()
        service.client.post = AsyncMock(return_value=mock_response)

        result = await service.generate_description(
            caption="Table 1: Results",
            headers=["Name", "Value"],
            sample_rows=[
                {"Name": "A", "Value": "1"},
                {"Name": "B", "Value": "2"},
                {"Name": "C", "Value": "3"}
            ]
        )

        assert result == "Table 1: Results"

    @pytest.mark.asyncio
    async def test_generate_description_no_caption_fallback(self):
        """Test returns None when no caption and API fails."""
        service = TableDescriptionService(api_key="test-key")

        service.client = Mock()
        service.client.post = AsyncMock(side_effect=httpx.HTTPError("Connection failed"))

        result = await service.generate_description(
            caption="",
            headers=["Name", "Value"],
            sample_rows=[
                {"Name": "A", "Value": "1"},
                {"Name": "B", "Value": "2"},
                {"Name": "C", "Value": "3"}
            ]
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_close(self):
        """Test client cleanup."""
        service = TableDescriptionService(api_key="test-key")
        service.client = Mock()
        service.client.aclose = AsyncMock()

        await service.close()
        service.client.aclose.assert_called_once()


class TestSingleton:
    """Test singleton pattern."""

    def teardown_method(self):
        """Reset singleton after each test."""
        global _table_description_service
        _table_description_service = None

    def test_get_table_description_service_singleton(self):
        """Test that get_table_description_service returns singleton."""
        service1 = get_table_description_service()
        service2 = get_table_description_service()
        assert service1 is service2

    @pytest.mark.asyncio
    async def test_create_table_description_service(self):
        """Test create_table_description_service factory function."""
        service = await create_table_description_service()
        assert isinstance(service, TableDescriptionService)


class TestRetryLogic:
    """Test retry behavior."""

    @pytest.mark.asyncio
    async def test_retry_on_failure(self):
        """Test that API calls are retried on failure."""
        service = TableDescriptionService(api_key="test-key")

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
        result = await service._call_api("test prompt")
        assert result == "Success after retries"
        assert service.client.post.call_count == 3
