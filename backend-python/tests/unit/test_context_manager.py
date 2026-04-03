"""Unit tests for Context Manager.

Tests the hierarchical context management system for Agent conversations.

Test Categories:
- Context building from session messages
- Important message identification
- Secondary message compression
- Token counting
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import List, Dict, Any

from app.core.context_manager import ContextManager, Context, Message


class TestMessage:
    """Test Message dataclass."""

    def test_message_creation(self):
        """Test creating a message."""
        msg = Message(
            role="user",
            content="Hello",
            metadata={"intent": "question"},
            is_important=True
        )

        assert msg.role == "user"
        assert msg.content == "Hello"
        assert msg.metadata["intent"] == "question"
        assert msg.is_important is True

    def test_message_defaults(self):
        """Test message with default values."""
        msg = Message(role="assistant", content="Hi there")

        assert msg.role == "assistant"
        assert msg.content == "Hi there"
        assert msg.metadata is None
        assert msg.is_important is False


class TestContext:
    """Test Context dataclass."""

    def test_context_creation(self):
        """Test creating a context."""
        ctx = Context(
            objective="Help user understand paper",
            important_messages=[],
            secondary_messages=[],
            tool_history=[],
            environment={"user_id": "test-user"},
            working_memory={}
        )

        assert ctx.objective == "Help user understand paper"
        assert ctx.environment["user_id"] == "test-user"


class TestContextManager:
    """Test Context Manager functionality."""

    @pytest.fixture
    def context_manager(self):
        """Create a ContextManager instance."""
        return ContextManager()

    def test_is_important_message_user(self, context_manager):
        """Test that user messages are identified as important."""
        msg = Message(role="user", content="What is machine learning?")

        assert context_manager.is_important_message(msg) is True

    def test_is_important_message_system(self, context_manager):
        """Test that system messages are identified as important."""
        msg = Message(role="system", content="You are a helpful assistant.")

        assert context_manager.is_important_message(msg) is True

    def test_is_important_message_with_decision_point(self, context_manager):
        """Test that messages with decision points are important."""
        msg = Message(
            role="assistant",
            content="Should I proceed?",
            metadata={"is_decision_point": True}
        )

        assert context_manager.is_important_message(msg) is True

    def test_is_important_message_with_citations(self, context_manager):
        """Test that messages with citations are important."""
        msg = Message(
            role="assistant",
            content="According to the paper...",
            metadata={"has_citations": True}
        )

        assert context_manager.is_important_message(msg) is True

    def test_is_important_message_tool_result(self, context_manager):
        """Test that tool results are NOT important (secondary)."""
        msg = Message(role="tool", content="Tool execution result")

        assert context_manager.is_important_message(msg) is False

    def test_count_tokens(self, context_manager):
        """Test 4: Token counting works."""
        messages = [
            Message(role="user", content="This is a test message"),
            Message(role="assistant", content="This is a response")
        ]

        # Simple estimation: 1 token ≈ 4 characters
        total_chars = sum(len(m.content) for m in messages)
        expected_tokens = total_chars // 4

        token_count = context_manager.count_tokens(messages)

        assert token_count == expected_tokens

    @pytest.mark.asyncio
    async def test_build_context_from_session(self, context_manager):
        """Test 1: Context built from session messages."""
        session_id = "test-session-123"

        # Mock database
        mock_messages = [
            {"role": "user", "content": "Hello", "metadata": None},
            {"role": "assistant", "content": "Hi there", "metadata": None}
        ]

        with patch('app.core.database.get_db_connection') as mock_db:
            mock_conn = AsyncMock()
            mock_conn.fetch = AsyncMock(return_value=mock_messages)
            mock_db.return_value.__aenter__.return_value = mock_conn

            # Mock Redis functions
            with patch('app.utils.cache.get_conversation_session', new_callable=AsyncMock) as mock_get_session:
                mock_get_session.return_value = None

                context = await context_manager.build_context(session_id)

                assert context is not None
                assert isinstance(context, Context)

    @pytest.mark.asyncio
    async def test_compress_secondary_messages(self, context_manager):
        """Test 3: Secondary messages compressed when token limit approached."""
        # Create many secondary messages
        messages = [
            Message(role="tool", content=f"Tool result {i}")
            for i in range(10)
        ]

        # Mock LLM summarization
        with patch('litellm.acompletion') as mock_llm:
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = "Summary of tool results"
            mock_llm.return_value = mock_response

            compressed = await context_manager.compress_secondary_messages(messages)

            # Should return a summary message
            assert len(compressed) == 1
            assert compressed[0].role == "system"
            assert "Summary" in compressed[0].content or "历史执行摘要" in compressed[0].content

    @pytest.mark.asyncio
    async def test_compress_small_message_list(self, context_manager):
        """Test that small message lists are not compressed."""
        # Create only 3 messages (below threshold)
        messages = [
            Message(role="tool", content=f"Result {i}")
            for i in range(3)
        ]

        compressed = await context_manager.compress_secondary_messages(messages)

        # Should return original messages unchanged
        assert len(compressed) == 3
        assert compressed == messages

    def test_max_context_tokens_constant(self, context_manager):
        """Test that MAX_CONTEXT_TOKENS is defined."""
        assert hasattr(context_manager, 'MAX_CONTEXT_TOKENS')
        assert context_manager.MAX_CONTEXT_TOKENS == 8000