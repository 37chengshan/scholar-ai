"""Persistence flow tests for PR22-B.

Ensures:
- API layer does not double-write assistant/tool messages.
- Orchestrator persists tool messages and updates assistant placeholder in place.
"""

import json
from unittest.mock import AsyncMock, patch

import pytest

from app.models.chat import ChatStreamRequest
from app.services.message_service import MessageService
from app.services.chat_orchestrator import chat_orchestrator


class _RequestStub:
    def __init__(self, headers=None):
        self.headers = headers or {}


@pytest.mark.asyncio
async def test_chat_api_stream_only_persists_user_message():
    from app.api import chat as chat_api

    async def _mock_stream():
        yield 'event: message\ndata: {"delta":"hello","seq":1}\n\n'
        yield 'event: tool_result\ndata: {"id":"tool_1","tool":"rag_search","success":true}\n\n'
        yield 'event: done\ndata: {"finish_reason":"stop"}\n\n'

    mock_save_message = AsyncMock(return_value="user-msg-id")

    with patch.object(chat_api.message_service, "save_message", mock_save_message), \
         patch.object(chat_api.session_manager, "get_session", AsyncMock(return_value=None)), \
         patch.object(chat_api.session_manager, "create_session", AsyncMock(return_value=type("S", (), {"id": "session-1"})())), \
         patch.object(chat_api.complexity_router, "route_async", AsyncMock(return_value={"complexity": "simple", "method": "rules", "confidence": 1.0})), \
         patch.object(chat_api.chat_orchestrator, "execute_with_streaming", return_value=_mock_stream()):

        response = await chat_api.chat_stream(
            request=ChatStreamRequest(session_id="session-1", message="hi"),
            http_request=_RequestStub(),
            user_id="user-1",
        )

        async for _ in response.body_iterator:
            pass

    assert mock_save_message.await_count == 1
    call_kwargs = mock_save_message.await_args.kwargs
    assert call_kwargs["role"] == "user"
    assert call_kwargs["content"] == "hi"


@pytest.mark.asyncio
async def test_chat_api_reconnect_is_replay_only_without_rerun():
    from app.api import chat as chat_api

    async def _mock_replay(_session_id, _last_event_id):
        yield 'id: evt-2\nevent: message\ndata: {"delta":"cached"}\n\n'

    mock_save_message = AsyncMock()
    mock_execute = AsyncMock()
    mock_route = AsyncMock()

    with patch.object(chat_api.session_manager, "get_session", AsyncMock(return_value=type("S", (), {"id": "session-1"})())), \
         patch.object(chat_api.sse_manager, "handle_reconnect", new=_mock_replay), \
         patch.object(chat_api.message_service, "save_message", mock_save_message), \
         patch.object(chat_api.chat_orchestrator, "execute_with_streaming", mock_execute), \
         patch.object(chat_api.complexity_router, "route_async", mock_route):

        response = await chat_api.chat_stream(
            request=ChatStreamRequest(session_id="session-1", message="hi"),
            http_request=_RequestStub(headers={"last-event-id": "evt-1"}),
            user_id="user-1",
        )

        replay_payload = ""
        async for chunk in response.body_iterator:
            replay_payload += chunk

    assert "event: message" in replay_payload
    mock_save_message.assert_not_awaited()
    mock_execute.assert_not_called()
    mock_route.assert_not_awaited()


@pytest.mark.asyncio
async def test_orchestrator_updates_placeholder_and_persists_tool_without_unknown():
    class _RunnerStub:
        def __init__(self):
            self.event_callback = None

        async def execute(self, **kwargs):
            await self.event_callback(
                "tool_call",
                {
                    "id": "tool_1",
                    "tool": "rag_search",
                    "parameters": {"query": "test"},
                },
            )
            await self.event_callback(
                "tool_result",
                {
                    "id": "tool_1",
                    "success": True,
                    "data": {"total": 1},
                },
            )
            return {
                "success": True,
                "answer": "final answer",
                "tokens_used": 10,
                "total_time_ms": 100,
            }

    runner = _RunnerStub()

    mock_save_message = AsyncMock(side_effect=["assistant-msg-id", "tool-msg-id"])
    mock_update_message = AsyncMock(return_value=True)

    with patch("app.services.chat_orchestrator.initialize_agent_components", return_value=(runner, None, None, None)), \
         patch("app.services.chat_orchestrator.message_service.save_message", mock_save_message), \
         patch("app.services.chat_orchestrator.message_service.update_message", mock_update_message):

        events = []
        async for event in chat_orchestrator.execute_with_streaming(
            user_input="hello",
            session_id="session-1",
            user_id="user-1",
            auto_confirm=False,
            mode="auto",
            scope=None,
        ):
            events.append(event)

    assert any("event: tool_result" in event for event in events)
    assert any("event: done" in event for event in events)

    assert mock_save_message.await_count == 2
    first_call = mock_save_message.await_args_list[0].kwargs
    second_call = mock_save_message.await_args_list[1].kwargs

    assert first_call["role"] == "assistant"
    assert first_call["content"] == ""

    assert second_call["role"] == "tool"
    assert second_call["tool_name"] == "rag_search"
    tool_payload = json.loads(second_call["content"])
    assert tool_payload["tool"] == "rag_search"

    mock_update_message.assert_awaited_once_with(
        message_id="assistant-msg-id",
        content="final answer",
    )


