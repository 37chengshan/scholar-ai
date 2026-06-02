"""Unit tests for trace_id unification across the request lifecycle.

Covers:
- Single trace_id propagated through entire request
- Error responses use the same trace_id as the request
- ProblemDetail no longer auto-generates UUID
- PipelineContext accepts external trace_id
- context.py exports get_trace_id()
"""

from __future__ import annotations

import uuid

import pytest

from app.core.observability.context import (
    clear_context,
    get_trace_id,
    request_id_var,
    set_request_context,
    trace_id_var,
)
from app.utils.problem_detail import ProblemDetail
from app.workers.pipeline_context import PipelineContext


# ---------------------------------------------------------------------------
# T3.1: get_trace_id() helper
# ---------------------------------------------------------------------------


class TestGetTraceId:
    """Test the get_trace_id() context helper."""

    def test_returns_trace_id_when_set(self):
        trace_id = str(uuid.uuid4())
        token = trace_id_var.set(trace_id)
        try:
            assert get_trace_id() == trace_id
        finally:
            trace_id_var.reset(token)

    def test_falls_back_to_request_id(self):
        request_id = str(uuid.uuid4())
        token = request_id_var.set(request_id)
        try:
            assert get_trace_id() == request_id
        finally:
            request_id_var.reset(token)

    def test_returns_none_when_no_context(self):
        clear_context()
        assert get_trace_id() is None

    def test_trace_id_takes_precedence_over_request_id(self):
        trace_id = str(uuid.uuid4())
        request_id = str(uuid.uuid4())
        t1 = trace_id_var.set(trace_id)
        t2 = request_id_var.set(request_id)
        try:
            assert get_trace_id() == trace_id
        finally:
            trace_id_var.reset(t1)
            request_id_var.reset(t2)


# ---------------------------------------------------------------------------
# T3.2: set_request_context sets both vars
# ---------------------------------------------------------------------------


class TestSetRequestContext:
    """Test that set_request_context sets both request_id and trace_id."""

    def test_sets_both_request_id_and_trace_id(self):
        rid = str(uuid.uuid4())
        set_request_context(request_id=rid, route="/test", user_id="u1")
        try:
            assert request_id_var.get() == rid
            assert trace_id_var.get() == rid
        finally:
            clear_context()


# ---------------------------------------------------------------------------
# T3.3: ProblemDetail uses contextvar instead of auto-generating UUID
# ---------------------------------------------------------------------------


class TestProblemDetailTraceId:
    """Test that ProblemDetail uses trace_id from context, not auto-generated."""

    def test_problem_detail_uses_context_trace_id(self):
        trace_id = str(uuid.uuid4())
        token = trace_id_var.set(trace_id)
        try:
            problem = ProblemDetail(
                type="/errors/test",
                title="Test",
                status=500,
            )
            assert problem.request_id == trace_id
        finally:
            trace_id_var.reset(token)

    def test_problem_detail_falls_back_to_uuid_without_context(self):
        clear_context()
        problem = ProblemDetail(
            type="/errors/test",
            title="Test",
            status=500,
        )
        # Without context, request_id falls back to auto-generated UUID
        assert problem.request_id is not None
        assert len(problem.request_id) == 36
        uuid.UUID(problem.request_id)

    def test_problem_detail_explicit_request_id_preserved(self):
        explicit_id = "explicit-id-123"
        problem = ProblemDetail(
            type="/errors/test",
            title="Test",
            status=500,
            request_id=explicit_id,
        )
        assert problem.request_id == explicit_id

    def test_problem_detail_to_dict_includes_request_id(self):
        trace_id = str(uuid.uuid4())
        token = trace_id_var.set(trace_id)
        try:
            problem = ProblemDetail(
                type="/errors/test",
                title="Test",
                status=500,
            )
            d = problem.to_dict()
            assert d["requestId"] == trace_id
        finally:
            trace_id_var.reset(token)


# ---------------------------------------------------------------------------
# T3.4: PipelineContext accepts external trace_id
# ---------------------------------------------------------------------------


class TestPipelineContextTraceId:
    """Test that PipelineContext accepts and uses external trace_id."""

    def test_accepts_external_trace_id(self):
        external_id = "external-trace-123"
        ctx = PipelineContext(
            task_id="t1",
            paper_id="p1",
            user_id="u1",
            storage_key="k1",
            trace_id=external_id,
        )
        assert ctx.trace_id == external_id

    def test_auto_generates_when_not_provided(self):
        ctx = PipelineContext(
            task_id="t2",
            paper_id="p2",
            user_id="u2",
            storage_key="k2",
        )
        # Should be a valid UUID
        assert len(ctx.trace_id) == 36
        assert ctx.trace_id.count("-") == 4
        # Verify it's a valid UUID
        uuid.UUID(ctx.trace_id)

    def test_different_instances_have_different_trace_ids(self):
        ctx1 = PipelineContext(task_id="t1", paper_id="p1", user_id="u1", storage_key="k1")
        ctx2 = PipelineContext(task_id="t2", paper_id="p2", user_id="u2", storage_key="k2")
        assert ctx1.trace_id != ctx2.trace_id

    def test_empty_string_triggers_generation(self):
        ctx = PipelineContext(
            task_id="t3",
            paper_id="p3",
            user_id="u3",
            storage_key="k3",
            trace_id="",
        )
        # Empty string should trigger auto-generation
        assert ctx.trace_id != ""
        uuid.UUID(ctx.trace_id)


# ---------------------------------------------------------------------------
# T3.5: trace_id_var is exported from context module
# ---------------------------------------------------------------------------


class TestContextExports:
    """Test that trace_id_var is properly exported."""

    def test_trace_id_var_is_context_var(self):
        from contextvars import ContextVar

        assert isinstance(trace_id_var, ContextVar)

    def test_context_module_exports_get_trace_id(self):
        from app.core.observability import context

        assert hasattr(context, "get_trace_id")
        assert callable(context.get_trace_id)
