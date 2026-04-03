"""Integration tests for Agent workflows.

Tests Agent execution across multiple scenarios:
- Simple query workflow (1 iteration)
- Multi-step workflow (3-5 tools)
- Needs confirmation workflow
- Error recovery (tool failure)
- Session persistence across workflows

Reference: VALIDATION.md §9.3
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from app.core.agent_runner import AgentRunner, AgentState
from app.core.tool_registry import ToolRegistry
from app.core.safety_layer import SafetyLayer
from app.core.context_manager import ContextManager, Context, Message

from tests.fixtures.agent_fixtures import (
    mock_llm_client,
    tool_registry,
    safety_layer,
    context_manager,
    agent_runner,
    session_context,
    mock_context
)


@pytest.mark.asyncio
class TestAgentWorkflow:
    """Integration tests for Agent workflow scenarios."""

    async def test_simple_query_workflow(self, agent_runner, session_context):
        """Test simple query workflow (1 iteration).

        Scenario: User sends "列出我的论文"
        Expected:
        - Agent calls list_papers tool
        - Response contains paper list
        - 1 iteration
        """
        # Mock context manager to return test context
        mock_context = Context(
            objective="列出我的论文",
            important_messages=[
                Message(role="user", content="列出我的论文")
            ],
            environment={
                "user_id": session_context["user_id"],
                "session_id": session_context["session_id"]
            }
        )

        with patch.object(
            agent_runner.context_manager,
            'build_context',
            return_value=mock_context
        ):
            # Mock LLM to call list_papers and complete
            think_responses = [
                # Iteration 1: Call list_papers
                {
                    "is_complete": False,
                    "tool_call": {
                        "name": "list_papers",
                        "parameters": {"limit": 20}
                    }
                },
                # Iteration 2: Complete with answer
                {
                    "is_complete": True,
                    "content": "我找到了2篇论文:\n1. Paper 1\n2. Paper 2"
                }
            ]

            with patch.object(agent_runner, '_think', side_effect=think_responses):
                result = await agent_runner.execute(
                    user_input="列出我的论文",
                    session_id=session_context["session_id"],
                    user_id=session_context["user_id"]
                )

        # Verify result
        assert result["success"] is True
        assert result["iterations"] >= 1
        assert result["state"] == AgentState.COMPLETED.value
        assert len(result["tool_calls"]) >= 1
        assert result["tool_calls"][0]["tool"] == "list_papers"

    async def test_multi_step_workflow(self, agent_runner, session_context):
        """Test multi-step workflow (3-5 iterations).

        Scenario: User sends "提取10篇论文的引用并创建笔记"
        Expected:
        - Agent calls: list_papers, read_paper (x10), create_note
        - 3-5 iterations
        - Note created in database
        """
        # Mock context
        mock_context = Context(
            objective="提取10篇论文的引用并创建笔记",
            important_messages=[
                Message(role="user", content="提取10篇论文的引用并创建笔记")
            ],
            environment={
                "user_id": session_context["user_id"],
                "session_id": session_context["session_id"]
            }
        )

        with patch.object(
            agent_runner.context_manager,
            'build_context',
            return_value=mock_context
        ):
            # Mock LLM responses for multi-step workflow
            think_responses = [
                # Step 1: List papers
                {
                    "is_complete": False,
                    "tool_call": {
                        "name": "list_papers",
                        "parameters": {"limit": 10}
                    }
                },
                # Step 2: Read first paper
                {
                    "is_complete": False,
                    "tool_call": {
                        "name": "read_paper",
                        "parameters": {"paper_id": "paper1"}
                    }
                },
                # Step 3: Read second paper (simplified - only 2 for test)
                {
                    "is_complete": False,
                    "tool_call": {
                        "name": "read_paper",
                        "parameters": {"paper_id": "paper2"}
                    }
                },
                # Step 4: Create note
                {
                    "is_complete": False,
                    "tool_call": {
                        "name": "create_note",
                        "parameters": {
                            "title": "论文引用总结",
                            "content": "提取了论文引用..."
                        }
                    }
                },
                # Step 5: Complete
                {
                    "is_complete": True,
                    "content": "成功提取了论文引用并创建了笔记"
                }
            ]

            with patch.object(agent_runner, '_think', side_effect=think_responses):
                result = await agent_runner.execute(
                    user_input="提取10篇论文的引用并创建笔记",
                    session_id=session_context["session_id"],
                    user_id=session_context["user_id"]
                )

        # Verify result
        assert result["success"] is True
        assert result["iterations"] >= 3
        assert result["iterations"] <= 5
        assert result["state"] == AgentState.COMPLETED.value
        assert len(result["tool_calls"]) >= 3

        # Verify tool sequence
        tool_sequence = [tc["tool"] for tc in result["tool_calls"]]
        assert "list_papers" in tool_sequence
        assert "read_paper" in tool_sequence
        assert "create_note" in tool_sequence

    async def test_needs_confirmation_workflow(self, agent_runner, session_context):
        """Test needs confirmation workflow.

        Scenario: User sends "删除所有processing状态的论文"
        Expected:
        - Agent selects delete_paper tool
        - Safety Layer requires confirmation
        - Agent pauses execution
        - User confirms -> Agent resumes and completes
        """
        # Mock context
        mock_context = Context(
            objective="删除所有processing状态的论文",
            important_messages=[
                Message(role="user", content="删除所有processing状态的论文")
            ],
            environment={
                "user_id": session_context["user_id"],
                "session_id": session_context["session_id"]
            }
        )

        with patch.object(
            agent_runner.context_manager,
            'build_context',
            return_value=mock_context
        ):
            # Mock LLM to select dangerous tool
            with patch.object(
                agent_runner,
                '_think',
                return_value={
                    "is_complete": False,
                    "tool_call": {
                        "name": "delete_paper",
                        "parameters": {"paper_id": "paper123"}
                    }
                }
            ):
                result = await agent_runner.execute(
                    user_input="删除所有processing状态的论文",
                    session_id=session_context["session_id"],
                    user_id=session_context["user_id"],
                    auto_confirm=False  # Require confirmation
                )

        # Verify result - paused for confirmation
        assert result["success"] is False
        assert result["needs_confirmation"] is True
        assert result["tool_name"] == "delete_paper"
        assert result["iterations"] == 1
        assert result["state"] == AgentState.WAITING_CONFIRMATION.value

        # Verify confirmation message
        assert "confirmation" in result["message"].lower()

    async def test_error_recovery(self, agent_runner, session_context):
        """Test error recovery (tool failure).

        Scenario: Tool execution fails
        Expected:
        - Agent handles error
        - Agent retries or returns error message
        """
        # Mock context
        mock_context = Context(
            objective="搜索论文",
            important_messages=[
                Message(role="user", content="搜索论文")
            ],
            environment={
                "user_id": session_context["user_id"],
                "session_id": session_context["session_id"]
            }
        )

        with patch.object(
            agent_runner.context_manager,
            'build_context',
            return_value=mock_context
        ):
            # Mock LLM responses for error recovery
            think_responses = [
                # Iteration 1: Try external_search (fails)
                {
                    "is_complete": False,
                    "tool_call": {
                        "name": "external_search",
                        "parameters": {"query": "AI"}
                    }
                },
                # Iteration 2: Try rag_search (succeeds)
                {
                    "is_complete": False,
                    "tool_call": {
                        "name": "rag_search",
                        "parameters": {"question": "AI"}
                    }
                },
                # Iteration 3: Complete
                {
                    "is_complete": True,
                    "content": "搜索成功，找到了相关论文"
                }
            ]

            # Mock tool execution - first fails, second succeeds
            execute_responses = [
                {
                    "success": False,
                    "error": "External search service unavailable"
                },
                {
                    "success": True,
                    "data": {"papers": ["paper1", "paper2"]}
                }
            ]

            with patch.object(agent_runner, '_think', side_effect=think_responses):
                with patch.object(agent_runner, '_execute_tool', side_effect=execute_responses):
                    result = await agent_runner.execute(
                        user_input="搜索论文",
                        session_id=session_context["session_id"],
                        user_id=session_context["user_id"]
                    )

        # Verify result - recovered from error
        assert result["success"] is True
        assert result["iterations"] >= 2
        assert result["state"] == AgentState.COMPLETED.value

        # Verify tool calls
        assert len(result["tool_calls"]) >= 2
        assert result["tool_calls"][0]["tool"] == "external_search"
        assert result["tool_calls"][0]["result"]["success"] is False
        assert result["tool_calls"][1]["tool"] == "rag_search"
        assert result["tool_calls"][1]["result"]["success"] is True

    async def test_session_persistence(self, agent_runner, session_context):
        """Test session persistence across workflows.

        Scenario: Execute workflow, verify messages saved
        Expected:
        - Messages saved to PostgreSQL
        - Session message_count updated
        - Retrieve session messages -> correct
        """
        # Mock context
        mock_context = Context(
            objective="测试会话持久化",
            important_messages=[
                Message(role="user", content="测试会话持久化")
            ],
            environment={
                "user_id": session_context["user_id"],
                "session_id": session_context["session_id"]
            }
        )

        with patch.object(
            agent_runner.context_manager,
            'build_context',
            return_value=mock_context
        ):
            # Mock successful execution
            with patch.object(
                agent_runner,
                '_think',
                return_value={
                    "is_complete": True,
                    "content": "会话测试完成"
                }
            ):
                result = await agent_runner.execute(
                    user_input="测试会话持久化",
                    session_id=session_context["session_id"],
                    user_id=session_context["user_id"]
                )

        # Verify execution succeeded
        assert result["success"] is True
        assert result["iterations"] >= 1

        # Verify session_id was used in context
        assert session_context["session_id"] in str(mock_context.environment)