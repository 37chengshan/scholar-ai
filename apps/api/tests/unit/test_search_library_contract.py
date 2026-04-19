"""Regression tests for library search contract normalization."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.api.search.library import search_library


@pytest.mark.asyncio
async def test_search_library_uses_normalized_text_and_score_fields():
    service = SimpleNamespace()
    service.search = AsyncMock(
        return_value={
            "results": [
                {
                    "id": "chunk-1",
                    "paper_id": "paper-1",
                    "text": "Normalized library content preview.",
                    "score": 0.88,
                    "page_num": 2,
                    "section": "Methods",
                }
            ]
        }
    )

    with patch(
        "app.api.search.library.get_multimodal_search_service",
        return_value=service,
    ):
        response = await search_library(
            q="library query",
            paper_ids=["paper-1"],
            limit=5,
            user_id="user-123",
        )

    assert response.success is True
    result = response.data["results"][0]
    assert result["content"] == "Normalized library content preview."
    assert result["rrfScore"] > 0
    assert result["denseScore"] > 0
