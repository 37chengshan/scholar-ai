"""Shared asyncio loop runner for Celery sync tasks.

Celery workers in this project execute synchronous task entrypoints that need
to run async code. Using one shared loop per worker process avoids cross-loop
reuse of pooled async DB connections.
"""

import asyncio
from typing import Optional

_worker_loop: Optional[asyncio.AbstractEventLoop] = None


def run_async_in_worker_loop(coro):
    """Run a coroutine on a single process-local event loop."""
    global _worker_loop
    if _worker_loop is None or _worker_loop.is_closed():
        _worker_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(_worker_loop)
    return _worker_loop.run_until_complete(coro)
