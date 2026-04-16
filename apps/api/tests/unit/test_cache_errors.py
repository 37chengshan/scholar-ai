"""Tests for Redis cache error handling.

Tests that CacheError is raised when Redis operations fail,
instead of silently returning None or False.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.utils.cache import (
    CacheError,
    get_cached_response,
    set_cached_response,
    get_conversation_session,
    save_conversation_session,
)


class TestCacheError:
    """Tests for CacheError exception."""

    def test_cache_error_is_exception(self):
        """Test that CacheError is a proper exception."""
        error = CacheError("Test error message")
        assert isinstance(error, Exception)
        assert str(error) == "Test error message"


class TestGetCachedResponseErrors:
    """Tests for get_cached_response error handling."""

    @pytest.mark.asyncio
    async def test_raises_cache_error_on_connection_failure(self):
        """Test that CacheError is raised when Redis connection fails."""
        with patch("app.utils.cache.redis_db") as mock_redis:
            mock_redis.get = AsyncMock(side_effect=ConnectionError("Redis unavailable"))

            with pytest.raises(CacheError) as exc_info:
                await get_cached_response("test query", ["paper-1"])

            assert "Redis get failed" in str(exc_info.value)
            assert exc_info.value.__cause__ is not None

    @pytest.mark.asyncio
    async def test_raises_cache_error_on_timeout(self):
        """Test that CacheError is raised when Redis times out."""
        with patch("app.utils.cache.redis_db") as mock_redis:
            mock_redis.get = AsyncMock(side_effect=TimeoutError("Redis timeout"))

            with pytest.raises(CacheError) as exc_info:
                await get_cached_response("test query", ["paper-1"])

            assert "Redis get failed" in str(exc_info.value)


class TestSetCachedResponseErrors:
    """Tests for set_cached_response error handling."""

    @pytest.mark.asyncio
    async def test_raises_cache_error_on_set_failure(self):
        """Test that CacheError is raised when Redis set fails."""
        with patch("app.utils.cache.redis_db") as mock_redis:
            mock_redis.set = AsyncMock(side_effect=ConnectionError("Redis unavailable"))

            with pytest.raises(CacheError) as exc_info:
                await set_cached_response("test query", ["paper-1"], {"answer": "test"})

            assert "Redis set failed" in str(exc_info.value)
            assert exc_info.value.__cause__ is not None

    @pytest.mark.asyncio
    async def test_raises_cache_error_on_serialization_failure(self):
        """Test that CacheError is raised when JSON serialization fails."""
        with patch("app.utils.cache.redis_db") as mock_redis:
            # Create an object that can't be serialized
            unserializable = {"data": object()}

            with pytest.raises(CacheError):
                await set_cached_response("test query", ["paper-1"], unserializable)


class TestConversationSessionErrors:
    """Tests for conversation session error handling."""

    @pytest.mark.asyncio
    async def test_get_session_raises_cache_error_on_failure(self):
        """Test that CacheError is raised when getting session fails."""
        with patch("app.utils.cache.redis_db") as mock_redis:
            mock_redis.get = AsyncMock(side_effect=Exception("Redis error"))

            with pytest.raises(CacheError) as exc_info:
                await get_conversation_session("session-123")

            assert "Redis get conversation failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_save_session_raises_cache_error_on_failure(self):
        """Test that CacheError is raised when saving session fails."""
        with patch("app.utils.cache.redis_db") as mock_redis:
            mock_redis.set = AsyncMock(side_effect=Exception("Redis error"))

            with pytest.raises(CacheError) as exc_info:
                await save_conversation_session("session-123", {"messages": []})

            assert "Redis set conversation failed" in str(exc_info.value)


class TestErrorLogging:
    """Tests that errors are properly logged."""

    @pytest.mark.asyncio
    async def test_get_cached_logs_error_before_raising(self):
        """Test that errors are logged before raising CacheError."""
        with patch("app.utils.cache.redis_db") as mock_redis:
            with patch("app.utils.cache.logger") as mock_logger:
                mock_redis.get = AsyncMock(side_effect=Exception("Test error"))

                with pytest.raises(CacheError):
                    await get_cached_response("test", ["paper-1"])

                # Verify error was logged
                mock_logger.error.assert_called_once()
                assert "Cache retrieval error" in mock_logger.error.call_args[0][0]

    @pytest.mark.asyncio
    async def test_set_cached_logs_error_before_raising(self):
        """Test that errors are logged before raising CacheError."""
        with patch("app.utils.cache.redis_db") as mock_redis:
            with patch("app.utils.cache.logger") as mock_logger:
                mock_redis.set = AsyncMock(side_effect=Exception("Test error"))

                with pytest.raises(CacheError):
                    await set_cached_response("test", ["paper-1"], {"answer": "test"})

                # Verify error was logged
                mock_logger.error.assert_called_once()
                assert "Cache storage error" in mock_logger.error.call_args[0][0]