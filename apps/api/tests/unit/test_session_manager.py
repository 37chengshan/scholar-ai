"""Unit tests for session manager deletion behavior."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.utils.session_manager import SessionManager


class _SessionContext:
    def __init__(self, db):
        self._db = db

    async def __aenter__(self):
        return self._db

    async def __aexit__(self, exc_type, exc, tb):
        return False


@pytest.mark.asyncio
async def test_delete_session_removes_messages_before_session():
    service = SessionManager()
    session_obj = SimpleNamespace(id="session-1", user_id="user-1")

    db = SimpleNamespace()
    db.execute = AsyncMock(side_effect=[
        SimpleNamespace(scalar_one_or_none=lambda: session_obj),
        SimpleNamespace(rowcount=1),
    ])
    db.commit = AsyncMock()
    db.rollback = AsyncMock()

    service.redis = SimpleNamespace(delete=AsyncMock(), client=None)

    with patch(
        "app.utils.session_manager.AsyncSessionLocal",
        return_value=_SessionContext(db),
    ), patch(
        "app.utils.session_manager.message_service.delete_session_messages",
        AsyncMock(return_value=2),
    ) as mock_delete_messages, patch.object(
        service,
        "_delete_from_redis",
        AsyncMock(),
    ) as mock_delete_redis, patch.object(
        service,
        "_remove_from_user_sessions",
        AsyncMock(),
    ) as mock_remove_user_session:
        deleted = await service.delete_session("session-1")

    assert deleted is True
    mock_delete_messages.assert_awaited_once_with("session-1")
    assert db.execute.await_count == 2
    db.commit.assert_awaited_once()
    mock_delete_redis.assert_awaited_once_with("session-1")
    mock_remove_user_session.assert_awaited_once_with("user-1", "session-1")


@pytest.mark.asyncio
async def test_delete_session_returns_false_when_missing():
    service = SessionManager()

    db = SimpleNamespace()
    db.execute = AsyncMock(return_value=SimpleNamespace(scalar_one_or_none=lambda: None))
    db.commit = AsyncMock()
    db.rollback = AsyncMock()

    service.redis = SimpleNamespace(delete=AsyncMock(), client=None)

    with patch(
        "app.utils.session_manager.AsyncSessionLocal",
        return_value=_SessionContext(db),
    ), patch(
        "app.utils.session_manager.message_service.delete_session_messages",
        AsyncMock(),
    ) as mock_delete_messages:
        deleted = await service.delete_session("missing-session")

    assert deleted is False
    mock_delete_messages.assert_not_awaited()
    db.commit.assert_not_awaited()
