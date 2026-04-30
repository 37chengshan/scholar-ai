"""Fast path routing and SSE contract tests for chat stream."""

import importlib
import json
from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.models.chat import ChatStreamRequest


class _RequestStub:
    def __init__(self, headers=None):
        self.headers = headers or {}


async def _collect_sse_events(response):
    chunks = []
    async for chunk in response.body_iterator:
        if isinstance(chunk, bytes):
            chunks.append(chunk.decode("utf-8", errors="replace"))
        else:
            chunks.append(str(chunk))

    events = []
    current_event = None
    for raw in chunks:
        for line in raw.splitlines():
            if line.startswith("event: "):
                current_event = line.replace("event: ", "").strip()
            elif line.startswith("data: ") and current_event:
                payload = json.loads(line.replace("data: ", ""))
                events.append((current_event, payload))
    return events


def _load_chat_module():
    from starlette.routing import Router

    original_init = Router.__init__

    def compatible_init(self, *args, **kwargs):
        kwargs.pop("on_startup", None)
        kwargs.pop("on_shutdown", None)
        kwargs.pop("lifespan", None)
        result = original_init(self, *args, **kwargs)
        if not hasattr(self, "on_startup"):
            self.on_startup = []
        if not hasattr(self, "on_shutdown"):
            self.on_shutdown = []
        return result

    with patch.object(Router, "__init__", compatible_init):
        return importlib.import_module("app.api.chat")


@pytest.mark.asyncio
async def test_simple_query_routes_to_fast_path_and_bypasses_orchestrator():
    chat_api = _load_chat_module()

    mock_execute_with_streaming = AsyncMock()

    with patch.object(chat_api.session_manager, "get_session", AsyncMock(return_value=None)), patch.object(
        chat_api.session_manager,
        "create_session",
        AsyncMock(return_value=type("S", (), {"id": "session-1"})()),
    ), patch.object(chat_api.complexity_router, "route_async", AsyncMock(return_value={"complexity": "simple", "method": "rule", "confidence": 0.95})), patch.object(
        chat_api.message_service,
        "save_message",
        AsyncMock(return_value="user-msg-id"),
    ), patch.object(chat_api.chat_orchestrator, "execute_with_streaming", mock_execute_with_streaming), patch.object(
        chat_api.chat_orchestrator,
        "_create_assistant_message",
        AsyncMock(return_value="assistant-fast-1"),
    ), patch.object(
        chat_api.chat_orchestrator,
        "_safe_update_assistant_message",
        AsyncMock(),
    ):
        response = await chat_api.chat_stream(
            request=ChatStreamRequest(session_id="session-1", message="你好"),
            http_request=_RequestStub(),
            user_id="user-1",
        )

        events = await _collect_sse_events(response)

    event_names = [name for name, _ in events]
    routing_payload = next(payload for name, payload in events if name == "routing_decision")
    assert "session_start" in event_names
    assert "routing_decision" in event_names
    assert "message" in event_names
    assert "done" in event_names
    assert routing_payload.get("message_id") == "assistant-fast-1"
    assert routing_payload.get("task_family") == "single_paper_fact"
    assert routing_payload.get("execution_mode") == "local_evidence"
    mock_execute_with_streaming.assert_not_called()


@pytest.mark.asyncio
async def test_short_academic_query_in_general_scope_does_not_use_fast_path():
    chat_api = _load_chat_module()

    async def _mock_orchestrator_stream():
        yield 'event: session_start\ndata: {"session_id":"session-1","task_type":"general","message_id":"m-rag"}\n\n'
        yield 'event: message\ndata: {"delta":"rag response","seq":1,"message_id":"m-rag"}\n\n'
        yield 'event: done\ndata: {"finish_reason":"stop","message_id":"m-rag","citations":[],"evidence_blocks":[]}\n\n'

    mock_execute_with_streaming = Mock(return_value=_mock_orchestrator_stream())

    with patch.object(chat_api.session_manager, "get_session", AsyncMock(return_value=type("S", (), {"id": "session-1", "user_id": "user-1"})())), patch.object(
        chat_api.complexity_router,
        "route_async",
        AsyncMock(return_value={"complexity": "simple", "method": "rule", "confidence": 0.95}),
    ), patch.object(chat_api.message_service, "save_message", AsyncMock(return_value="user-msg-id")), patch.object(
        chat_api.chat_orchestrator,
        "execute_with_streaming",
        mock_execute_with_streaming,
    ):
        response = await chat_api.chat_stream(
            request=ChatStreamRequest(
                session_id="session-1",
                message="RAG是什么",
                scope={"type": "general"},
            ),
            http_request=_RequestStub(),
            user_id="user-1",
        )
        events = await _collect_sse_events(response)

    assert any(name == "message" for name, _ in events)
    mock_execute_with_streaming.assert_called_once()


