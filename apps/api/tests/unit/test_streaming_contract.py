"""Regression tests for streaming retrieval contract and user isolation."""

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.core.streaming import stream_rag_response


@pytest.mark.asyncio
async def test_stream_rag_response_requires_user_id():
    with pytest.raises(ValueError, match="user_id is required"):
        await stream_rag_response(
            query="q",
            paper_ids=["paper-1"],
            user_id=None,
        )


@pytest.mark.asyncio
async def test_stream_rag_response_passes_authenticated_user_id_and_emits_canonical_citations():
    service = SimpleNamespace()
    service.search = AsyncMock(
        return_value={
            "results": [
                {
                    "paper_id": "paper-1",
                    "content_data": "This is evidence content for the answer.",
                    "score": 0.88,
                    "page": 3,
                }
            ]
        }
    )

    token_chunk = SimpleNamespace(
        choices=[SimpleNamespace(delta=SimpleNamespace(content="Token"))]
    )

    fake_client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(create=lambda **_: [token_chunk])
        )
    )

    fake_llm = SimpleNamespace(client=fake_client, model="fake-model")

    with patch(
        "app.core.multimodal_search_service.get_multimodal_search_service",
        return_value=service,
    ), patch("app.utils.zhipu_client.ZhipuLLMClient", return_value=fake_llm):
        response = await stream_rag_response(
            query="What is the key finding?",
            paper_ids=["paper-1"],
            user_id="user-123",
            top_k=5,
        )

        events = []
        async for event in response.body_iterator:
            events.append(event)

    service.search.assert_awaited_once()
    assert service.search.await_args.kwargs["user_id"] == "user-123"

    citations_event = next(
        event for event in events if '"type": "citations"' in event
    )
    payload = json.loads(citations_event.split("data: ", 1)[1])
    citation = payload["content"][0]

    assert citation["score"] == 0.88
    assert citation["page_num"] == 3
    assert citation["text_preview"]
    assert citation["content_preview"]


@pytest.mark.asyncio
async def test_stream_rag_response_uses_normalized_text_field():
    service = SimpleNamespace()
    service.search = AsyncMock(
        return_value={
            "results": [
                {
                    "paper_id": "paper-1",
                    "text": "Normalized evidence content for the answer.",
                    "score": 0.88,
                    "page_num": 3,
                    "section": "Methods",
                }
            ]
        }
    )

    token_chunk = SimpleNamespace(
        choices=[SimpleNamespace(delta=SimpleNamespace(content="Token"))]
    )

    captured = {}

    def fake_create(**kwargs):
        captured["messages"] = kwargs["messages"]
        return [token_chunk]

    fake_client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(create=fake_create)
        )
    )

    fake_llm = SimpleNamespace(client=fake_client, model="fake-model")

    with patch(
        "app.core.multimodal_search_service.get_multimodal_search_service",
        return_value=service,
    ), patch("app.utils.zhipu_client.ZhipuLLMClient", return_value=fake_llm):
        response = await stream_rag_response(
            query="What is the key finding?",
            paper_ids=["paper-1"],
            user_id="user-123",
            top_k=5,
        )

        events = []
        async for event in response.body_iterator:
            events.append(event)

    service.search.assert_awaited_once()

    context_block = captured["messages"][1]["content"].split("Context from papers:\n", 1)[1]
    assert "Normalized evidence content for the answer." in context_block

    citations_event = next(
        event for event in events if '"type": "citations"' in event
    )
    payload = json.loads(citations_event.split("data: ", 1)[1])
    citation = payload["content"][0]

    assert citation["text_preview"] == "Normalized evidence content for the answer."
    assert citation["content_preview"] == "Normalized evidence content for the answer."
