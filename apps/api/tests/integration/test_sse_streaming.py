"""Integration tests for SSE streaming.

Tests SSE connection resilience features:
- Heartbeat maintenance
- Event replay after reconnection
- Graceful disconnect handling

Reference: VALIDATION.md §9.3
"""

import asyncio
import json
from types import SimpleNamespace

import pytest
from app.utils.sse_manager import sse_manager


@pytest.mark.asyncio
class TestSSEStreaming:
    """Integration tests for SSE streaming."""

    async def test_heartbeat(self):
        """Test heartbeat is sent during idle periods.

        Expected:
        - Heartbeat sent every 15 seconds
        - Heartbeat format: event: heartbeat\ndata: {timestamp}\n\n
        """
        async def _idle_business_events():
            if False:
                yield ""
            await asyncio.Future()

        original_interval = sse_manager.HEARTBEAT_INTERVAL
        sse_manager.HEARTBEAT_INTERVAL = 0.01

        try:
            iterator = sse_manager.stream_with_heartbeat(
                "session-heartbeat",
                _idle_business_events(),
            )

            first = await iterator.__anext__()

            assert first.startswith(": heartbeat ")
        finally:
            sse_manager.HEARTBEAT_INTERVAL = original_interval

    async def test_reconnection_replay(self):
        """Test event replay after reconnection.

        Scenario: Client reconnects with Last-Event-ID header
        Expected:
        - Missed events replayed from Redis cache
        - Correct event order
        """
        cached_events = [
            {"event_id": "1", "event_str": "event: message\ndata: {\"idx\":1}\n\n"},
            {"event_id": "2", "event_str": "event: message\ndata: {\"idx\":2}\n\n"},
            {"event_id": "3", "event_str": "event: done\ndata: {\"idx\":3}\n\n"},
        ]

        async def _mock_get_cached_events(_session_id):
            return cached_events

        original_get_cached_events = sse_manager._get_cached_events
        sse_manager._get_cached_events = _mock_get_cached_events

        try:
            replayed = [
                event
                async for event in sse_manager.handle_reconnect("session-replay", "1")
            ]
        finally:
            sse_manager._get_cached_events = original_get_cached_events

        assert replayed == [
            "event: message\ndata: {\"idx\":2}\n\n",
            "event: done\ndata: {\"idx\":3}\n\n",
        ]

    async def test_event_caching(self):
        """Test events are cached in Redis.

        Expected:
        - Events stored with incrementing IDs
        - Max 100 events cached
        - 1-hour TTL
        """
        class _FakeRedisClient:
            def __init__(self):
                self.counters = {}
                self.lists = {}
                self.expiry = {}

            async def incr(self, key):
                self.counters[key] = self.counters.get(key, 0) + 1
                return self.counters[key]

            async def expire(self, key, ttl):
                self.expiry[key] = ttl

            async def lpush(self, key, value):
                self.lists.setdefault(key, []).insert(0, value)

            async def ltrim(self, key, start, end):
                current = self.lists.get(key, [])
                self.lists[key] = current[start : end + 1]

            async def lrange(self, key, start, end):
                current = self.lists.get(key, [])
                if end == -1:
                    end = len(current) - 1
                return current[start : end + 1]

        fake_client = _FakeRedisClient()
        original_redis = sse_manager.redis
        original_max_events = sse_manager.MAX_CACHED_EVENTS
        original_ttl = sse_manager.EVENT_CACHE_TTL
        sse_manager.redis = SimpleNamespace(client=fake_client)
        sse_manager.MAX_CACHED_EVENTS = 3
        sse_manager.EVENT_CACHE_TTL = 60

        try:
            for idx in range(5):
                await sse_manager.store_event(
                    "session-cache",
                    f"event: message\\ndata: {json.dumps({'idx': idx})}\\n\\n",
                )

            cached = await sse_manager._get_cached_events("session-cache")
        finally:
            sse_manager.redis = original_redis
            sse_manager.MAX_CACHED_EVENTS = original_max_events
            sse_manager.EVENT_CACHE_TTL = original_ttl

        assert [item["event_id"] for item in cached] == ["3", "4", "5"]
        assert len(cached) == 3
        assert fake_client.expiry["session:session-cache:events"] == 60
        assert fake_client.expiry["session:session-cache:event_counter"] == 60