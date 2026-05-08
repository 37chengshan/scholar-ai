from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.models.paper import PaperChunk
from app.services.evidence_source_service import resolve_evidence_source


@pytest.mark.asyncio
async def test_resolve_evidence_source_prefers_sql_chunk_rows() -> None:
    chunk = PaperChunk(
        id="chunk-stable-123",
        content="Evidence content from SQL chunk rows.",
        section="method",
        page_start=4,
        page_end=4,
        is_table=False,
        is_figure=False,
        is_formula=False,
        paper_id="paper-123",
    )
    db = AsyncMock()
    db.execute = AsyncMock(return_value=SimpleNamespace(first=lambda: (chunk, "user-123")))

    response = await resolve_evidence_source(
        db,
        source_chunk_id="chunk-stable-123",
        user_id="user-123",
    )

    assert response is not None
    assert response["source_chunk_id"] == "chunk-stable-123"
    assert response["paper_id"] == "paper-123"
    assert response["page_num"] == 4
    assert response["section_path"] == "method"
    assert response["content"] == "Evidence content from SQL chunk rows."
    assert response["citation_jump_url"] == "/read/paper-123?page=4&source=evidence&source_id=chunk-stable-123"


@pytest.mark.asyncio
async def test_resolve_evidence_source_falls_back_to_artifact_payload() -> None:
    db = AsyncMock()
    db.execute = AsyncMock(return_value=SimpleNamespace(first=lambda: None))
    payload = {
        "source_chunk_id": "artifact-chunk-1",
        "content": "artifact payload",
    }

    with patch(
        "app.services.evidence_source_service.get_evidence_source_payload",
        return_value=payload,
    ) as mocked_fallback:
        response = await resolve_evidence_source(
            db,
            source_chunk_id="artifact-chunk-1",
            user_id="user-123",
        )

    assert response == payload
    mocked_fallback.assert_called_once_with("artifact-chunk-1")
