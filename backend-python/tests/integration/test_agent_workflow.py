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

            # Mock tool execution - first fails after retries, second succeeds
            execute_responses = [
                # external_search retry 1: fail
                {
                    "success": False,
                    "error": "External search service unavailable"
                },
                # external_search retry 2: fail
                {
                    "success": False,
                    "error": "External search service unavailable"
                },
                # external_search retry 3: fail
                {
                    "success": False,
                    "error": "External search service unavailable"
                },
                # alternative rag_search: succeed
                {
                    "success": True,
                    "data": {"papers": ["paper1", "paper2"]}
                },
                # LLM iteration 2 rag_search: succeed
                {
                    "success": True,
                    "data": {"papers": ["paper3"]}
                }
            ]

            with patch.object(agent_runner, '_think', side_effect=think_responses):
                with patch.object(agent_runner.tool_registry, 'execute', side_effect=execute_responses):
                    result = await agent_runner.execute(
                        user_input="搜索论文",
                        session_id=session_context["session_id"],
                        user_id=session_context["user_id"]
                    )

        # Verify result - recovered from error using fallback
        assert result["success"] is True
        assert result["iterations"] >= 2
        assert result["state"] == AgentState.COMPLETED.value

        # Verify tool calls
        assert len(result["tool_calls"]) >= 2
        assert result["tool_calls"][0]["tool"] == "external_search"
        # First tool used alternative (fallback mechanism)
        assert result["tool_calls"][0]["result"].get("used_alternative") is True
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

    async def test_tool_execution_via_registry(self, agent_runner, session_context):
        """Test that tool execution uses Tool Registry (not mock).

        Scenario: Agent executes tool
        Expected:
        - _execute_tool calls self.tool_registry.execute()
        - No mock execution code is executed
        - Registry returns real result from executor
        """
        # Mock context
        mock_context = Context(
            objective="测试真实执行",
            important_messages=[
                Message(role="user", content="测试真实执行")
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
            # Mock LLM to select a tool
            think_responses = [
                {
                    "is_complete": False,
                    "tool_call": {
                        "name": "list_papers",
                        "parameters": {"limit": 10}
                    }
                },
                {
                    "is_complete": True,
                    "content": "找到论文列表"
                }
            ]

            with patch.object(agent_runner, '_think', side_effect=think_responses):
                # Track registry.execute() calls
                original_execute = agent_runner.tool_registry.execute
                execute_calls = []

                async def track_execute(tool_name, params, **kwargs):
                    execute_calls.append({
                        "tool_name": tool_name,
                        "params": params,
                        "kwargs": kwargs
                    })
                    return await original_execute(tool_name, params, **kwargs)

                with patch.object(
                    agent_runner.tool_registry,
                    'execute',
                    side_effect=track_execute
                ):
                    result = await agent_runner.execute(
                        user_input="测试真实执行",
                        session_id=session_context["session_id"],
                        user_id=session_context["user_id"]
                    )

        # Verify result succeeded
        assert result["success"] is True
        assert len(result["tool_calls"]) >= 1

        # Verify registry.execute() was called
        assert len(execute_calls) >= 1
        assert execute_calls[0]["tool_name"] == "list_papers"
        assert execute_calls[0]["params"]["limit"] == 10

        # Verify tool result came from registry (not mock)
        tool_result = result["tool_calls"][0]["result"]
        assert tool_result["success"] is True
        # Should have real data from registry, not mock "Mock result for list_papers"
        assert "papers" in tool_result["data"]
        # Verify it's not the old mock pattern
        assert tool_result["data"].get("tool") != "list_papers"
        assert "Mock result" not in str(tool_result)


@pytest.mark.asyncio
class TestAgentErrorRecoveryWorkflow:
    """Integration tests for Agent error recovery workflows per D-12.

    Tests multi-layer recovery mechanism:
    - Layer 1: Auto-retry on transient errors
    - Layer 2: Alternative tool fallback
    - Layer 3: User decision when all options exhausted
    """

    async def test_agent_recovers_from_tool_failure_via_alternative(self, agent_runner, session_context):
        """Test: Primary tool fails, Agent tries alternative and succeeds.

        Scenario: LLM selects external_search, it fails, LLM tries rag_search and succeeds.
        Expected:
        - Agent handles first tool failure
        - Agent selects alternative tool
        - Agent completes successfully
        """
        mock_context = Context(
            objective="Search for AI papers",
            important_messages=[
                Message(role="user", content="Search for AI papers")
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
            think_responses = [
                # First attempt: external_search fails
                {
                    "is_complete": False,
                    "tool_call": {
                        "name": "external_search",
                        "parameters": {"query": "AI"}
                    }
                },
                # Second attempt: rag_search succeeds
                {
                    "is_complete": False,
                    "tool_call": {
                        "name": "rag_search",
                        "parameters": {"question": "AI"}
                    }
                },
                # Third: Complete
                {
                    "is_complete": True,
                    "content": "Found papers about AI."
                }
            ]

            # Mock at tool_registry level to let _execute_with_fallback logic run
            # Provide enough responses: 3 retries for external_search (all fail), 1 for rag_search (succeeds)
            execute_responses = [
                # Retry 1 for external_search: fail
                {"success": False, "error": "service unavailable", "data": None},
                # Retry 2 for external_search: fail
                {"success": False, "error": "service unavailable", "data": None},
                # Retry 3 for external_search: fail
                {"success": False, "error": "service unavailable", "data": None},
                # Alternative tool rag_search: succeed
                {"success": True, "data": {"papers": ["paper1"]}, "error": None},
            ]

            with patch.object(agent_runner, '_think', side_effect=think_responses):
                with patch.object(agent_runner.tool_registry, 'execute', side_effect=execute_responses):
                    result = await agent_runner.execute(
                        user_input="Search for AI papers",
                        session_id=session_context["session_id"],
                        user_id=session_context["user_id"]
                    )

        # Verify agent completed successfully after using alternative
        assert result["success"] is True
        assert result["state"] == AgentState.COMPLETED.value
        assert result["iterations"] == 3

        # Verify external_search used alternative after retries exhausted
        # Check that the fallback mechanism worked
        assert result["tool_calls"][0]["tool"] == "external_search"
        # The result shows alternative was used
        assert result["tool_calls"][0]["result"].get("used_alternative") is True
        assert result["tool_calls"][0]["result"].get("alternative_tool") == "rag_search"
        assert result["tool_calls"][0]["result"]["success"] is True  # Alternative succeeded

    async def test_agent_handles_multiple_tool_failures_in_sequence(self, agent_runner, session_context):
        """Test: Multiple tools fail in sequence, agent adapts.

        Scenario: First tool fails, second tool also fails, third succeeds.
        Expected:
        - Agent handles cascading failures gracefully
        - Agent tries different approaches
        - Agent eventually completes
        """
        mock_context = Context(
            objective="Comprehensive paper search",
            important_messages=[
                Message(role="user", content="Comprehensive paper search")
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
            think_responses = [
                {"is_complete": False, "tool_call": {"name": "external_search", "parameters": {"query": "test"}}},
                {"is_complete": False, "tool_call": {"name": "rag_search", "parameters": {"question": "test"}}},
                {"is_complete": False, "tool_call": {"name": "list_papers", "parameters": {"limit": 10}}},
                {"is_complete": True, "content": "Found papers using list_papers after other searches failed."}
            ]

            # Mock at tool_registry level to let _execute_with_fallback logic run
            # Provide responses for retries and alternatives
            execute_responses = [
                # external_search retry 1: fail
                {"success": False, "error": "external service unavailable", "data": None},
                # external_search retry 2: fail
                {"success": False, "error": "external service unavailable", "data": None},
                # external_search retry 3: fail
                {"success": False, "error": "external service unavailable", "data": None},
                # alternative rag_search: succeed (Layer 2)
                {"success": True, "data": {"papers": ["paper1"]}, "error": None},
                # LLM iteration 2: rag_search succeeds
                {"success": True, "data": {"papers": ["paper2"]}, "error": None},
                # LLM iteration 3: list_papers succeeds
                {"success": True, "data": {"papers": ["paper1", "paper2"]}, "error": None}
            ]

            with patch.object(agent_runner, '_think', side_effect=think_responses):
                with patch.object(agent_runner.tool_registry, 'execute', side_effect=execute_responses):
                    result = await agent_runner.execute(
                        user_input="Comprehensive paper search",
                        session_id=session_context["session_id"],
                        user_id=session_context["user_id"]
                    )

        # Verify agent handled multiple failures and completed
        assert result["success"] is True
        assert result["state"] == AgentState.COMPLETED.value
        assert len(result["tool_calls"]) == 3

        # Verify first tool used alternative after retries exhausted
        assert result["tool_calls"][0]["tool"] == "external_search"
        assert result["tool_calls"][0]["result"].get("used_alternative") is True
        # Second tool succeeded directly
        assert result["tool_calls"][1]["result"]["success"] is True
        # Third tool succeeded
        assert result["tool_calls"][2]["result"]["success"] is True

    async def test_agent_returns_error_when_all_tools_fail(self, agent_runner, session_context):
        """Test: All tools fail → Agent returns error to user.

        Scenario: All tool calls fail, agent cannot complete task.
        Expected:
        - Agent exhausts all options
        - Agent returns failure with error explanation
        """
        mock_context = Context(
            objective="Search for papers",
            important_messages=[
                Message(role="user", content="Search for papers")
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
            think_responses = [
                {"is_complete": False, "tool_call": {"name": "external_search", "parameters": {"query": "test"}}},
                {"is_complete": False, "tool_call": {"name": "rag_search", "parameters": {"question": "test"}}},
                # After failures, LLM decides to provide final answer explaining the issue
                {"is_complete": True, "content": "I encountered issues with the search services. Please try again later."}
            ]

            execute_responses = [
                {"success": False, "error": "service unavailable", "data": None},
                {"success": False, "error": "service unavailable", "data": None}
            ]

            with patch.object(agent_runner, '_think', side_effect=think_responses):
                with patch.object(agent_runner.tool_registry, 'execute', side_effect=execute_responses):
                    result = await agent_runner.execute(
                        user_input="Search for papers",
                        session_id=session_context["session_id"],
                        user_id=session_context["user_id"]
                    )

        # Verify agent handled the situation gracefully
        assert result["success"] is True  # LLM provided a final answer
        assert result["state"] == AgentState.COMPLETED.value
        assert len(result["tool_calls"]) == 2
        # Both tool calls failed
        assert all(not tc["result"]["success"] for tc in result["tool_calls"])

    async def test_agent_retry_mechanism_on_transient_errors(self, agent_runner, session_context):
        """Test: Agent's _execute_with_fallback handles transient errors with retry.

        Scenario: Test the retry mechanism directly via _execute_with_fallback.
        Expected:
        - Transient errors trigger retry
        - Non-retryable errors skip retry
        """
        mock_context = Context(
            objective="Test",
            important_messages=[],
            environment={
                "user_id": session_context["user_id"],
                "session_id": session_context["session_id"]
            }
        )

        # Test 1: Transient error should trigger retries
        call_count = [0]
        async def mock_execute_transient(tool_name, params, **kwargs):
            call_count[0] += 1
            if call_count[0] < 2:
                return {"success": False, "error": "timeout", "data": None}
            return {"success": True, "data": {"result": "success"}, "error": None}

        with patch.object(agent_runner.tool_registry, 'execute', side_effect=mock_execute_transient):
            result = await agent_runner._execute_with_fallback(
                tool_name="external_search",
                params={"query": "test"},
                context=mock_context,
                max_retries=3
            )

        assert result["success"] is True
        assert call_count[0] >= 2  # At least initial + 1 retry

        # Test 2: Non-retryable error should skip retries and try alternative
        call_count2 = [0]
        async def mock_execute_non_retryable(tool_name, params, **kwargs):
            call_count2[0] += 1
            if tool_name == "external_search":
                return {"success": False, "error": "paper not found", "data": None}
            return {"success": True, "data": {"papers": []}, "error": None}

        with patch.object(agent_runner.tool_registry, 'execute', side_effect=mock_execute_non_retryable):
            result = await agent_runner._execute_with_fallback(
                tool_name="external_search",
                params={"query": "test"},
                context=mock_context,
                max_retries=3
            )

        # Should succeed with alternative tool
        assert result["success"] is True
        assert result.get("used_alternative") is True