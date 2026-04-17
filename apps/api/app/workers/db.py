"""Worker-side database helpers.

Keeps Celery task entrypoints thin and centralizes async session usage.
"""

import asyncio
from typing import Awaitable, Callable, TypeVar

from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal

T = TypeVar("T")


async def with_db_session(func: Callable[[AsyncSession], Awaitable[T]]) -> T:
    """Run async work with a managed SQLAlchemy async session."""
    async with AsyncSessionLocal() as db:
        return await func(db)


def run_async(coro: Awaitable[T]) -> T:
    """Run async coroutine from Celery sync task context."""
    return asyncio.run(coro)
