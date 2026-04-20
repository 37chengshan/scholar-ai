"""Contract-focused integration tests for PR23-A.

Covers three critical chains:
1) POST /api/v1/import-sources/resolve-batch
2) POST /api/v1/import-batches/{id}/files
3) POST /api/v1/chat/stream -> GET /api/v1/sessions/{id}/messages
"""

import json
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import UploadFile

from app.api.chat import chat_stream
from app.api.imports.batches import upload_batch_local_files
from app.api.imports.sources import ResolveBatchRequest, resolve_batch_sources
from app.api.session import get_session_messages
from app.services.source_resolver_service import BatchResolveItem


@pytest.mark.asyncio
async def test_resolve_batch_contract_fields_are_stable():
    class _Resolver:
        async def resolve_batch(self, items):
            return [
                BatchResolveItem(
                    input=items[0],
                    resolved=True,
                    source_type="arxiv",
                    normalized={"canonicalId": "2501.00001"},
                    preview={"title": "A"},
                ),
                BatchResolveItem(
                    input=items[1],
                    resolved=False,
                    source_type="unknown",
                    error_code="NOT_FOUND",
                    error_message="missing",
                ),
            ]

    with patch("app.api.imports.sources.get_source_resolver_service", return_value=_Resolver()):
        response = await resolve_batch_sources(
            request=ResolveBatchRequest(items=["2501.00001", "bad-input"])
        )

    assert response.success is True
    assert response.data["total"] == 2
    assert response.data["resolvedCount"] == 1
    assert response.data["items"][0]["resolved"] is True
    assert response.data["items"][1]["errorCode"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_import_batch_files_contract_partial_success_shape(tmp_path):
    class _ScalarOneResult:
        def __init__(self, obj):
            self._obj = obj

        def scalar_one_or_none(self):
            return self._obj

    class _ScalarsResult:
        def __init__(self, items):
            self._items = items

        def scalars(self):
            return self

        def all(self):
            return self._items

    batch = SimpleNamespace(id="batch-1", user_id="user-1")
    job = SimpleNamespace(
        id="job-1",
        batch_id="batch-1",
        user_id="user-1",
        source_type="local_file",
        status="created",
        stage="created",
        progress=0,
        next_action={"type": "upload_file"},
        storage_key=None,
        file_sha256=None,
        size_bytes=None,
        filename=None,
        mime_type=None,
        updated_at=None,
    )

    db = AsyncMock()
    db.execute = AsyncMock(
        side_effect=[
            _ScalarOneResult(batch),
            _ScalarsResult([job]),
        ]
    )
    db.commit = AsyncMock()
    db.refresh = AsyncMock()

    file_ok = UploadFile(filename="ok.pdf", file=BytesIO(b"%PDF-1.4 content"))

    manifest = json.dumps([
        {"importJobId": "job-1", "filename": "ok.pdf"},
        {"importJobId": "job-missing", "filename": "missing.pdf"},
    ])

    with patch("app.api.imports.batches.os.getenv", return_value=str(tmp_path)), \
         patch("app.workers.import_worker.process_import_job") as mocked_worker:
        mocked_worker.delay = MagicMock(return_value=None)
        response = await upload_batch_local_files(
            batch_id="batch-1",
            manifest=manifest,
            files=[file_ok],
            user_id="user-1",
            db=db,
        )

    assert response.success is True
    data = response.data
    assert data["batchJobId"] == "batch-1"
    assert data["acceptedCount"] == 1
    assert data["rejectedCount"] == 1
    assert data["accepted"][0]["importJobId"] == "job-1"
    assert data["rejected"][0]["importJobId"] == "job-missing"
    assert "reason" in data["rejected"][0]


class _MessageStore:
    def __init__(self):
        self._messages = []
        self._next_id = 1

    async def save_message(self, session_id, role, content, tool_name=None, tool_params=None):
        mid = f"m-{self._next_id}"
        self._next_id += 1
        self._messages.append(
            {
                "id": mid,
                "session_id": session_id,
                "role": role,
                "content": content,
                "tool_name": tool_name,
                "tool_params": tool_params,
                "created_at": "2026-04-18T00:00:00Z",
            }
        )
        return mid

    async def update_message(self, message_id, content):
        for item in self._messages:
            if item["id"] == message_id:
                item["content"] = content
                return True
        return False

    async def get_messages(self, session_id, limit=50, offset=0, order="desc"):
        items = [m for m in self._messages if m["session_id"] == session_id]
        if order == "desc":
            items = list(reversed(items))
        return items[offset : offset + limit]

    async def count_messages(self, session_id):
        return len([m for m in self._messages if m["session_id"] == session_id])


class _RequestStub:
    headers = {}


@pytest.mark.asyncio
async def test_chat_stream_to_session_messages_history_readback_contract():
    store = _MessageStore()
    final_answer = "final answer"
    assistant_id_holder: dict[str, str] = {}
    tool_payload = '{"id":"tool-1","tool":"rag_search","success":true}'

    async def _mock_stream():
        assistant_id = await store.save_message("session-1", "assistant", "")
        assistant_id_holder["id"] = assistant_id
        await store.save_message(
            "session-1",
            "tool",
            tool_payload,
            tool_name="rag_search",
            tool_params={"query": "hello"},
        )
        await store.update_message(assistant_id, final_answer)

        yield (
            "event: session_start\n"
            f'data: {{"message_id":"{assistant_id}","session_id":"session-1","task_type":"general"}}\n\n'
        )
        yield (
            "event: message\n"
            f'data: {{"message_id":"{assistant_id}","delta":"{final_answer}"}}\n\n'
        )
        yield (
            "event: done\n"
            f'data: {{"message_id":"{assistant_id}","finish_reason":"stop"}}\n\n'
        )

    with patch("app.api.chat.message_service", store), \
         patch("app.api.chat.session_manager.get_session", AsyncMock(return_value=SimpleNamespace(id="session-1", user_id="user-1"))), \
         patch("app.api.chat.complexity_router.route_async", AsyncMock(return_value={"complexity": "simple", "method": "rules", "confidence": 1.0})), \
         patch("app.api.chat.chat_orchestrator.execute_with_streaming", return_value=_mock_stream()):

        response = await chat_stream(
            request=SimpleNamespace(session_id="session-1", message="hello", context=None, mode="auto", scope=None),
            http_request=_RequestStub(),
            user_id="user-1",
        )
        chunks = []
        async for chunk in response.body_iterator:
            chunks.append(chunk)

    stream_text = "".join(chunks)
    assistant_id = assistant_id_holder["id"]
    assert "event: message" in stream_text
    assert "event: done" in stream_text
    assert f'"message_id": "{assistant_id}"' in stream_text

    with patch("app.api.session.session_manager.get_session", AsyncMock(return_value=SimpleNamespace(id="session-1", user_id="user-1"))), \
         patch("app.services.message_service.message_service", store):
        msg_response = await get_session_messages(
            session_id="session-1",
            user_id="user-1",
            limit=50,
            offset=0,
            order="desc",
        )

    assert msg_response.success is True
    assert msg_response.data["total"] == 3
    assert msg_response.data["session_id"] == "session-1"
    assert msg_response.data["limit"] == 50
    assert msg_response.data["offset"] == 0
    assert msg_response.data["order"] == "desc"
    assert "pagination" in msg_response.data
    assert msg_response.data["pagination"]["returned"] == len(msg_response.data["messages"])
    assert msg_response.data["pagination"]["next_offset"] == (
        msg_response.data["offset"] + msg_response.data["pagination"]["returned"]
    )
    assert msg_response.data["pagination"]["has_more"] is False

    roles = [m["role"] for m in msg_response.data["messages"]]
    assert "user" in roles
    assert "assistant" in roles
    assert "tool" in roles

    tool_msgs = [m for m in msg_response.data["messages"] if m["role"] == "tool"]
    assert tool_msgs
    assert tool_msgs[0]["tool_name"] == "rag_search"
    assert tool_msgs[0]["tool_name"] != "unknown"
    assert tool_msgs[0]["content"] == tool_payload

    assistant_msgs = [m for m in msg_response.data["messages"] if m["role"] == "assistant"]
    assert len(assistant_msgs) == 1
    assert assistant_msgs[0]["id"] == assistant_id
    assert assistant_msgs[0]["content"] == final_answer
    assert not any(
        message["role"] == "assistant" and not message["content"]
        for message in msg_response.data["messages"]
    )
