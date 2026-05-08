from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.api.session import create_session, get_session_messages
from app.schemas.session import SessionCreate


@pytest.mark.asyncio
async def test_create_session_forwards_metadata_to_session_manager():
    session = SimpleNamespace(
        id="session-1",
        user_id="user-1",
        title="Scoped chat",
        status="active",
        session_metadata={"scopeType": "single_paper", "paperId": "paper-1"},
        message_count=0,
        tool_call_count=0,
        created_at=None,
        updated_at=None,
        last_activity_at=None,
        expires_at=None,
    )

    with patch(
        "app.api.session.session_manager.create_session",
        AsyncMock(return_value=session),
    ) as mock_create_session:
        response = await create_session(
            session_data=SessionCreate(
                title="Scoped chat",
                metadata={"scopeType": "single_paper", "paperId": "paper-1"},
            ),
            user_id="user-1",
        )

    mock_create_session.assert_awaited_once_with(
        user_id="user-1",
        title="Scoped chat",
        metadata={"scopeType": "single_paper", "paperId": "paper-1"},
    )
    assert response.data["metadata"] == {
        "scopeType": "single_paper",
        "paperId": "paper-1",
    }


@pytest.mark.asyncio
async def test_get_session_messages_returns_answer_contract_metadata():
    session = SimpleNamespace(
        id="session-1",
        user_id="user-1",
    )
    messages = [
        {
            "id": "message-1",
            "session_id": "session-1",
            "role": "assistant",
            "content": "Grounded answer",
            "tool_name": None,
            "reasoning_content": "retrieving",
            "current_phase": "done",
            "tool_timeline": [{"id": "tool-1", "tool": "rag_search"}],
            "citations": [{"paper_id": "paper-1", "source_chunk_id": "chunk-1"}],
            "answer_contract": {
                "response_type": "rag",
                "answer_mode": "partial",
                "citations": [{"paper_id": "paper-1", "source_chunk_id": "chunk-1"}],
                "evidence_blocks": [{"source_chunk_id": "chunk-1"}],
            },
            "stream_status": "completed",
            "tokens_used": 128,
            "cost": 0.02,
            "duration_ms": 900,
            "response_type": "rag",
            "trace_id": "trace-1",
            "run_id": "run-1",
            "created_at": "2026-05-06T10:00:00",
        }
    ]

    with patch(
        "app.api.session.session_manager.get_session",
        AsyncMock(return_value=session),
    ), patch(
        "app.services.message_service.message_service.get_messages",
        AsyncMock(return_value=messages),
    ), patch(
        "app.services.message_service.message_service.count_messages",
        AsyncMock(return_value=1),
    ):
        response = await get_session_messages(
            session_id="session-1",
            user_id="user-1",
            limit=50,
            offset=0,
            order="desc",
        )

    payload = response.data["messages"][0]
    assert payload["answer_contract"]["response_type"] == "rag"
    assert payload["citations"][0]["source_chunk_id"] == "chunk-1"
    assert payload["stream_status"] == "completed"
    assert payload["trace_id"] == "trace-1"
