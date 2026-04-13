"""
Unit tests for SSEEventBuffer.

Tests SSE consistency guarantees:
- Unique UUID + sequential ID per event
- Timestamp for ordering verification
- Async-safe concurrent emit
- Capacity limit + TTL
- Last-Event-ID replay support
"""

import asyncio
import json
import time
import uuid
from typing import List, Optional
from unittest.mock import AsyncMock, patch

import pytest

from app.core.sse_event_buffer import SSEEvent, SSEEventBuffer


class TestSSEEventBufferBasics:
    """Test basic SSEEventBuffer functionality."""

    def test_init_with_defaults(self):
        """Test initialization with default parameters."""
        buffer = SSEEventBuffer(session_id="test-session")
        assert buffer.session_id == "test-session"
        assert buffer.max_events == 100
        assert buffer.ttl_seconds == 3600
        assert buffer._next_sequence == 0

    def test_init_with_custom_params(self):
        """Test initialization with custom parameters."""
        buffer = SSEEventBuffer(
            session_id="custom-session",
            max_events=50,
            ttl_seconds=1800,
        )
        assert buffer.session_id == "custom-session"
        assert buffer.max_events == 50
        assert buffer.ttl_seconds == 1800

    @pytest.mark.asyncio
    async def test_emit_creates_event_with_uuid_and_sequence(self):
        """Test that emit creates event with unique UUID and sequence."""
        buffer = SSEEventBuffer(session_id="test-session")

        event = await buffer.emit("message", {"content": "Hello"})

        # Verify UUID format
        assert isinstance(event.id, str)
        uuid.UUID(event.id)  # Validates UUID format

        # Verify sequence starts at 0
        assert event.sequence == 0

        # Verify timestamp
        assert isinstance(event.timestamp, float)
        assert event.timestamp > 0

        # Verify event data
        assert event.event_type == "message"
        assert event.data == {"content": "Hello"}
        assert event.session_id == "test-session"

    @pytest.mark.asyncio
    async def test_sequence_increments_monotonically(self):
        """Test that sequence numbers increment monotonically."""
        buffer = SSEEventBuffer(session_id="test-session")

        events = []
        for i in range(5):
            event = await buffer.emit("message", {"index": i})
            events.append(event)

        # Verify sequences are sequential
        sequences = [e.sequence for e in events]
        assert sequences == [0, 1, 2, 3, 4]

        # Verify all IDs are unique
        ids = [e.id for e in events]
        assert len(ids) == len(set(ids))

    @pytest.mark.asyncio
    async def test_multiple_events_ordered_by_sequence(self):
        """Test that events are stored in sequence order."""
        buffer = SSEEventBuffer(session_id="test-session")

        # Emit different event types
        await buffer.emit("message", {"text": "First"})
        await buffer.emit("tool_use", {"tool": "search"})
        await buffer.emit("tool_result", {"result": "data"})
        await buffer.emit("message", {"text": "Last"})

        all_events = await buffer.get_all_events()

        # Verify ordering
        assert len(all_events) == 4
        assert all_events[0].event_type == "message"
        assert all_events[1].event_type == "tool_use"
        assert all_events[2].event_type == "tool_result"
        assert all_events[3].event_type == "message"

        # Verify sequences are in order
        for i, event in enumerate(all_events):
            assert event.sequence == i