@pytest.mark.asyncio
async def test_compare_query_in_general_scope_does_not_use_fast_path():
    chat_api = _load_chat_module()

    async def _mock_orchestrator_stream():
        yield 'event: session_start\ndata: {"session_id":"session-1","task_type":"general","message_id":"m1"}\n\n'
        yield 'event: message\ndata: {"delta":"orchestrator","seq":1,"message_id":"m1"}\n\n'
        yield 'event: done\ndata: {"finish_reason":"stop","message_id":"m1"}\n\n'

    mock_execute_with_streaming = Mock(return_value=_mock_orchestrator_stream())

    with patch.object(chat_api.session_manager, "get_session", AsyncMock(return_value=type("S", (), {"id": "session-1", "user_id": "user-1"})())), patch.object(
        chat_api.complexity_router,
        "route_async",
        AsyncMock(return_value={"complexity": "simple", "method": "rule", "confidence": 0.95}),
    ), patch.object(chat_api.message_service, "save_message", AsyncMock(return_value="user-msg-id")), patch.object(
        chat_api.chat_orchestrator,
        "execute_with_streaming",
        mock_execute_with_streaming,
    ):
        response = await chat_api.chat_stream(
            request=ChatStreamRequest(
                session_id="session-1",
                message="比较这两篇论文的差异",
                scope={"type": "general"},
            ),
            http_request=_RequestStub(),
            user_id="user-1",
        )
        events = await _collect_sse_events(response)

    assert any(name == "message" for name, _ in events)
    mock_execute_with_streaming.assert_called_once()


@pytest.mark.asyncio
async def test_paper_scope_query_does_not_use_fast_path():
    chat_api = _load_chat_module()

    async def _mock_orchestrator_stream():
        yield 'event: session_start\ndata: {"session_id":"session-1","task_type":"general","message_id":"m1"}\n\n'
        yield 'event: message\ndata: {"delta":"orchestrator","seq":1,"message_id":"m1"}\n\n'
        yield 'event: done\ndata: {"finish_reason":"stop","message_id":"m1"}\n\n'

    mock_execute_with_streaming = Mock(return_value=_mock_orchestrator_stream())

    with patch.object(chat_api.session_manager, "get_session", AsyncMock(return_value=type("S", (), {"id": "session-1", "user_id": "user-1"})())), patch.object(
        chat_api.complexity_router,
        "route_async",
        AsyncMock(return_value={"complexity": "simple", "method": "rule", "confidence": 0.95}),
    ), patch.object(chat_api.message_service, "save_message", AsyncMock(return_value="user-msg-id")), patch.object(
        chat_api.chat_orchestrator,
        "execute_with_streaming",
        mock_execute_with_streaming,
    ):
        response = await chat_api.chat_stream(
            request=ChatStreamRequest(
                session_id="session-1",
                message="请总结这篇论文",
                scope={"type": "single_paper", "paper_id": "paper-1"},
            ),
            http_request=_RequestStub(),
            user_id="user-1",
        )
        events = await _collect_sse_events(response)

    assert any(name == "message" for name, _ in events)
    mock_execute_with_streaming.assert_called_once()


@pytest.mark.asyncio
async def test_fast_path_sse_order_is_session_start_then_message_then_done():
    chat_api = _load_chat_module()

    with patch.object(chat_api.session_manager, "get_session", AsyncMock(return_value=type("S", (), {"id": "session-1", "user_id": "user-1"})())), patch.object(
        chat_api.complexity_router,
        "route_async",
        AsyncMock(return_value={"complexity": "simple", "method": "rule", "confidence": 0.95}),
    ), patch.object(chat_api.message_service, "save_message", AsyncMock(return_value="user-msg-id")), patch.object(
        chat_api.chat_orchestrator,
        "execute_with_streaming",
        AsyncMock(),
    ), patch.object(chat_api.chat_orchestrator, "_create_assistant_message", AsyncMock(return_value="assistant-fast-2")), patch.object(
        chat_api.chat_orchestrator,
        "_safe_update_assistant_message",
        AsyncMock(),
    ):
        response = await chat_api.chat_stream(
            request=ChatStreamRequest(session_id="session-1", message="hello"),
            http_request=_RequestStub(),
            user_id="user-1",
        )
        events = await _collect_sse_events(response)

    names = [name for name, _ in events]
    first_session = names.index("session_start")
    first_routing = names.index("routing_decision")
    first_message = names.index("message")
    first_done = names.index("done")
    routing_payload = next(payload for name, payload in events if name == "routing_decision")
    assert first_session < first_routing < first_message < first_done
    assert routing_payload.get("message_id") == "assistant-fast-2"


