"""Unit tests for Sprint 3: Confirmation mechanism closure.

Tests:
- ConfirmationState persistence in Redis
- handle_confirmation_required creates and stores confirmation
- get_confirmation_state retrieves valid confirmation
- resume_with_confirmation streams tool execution events

Per Sprint 3: Backend Confirmation持久化与恢复.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone, timedelta
import json

from app.models.confirmation import ConfirmationState
from app.services.chat_orchestrator import ChatOrchestrator
from app.models.chat import SSEEventType


class TestConfirmationStateModel:
    """Test ConfirmationState model."""

    def test_confirmation_state_creation(self):
        """Test creating ConfirmationState."""
        state = ConfirmationState(
            confirmation_id="test-123",
            session_id="session-456",
            user_id="user-789",
            tool_name="delete_paper",
            parameters={"paper_id": "abc"},
            status="pending",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )

        assert state.confirmation_id == "test-123"
        assert state.session_id == "session-456"
        assert state.user_id == "user-789"
        assert state.tool_name == "delete_paper"
        assert state.parameters == {"paper_id": "abc"}
        assert state.status == "pending"

    def test_is_expired_false(self):
        """Test is_expired returns False for valid confirmation."""
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
        """Test is_expired returns True for expired confirmation."""
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
        """Test serialization to JSON."""
        state = ConfirmationState(
            confirmation_id="test-123",
            session_id="session-456",
            user_id="user-789",
            tool_name="delete_paper",
            parameters={"paper_id": "abc"},
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )

        json_str = state.model_dump_json()
        data = json.loads(json_str)

        assert data["confirmation_id"] == "test-123"
        assert data["tool_name"] == "delete_paper"


class TestChatOrchestratorConfirmation:
    """Test ChatOrchestrator confirmation persistence methods."""

    @pytest.fixture
    def orchestrator(self):
        """Create ChatOrchestrator instance."""
        return ChatOrchestrator()

    @pytest.fixture
    def mock_redis(self):
        """Create mock Redis client."""
        mock = AsyncMock()
        mock.setex = AsyncMock()
        mock.get = AsyncMock()
        mock.sadd = AsyncMock()
        mock.expire = AsyncMock()
        mock.delete = AsyncMock()
        return mock

    @pytest.mark.asyncio
    async def test_handle_confirmation_required(self, orchestrator, mock_redis):
        """Test handle_confirmation_required creates and stores confirmation."""
        with patch(
            "app.services.chat_orchestrator.redis.from_url", return_value=mock_redis
        ):
            state = await orchestrator.handle_confirmation_required(
                session_id="session-123",
                user_id="user-456",
                tool_name="delete_paper",
                parameters={"paper_id": "abc"},
            )

            assert state.confirmation_id is not None
            assert state.session_id == "session-123"
            assert state.user_id == "user-456"
            assert state.tool_name == "delete_paper"
            assert state.parameters == {"paper_id": "abc"}
            assert state.status == "pending"
            assert state.is_expired() is False

            # Verify Redis calls
            mock_redis.setex.assert_called_once()
            mock_redis.sadd.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_confirmation_state_valid(self, orchestrator, mock_redis):
        """Test get_confirmation_state retrieves valid confirmation."""
        state = ConfirmationState(
            confirmation_id="test-123",
            session_id="session-456",
            user_id="user-789",
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
            assert retrieved.tool_name == "delete_paper"

    @pytest.mark.asyncio
    async def test_get_confirmation_state_expired(self, orchestrator, mock_redis):
        """Test get_confirmation_state returns None for expired confirmation."""
        mock_redis.get.return_value = None

        with patch(
            "app.services.chat_orchestrator.redis.from_url", return_value=mock_redis
        ):
            retrieved = await orchestrator.get_confirmation_state("test-123")

            assert retrieved is None

    @pytest.mark.asyncio
    async def test_update_confirmation_status(self, orchestrator, mock_redis):
        """Test update_confirmation_status updates status."""
        state = ConfirmationState(
            confirmation_id="test-123",
            session_id="session-456",
            user_id="user-789",
            tool_name="delete_paper",
            parameters={},
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )

        mock_redis.get.return_value = state.model_dump_json()

        with patch(
            "app.services.chat_orchestrator.redis.from_url", return_value=mock_redis
        ):
            await orchestrator.update_confirmation_status("test-123", "approved")

            # Verify setex was called with updated status
            mock_redis.setex.assert_called()


class TestResumeWithConfirmation:
    """Test resume_with_confirmation streaming."""

    @pytest.fixture
    def orchestrator(self):
        """Create ChatOrchestrator instance."""
        return ChatOrchestrator()

    @pytest.fixture
    def mock_redis(self):
        """Create mock Redis client."""
        mock = AsyncMock()
        mock.get = AsyncMock()
        mock.setex = AsyncMock()
        mock.delete = AsyncMock()
        return mock

    @pytest.fixture
    def mock_runner(self):
        """Create mock AgentRunner."""
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
        """Test resume_with_confirmation streams events for approved tool."""
        state = ConfirmationState(
            confirmation_id="test-123",
            session_id="session-456",
            user_id="user-789",
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
                "app.services.chat_orchestrator.initialize_agent_components",
                return_value=(mock_runner, None, None, None),
            ):
                events = []
                async for event in orchestrator.resume_with_confirmation(
                    "test-123", approved=True
                ):
                    events.append(event)

                # Should have tool_call, tool_result, and done events
                assert len(events) >= 3

                # First event should be tool_call
                assert "tool_call" in events[0]

                # Should delete confirmation after processing
                mock_redis.delete.assert_called()

    @pytest.mark.asyncio
    async def test_resume_with_confirmation_rejected(self, orchestrator, mock_redis):
        """Test resume_with_confirmation streams rejection event."""
        state = ConfirmationState(
            confirmation_id="test-123",
            session_id="session-456",
            user_id="user-789",
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

            # Should have tool_rejected and done events
            assert len(events) >= 2

            # First event should be tool_rejected
            assert "tool_rejected" in events[0]

            # Should delete confirmation after processing
            mock_redis.delete.assert_called()

    @pytest.mark.asyncio
    async def test_resume_with_confirmation_expired(self, orchestrator, mock_redis):
        """Test resume_with_confirmation returns error for expired confirmation."""
        state = ConfirmationState(
            confirmation_id="test-123",
            session_id="session-456",
            user_id="user-789",
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

            # Should have error event
            assert len(events) == 1
            assert "error" in events[0]
            assert "expired" in events[0].lower()

    @pytest.mark.asyncio
    async def test_resume_with_confirmation_not_found(self, orchestrator, mock_redis):
        """Test resume_with_confirmation returns error for missing confirmation."""
        mock_redis.get.return_value = None

        with patch(
            "app.services.chat_orchestrator.redis.from_url", return_value=mock_redis
        ):
            events = []
            async for event in orchestrator.resume_with_confirmation(
                "test-123", approved=True
            ):
                events.append(event)

            # Should have error event
            assert len(events) == 1
            assert "error" in events[0]
            assert "not found" in events[0].lower()
