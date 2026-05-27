"""Unit tests for the current Context Manager implementation."""

import pytest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.context_manager import ContextManager, Context, Message


class TestMessage:
    """Test Message dataclass."""

    def test_message_creation(self):
        msg = Message(
            role="user",
            content="Hello",
            metadata={"intent": "question"},
            is_important=True,
        )

        assert msg.role == "user"
        assert msg.content == "Hello"
        assert msg.metadata["intent"] == "question"
        assert msg.is_important is True

    def test_message_defaults(self):
        msg = Message(role="assistant", content="Hi there")

        assert msg.role == "assistant"
        assert msg.content == "Hi there"
        assert msg.metadata is None
        assert msg.is_important is False


class TestContext:
    """Test Context dataclass."""

    def test_context_creation(self):
        ctx = Context(
            objective="Help user understand paper",
            important_messages=[],
            secondary_messages=[],
            tool_history=[],
            environment={"user_id": "test-user"},
            working_memory={},
        )

        assert ctx.objective == "Help user understand paper"
        assert ctx.environment["user_id"] == "test-user"


class TestContextManager:
    """Test Context Manager functionality."""

    @pytest.fixture
    def context_manager(self):
        return ContextManager()

    def test_is_important_message_user(self, context_manager):
        msg = Message(role="user", content="What is machine learning?")

        assert context_manager.is_important_message(msg) is True

    def test_is_important_message_system(self, context_manager):
        msg = Message(role="system", content="You are a helpful assistant.")

        assert context_manager.is_important_message(msg) is True

    def test_is_important_message_with_decision_point(self, context_manager):
        msg = Message(
            role="assistant",
            content="Should I proceed?",
            metadata={"is_decision_point": True},
        )

        assert context_manager.is_important_message(msg) is True

    def test_is_important_message_with_citations(self, context_manager):
        msg = Message(
            role="assistant",
            content="According to the paper...",
            metadata={"has_citations": True},
        )

        assert context_manager.is_important_message(msg) is True

    def test_is_important_message_tool_result(self, context_manager):
        msg = Message(role="tool", content="Tool execution result")

        assert context_manager.is_important_message(msg) is False

    def test_count_tokens(self, context_manager):
        messages = [
            Message(role="user", content="This is a test message"),
            Message(role="assistant", content="This is a response"),
        ]

        total_chars = sum(len(m.content) for m in messages)
        expected_tokens = total_chars // 4

        token_count = context_manager.count_tokens(messages)

        assert token_count == expected_tokens

    @pytest.mark.asyncio
    async def test_build_context_from_session(self, context_manager):
        session_id = "test-session-123"
        user_id = "test-user-123"

        rows = [
            SimpleNamespace(
                role="user",
                content="Hello",
                tool_params=None,
                created_at=1,
            ),
            SimpleNamespace(
                role="assistant",
                content="Hi there",
                tool_params=None,
                created_at=2,
            ),
        ]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = rows
        mock_db = AsyncMock()
        mock_db.execute.return_value = mock_result
        mock_session_factory = MagicMock()
        mock_session_factory.return_value.__aenter__.return_value = mock_db
        mock_session_factory.return_value.__aexit__.return_value = False

        with patch(
            "app.core.context_manager.AsyncSessionLocal",
            mock_session_factory,
        ), patch.object(
            context_manager,
            "get_user_preferences",
            AsyncMock(return_value={"language": "zh-CN"}),
        ):
            context = await context_manager.build_context(session_id, user_id)

        assert context is not None
        assert isinstance(context, Context)
        assert context.environment == {
            "session_id": session_id,
            "user_id": user_id,
        }
        assert context.objective == "Hello"
        assert [msg.content for msg in context.important_messages] == ["Hello"]
        assert [msg.content for msg in context.secondary_messages] == ["Hi there"]
        assert len(context.recent_messages) == 2

    @pytest.mark.asyncio
    async def test_build_context_returns_empty_context_on_db_error(self, context_manager):
        mock_db = AsyncMock()
        mock_db.execute.side_effect = RuntimeError("db offline")
        mock_session_factory = MagicMock()
        mock_session_factory.return_value.__aenter__.return_value = mock_db
        mock_session_factory.return_value.__aexit__.return_value = False

        with patch("app.core.context_manager.AsyncSessionLocal", mock_session_factory):
            context = await context_manager.build_context("broken-session", "user-1")

        assert context.important_messages == []
        assert context.secondary_messages == []
        assert context.environment == {
            "session_id": "broken-session",
            "user_id": "user-1",
        }

    @pytest.mark.asyncio
    async def test_compress_secondary_messages(self, context_manager):
        messages = [
            Message(role="tool", content=f"Tool result {i}")
            for i in range(10)
        ]

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Summary of tool results"
        mock_client = AsyncMock()
        mock_client.chat_completion.return_value = mock_response

        with patch("app.core.context_manager.get_llm_client", return_value=mock_client):
            compressed = await context_manager.compress_secondary_messages(messages)

        assert len(compressed) == 1
        assert compressed[0].role == "system"
        assert "Summary" in compressed[0].content or "历史执行摘要" in compressed[0].content
        mock_client.chat_completion.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_compress_small_message_list(self, context_manager):
        messages = [
            Message(role="tool", content=f"Result {i}")
            for i in range(3)
        ]

        compressed = await context_manager.compress_secondary_messages(messages)

        # Should return original messages unchanged
        assert len(compressed) == 3
        assert compressed == messages

    def test_max_context_tokens_constant(self, context_manager):
        assert hasattr(context_manager, "MAX_CONTEXT_TOKENS")
        assert context_manager.MAX_CONTEXT_TOKENS == 8000
