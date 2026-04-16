"""Shared event loop runner for synchronous Celery workers.

Celery workers run task callables synchronously. When these callables need to
run async coroutines, they must reuse one process-local event loop. Otherwise,
async DB connections (e.g. asyncpg) can be created on one loop and reused from
another, which raises runtime errors.
"""

import asyncio
from typing import Any, Coroutine, Optional

_PROCESS_EVENT_LOOP: Optional[asyncio.AbstractEventLoop] = None


def run_in_worker_event_loop(coro: Coroutine[Any, Any, Any]) -> Any:
    """Run a coroutine on a process-local persistent event loop."""
    global _PROCESS_EVENT_LOOP

    if _PROCESS_EVENT_LOOP is None or _PROCESS_EVENT_LOOP.is_closed():
        _PROCESS_EVENT_LOOP = asyncio.new_event_loop()

    asyncio.set_event_loop(_PROCESS_EVENT_LOOP)
    return _PROCESS_EVENT_LOOP.run_until_complete(coro)