class TestSSEEventBufferReplay:
    """Test SSE replay functionality for reconnection."""

    @pytest.mark.asyncio
    async def test_get_events_after_sequence(self):
        """Test replay by sequence number."""
        buffer = SSEEventBuffer(session_id="test-session")

        # Emit 5 events
        for i in range(5):
            await buffer.emit("message", {"index": i})

        # Get events after sequence 2
        replay_events = await buffer.get_events_after(2)

        # Should return events with sequences 3, 4
        assert len(replay_events) == 2
        assert replay_events[0].sequence == 3
        assert replay_events[1].sequence == 4

    @pytest.mark.asyncio
    async def test_get_events_after_sequence_zero(self):
        """Test replay from beginning (sequence -1 or 0)."""
        buffer = SSEEventBuffer(session_id="test-session")

        # Emit events
        for i in range(3):
            await buffer.emit("message", {"index": i})

        # Get all events (after -1 means from start)
        replay_events = await buffer.get_events_after(-1)
        assert len(replay_events) == 3

        # Get events after 0 (should return sequences 1, 2)
        replay_events = await buffer.get_events_after(0)
        assert len(replay_events) == 2

    @pytest.mark.asyncio
    async def test_get_events_after_event_id(self):
        """Test replay by event ID (Last-Event-ID standard)."""
        buffer = SSEEventBuffer(session_id="test-session")

        # Emit events
        events = []
        for i in range(5):
            event = await buffer.emit("message", {"index": i})
            events.append(event)

        # Get events after the second event's ID
        replay_events = await buffer.get_events_after_event_id(events[1].id)

        # Should return events after sequence 1
        assert len(replay_events) == 3
        assert replay_events[0].sequence == 2
        assert replay_events[1].sequence == 3
        assert replay_events[2].sequence == 4

    @pytest.mark.asyncio
    async def test_get_events_after_unknown_event_id(self):
        """Test replay with unknown event ID returns all events."""
        buffer = SSEEventBuffer(session_id="test-session")

        # Emit events
        for i in range(3):
            await buffer.emit("message", {"index": i})

        # Get events after unknown ID
        unknown_id = str(uuid.uuid4())
        replay_events = await buffer.get_events_after_event_id(unknown_id)

        # Should return all events (safe fallback)
        assert len(replay_events) == 3

    @pytest.mark.asyncio
    async def test_sse_format_includes_sequence_and_timestamp(self):
        """Test SSE format output includes metadata for replay."""
        buffer = SSEEventBuffer(session_id="test-session-123")

        event = await buffer.emit("message", {"content": "Hello world"})

        sse_output = event.to_sse_format()

        # Verify SSE format structure
        assert f"id: {event.id}" in sse_output
        assert "event: message" in sse_output
        assert "data:" in sse_output

        # Verify metadata in data
        import json

        # Extract data line
        data_line = None
        for line in sse_output.split("\n"):
            if line.startswith("data: "):
                data_line = line[6:]
                break

        assert data_line is not None
        data_obj = json.loads(data_line)

        # Verify enriched metadata
        assert data_obj["sequence"] == event.sequence
        assert data_obj["timestamp"] == event.timestamp
        assert data_obj["session_id"] == "test-session-123"
        assert data_obj["content"] == "Hello world"

    @pytest.mark.asyncio
    async def test_empty_buffer_replay(self):
        """Test replay on empty buffer."""
        buffer = SSEEventBuffer(session_id="test-session")

        # Get events from empty buffer
        replay_by_seq = await buffer.get_events_after(0)
        replay_by_id = await buffer.get_events_after_event_id(str(uuid.uuid4()))

        assert len(replay_by_seq) == 0
        assert len(replay_by_id) == 0


class TestSSEEventBufferCapacity:
    """Test capacity limit functionality."""

    @pytest.mark.asyncio
    async def test_max_events_limit(self):
        """Test that buffer enforces max_events limit."""
        buffer = SSEEventBuffer(session_id="test-session", max_events=5)

        # Emit 10 events
        for i in range(10):
            await buffer.emit("message", {"index": i})

        all_events = await buffer.get_all_events()

        # Should only keep last 5 events
        assert len(all_events) == 5

        # Should have sequences 5-9 (oldest 0-4 removed)
        sequences = [e.sequence for e in all_events]
        assert sequences == [5, 6, 7, 8, 9]

    @pytest.mark.asyncio
    async def test_capacity_limit_preserves_ordering(self):
        """Test that capacity limit preserves sequence ordering."""
        buffer = SSEEventBuffer(session_id="test-session", max_events=3)

        # Emit events
        events = []
        for i in range(10):
            event = await buffer.emit("message", {"index": i})
            events.append(event)

        all_events = await buffer.get_all_events()

        # Verify ordering is preserved
        assert len(all_events) == 3
        for i in range(len(all_events) - 1):
            assert all_events[i].sequence < all_events[i + 1].sequence

    @pytest.mark.asyncio
    async def test_get_events_after_respects_capacity(self):
        """Test replay respects removed events."""
        buffer = SSEEventBuffer(session_id="test-session", max_events=5)

        # Emit 10 events (keeps last 5)
        for i in range(10):
            await buffer.emit("message", {"index": i})

        # Request replay from sequence 3 (already removed)
        replay_events = await buffer.get_events_after(3)

        # Should return events from sequence 5 onwards
        assert len(replay_events) == 5
        assert replay_events[0].sequence == 5

    @pytest.mark.asyncio
    async def test_default_capacity_is_100(self):
        """Test that default capacity is 100 events."""
        buffer = SSEEventBuffer(session_id="test-session")

        # Emit 150 events
        for i in range(150):
            await buffer.emit("message", {"index": i})

        all_events = await buffer.get_all_events()

        # Should keep last 100
        assert len(all_events) == 100
        assert all_events[0].sequence == 50


