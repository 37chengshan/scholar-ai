"""Unit tests for database.py - Neo4j explicit disable logic.

Tests for NEO4J_DISABLED environment variable handling:
- NEO4J_DISABLED=true: skip connection, log info
- NEO4J_DISABLED=false: try connection, warn on failure
- Redis: must raise on failure (required service)
"""

import os
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from app.core.database import init_databases, close_databases, neo4j_db, redis_db


class TestNeo4jExplicitDisable:
    """Tests for NEO4J_DISABLED environment variable logic."""

    @pytest.mark.asyncio
    async def test_neo4j_disabled_true_skips_connection(self):
        """When NEO4J_DISABLED=true, neo4j_db.connect() should not be called."""
        with patch.dict(os.environ, {"NEO4J_DISABLED": "true"}, clear=False):
            # Mock neo4j_db.connect to track if it was called
            with patch.object(neo4j_db, "connect", new_callable=AsyncMock) as mock_connect:
                # Mock redis_db.connect to allow the test to proceed
                with patch.object(redis_db, "connect", new_callable=AsyncMock) as mock_redis_connect:
                    await init_databases()

                    # neo4j_db.connect should NOT have been called
                    mock_connect.assert_not_called()

                    # redis_db.connect should have been called (required service)
                    mock_redis_connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_neo4j_disabled_false_attempts_connection(self):
        """When NEO4J_DISABLED=false, neo4j_db.connect() should be attempted."""
        with patch.dict(os.environ, {"NEO4J_DISABLED": "false"}, clear=False):
            # Mock neo4j_db.connect to succeed
            with patch.object(neo4j_db, "connect", new_callable=AsyncMock) as mock_connect:
                with patch.object(redis_db, "connect", new_callable=AsyncMock) as mock_redis_connect:
                    await init_databases()

                    # neo4j_db.connect should have been called
                    mock_connect.assert_called_once()

                    # redis_db.connect should have been called
                    mock_redis_connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_neo4j_connection_failure_with_disabled_false_warns_not_raises(self):
        """When NEO4J_DISABLED=false and connection fails, should warn not raise."""
        with patch.dict(os.environ, {"NEO4J_DISABLED": "false"}, clear=False):
            # Mock neo4j_db.connect to raise an exception
            with patch.object(neo4j_db, "connect", new_callable=AsyncMock) as mock_connect:
                mock_connect.side_effect = Exception("Connection refused")

                with patch.object(redis_db, "connect", new_callable=AsyncMock) as mock_redis_connect:
                    # Should NOT raise - just warn
                    await init_databases()

                    # neo4j_db.connect was attempted
                    mock_connect.assert_called_once()

                    # redis_db.connect should still succeed
                    mock_redis_connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_neo4j_disabled_unset_attempts_connection(self):
        """When NEO4J_DISABLED is not set, should attempt connection (default behavior)."""
        # Ensure NEO4J_DISABLED is not in environment
        env_copy = os.environ.copy()
        if "NEO4J_DISABLED" in env_copy:
            del env_copy["NEO4J_DISABLED"]

        with patch.dict(os.environ, env_copy, clear=True):
            with patch.object(neo4j_db, "connect", new_callable=AsyncMock) as mock_connect:
                with patch.object(redis_db, "connect", new_callable=AsyncMock) as mock_redis_connect:
                    await init_databases()

                    # neo4j_db.connect should have been called
                    mock_connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_databases_with_neo4j_disabled_true(self):
        """When NEO4J_DISABLED=true, neo4j_db.disconnect() should not be called."""
        with patch.dict(os.environ, {"NEO4J_DISABLED": "true"}, clear=False):
            with patch.object(neo4j_db, "disconnect", new_callable=AsyncMock) as mock_disconnect:
                with patch.object(redis_db, "disconnect", new_callable=AsyncMock) as mock_redis_disconnect:
                    await close_databases()

                    # neo4j_db.disconnect should NOT have been called
                    mock_disconnect.assert_not_called()

                    # redis_db.disconnect should have been called
                    mock_redis_disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_databases_with_neo4j_disabled_false(self):
        """When NEO4J_DISABLED=false, neo4j_db.disconnect() should be called."""
        with patch.dict(os.environ, {"NEO4J_DISABLED": "false"}, clear=False):
            with patch.object(neo4j_db, "disconnect", new_callable=AsyncMock) as mock_disconnect:
                with patch.object(redis_db, "disconnect", new_callable=AsyncMock) as mock_redis_disconnect:
                    await close_databases()

                    # neo4j_db.disconnect should have been called
                    mock_disconnect.assert_called_once()

                    # redis_db.disconnect should have been called
                    mock_redis_disconnect.assert_called_once()


class TestRedisRequiredService:
    """Tests for Redis connection - required service behavior."""

    @pytest.mark.asyncio
    async def test_redis_failure_raises_exception(self):
        """Redis connection failure must raise - it's a required service."""
        with patch.dict(os.environ, {"NEO4J_DISABLED": "true"}, clear=False):
            # Mock neo4j_db.connect to skip
            with patch.object(neo4j_db, "connect", new_callable=AsyncMock) as mock_neo4j:
                # Mock redis_db.connect to raise
                with patch.object(redis_db, "connect", new_callable=AsyncMock) as mock_redis:
                    mock_redis.side_effect = Exception("Redis connection refused")

                    # Should raise because Redis is required
                    with pytest.raises(Exception, match="Redis connection refused"):
                        await init_databases()

                    # neo4j should have been skipped
                    mock_neo4j.assert_not_called()

                    # redis attempt was made
                    mock_redis.assert_called_once()