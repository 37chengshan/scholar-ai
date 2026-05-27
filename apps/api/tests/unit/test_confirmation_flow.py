"""Unit tests for the current confirmation flow implementation."""

import json
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest

from app.models.confirmation import ConfirmationState
from app.services.chat_orchestrator import ChatOrchestrator


class TestConfirmationStateModel:
    """Test ConfirmationState model."""

    def test_confirmation_state_creation(self):
        state = ConfirmationState(
            confirmation_id="test-123",
            session_id="session-456",
            user_id="user-789",
            message_id="msg-0001",
            tool_name="delete_paper",
            parameters={"paper_id": "abc"},
            status="pending",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )

        assert state.confirmation_id == "test-123"
        assert state.session_id == "session-456"
        assert state.user_id == "user-789"
        assert state.message_id == "msg-0001"
        assert state.tool_name == "delete_paper"
        assert state.parameters == {"paper_id": "abc"}
        assert state.status == "pending"

    def test_is_expired_false(self):
        state = ConfirmationState(
            confirmation_id="test-123",
            session_id="session-456",
            user_id="user-789",
            tool_name="delete_paper",
            parameters={},
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )

        assert state.is_expired() is False

    def test_is_expired_true(self):
        state = ConfirmationState(
            confirmation_id="test-123",
            session_id="session-456",
            user_id="user-789",
            tool_name="delete_paper",
            parameters={},
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
        )

        assert state.is_expired() is True

    def test_model_dump_json(self):
        state = ConfirmationState(
            confirmation_id="test-123",
            session_id="session-456",
            user_id="user-789",
            message_id="msg-0002",
            tool_name="delete_paper",
            parameters={"paper_id": "abc"},
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )

        json_str = state.model_dump_json()
        data = json.loads(json_str)

        assert data["confirmation_id"] == "test-123"
        assert data["message_id"] == "msg-0002"
        assert data["tool_name"] == "delete_paper"


class TestChatOrchestratorConfirmation:
    """Test ChatOrchestrator confirmation persistence methods."""

    @pytest.fixture
    def orchestrator(self):
        return ChatOrchestrator()

    @pytest.fixture
    def mock_redis(self):
        mock = AsyncMock()
        mock.set = AsyncMock(return_value=True)
        mock.setex = AsyncMock()
        mock.get = AsyncMock()
        mock.sadd = AsyncMock()
        mock.expire = AsyncMock()
        mock.delete = AsyncMock()
        return mock

    @pytest.mark.asyncio
    async def test_handle_confirmation_required(self, orchestrator, mock_redis):
        with patch(
            "app.services.chat_orchestrator.redis.from_url", return_value=mock_redis
        ):
            state = await orchestrator.handle_confirmation_required(
                session_id="session-123",
                user_id="user-456",
                message_id="msg-123",
                tool_name="delete_paper",
                parameters={"paper_id": "abc"},
            )

            assert state.confirmation_id is not None
            assert state.session_id == "session-123"
            assert state.user_id == "user-456"
            assert state.message_id == "msg-123"
            assert state.tool_name == "delete_paper"
            assert state.parameters == {"paper_id": "abc"}
            assert state.status == "pending"
            assert state.is_expired() is False

            mock_redis.setex.assert_called_once()
            mock_redis.sadd.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_confirmation_state_valid(self, orchestrator, mock_redis):
        state = ConfirmationState(
            confirmation_id="test-123",
            session_id="session-456",
            user_id="user-789",
            message_id="msg-123",
            tool_name="delete_paper",
            parameters={"paper_id": "abc"},
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )

        mock_redis.get.return_value = state.model_dump_json()

        with patch(
            "app.services.chat_orchestrator.redis.from_url", return_value=mock_redis
        ):
            retrieved = await orchestrator.get_confirmation_state("test-123")

            assert retrieved is not None
            assert retrieved.confirmation_id == "test-123"
            assert retrieved.message_id == "msg-123"
            assert retrieved.tool_name == "delete_paper"

    @pytest.mark.asyncio
    async def test_get_confirmation_state_expired(self, orchestrator, mock_redis):
        mock_redis.get.return_value = None

        with patch(
            "app.services.chat_orchestrator.redis.from_url", return_value=mock_redis
        ):
            retrieved = await orchestrator.get_confirmation_state("test-123")

            assert retrieved is None

    @pytest.mark.asyncio
    async def test_update_confirmation_status(self, orchestrator, mock_redis):
        state = ConfirmationState(
            confirmation_id="test-123",
            session_id="session-456",
            user_id="user-789",
            message_id="msg-123",
            tool_name="delete_paper",
            parameters={},
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )

        mock_redis.get.return_value = state.model_dump_json()

        with patch(
            "app.services.chat_orchestrator.redis.from_url", return_value=mock_redis
        ):
            await orchestrator.update_confirmation_status("test-123", "approved")

            mock_redis.setex.assert_called()


