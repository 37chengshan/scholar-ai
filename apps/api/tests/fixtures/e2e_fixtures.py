"""E2E fixtures for user goal tests.

Provides test setup for end-to-end scenarios:
- Mock test client
- Mock session manager
- Mock agent runner for complete workflows
- SSE event parsing utilities

Reference: VALIDATION.md §9.4
"""

import pytest
import json
from typing import Dict, Any, List
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.agent_runner import AgentRunner, AgentState
from app.core.context_manager import Context, Message


@pytest.fixture
def e2e_client():
    """Create mock test client for E2E tests.

    Note: Returns None due to GLMClient import error in app.main.
    Tests use mock agents and session managers instead.
    """
    return None


@pytest.fixture
async def test_session():
    """Create test session context."""
    return {
        "id": "e2e_session_123",
        "user_id": "e2e_user_456",
        "title": "Test Session",
        "message_count": 0,
        "created_at": "2026-04-03T00:00:00Z"
    }


@pytest.fixture
def mock_session_manager():
    """Create mock session manager for E2E tests."""
    manager = MagicMock()

    # Mock create_session
    async def create_session(user_id: str, title: str = "") -> Dict[str, Any]:
        return {
            "id": "e2e_session_123",
            "user_id": user_id,
            "title": title or "Test Session",
            "message_count": 0
        }

    # Mock get_session
    async def get_session(session_id: str) -> Dict[str, Any]:
        return {
            "id": session_id,
            "user_id": "e2e_user_456",
            "title": "Test Session",
            "message_count": 5
        }

    manager.create_session = AsyncMock(side_effect=create_session)
    manager.get_session = AsyncMock(side_effect=get_session)

    return manager


@pytest.fixture
def mock_e2e_agent():
    """Create mock agent for E2E scenarios."""
    runner = MagicMock(spec=AgentRunner)

    # Mock execute with different scenarios
    async def execute_scenario(*args, **kwargs):
        user_input = args[0] if args else kwargs.get("user_input", "")

        # Detect scenario from user input
        if "arXiv" in user_input or "search" in user_input.lower():
            return {
                "success": True,
                "answer": "找到10篇相关论文",
                "tool_calls": [
                    {
                        "tool": "external_search",
                        "parameters": {"query": "AI", "sources": ["arxiv"]},
                        "result": {"success": True, "data": {"papers": []}}
                    }
                ],
                "iterations": 2,
                "state": AgentState.COMPLETED.value
            }
        elif "比较" in user_input or "compare" in user_input.lower():
            return {
                "success": True,
                "answer": "论文对比分析完成",
                "tool_calls": [
                    {"tool": "read_paper", "parameters": {"paper_id": "paper1"}},
                    {"tool": "read_paper", "parameters": {"paper_id": "paper2"}},
                    {"tool": "merge_documents", "parameters": {}}
                ],
                "iterations": 4,
                "state": AgentState.COMPLETED.value
            }
        elif "笔记" in user_input or "note" in user_input.lower():
            return {
                "success": True,
                "answer": "笔记创建成功",
                "tool_calls": [
                    {"tool": "read_paper", "parameters": {"paper_id": "paper1"}},
                    {"tool": "create_note", "parameters": {"title": "Test Note"}}
                ],
                "iterations": 3,
                "state": AgentState.COMPLETED.value
            }
        elif "删除" in user_input or "delete" in user_input.lower():
            return {
                "success": False,
                "needs_confirmation": True,
                "tool_name": "delete_paper",
                "tool_parameters": {"paper_id": "paper123"},
                "message": "删除论文需要确认",
                "iterations": 1,
                "state": AgentState.WAITING_CONFIRMATION.value
            }
        else:
            # Default RAG search scenario
            return {
                "success": True,
                "answer": "搜索完成，找到相关内容",
                "tool_calls": [
                    {"tool": "rag_search", "parameters": {"question": user_input}}
                ],
                "iterations": 1,
                "state": AgentState.COMPLETED.value
            }

    runner.execute = AsyncMock(side_effect=execute_scenario)
    return runner


@pytest.fixture
def sse_event_parser():
    """Parse SSE events from stream."""
    def parse_events(text: str) -> List[Dict[str, Any]]:
        events = []
        current_event = {}

        for line in text.split('\n'):
            if line.startswith('event:'):
                current_event['event'] = line[6:].strip()
            elif line.startswith('data:'):
                data_str = line[5:].strip()
                try:
                    current_event['data'] = json.loads(data_str)
                except json.JSONDecodeError:
                    current_event['data'] = data_str
            elif line == '' and current_event:
                events.append(current_event)
                current_event = {}

        return events

    return parse_events


@pytest.fixture
def mock_context_e2e():
    """Create mock context for E2E tests."""
    return Context(
        objective="E2E测试",
        important_messages=[Message(role="user", content="E2E测试")],
        environment={
            "user_id": "e2e_user_456",
            "session_id": "e2e_session_123"
        }
    )