@pytest.mark.asyncio
async def test_fast_path_done_event_contains_latency_diagnostics():
    chat_api = _load_chat_module()

    with patch.object(chat_api.session_manager, "get_session", AsyncMock(return_value=type("S", (), {"id": "session-1", "user_id": "user-1"})())), patch.object(
        chat_api.complexity_router,
        "route_async",
        AsyncMock(return_value={"complexity": "simple", "method": "rule", "confidence": 0.95}),
    ), patch.object(chat_api.message_service, "save_message", AsyncMock(return_value="user-msg-id")), patch.object(
        chat_api.chat_orchestrator,
        "execute_with_streaming",
        AsyncMock(),
    ), patch.object(chat_api.chat_orchestrator, "_create_assistant_message", AsyncMock(return_value="assistant-fast-3")), patch.object(
        chat_api.chat_orchestrator,
        "_safe_update_assistant_message",
        AsyncMock(),
    ):
        response = await chat_api.chat_stream(
            request=ChatStreamRequest(session_id="session-1", message="hey"),
            http_request=_RequestStub(),
            user_id="user-1",
        )
        events = await _collect_sse_events(response)

    done_payload = next(payload for name, payload in events if name == "done")
    diagnostics = done_payload.get("diagnostics")

    assert done_payload.get("response_type") == "general"
    assert done_payload.get("answer_mode") is None
    assert done_payload.get("claims") == []
    assert done_payload.get("citations") == []
    assert done_payload.get("evidence_blocks") == []
    assert done_payload.get("quality") is None
    assert isinstance(diagnostics, dict)
    assert diagnostics.get("path") == "smalltalk_fast_path"
    assert isinstance(diagnostics.get("route_decision_latency_ms"), int)
    assert isinstance(diagnostics.get("first_token_emit_latency_ms"), int)
    assert isinstance(diagnostics.get("total_stream_latency_ms"), int)
    assert diagnostics.get("first_token_emit_latency_ms", 999999) <= 3000


@pytest.mark.asyncio
async def test_context_paper_ids_use_scoped_rag_path():
    chat_api = _load_chat_module()

    mock_execute_with_streaming = AsyncMock()
    scoped_payload = {
        "response_type": "rag",
        "answer_mode": "partial",
        "answer": "Scoped answer",
        "claims": [],
        "citations": [{"paper_id": "paper-1", "source_chunk_id": "chunk-1"}],
        "evidence_blocks": [{"evidence_id": "chunk-1", "paper_id": "paper-1"}],
        "quality": {"fallback_used": False, "fallback_reason": None},
        "trace_id": "trace-1",
        "run_id": "run-1",
        "retrieval_trace_id": "trace-1",
        "error_state": None,
    }

    with patch.object(chat_api.session_manager, "get_session", AsyncMock(return_value=type("S", (), {"id": "session-1", "user_id": "user-1"})())), patch.object(
        chat_api.complexity_router,
        "route_async",
        AsyncMock(return_value={"complexity": "simple", "method": "rule", "confidence": 0.95}),
    ), patch.object(chat_api.message_service, "save_message", AsyncMock(return_value="user-msg-id")), patch.object(
        chat_api.chat_orchestrator,
        "execute_with_streaming",
        mock_execute_with_streaming,
    ), patch.object(
        chat_api,
        "build_answer_contract_payload",
        Mock(return_value=scoped_payload),
    ) as build_payload_mock, patch.object(
        chat_api.chat_orchestrator,
        "_create_assistant_message",
        AsyncMock(return_value="assistant-scoped-1"),
    ), patch.object(
        chat_api.chat_orchestrator,
        "_safe_update_assistant_message",
        AsyncMock(),
    ):
        response = await chat_api.chat_stream(
            request=ChatStreamRequest(
                session_id="session-1",
                message="compare these findings",
                mode="rag",
                context={"paper_ids": ["paper-1", "paper-2"]},
            ),
            http_request=_RequestStub(),
            user_id="user-1",
        )
        events = await _collect_sse_events(response)

    done_payload = next(payload for name, payload in events if name == "done")
    mock_execute_with_streaming.assert_not_called()
    build_payload_mock.assert_called_once()
    assert build_payload_mock.call_args.kwargs["query"] == "compare these findings"
    assert build_payload_mock.call_args.kwargs["user_id"] == "user-1"
    assert build_payload_mock.call_args.kwargs["paper_scope"] == ["paper-1", "paper-2"]
    assert build_payload_mock.call_args.kwargs["query_family"] == "compare"
    assert build_payload_mock.call_args.kwargs["stage"] == "rule"
    assert done_payload.get("diagnostics", {}).get("path") == "scoped_paper_rag"
    assert done_payload.get("citations") == scoped_payload["citations"]
    assert done_payload.get("message_id") == "assistant-scoped-1"
    assert done_payload.get("task_family") == scoped_payload.get("task_family")


@pytest.mark.asyncio
async def test_chat_stream_rejects_session_from_different_user():
    chat_api = _load_chat_module()

    foreign_session = type("S", (), {"id": "session-foreign", "user_id": "user-2"})()

    with patch.object(chat_api.session_manager, "get_session", AsyncMock(return_value=foreign_session)):
        response = await chat_api.chat_stream(
            request=ChatStreamRequest(session_id="session-foreign", message="你好"),
            http_request=_RequestStub(),
            user_id="user-1",
        )
        events = await _collect_sse_events(response)

    error_payload = next(payload for name, payload in events if name == "error")
    done_payload = next(payload for name, payload in events if name == "done")

    assert "forbidden" in str(error_payload).lower()
    assert done_payload.get("status") == "init_error"
