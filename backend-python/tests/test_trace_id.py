"""Test trace_id functionality.

Per Review Fix #8: 全链路 trace 追踪。
"""

import uuid

import pytest
import structlog

from app.workers.pipeline_context import PipelineContext


def test_context_has_trace_id():
    """验证 PipelineContext 自动生成 trace_id。"""
    ctx = PipelineContext(
        task_id="test-123",
        paper_id="paper-456",
        user_id="user-789",
        storage_key="test/key.pdf",
    )

    assert ctx.trace_id is not None
    assert len(ctx.trace_id) == 36  # UUID format: 8-4-4-4-12


def test_trace_id_format():
    """验证 trace_id 是有效的 UUID。"""
    ctx = PipelineContext(
        task_id="test",
        paper_id="test",
        user_id="test",
        storage_key="test",
    )

    # UUID 格式: 8-4-4-4-12，如果无效会抛异常
    parsed_uuid = uuid.UUID(ctx.trace_id)
    assert parsed_uuid.version == 4  # UUID4


def test_each_context_unique_trace_id():
    """验证每个 PipelineContext 生成不同的 trace_id。"""
    ctx1 = PipelineContext(
        task_id="test1",
        paper_id="test",
        user_id="test",
        storage_key="test",
    )
    ctx2 = PipelineContext(
        task_id="test2",
        paper_id="test",
        user_id="test",
        storage_key="test",
    )

    assert ctx1.trace_id != ctx2.trace_id


def test_trace_id_can_be_explicitly_set():
    """验证 trace_id 可以显式指定。"""
    explicit_trace_id = "explicit-trace-123"
    ctx = PipelineContext(
        task_id="test",
        paper_id="test",
        user_id="test",
        storage_key="test",
        trace_id=explicit_trace_id,
    )

    assert ctx.trace_id == explicit_trace_id


def test_log_context_binding_and_unbind():
    """验证 structlog contextvars 绑定和解绑。"""
    ctx = PipelineContext(
        task_id="test",
        paper_id="test",
        user_id="test",
        storage_key="test",
    )

    # 绑定上下文
    structlog.contextvars.bind_contextvars(
        trace_id=ctx.trace_id,
        paper_id=ctx.paper_id,
        task_id=ctx.task_id,
    )

    # 验证绑定成功（通过创建日志事件检查）
    test_logger = structlog.get_logger()
    # 创建一个事件字典模拟日志处理
    event_dict = {"event": "test_message"}
    # merge_contextvars processor 会添加绑定的上下文
    merged = structlog.contextvars.merge_contextvars(test_logger, "info", event_dict)

    assert merged.get("trace_id") == ctx.trace_id
    assert merged.get("paper_id") == ctx.paper_id
    assert merged.get("task_id") == ctx.task_id

    # 解绑 trace_id
    structlog.contextvars.unbind_contextvars("trace_id")
    event_dict2 = {"event": "test_message2"}
    merged2 = structlog.contextvars.merge_contextvars(test_logger, "info", event_dict2)

    assert merged2.get("trace_id") is None
    assert merged2.get("paper_id") == ctx.paper_id  # paper_id 还在

    # 清空所有
    structlog.contextvars.clear_contextvars()
    event_dict3 = {"event": "test_message3"}
    merged3 = structlog.contextvars.merge_contextvars(test_logger, "info", event_dict3)

    assert merged3.get("trace_id") is None
    assert merged3.get("paper_id") is None
    assert merged3.get("task_id") is None