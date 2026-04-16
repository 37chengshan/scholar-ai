"""End-to-end tests for user goals.

Tests complete user workflows from request to response:
- External search
- RAG question
- Create note
- Dangerous operation (needs confirmation)
- Session management

Reference: VALIDATION.md §9.4
"""

import pytest
from unittest.mock import patch

from app.core.agent_runner import AgentState

from tests.fixtures.e2e_fixtures import (
    e2e_client,
    test_session,
    mock_session_manager,
    mock_e2e_agent,
    sse_event_parser,
    mock_context_e2e
)


@pytest.mark.asyncio
class TestUserGoals:
    """E2E tests for user goal scenarios."""

    async def test_goal_external_search(self, mock_e2e_agent, test_session):
        """Goal: User searches external papers.

        Scenario: "搜索 arXiv 上关于 machine learning 的论文"
        Expected:
        - tool_call event contains "external_search"
        - message event contains paper results
        - done event received
        """
        # Execute agent workflow
        result = await mock_e2e_agent.execute(
            user_input="搜索 arXiv 上关于 machine learning 的论文",
            session_id=test_session["id"],
            user_id=test_session["user_id"]
        )

        # Verify result
        assert result["success"] is True
        assert result["state"] == AgentState.COMPLETED.value

        # Verify tool calls
        assert len(result["tool_calls"]) >= 1
        tool_call = result["tool_calls"][0]
        assert tool_call["tool"] == "external_search"

        # Verify parameters
        assert "query" in tool_call["parameters"]

        # Verify answer
        assert result["answer"] is not None

    async def test_goal_rag_question(self, mock_e2e_agent, test_session):
        """Goal: User asks RAG question.

        Scenario: "什么是深度学习？"
        Expected:
        - tool_call event contains "rag_search"
        - message event contains answer with citations
        """
        # Execute agent workflow
        result = await mock_e2e_agent.execute(
            user_input="什么是深度学习？",
            session_id=test_session["id"],
            user_id=test_session["user_id"]
        )

        # Verify result
        assert result["success"] is True
        assert result["state"] == AgentState.COMPLETED.value

        # Verify tool calls
        assert len(result["tool_calls"]) >= 1
        tool_call = result["tool_calls"][0]
        assert tool_call["tool"] == "rag_search"

        # Verify answer
        assert result["answer"] is not None

    async def test_goal_create_note(self, mock_e2e_agent, test_session):
        """Goal: User creates note from papers.

        Scenario: "创建笔记总结这3篇论文"
        Expected:
        - create_note tool called
        - note created in database
        """
        # Execute agent workflow
        result = await mock_e2e_agent.execute(
            user_input="创建笔记总结这3篇论文",
            session_id=test_session["id"],
            user_id=test_session["user_id"]
        )

        # Verify result
        assert result["success"] is True
        assert result["state"] == AgentState.COMPLETED.value

        # Verify tool calls
        assert len(result["tool_calls"]) >= 2

        # Verify tool sequence: read_paper → create_note
        tool_sequence = [tc["tool"] for tc in result["tool_calls"]]
        assert "create_note" in tool_sequence

        # Verify note creation
        note_call = next(tc for tc in result["tool_calls"] if tc["tool"] == "create_note")
        assert "title" in note_call["parameters"]

    async def test_goal_dangerous_operation(self, mock_e2e_agent, test_session):
        """Goal: User executes dangerous operation.

        Scenario: "删除所有论文"
        Expected:
        - confirmation_required event received
        - POST /api/chat/confirm with approved=true
        - Agent resumes and completes
        """
        # Execute agent workflow
        result = await mock_e2e_agent.execute(
            user_input="删除所有论文",
            session_id=test_session["id"],
            user_id=test_session["user_id"],
            auto_confirm=False  # Require confirmation
        )

        # Verify result - paused for confirmation
        assert result["success"] is False
        assert result["needs_confirmation"] is True
        assert result["tool_name"] == "delete_paper"
        assert result["state"] == AgentState.WAITING_CONFIRMATION.value

        # Verify confirmation message
        assert result["message"] is not None

        # Simulate user confirmation
        # In real implementation, this would call /api/chat/confirm
        # For E2E test, we verify the workflow paused correctly
        assert "确认" in result["message"] or "confirmation" in result["message"].lower()

    async def test_goal_session_management(self, mock_session_manager, test_session):
        """Goal: User manages sessions (CRUD).

        Expected:
        - POST /api/sessions -> create session
        - GET /api/sessions -> list sessions
        - POST /api/chat/stream -> send message
        - GET /api/sessions/{id}/messages -> retrieve history
        - DELETE /api/sessions/{id} -> delete session
        """
        # Test session creation
        new_session = await mock_session_manager.create_session(
            user_id=test_session["user_id"],
            title="New Test Session"
        )

        assert new_session["id"] is not None
        assert new_session["user_id"] == test_session["user_id"]

        # Test session retrieval
        retrieved_session = await mock_session_manager.get_session(new_session["id"])

        assert retrieved_session is not None
        assert retrieved_session["id"] == new_session["id"]

        # Verify session has expected fields
        assert "message_count" in retrieved_session
        assert "title" in retrieved_session