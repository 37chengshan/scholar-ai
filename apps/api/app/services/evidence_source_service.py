from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.paper import Paper, PaperChunk
from app.services.evidence_contract_service import (
    build_citation_jump_url,
    get_evidence_source_payload,
)


def _serialize_chunk_source(chunk: PaperChunk) -> dict[str, Any]:
    page_num = chunk.page_start or chunk.page_end
    if chunk.is_table:
        content_type = "table"
    elif chunk.is_figure:
        content_type = "figure"
    elif chunk.is_formula:
        content_type = "formula"
    else:
        content_type = "text"

    citation_jump_url = build_citation_jump_url(
        paper_id=chunk.paper_id,
        source_chunk_id=chunk.id,
        page_num=page_num,
    )
    return {
        "evidence_id": chunk.id,
        "source_type": "paper",
        "source_chunk_id": chunk.id,
        "paper_id": chunk.paper_id,
        "page_num": page_num,
        "section_path": chunk.section,
        "content_type": content_type,
        "anchor_text": (chunk.content or "")[:300],
        "content": chunk.content or "",
        "citation_jump_url": citation_jump_url,
        "read_url": citation_jump_url,
        "pdf_url": f"/api/v1/papers/{chunk.paper_id}/pdf",
    }


async def resolve_evidence_source(
    db: AsyncSession,
    *,
    source_chunk_id: str,
    user_id: str,
) -> dict[str, Any] | None:
    result = await db.execute(
        select(PaperChunk, Paper.user_id)
        .join(Paper, Paper.id == PaperChunk.paper_id)
        .where(PaperChunk.id == source_chunk_id, Paper.user_id == user_id)
        .limit(1)
    )
    row = result.first()
    if row:
        chunk, _ = row
        return _serialize_chunk_source(chunk)

    return get_evidence_source_payload(source_chunk_id)