@pytest.mark.asyncio
async def test_count_messages_without_explicit_db_session():
    service = MessageService()

    class _ScalarResult:
        def scalar_one(self):
            return 3

    class _SessionStub:
        async def execute(self, *_args, **_kwargs):
            return _ScalarResult()

    class _SessionContext:
        async def __aenter__(self):
            return _SessionStub()

        async def __aexit__(self, exc_type, exc, tb):
            return False

    with patch("app.services.message_service.AsyncSessionLocal", return_value=_SessionContext()):
        total = await service.count_messages(session_id="session-1")

    assert total == 3


@pytest.mark.asyncio
async def test_orchestrator_tool_persistence_failure_is_non_blocking():
    class _RunnerStub:
        def __init__(self):
            self.event_callback = None

        async def execute(self, **kwargs):
            await self.event_callback(
                "tool_call",
                {"id": "tool_1", "tool": "rag_search", "parameters": {"q": "x"}},
            )
            await self.event_callback(
                "tool_result",
                {"id": "tool_1", "success": True, "data": {"total": 1}},
            )
            return {"success": True, "answer": "ok", "total_time_ms": 10}

    runner = _RunnerStub()
    mock_save_message = AsyncMock(side_effect=["assistant-msg-id", RuntimeError("db down")])
    mock_update_message = AsyncMock(return_value=True)

    with patch("app.services.chat_orchestrator.initialize_agent_components", return_value=(runner, None, None, None)), \
         patch("app.services.chat_orchestrator.message_service.save_message", mock_save_message), \
         patch("app.services.chat_orchestrator.message_service.update_message", mock_update_message):
        events = []
        async for event in chat_orchestrator.execute_with_streaming(
            user_input="hello",
            session_id="session-1",
            user_id="user-1",
        ):
            events.append(event)

    assert any("event: done" in event for event in events)


@pytest.mark.asyncio
async def test_orchestrator_assistant_update_failure_is_non_blocking():
    class _RunnerStub:
        def __init__(self):
            self.event_callback = None

        async def execute(self, **kwargs):
            return {"success": True, "answer": "ok", "total_time_ms": 10}

    runner = _RunnerStub()
    mock_save_message = AsyncMock(return_value="assistant-msg-id")
    mock_update_message = AsyncMock(side_effect=RuntimeError("db down"))

    with patch("app.services.chat_orchestrator.initialize_agent_components", return_value=(runner, None, None, None)), \
         patch("app.services.chat_orchestrator.message_service.save_message", mock_save_message), \
         patch("app.services.chat_orchestrator.message_service.update_message", mock_update_message):
        events = []
        async for event in chat_orchestrator.execute_with_streaming(
            user_input="hello",
            session_id="session-1",
            user_id="user-1",
        ):
            events.append(event)

    assert any("event: done" in event for event in events)


@pytest.mark.asyncio
async def test_orchestrator_updates_assistant_before_done_for_early_disconnect():
    class _RunnerStub:
        def __init__(self):
            self.event_callback = None

        async def execute(self, **kwargs):
            return {"success": True, "answer": "ok", "total_time_ms": 10}

    runner = _RunnerStub()
    mock_save_message = AsyncMock(return_value="assistant-msg-id")
    mock_update_message = AsyncMock(return_value=True)

    with patch("app.services.chat_orchestrator.initialize_agent_components", return_value=(runner, None, None, None)), \
         patch("app.services.chat_orchestrator.message_service.save_message", mock_save_message), \
         patch("app.services.chat_orchestrator.message_service.update_message", mock_update_message):
        async for event in chat_orchestrator.execute_with_streaming(
            user_input="hello",
            session_id="session-1",
            user_id="user-1",
        ):
            if "event: done" in event:
                # Simulate client disconnecting right after done event.
                break

    mock_update_message.assert_awaited_once_with(
        message_id="assistant-msg-id",
        content="ok",
    )
