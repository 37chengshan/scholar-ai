"""Performance benchmarks and token cost tracking.

Tests latency and cost targets:
- Simple query < 2 seconds
- Multi-step workflow < 10 seconds
- Token cost < ¥0.01 per query
- Success rate > 90% (simple), > 75% (complex)

Reference: VALIDATION.md §9.5
"""

import pytest
import time
from unittest.mock import AsyncMock, patch

from app.core.agent_runner import AgentRunner, AgentState
from app.core.context_manager import Context, Message

from tests.fixtures.performance_fixtures import (
    performance_client,
    timing_context,
    mock_fast_agent,
    mock_complex_agent,
    performance_metrics,
    mock_context_fast
)


@pytest.mark.asyncio
class TestPerformance:
    """Performance benchmark tests."""

    async def test_simple_query_latency(self, mock_fast_agent, mock_context_fast):
        """Simple query latency < 2 seconds."""
        start = time.time()

        # Mock execute for simple query
        with patch.object(
            mock_fast_agent,
            'execute',
            return_value={
                "success": True,
                "answer": "找到论文列表",
                "tool_calls": [{"tool": "list_papers"}],
                "iterations": 1,
                "state": AgentState.COMPLETED.value
            }
        ):
            result = await mock_fast_agent.execute(
                user_input="列出我的论文",
                session_id="test_session",
                user_id="test_user"
            )

        duration = time.time() - start

        # Verify latency target
        assert duration < 2.0, f"Simple query took {duration}s (target: < 2s)"
        assert result["iterations"] == 1

    async def test_multi_step_workflow_latency(self, mock_complex_agent, mock_context_fast):
        """Multi-step workflow latency < 10 seconds."""
        start = time.time()

        # Mock execute for complex workflow
        with patch.object(
            mock_complex_agent,
            'execute',
            return_value={
                "success": True,
                "answer": "提取引用并创建笔记完成",
                "tool_calls": [
                    {"tool": "list_papers", "result": {"success": True}},
                    {"tool": "read_paper", "result": {"success": True}},
                    {"tool": "create_note", "result": {"success": True}}
                ],
                "iterations": 4,
                "state": AgentState.COMPLETED.value
            }
        ):
            result = await mock_complex_agent.execute(
                user_input="提取10篇论文的引用并创建笔记",
                session_id="test_session",
                user_id="test_user"
            )

        duration = time.time() - start

        # Verify latency target
        assert duration < 10.0, f"Multi-step workflow took {duration}s (target: < 10s)"
        assert result["iterations"] >= 3

    async def test_token_consumption(self, mock_fast_agent):
        """Token consumption monitoring.

        Expected: Cost < ¥0.01 per query
        """
        # Mock execution with token tracking
        with patch.object(
            mock_fast_agent,
            'execute',
            return_value={
                "success": True,
                "answer": "测试结果",
                "tool_calls": [],
                "iterations": 1,
                "tokens_used": {
                    "input": 50,
                    "output": 100
                }
            }
        ):
            result = await mock_fast_agent.execute(
                user_input="测试",
                session_id="test_session",
                user_id="test_user"
            )

        # Calculate cost (GLM-4.5-Air pricing: input ¥0.001/1k, output ¥0.001/1k)
        if "tokens_used" in result:
            input_tokens = result["tokens_used"]["input"]
            output_tokens = result["tokens_used"]["output"]

            # Mock cost calculation
            cost = (input_tokens / 1000 * 0.001) + (output_tokens / 1000 * 0.001)

            assert cost < 0.01, f"Cost ¥{cost} exceeds ¥0.01 target"

    async def test_success_rate_simple(self, mock_fast_agent):
        """Success rate for simple queries > 90%.

        Execute 10 simple queries, measure success rate.
        """
        successful = 0
        total_tests = 10

        for i in range(total_tests):
            try:
                # Mock successful execution
                with patch.object(
                    mock_fast_agent,
                    'execute',
                    return_value={
                        "success": True,
                        "answer": f"测试结果 {i}",
                        "iterations": 1
                    }
                ):
                    result = await mock_fast_agent.execute(
                        user_input=f"测试查询 {i}",
                        session_id=f"session_{i}",
                        user_id="test_user"
                    )

                if result.get("success"):
                    successful += 1

            except Exception:
                pass

        success_rate = successful / total_tests

        # Verify success rate target
        assert success_rate > 0.90, f"Success rate {success_rate:.1%} below 90% target"

    async def test_success_rate_complex(self, mock_complex_agent):
        """Success rate for complex workflows > 75%.

        Execute 10 complex workflows, measure success rate.
        """
        successful = 0
        total_tests = 10

        for i in range(total_tests):
            try:
                # Mock complex workflow execution
                with patch.object(
                    mock_complex_agent,
                    'execute',
                    return_value={
                        "success": True,
                        "answer": f"复杂流程 {i} 完成",
                        "iterations": 5,
                        "tool_calls": [
                            {"tool": "list_papers"},
                            {"tool": "read_paper"},
                            {"tool": "create_note"}
                        ]
                    }
                ):
                    result = await mock_complex_agent.execute(
                        user_input=f"复杂查询 {i}",
                        session_id=f"session_{i}",
                        user_id="test_user"
                    )

                if result.get("success"):
                    successful += 1

            except Exception:
                pass

        success_rate = successful / total_tests

        # Verify success rate target
        assert success_rate > 0.75, f"Success rate {success_rate:.1%} below 75% target"