class TestSSEEventBufferTTL:
    """Test TTL expiration functionality."""

    @pytest.mark.asyncio
    async def test_ttl_expiration_removes_old_events(self):
        """Test that cleanup removes expired events."""
        buffer = SSEEventBuffer(session_id="test-session", ttl_seconds=1.0)

        # Emit events
        event1 = await buffer.emit("message", {"text": "Old"})
        event2 = await buffer.emit("message", {"text": "New"})

        # Wait for TTL to expire for first event
        await asyncio.sleep(1.5)

        # Emit another event (still within TTL)
        event3 = await buffer.emit("message", {"text": "Fresh"})

        # Cleanup expired events
        removed_count = await buffer.cleanup_expired()

        # Should remove expired events
        assert removed_count >= 1

        all_events = await buffer.get_all_events()
        # Fresh event should still be present
        assert event3 in all_events or any(e.id == event3.id for e in all_events)

    @pytest.mark.asyncio
    async def test_ttl_cleanup_keeps_recent_events(self):
        """Test that cleanup keeps recent events."""
        buffer = SSEEventBuffer(session_id="test-session", ttl_seconds=10.0)

        # Emit events
        for i in range(5):
            await buffer.emit("message", {"index": i})

        # Immediate cleanup (all events recent)
        removed_count = await buffer.cleanup_expired()

        # Should not remove any events
        assert removed_count == 0

        all_events = await buffer.get_all_events()
        assert len(all_events) == 5

    @pytest.mark.asyncio
    async def test_default_ttl_is_3600_seconds(self):
        """Test that default TTL is 1 hour."""
        buffer = SSEEventBuffer(session_id="test-session")
        assert buffer.ttl_seconds == 3600


class TestSSEEventBufferConsistency:
    """Test concurrent consistency."""

    @pytest.mark.asyncio
    async def test_concurrent_emit_maintains_ordering(self):
        """Test that concurrent emits maintain sequence ordering."""
        buffer = SSEEventBuffer(session_id="test-session")

        # Emit events concurrently
        async def emit_event(index: int):
            return await buffer.emit("message", {"index": index})

        # Run 20 concurrent emits
        tasks = [emit_event(i) for i in range(20)]
        events = await asyncio.gather(*tasks)

        # Get all events from buffer
        all_events = await buffer.get_all_events()

        # Verify all events present
        assert len(all_events) == 20

        # Verify sequences are unique and in valid range
        sequences = sorted([e.sequence for e in all_events])
        assert sequences == list(range(20))

        # Verify all IDs are unique
        ids = [e.id for e in all_events]
        assert len(ids) == len(set(ids))

    @pytest.mark.asyncio
    async def test_concurrent_emit_and_read_consistency(self):
        """Test consistency when reading during concurrent emits."""
        buffer = SSEEventBuffer(session_id="test-session")

        results = []

        async def emit_events():
            for i in range(10):
                await buffer.emit("message", {"emit_index": i})
                await asyncio.sleep(0.01)

        async def read_events():
            for i in range(10):
                events = await buffer.get_all_events()
                results.append(len(events))
                await asyncio.sleep(0.01)

        # Run emit and read concurrently
        await asyncio.gather(emit_events(), read_events())

        # Final state should be consistent
        all_events = await buffer.get_all_events()
        assert len(all_events) == 10

    @pytest.mark.asyncio
    async def test_concurrent_replay_consistency(self):
        """Test replay consistency under concurrent access."""
        buffer = SSEEventBuffer(session_id="test-session")

        # Pre-populate buffer
        for i in range(20):
            await buffer.emit("message", {"index": i})

        # Concurrent replays
        async def replay_from(seq: int):
            return await buffer.get_events_after(seq)

        tasks = [replay_from(i) for i in range(10)]
        results = await asyncio.gather(*tasks)

        # Verify each result is correct
        for i, events in enumerate(results):
            expected_count = 20 - i - 1
            assert len(events) == expected_count


class TestSSEEventBufferHelpers:
    """Test helper methods."""

    @pytest.mark.asyncio
    async def test_get_latest_sequence(self):
        """Test get_latest_sequence helper."""
        buffer = SSEEventBuffer(session_id="test-session")

        # Empty buffer
        assert buffer.get_latest_sequence() == -1

        # After emits
        for i in range(5):
            await buffer.emit("message", {"index": i})

        assert buffer.get_latest_sequence() == 4

    @pytest.mark.asyncio
    async def test_get_latest_event_id(self):
        """Test get_latest_event_id helper."""
        buffer = SSEEventBuffer(session_id="test-session")

        # Empty buffer
        assert buffer.get_latest_event_id() is None

        # After emits
        events = []
        for i in range(3):
            event = await buffer.emit("message", {"index": i})
            events.append(event)

        latest_id = buffer.get_latest_event_id()
        assert latest_id == events[-1].id

    @pytest.mark.asyncio
    async def test_clear_buffer(self):
        """Test clear method."""
        buffer = SSEEventBuffer(session_id="test-session")

        # Emit events
        for i in range(10):
            await buffer.emit("message", {"index": i})

        # Clear buffer
        await buffer.clear()

        # Verify empty
        all_events = await buffer.get_all_events()
        assert len(all_events) == 0

        # Verify sequence reset
        assert buffer._next_sequence == 0
        assert buffer.get_latest_sequence() == -1