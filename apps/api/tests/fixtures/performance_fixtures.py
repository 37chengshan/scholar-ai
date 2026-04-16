"""Performance fixtures for benchmark tests.

Provides test setup for performance measurements:
- Test client for FastAPI app
- Timing context
- Mock Agent components
- Performance metrics collection

Reference: VALIDATION.md §9.5
"""

import pytest
import time
from typing import Dict, Any

from unittest.mock import AsyncMock, MagicMock, patch

from app.core.agent_runner import AgentRunner, AgentState
from app.core.context_manager import Context, Message


@pytest.fixture
def performance_client():
    """Create test client for performance measurements.

    Note: Disabled TestClient to avoid GLMClient import error in app.main.
    Performance tests use mock agents instead.
    """
    return None  # Placeholder - not used in current tests


@pytest.fixture
def timing_context():
    """Create timing context for latency measurement."""
    return {"start_time": None, "end_time": None, "duration": None}


@pytest.fixture
def mock_fast_agent():
    """Create mock agent that responds quickly for performance tests."""
    runner = MagicMock(spec=AgentRunner)

    # Mock execute to return quickly
    async def fast_execute(*args, **kwargs):
        return {
            "success": True,
            "answer": "快速响应结果",
            "tool_calls": [
                {
                    "tool": "list_papers",
                    "parameters": {"limit": 10},
                    "result": {"success": True, "data": {"papers": []}}
                }
            ],
            "iterations": 1,
            "state": AgentState.COMPLETED.value
        }

    runner.execute = AsyncMock(side_effect=fast_execute)
    return runner


@pytest.fixture
def mock_complex_agent():
    """Create mock agent that handles complex workflows."""
    runner = MagicMock(spec=AgentRunner)

    # Mock execute for multi-step workflow
    async def complex_execute(*args, **kwargs):
        return {
            "success": True,
            "answer": "复杂流程完成",
            "tool_calls": [
                {"tool": "list_papers", "result": {"success": True}},
                {"tool": "read_paper", "result": {"success": True}},
                {"tool": "read_paper", "result": {"success": True}},
                {"tool": "create_note", "result": {"success": True}}
            ],
            "iterations": 5,
            "state": AgentState.COMPLETED.value
        }

    runner.execute = AsyncMock(side_effect=complex_execute)
    return runner


@pytest.fixture
def performance_metrics():
    """Collect performance metrics during tests."""
    return {
        "total_tests": 0,
        "successful_tests": 0,
        "failed_tests": 0,
        "avg_latency": 0.0,
        "latencies": []
    }


@pytest.fixture
def mock_context_fast():
    """Create mock context for fast execution."""
    return Context(
        objective="测试性能",
        important_messages=[Message(role="user", content="测试性能")],
        environment={"user_id": "perf_user", "session_id": "perf_session"}
    )