"""SSE connection resilience manager.

Provides:
- Heartbeat maintenance (15-second intervals)
- Event replay after reconnection
- Redis event caching (1-hour TTL)
- Graceful disconnect handling
"""

import asyncio
import json
import time
import uuid
from datetime import datetime, timezone
from typing import AsyncIterator, Dict, List, Optional

from app.core.database import redis_db
from app.utils.logger import logger


class SSEConnectionManager:
    """Manages SSE connection resilience with heartbeat and event replay.

    Features:
    - Send heartbeat every 15 seconds if no business events
    - Cache recent 100 events per session in Redis
    - Replay missed events after reconnection
    - Handle client disconnect gracefully

    Redis Keys:
    - session:{session_id}:events → List of recent events (TTL: 1 hour)
    - session:{session_id}:event_counter → Event ID counter (TTL: 1 hour)
    """

    HEARTBEAT_INTERVAL = 15  # seconds
    MAX_CACHED_EVENTS = 100
    EVENT_CACHE_TTL = 3600  # 1 hour

    def __init__(self):
        """Initialize SSE connection manager."""
        self.redis = redis_db

    async def stream_with_heartbeat(
        self,
        session_id: str,
        generator: AsyncIterator[str]
    ) -> AsyncIterator[str]:
        """Merge business events with heartbeat events.

        Args:
            session_id: Session ID for event caching
            generator: Business event generator

        Yields:
            SSE event strings (business or heartbeat)
        """
        last_heartbeat = time.time()

        try:
            async for event in generator:
                # Update last event time
                last_heartbeat = time.time()

                # Cache event
                await self.store_event(session_id, event)

                yield event

                # Check if we should send a heartbeat
                elapsed = time.time() - last_heartbeat
                if elapsed >= self.HEARTBEAT_INTERVAL:
                    yield f"event: heartbeat\ndata: {int(time.time())}\n\n"
                    last_heartbeat = time.time()

        except Exception as e:
            logger.error("Stream with heartbeat error", error=str(e))
            raise

    async def handle_reconnect(
        self,
        session_id: str,
        last_event_id: str
    ) -> AsyncIterator[str]:
        """Replay missed events after reconnection.

        Args:
            session_id: Session ID
            last_event_id: Last event ID received by client

        Yields:
            Missed SSE events
        """
        try:
            # Get cached events
            cached_events = await self._get_cached_events(session_id)

            # Find events after last_event_id
            found_last = False
            replayed = 0

            for event_data in cached_events:
                event_id = event_data.get("event_id")

                if found_last:
                    # Replay this event
                    yield event_data.get("event_str")
                    replayed += 1

                if event_id == last_event_id:
                    found_last = True

            logger.info(
                "Reconnected SSE stream",
                session_id=session_id,
                last_event_id=last_event_id,
                replayed=replayed
            )

        except Exception as e:
            logger.error(
                "Reconnect error",
                error=str(e),
                session_id=session_id
            )

    async def store_event(self, session_id: str, event_str: str) -> str:
        """Cache event in Redis for replay after reconnection.

        Args:
            session_id: Session ID
            event_str: SSE event string

        Returns:
            Event ID
        """
        try:
            # Generate event ID
            event_id = str(uuid.uuid4())

            # Get event counter
            counter_key = f"session:{session_id}:event_counter"
            if self.redis.client:
                event_counter = await self.redis.client.incr(counter_key)
                await self.redis.client.expire(counter_key, self.EVENT_CACHE_TTL)
            else:
                event_counter = int(time.time() * 1000)

            event_id = f"{event_counter}"

            # Store event
            event_data = {
                "event_id": event_id,
                "event_str": event_str,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

            cache_key = f"session:{session_id}:events"

            if self.redis.client:
                # Add to list
                await self.redis.client.lpush(cache_key, json.dumps(event_data))

                # Keep only last 100 events
                await self.redis.client.ltrim(cache_key, 0, self.MAX_CACHED_EVENTS - 1)

                # Set TTL
                await self.redis.client.expire(cache_key, self.EVENT_CACHE_TTL)

            logger.debug(
                "Cached SSE event",
                session_id=session_id,
                event_id=event_id
            )

            return event_id

        except Exception as e:
            logger.error(
                "Failed to cache event",
                error=str(e),
                session_id=session_id
            )
            return ""

    # Private helper methods

    async def _heartbeat_loop(self) -> None:
        """Sleep for HEARTBEAT_INTERVAL seconds."""
        await asyncio.sleep(self.HEARTBEAT_INTERVAL)

    async def _collect_generator(self, generator: AsyncIterator[str]) -> List[str]:
        """Collect all events from generator into a list.

        Args:
            generator: Async generator of SSE events

        Returns:
            List of SSE event strings
        """
        events = []
        async for event in generator:
            events.append(event)
        return events

    async def _get_cached_events(self, session_id: str) -> List[Dict]:
        """Retrieve cached events from Redis.

        Args:
            session_id: Session ID

        Returns:
            List of cached event data (oldest first)
        """
        try:
            cache_key = f"session:{session_id}:events"

            if self.redis.client:
                # Get all events (Redis stores newest first, so reverse)
                cached = await self.redis.client.lrange(cache_key, 0, -1)

                # Parse and reverse (oldest first)
                events = []
                for event_json in reversed(cached):
                    try:
                        event_data = json.loads(event_json)
                        events.append(event_data)
                    except:
                        pass

                return events

            return []

        except Exception as e:
            logger.error(
                "Failed to get cached events",
                error=str(e),
                session_id=session_id
            )
            return []


# Singleton instance
sse_manager = SSEConnectionManager()