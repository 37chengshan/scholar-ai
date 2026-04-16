"""Tests for ConcurrentControl - Redis-based concurrent paper addition limiting.

Tests the following behaviors:
1. can_add_paper returns True when user has 0 pending papers
2. can_add_paper returns False when user has 5 pending papers
3. increment_pending increases counter by 1
4. decrement_pending decreases counter by 1
5. Counter expires after TTL (1 hour)

Requirements:
- API-02: External search routes
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import redis.asyncio as redis

from app.core.concurrent_control import ConcurrentControl


@pytest.fixture
def mock_redis():
    """Create mock Redis client for testing."""
    mock = AsyncMock(spec=redis.Redis)
    return mock


@pytest.fixture
def concurrent_control(mock_redis):
    """Create ConcurrentControl instance with mock Redis."""
    control = ConcurrentControl(redis_client=mock_redis)
    return control


class TestCanAddPaper:
    """Tests for can_add_paper method."""

    @pytest.mark.asyncio
    async def test_can_add_paper_returns_true_when_zero_pending(self, concurrent_control, mock_redis):
        """Test 1: can_add_paper returns True when user has 0 pending papers."""
        # Setup: Redis returns None (key doesn't exist)
        mock_redis.get = AsyncMock(return_value=None)

        # Execute
        result = await concurrent_control.can_add_paper("user-123")

        # Verify
        assert result is True
        mock_redis.get.assert_called_once_with("user:user-123:pending_papers")

    @pytest.mark.asyncio
    async def test_can_add_paper_returns_true_when_below_limit(self, concurrent_control, mock_redis):
        """Test that can_add_paper returns True when count < MAX_CONCURRENT."""
        # Setup: Redis returns "3" (3 pending papers)
        mock_redis.get = AsyncMock(return_value="3")

        # Execute
        result = await concurrent_control.can_add_paper("user-123")

        # Verify
        assert result is True

    @pytest.mark.asyncio
    async def test_can_add_paper_returns_false_when_at_limit(self, concurrent_control, mock_redis):
        """Test 2: can_add_paper returns False when user has 5 pending papers."""
        # Setup: Redis returns "5" (5 pending papers - at limit)
        mock_redis.get = AsyncMock(return_value="5")

        # Execute
        result = await concurrent_control.can_add_paper("user-123")

        # Verify
        assert result is False
        mock_redis.get.assert_called_once_with("user:user-123:pending_papers")

    @pytest.mark.asyncio
    async def test_can_add_paper_returns_false_when_exceeds_limit(self, concurrent_control, mock_redis):
        """Test that can_add_paper returns False when count > MAX_CONCURRENT."""
        # Setup: Redis returns "7" (7 pending papers - exceeds limit)
        mock_redis.get = AsyncMock(return_value="7")

        # Execute
        result = await concurrent_control.can_add_paper("user-123")

        # Verify
        assert result is False

    @pytest.mark.asyncio
    async def test_can_add_paper_fails_open_on_redis_error(self, concurrent_control, mock_redis):
        """Test that can_add_paper returns True if Redis check fails (fail-open strategy)."""
        # Setup: Redis raises exception
        mock_redis.get = AsyncMock(side_effect=Exception("Redis connection error"))

        # Execute
        result = await concurrent_control.can_add_paper("user-123")

        # Verify: Should return True (fail-open)
        assert result is True


class TestIncrementPending:
    """Tests for increment_pending method."""

    @pytest.mark.asyncio
    async def test_increment_pending_increases_counter_by_one(self, concurrent_control, mock_redis):
        """Test 3: increment_pending increases counter by 1."""
        # Setup: Redis INCR returns 1 (new value after increment)
        mock_redis.get = AsyncMock(return_value=None)  # No existing count
        mock_redis.incr = AsyncMock(return_value=1)
        mock_redis.expire = AsyncMock()

        # Execute
        result = await concurrent_control.increment_pending("user-123")

        # Verify
        assert result == 1
        mock_redis.incr.assert_called_once_with("user:user-123:pending_papers")
        mock_redis.expire.assert_called_once_with("user:user-123:pending_papers", 3600)

    @pytest.mark.asyncio
    async def test_increment_pending_increases_existing_counter(self, concurrent_control, mock_redis):
        """Test incrementing existing counter."""
        # Setup: Redis shows 2 pending, INCR returns 3
        mock_redis.get = AsyncMock(return_value="2")
        mock_redis.incr = AsyncMock(return_value=3)
        mock_redis.expire = AsyncMock()

        # Execute
        result = await concurrent_control.increment_pending("user-123")

        # Verify
        assert result == 3

    @pytest.mark.asyncio
    async def test_increment_pending_raises_error_when_at_limit(self, concurrent_control, mock_redis):
        """Test that increment_pending raises ValueError when at MAX_CONCURRENT."""
        # Setup: Redis shows 5 pending (at limit)
        mock_redis.get = AsyncMock(return_value="5")

        # Execute & Verify
        with pytest.raises(ValueError, match="has reached concurrent limit of 5"):
            await concurrent_control.increment_pending("user-123")

        # Redis INCR should not be called
        mock_redis.incr.assert_not_called()

    @pytest.mark.asyncio
    async def test_increment_pending_raises_on_redis_error(self, concurrent_control, mock_redis):
        """Test that increment_pending raises exception on Redis error."""
        # Setup: Redis INCR raises exception
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.incr = AsyncMock(side_effect=Exception("Redis error"))

        # Execute & Verify
        with pytest.raises(Exception, match="Redis error"):
            await concurrent_control.increment_pending("user-123")


class TestDecrementPending:
    """Tests for decrement_pending method."""

    @pytest.mark.asyncio
    async def test_decrement_pending_decreases_counter_by_one(self, concurrent_control, mock_redis):
        """Test 4: decrement_pending decreases counter by 1."""
        # Setup: Redis DECR returns 1 (from 2 to 1)
        mock_redis.decr = AsyncMock(return_value=1)

        # Execute
        result = await concurrent_control.decrement_pending("user-123")

        # Verify
        assert result == 1
        mock_redis.decr.assert_called_once_with("user:user-123:pending_papers")

    @pytest.mark.asyncio
    async def test_decrement_pending_deletes_key_when_reaches_zero(self, concurrent_control, mock_redis):
        """Test that decrement_pending deletes key when counter reaches 0."""
        # Setup: Redis DECR returns 0
        mock_redis.decr = AsyncMock(return_value=0)
        mock_redis.delete = AsyncMock()

        # Execute
        result = await concurrent_control.decrement_pending("user-123")

        # Verify
        assert result == 0
        mock_redis.delete.assert_called_once_with("user:user-123:pending_papers")

    @pytest.mark.asyncio
    async def test_decrement_pending_deletes_key_when_negative(self, concurrent_control, mock_redis):
        """Test that decrement_pending handles negative values by deleting key."""
        # Setup: Redis DECR returns -1 (edge case)
        mock_redis.decr = AsyncMock(return_value=-1)
        mock_redis.delete = AsyncMock()

        # Execute
        result = await concurrent_control.decrement_pending("user-123")

        # Verify
        assert result == 0
        mock_redis.delete.assert_called_once_with("user:user-123:pending_papers")

    @pytest.mark.asyncio
    async def test_decrement_pending_raises_on_redis_error(self, concurrent_control, mock_redis):
        """Test that decrement_pending raises exception on Redis error."""
        # Setup: Redis DECR raises exception
        mock_redis.decr = AsyncMock(side_effect=Exception("Redis error"))

        # Execute & Verify
        with pytest.raises(Exception, match="Redis error"):
            await concurrent_control.decrement_pending("user-123")


class TestTTLExpiration:
    """Tests for TTL expiration behavior."""

    @pytest.mark.asyncio
    async def test_counter_expires_after_ttl(self, concurrent_control, mock_redis):
        """Test 5: Counter expires after TTL (1 hour)."""
        # Setup: Verify TTL is set when incrementing
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.incr = AsyncMock(return_value=1)
        mock_redis.expire = AsyncMock()

        # Execute
        await concurrent_control.increment_pending("user-123")

        # Verify: TTL should be set to 3600 seconds (1 hour)
        mock_redis.expire.assert_called_once_with(
            "user:user-123:pending_papers",
            3600  # TTL = 1 hour as specified in D-180
        )

    @pytest.mark.asyncio
    async def test_ttl_is_set_on_each_increment(self, concurrent_control, mock_redis):
        """Test that TTL is refreshed on each increment."""
        # Setup: Multiple increments
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.incr = AsyncMock(return_value=1)
        mock_redis.expire = AsyncMock()

        # Execute first increment
        await concurrent_control.increment_pending("user-123")

        # Setup for second increment
        mock_redis.get = AsyncMock(return_value="1")
        mock_redis.incr = AsyncMock(return_value=2)

        # Execute second increment
        await concurrent_control.increment_pending("user-123")

        # Verify: TTL should be set twice
        assert mock_redis.expire.call_count == 2


class TestGetPendingCount:
    """Tests for get_pending_count method."""

    @pytest.mark.asyncio
    async def test_get_pending_count_returns_zero_when_no_key(self, concurrent_control, mock_redis):
        """Test get_pending_count returns 0 when key doesn't exist."""
        # Setup: Redis returns None
        mock_redis.get = AsyncMock(return_value=None)

        # Execute
        result = await concurrent_control.get_pending_count("user-123")

        # Verify
        assert result == 0

    @pytest.mark.asyncio
    async def test_get_pending_count_returns_current_value(self, concurrent_control, mock_redis):
        """Test get_pending_count returns current counter value."""
        # Setup: Redis returns "3"
        mock_redis.get = AsyncMock(return_value="3")

        # Execute
        result = await concurrent_control.get_pending_count("user-123")

        # Verify
        assert result == 3

    @pytest.mark.asyncio
    async def test_get_pending_count_returns_zero_on_error(self, concurrent_control, mock_redis):
        """Test get_pending_count returns 0 on Redis error."""
        # Setup: Redis raises exception
        mock_redis.get = AsyncMock(side_effect=Exception("Redis error"))

        # Execute
        result = await concurrent_control.get_pending_count("user-123")

        # Verify: Should return 0 on error
        assert result == 0


class TestConcurrentControlIntegration:
    """Integration tests for complete workflow."""

    @pytest.mark.asyncio
    async def test_complete_workflow(self, concurrent_control, mock_redis):
        """Test complete workflow: check -> increment -> check -> decrement."""
        # Step 1: Check (should be allowed)
        mock_redis.get = AsyncMock(return_value=None)
        can_add = await concurrent_control.can_add_paper("user-123")
        assert can_add is True

        # Step 2: Increment
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.incr = AsyncMock(return_value=1)
        mock_redis.expire = AsyncMock()
        count = await concurrent_control.increment_pending("user-123")
        assert count == 1

        # Step 3: Check again (should still be allowed)
        mock_redis.get = AsyncMock(return_value="1")
        can_add = await concurrent_control.can_add_paper("user-123")
        assert can_add is True

        # Step 4: Decrement
        mock_redis.decr = AsyncMock(return_value=0)
        mock_redis.delete = AsyncMock()
        count = await concurrent_control.decrement_pending("user-123")
        assert count == 0

        # Step 5: Final check (should be allowed)
        mock_redis.get = AsyncMock(return_value=None)
        can_add = await concurrent_control.can_add_paper("user-123")
        assert can_add is True