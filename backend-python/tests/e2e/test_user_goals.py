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
from fastapi.testclient import TestClient
from app.main import app


@pytest.mark.asyncio
class TestUserGoals:
    """E2E tests for user goal scenarios."""

    async def test_goal_external_search(self):
        """Goal: User searches external papers.

        Scenario: "搜索 arXiv 上关于 machine learning 的论文"
        Expected:
        - tool_call event contains "external_search"
        - message event contains paper results
        - done event received
        """
        # TODO: Implement test
        pass

    async def test_goal_rag_question(self):
        """Goal: User asks RAG question.

        Scenario: "什么是深度学习？"
        Expected:
        - tool_call event contains "rag_search"
        - message event contains answer with citations
        """
        # TODO: Implement test
        pass

    async def test_goal_create_note(self):
        """Goal: User creates note from papers.

        Scenario: "创建笔记总结这3篇论文"
        Expected:
        - create_note tool called
        - note created in database
        """
        # TODO: Implement test
        pass

    async def test_goal_dangerous_operation(self):
        """Goal: User executes dangerous operation.

        Scenario: "删除所有论文"
        Expected:
        - confirmation_required event received
        - POST /api/chat/confirm with approved=true
        - Agent resumes and completes
        """
        # TODO: Implement test
        pass

    async def test_goal_session_management(self):
        """Goal: User manages sessions (CRUD).

        Expected:
        - POST /api/sessions -> create session
        - GET /api/sessions -> list sessions
        - POST /api/chat/stream -> send message
        - GET /api/sessions/{id}/messages -> retrieve history
        - DELETE /api/sessions/{id} -> delete session
        """
        # TODO: Implement test
        pass