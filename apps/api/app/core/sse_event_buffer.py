"""
SSE Event Buffer for ordered event transmission with replay support.

Provides SSE consistency guarantees:
- Unique UUID + sequential ID per event
- Timestamp for ordering verification
- Async-safe concurrent emit
- Capacity limit (max_events=100) + TTL expiration (ttl_seconds=3600)
- Last-Event-ID replay support for reconnection

Usage:
    buffer = SSEEventBuffer(session_id="chat-123")

    # Emit events
    event = await buffer.emit("message", {"content": "Hello"})
    print(event.to_sse_format())  # SSE formatted output

    # Replay after reconnection
    events = await buffer.get_events_after(last_sequence)
    # or
    events = await buffer.get_events_after_event_id(last_event_id)
"""

import asyncio
import json
import time
import uuid
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class SSEEvent:
    """
    SSE event data structure.

    Attributes:
        id: Unique UUID for the event
        sequence: Monotonically increasing sequence number
        event_type: SSE event type (e.g., 'message', 'tool_use', 'tool_result')
        data: Event payload dictionary
        timestamp: Unix timestamp for ordering verification
        session_id: Session identifier for context
    """

    id: str  # UUID
    sequence: int  # Monotonically increasing
    event_type: str
    data: Dict
    timestamp: float
    session_id: str

    def to_sse_format(self) -> str:
        """
        Convert to SSE format string.

        SSE format:
            id: <uuid>
            event: <event_type>
            data: <json with sequence/timestamp/session_id>

        Returns:
            SSE formatted string with double newline terminator
        """
        lines = [f"id: {self.id}", f"event: {self.event_type}"]

        # Include sequence and timestamp in data for replay support
        enriched_data = {
            **self.data,
            "sequence": self.sequence,
            "timestamp": self.timestamp,
            "session_id": self.session_id,
        }
        lines.append(f"data: {json.dumps(enriched_data)}")

        return "\n".join(lines) + "\n\n"


class SSEEventBuffer:
    """
    SSE event buffer with ordering and replay support.

    Features:
    - Unique UUID + sequential ID per event
    - Timestamp for ordering verification
    - Async-safe concurrent emit (asyncio.Lock)
    - Capacity limit (max_events) with FIFO eviction
    - TTL expiration cleanup
    - Last-Event-ID replay support for reconnection recovery

    Attributes:
        session_id: Session identifier
        max_events: Maximum events to retain (default: 100)
        ttl_seconds: Time-to-live in seconds (default: 3600)

    Example:
        buffer = SSEEventBuffer("session-123", max_events=50, ttl_seconds=1800)

        # Emit event
        event = await buffer.emit("message", {"text": "Hello"})

        # Get SSE format
        sse_string = event.to_sse_format()

        # Replay after reconnection
        missed_events = await buffer.get_events_after(last_sequence)
    """

    def __init__(
        self,
        session_id: str,
        max_events: int = 100,
        ttl_seconds: float = 3600,
    ):
        """
        Initialize SSE event buffer.

        Args:
            session_id: Unique session identifier
            max_events: Maximum number of events to retain (default: 100)
            ttl_seconds: Event time-to-live in seconds (default: 3600 = 1 hour)
        """
        self.session_id = session_id
        self.max_events = max_events
        self.ttl_seconds = ttl_seconds
        self._events: List[SSEEvent] = []
        self._lock = asyncio.Lock()
        self._next_sequence = 0

    async def emit(self, event_type: str, data: Dict) -> SSEEvent:
        """
        Emit a new event with unique ID and sequence.

        Thread-safe via asyncio.Lock. Automatically enforces capacity limit.

        Args:
            event_type: SSE event type (e.g., 'message', 'tool_use')
            data: Event payload dictionary

        Returns:
            The created SSEEvent with unique id, sequence, and timestamp
        """
        async with self._lock:
            # Create event with unique UUID and monotonically increasing sequence
            event = SSEEvent(
                id=str(uuid.uuid4()),
                sequence=self._next_sequence,
                event_type=event_type,
                data=data,
                timestamp=time.time(),
                session_id=self.session_id,
            )
            self._next_sequence += 1

            # Add to buffer
            self._events.append(event)

            # Enforce capacity limit - remove oldest events if exceeded
            if len(self._events) > self.max_events:
                excess = len(self._events) - self.max_events
                self._events = self._events[excess:]

            return event

    async def get_events_after(self, sequence: int) -> List[SSEEvent]:
        """
        Get all events after a given sequence number.

        Used for replay when client reconnects with last known sequence.
        Supports recovery protocol: client sends last received sequence,
        server returns all events with higher sequence numbers.

        Args:
            sequence: The last sequence number client received
                     Use -1 to get all events from start

        Returns:
            List of events with sequence > given sequence (copy, safe to iterate)
        """
        async with self._lock:
            # Filter events after the given sequence
            events = [e for e in self._events if e.sequence > sequence]
            return events.copy()

    async def get_events_after_event_id(self, event_id: str) -> List[SSEEvent]:
        """
        Get all events after a given event ID.

        Supports standard SSE Last-Event-ID header protocol.
        If event_id not found in buffer, returns all events (safe fallback).

        Args:
            event_id: The last event ID (UUID) client received

        Returns:
            List of events after the event with given ID (copy, safe to iterate)
        """
        async with self._lock:
            # Find the event with the given ID to determine its sequence
            target_sequence = None
            for event in self._events:
                if event.id == event_id:
                    target_sequence = event.sequence
                    break

            if target_sequence is None:
                # Event not found (may have been evicted), return all events
                # This is a safe fallback for reconnection
                return self._events.copy()

            # Return events after the found event's sequence
            events = [e for e in self._events if e.sequence > target_sequence]
            return events.copy()

    async def get_all_events(self) -> List[SSEEvent]:
        """
        Get all events in buffer.

        Returns:
            Copy of all events (safe to iterate without lock)
        """
        async with self._lock:
            return self._events.copy()

    async def cleanup_expired(self) -> int:
        """
        Remove events that have exceeded TTL.

        Should be called periodically (e.g., by background task).

        Returns:
            Number of events removed
        """
        async with self._lock:
            current_time = time.time()
            cutoff_time = current_time - self.ttl_seconds

            # Filter out expired events
            original_count = len(self._events)
            self._events = [e for e in self._events if e.timestamp >= cutoff_time]

            return original_count - len(self._events)

    async def clear(self) -> None:
        """
        Clear all events from buffer and reset sequence.

        Used when session ends or buffer needs full reset.
        """
        async with self._lock:
            self._events.clear()
            self._next_sequence = 0

    def get_latest_sequence(self) -> int:
        """
        Get the latest sequence number.

        Non-async for quick access (thread-safe read of last element).

        Returns:
            Latest sequence number, or -1 if buffer is empty
        """
        if not self._events:
            return -1
        return self._events[-1].sequence

    def get_latest_event_id(self) -> Optional[str]:
        """
        Get the latest event ID.

        Non-async for quick access (thread-safe read of last element).
        Useful for SSE id field or Last-Event-ID header.

        Returns:
            Latest event UUID, or None if buffer is empty
        """
        if not self._events:
            return None
        return self._events[-1].id

    def __len__(self) -> int:
        """Get current number of events in buffer."""
        return len(self._events)

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"SSEEventBuffer(session_id={self.session_id}, "
            f"events={len(self._events)}, "
            f"max_events={self.max_events}, "
            f"ttl={self.ttl_seconds}s)"
        )