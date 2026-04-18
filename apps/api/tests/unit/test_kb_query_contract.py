"""Regression tests for KB query contract normalization."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.api.kb.kb_papers import kb_query


class _ScalarOneResult:
    def __init__(self, obj):
        self._obj = obj

    def scalar_one_or_none(self):
        return self._obj


class _FetchAllResult:
    def __init__(self, rows):
        self._rows = rows

    def fetchall(self):
        return self._rows


@pytest.mark.asyncio
async def test_kb_query_uses_normalized_text_field():
    kb = SimpleNamespace(id="kb-1", user_id="user-1", name="Knowledge Base")
    paper_ids = [("paper-1",)]
    paper_titles = [("paper-1", "Paper Title")]

    db = AsyncMock()
    db.execute = AsyncMock(
        side_effect=[
            _ScalarOneResult(kb),
            _FetchAllResult(paper_ids),
            _FetchAllResult(paper_titles),
        ]
    )

    service = SimpleNamespace()
    service.search = AsyncMock(
        return_value={
            "results": [
                {
                    "id": "chunk-1",
                    "paper_id": "paper-1",
                    "text": "KB normalized content preview.",
                    "score": 0.91,
                    "page_num": 4,
                    "content_type": "text",
                }
            ]
        }
    )

    captured = {}

    class _LLMClient:
        async def chat_completion(self, *, messages, **kwargs):
            captured["messages"] = messages
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content="KB answer"))]
            )

    with patch(
        "app.core.multimodal_search_service.get_multimodal_search_service",
        return_value=service,
    ), patch(
        "app.utils.zhipu_client.ZhipuLLMClient",
        return_value=_LLMClient(),
    ):
        response = await kb_query(
            kb_id="kb-1",
            request=SimpleNamespace(query="What is in the KB?", topK=5),
            user_id="user-1",
            db=db,
        )

    assert response.success is True
    assert response.data["citations"][0]["content_preview"] == "KB normalized content preview."
    assert response.data["citations"][0]["score"] == 0.91
    assert "KB normalized content preview." in captured["messages"][1]["content"]
