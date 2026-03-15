"""Tests for retry utility"""

import pytest
import asyncio
from unittest.mock import Mock, patch

from app.utils.retry import with_retry, fetch_with_retry


class TestWithRetry:
    """Tests for with_retry decorator"""

    @pytest.mark.asyncio
    async def test_successful_call_no_retry(self):
        """Test that successful call doesn't retry"""
        call_count = 0

        @with_retry(max_retries=3)
        async def success_func():
            nonlocal call_count
            call_count += 1
            return "success"

        result = await success_func()

        assert result == "success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retry_on_failure(self):
        """Test that function retries on failure"""
        call_count = 0

        @with_retry(max_retries=3)
        async def fail_twice():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Temporary failure")
            return "success"

        result = await fail_twice()

        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self):
        """Test that exception is raised after max retries"""
        call_count = 0

        @with_retry(max_retries=2)
        async def always_fail():
            nonlocal call_count
            call_count += 1
            raise Exception("Persistent failure")

        with pytest.raises(Exception, match="Persistent failure"):
            await always_fail()

        assert call_count == 3  # initial + 2 retries

    @pytest.mark.asyncio
    async def test_retry_with_specific_exceptions(self):
        """Test that only specified exceptions trigger retry"""
        call_count = 0

        @with_retry(max_retries=3, exceptions=(ValueError,))
        async def raise_different_errors():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ValueError("Should retry")
            if call_count == 2:
                raise TypeError("Should not retry")
            return "success"

        with pytest.raises(TypeError):
            await raise_different_errors()

        assert call_count == 2

    @pytest.mark.asyncio
    async def test_sync_function_retry(self):
        """Test that sync functions also work with retry"""
        call_count = 0

        @with_retry(max_retries=3)
        def sync_fail_once():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Retry me")
            return "sync success"

        result = sync_fail_once()

        assert result == "sync success"
        assert call_count == 2


class TestFetchWithRetry:
    """Tests for fetch_with_retry function"""

    @pytest.mark.asyncio
    async def test_successful_fetch(self):
        """Test successful fetch without retry"""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_client.request = Mock(return_value=asyncio.Future())
        mock_client.request.return_value.set_result(mock_response)

        result = await fetch_with_retry(
            "http://example.com",
            mock_client,
            method="GET"
        )

        assert result.status_code == 200
        assert mock_client.request.call_count == 1

    @pytest.mark.asyncio
    async def test_retry_on_server_error(self):
        """Test retry on 5xx errors"""
        mock_client = Mock()

        # First two calls return 500, third returns 200
        responses = [
            Mock(status_code=500),
            Mock(status_code=500),
            Mock(status_code=200)
        ]

        async def mock_request(*args, **kwargs):
            return responses.pop(0)

        mock_client.request = mock_request

        result = await fetch_with_retry(
            "http://example.com",
            mock_client,
            max_retries=3
        )

        assert result.status_code == 200

    @pytest.mark.asyncio
    async def test_no_retry_on_client_error(self):
        """Test no retry on 4xx errors"""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.status_code = 404

        async def mock_request(*args, **kwargs):
            return mock_response

        mock_client.request = mock_request

        # Should return 404 without retry
        result = await fetch_with_retry(
            "http://example.com",
            mock_client,
            max_retries=3
        )

        assert result.status_code == 404

    @pytest.mark.asyncio
    async def test_custom_timeout(self):
        """Test custom timeout parameter"""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.status_code = 200

        mock_future = asyncio.Future()
        mock_future.set_result(mock_response)
        mock_client.request = Mock(return_value=mock_future)

        await fetch_with_retry(
            "http://example.com",
            mock_client,
            timeout=60.0
        )

        # Verify timeout was passed
        call_kwargs = mock_client.request.call_args[1]
        assert call_kwargs['timeout'] == 60.0


class TestExponentialBackoff:
    """Tests for exponential backoff behavior"""

    @pytest.mark.asyncio
    async def test_delay_increases_with_attempt(self):
        """Test that delay increases exponentially"""
        delays = []

        original_sleep = asyncio.sleep

        async def capture_sleep(seconds):
            delays.append(seconds)
            return None

        with patch('asyncio.sleep', side_effect=capture_sleep):
            @with_retry(max_retries=3, base_delay=1.0)
            async def always_fail():
                raise Exception("Fail")

            try:
                await always_fail()
            except Exception:
                pass

        # Should have 3 delays (for 3 retries)
        assert len(delays) == 3

        # Each delay should be roughly 2x the previous (with jitter)
        # Delay pattern: ~1s, ~2s, ~4s (plus 0-1s jitter)
        assert delays[0] < delays[1] < delays[2]

    @pytest.mark.asyncio
    async def test_max_delay_cap(self):
        """Test that delay is capped at max_delay"""
        delays = []

        async def capture_sleep(seconds):
            delays.append(seconds)
            return None

        with patch('asyncio.sleep', side_effect=capture_sleep):
            @with_retry(max_retries=5, base_delay=1.0, max_delay=3.0)
            async def always_fail():
                raise Exception("Fail")

            try:
                await always_fail()
            except Exception:
                pass

        # All delays should be <= max_delay + jitter
        for delay in delays:
            assert delay <= 4.0  # 3.0 + 1.0 jitter