class TestResumeWithConfirmation:
    """Test resume_with_confirmation streaming."""

    @pytest.fixture
    def orchestrator(self):
        return ChatOrchestrator()

    @pytest.fixture
    def mock_redis(self):
        mock = AsyncMock()
        mock.set = AsyncMock(return_value=True)
        mock.get = AsyncMock()
        mock.setex = AsyncMock()
        mock.delete = AsyncMock()
        return mock

    @pytest.fixture
    def mock_runner(self):
        mock = AsyncMock()
        mock.resume_with_tool = AsyncMock(
            return_value={
                "success": True,
                "data": {"deleted": True},
            }
        )
        return mock

    @pytest.mark.asyncio
    async def test_resume_with_confirmation_approved(
        self, orchestrator, mock_redis, mock_runner
    ):
        state = ConfirmationState(
            confirmation_id="test-123",
            session_id="session-456",
            user_id="user-789",
            message_id="msg-123",
            tool_name="delete_paper",
            parameters={"paper_id": "abc"},
            status="pending",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )

        mock_redis.get.return_value = state.model_dump_json()

        with patch(
            "app.services.chat_orchestrator.redis.from_url", return_value=mock_redis
        ):
            with patch(
                "app.services.chat_orchestrator.ChatOrchestrator._initialize_agent_components",
                return_value=(mock_runner, None, None, None),
            ):
                events = []
                async for event in orchestrator.resume_with_confirmation(
                    "test-123", approved=True
                ):
                    events.append(event)

                assert len(events) >= 3
                assert "tool_call" in events[0]
                assert "tool_result" in events[1]
                assert "done" in events[-1]
                assert '"message_id": "msg-123"' in events[0]
                assert mock_redis.delete.await_count == 2

    @pytest.mark.asyncio
    async def test_resume_with_confirmation_rejected(self, orchestrator, mock_redis):
        state = ConfirmationState(
            confirmation_id="test-123",
            session_id="session-456",
            user_id="user-789",
            message_id="msg-456",
            tool_name="delete_paper",
            parameters={},
            status="pending",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )

        mock_redis.get.return_value = state.model_dump_json()

        with patch(
            "app.services.chat_orchestrator.redis.from_url", return_value=mock_redis
        ):
            events = []
            async for event in orchestrator.resume_with_confirmation(
                "test-123", approved=False
            ):
                events.append(event)

            assert len(events) >= 2
            assert "tool_rejected" in events[0]
            assert "done" in events[-1]
            assert '"message_id": "msg-456"' in events[0]
            assert mock_redis.delete.await_count == 2

    @pytest.mark.asyncio
    async def test_resume_with_confirmation_expired(self, orchestrator, mock_redis):
        state = ConfirmationState(
            confirmation_id="test-123",
            session_id="session-456",
            user_id="user-789",
            message_id="msg-expired",
            tool_name="delete_paper",
            parameters={},
            status="pending",
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1),  # Expired
        )

        mock_redis.get.return_value = state.model_dump_json()

        with patch(
            "app.services.chat_orchestrator.redis.from_url", return_value=mock_redis
        ):
            events = []
            async for event in orchestrator.resume_with_confirmation(
                "test-123", approved=True
            ):
                events.append(event)

            assert len(events) == 1
            assert "error" in events[0]
            assert "expired" in events[0].lower()

    @pytest.mark.asyncio
    async def test_resume_with_confirmation_not_found(self, orchestrator, mock_redis):
        mock_redis.get.return_value = None

        with patch(
            "app.services.chat_orchestrator.redis.from_url", return_value=mock_redis
        ):
            events = []
            async for event in orchestrator.resume_with_confirmation(
                "test-123", approved=True
            ):
                events.append(event)

            assert len(events) == 1
            assert "error" in events[0]
            assert "not found" in events[0].lower()
