"""Evidence processing helpers for the RAG pipeline.

Extracted from main_path_service.py to keep the orchestration layer under 800 lines.
"""

from __future__ import annotations

from typing import Any

from app.database import AsyncSessionLocal
from app.models import Paper
from app.services.paper_display_metadata import sanitize_paper_display_metadata
from app.services.evidence_contract_service import build_citation_jump_url
from sqlalchemy import select
from sqlalchemy.orm import selectinload


def normalize_handoff_evidence_rows(handoff_evidence: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    normalized_rows: list[dict[str, Any]] = []
    for row in handoff_evidence or []:
        if not isinstance(row, dict):
            continue
        paper_id = str(row.get("paper_id") or row.get("paperId") or "").strip()
        source_chunk_id = str(row.get("source_chunk_id") or row.get("sourceChunkId") or "").strip()
        text = str(row.get("text") or "").strip()
        if not paper_id or not source_chunk_id:
            continue
        normalized_rows.append(
            {
                "handoff_id": str(row.get("handoff_id") or row.get("handoffId") or "").strip(),
                "paper_id": paper_id,
                "source_chunk_id": source_chunk_id,
                "page_num": row.get("page_num", row.get("pageNum")),
                "claim": str(row.get("claim") or "").strip(),
                "dimension_id": str(row.get("dimension_id") or row.get("dimensionId") or "").strip(),
                "section_path": str(row.get("section_path") or row.get("sectionPath") or "").strip(),
                "content_type": str(row.get("content_type") or row.get("contentType") or "text").strip() or "text",
                "text": text,
                "citation_jump_url": str(row.get("citation_jump_url") or row.get("citationJumpUrl") or "").strip(),
                "title": str(row.get("title") or "").strip(),
            }
        )
    return normalized_rows


async def load_paper_display_title_map(user_id: str, paper_ids: list[str] | None) -> dict[str, str]:
    scoped_paper_ids = [paper_id for paper_id in dict.fromkeys(paper_ids or []) if paper_id]
    if not scoped_paper_ids:
        return {}

    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Paper)
                .options(selectinload(Paper.upload_history))
                .where(
                    Paper.user_id == user_id,
                    Paper.id.in_(scoped_paper_ids),
                )
            )
            papers = result.scalars().all()
    except Exception:
        return {}

    display_titles: dict[str, str] = {}
    for paper in papers:
        latest_upload_filename = None
        if getattr(paper, "upload_history", None):
            latest_row = max(
                paper.upload_history,
                key=lambda row: row.created_at or getattr(paper, "updated_at", None) or getattr(paper, "created_at", None),
            )
            latest_upload_filename = latest_row.filename
        display = sanitize_paper_display_metadata(
            paper_id=paper.id,
            title=paper.title,
            authors=paper.authors,
            year=paper.year,
            venue=paper.venue,
            fallback_title=latest_upload_filename,
        )
        display_titles[paper.id] = display["title"] or paper.id
    return display_titles


def build_summary_record_map(summary_records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {
        str(record.get("paper_id") or ""): record
        for record in summary_records
        if str(record.get("paper_id") or "").strip()
    }


def append_abstain_scope_fallback(
    *,
    citations: list[dict[str, Any]],
    evidence_blocks: list[dict[str, Any]],
    paper_scope: list[str] | None,
    paper_title_map: dict[str, str],
) -> None:
    if citations or evidence_blocks or not paper_scope:
        return

    fallback_paper_id = str(paper_scope[0] or "").strip()
    if not fallback_paper_id:
        return

    fallback_chunk_id = f"paper-scope-fallback::{fallback_paper_id}"
    fallback_title = paper_title_map.get(fallback_paper_id) or fallback_paper_id
    fallback_jump_url = build_citation_jump_url(
        paper_id=fallback_paper_id,
        source_chunk_id=fallback_chunk_id,
    )
    fallback_anchor = "当前回答未达到可直接作答的证据阈值，请回到原文继续核验。"

    citations.append(
        {
            "paper_id": fallback_paper_id,
            "source_chunk_id": fallback_chunk_id,
            "source_id": fallback_chunk_id,
            "page_num": 1,
            "section_path": "paper_scope_fallback",
            "title": fallback_title,
            "anchor_text": fallback_anchor,
            "text_preview": fallback_anchor,
            "content_type": "text",
            "score": 0.0,
            "citation_jump_url": fallback_jump_url,
        }
    )
    evidence_blocks.append(
        {
            "evidence_id": fallback_chunk_id,
            "source_type": "paper",
            "source_chunk_id": fallback_chunk_id,
            "paper_id": fallback_paper_id,
            "page_num": 1,
            "section_path": "paper_scope_fallback",
            "content_type": "text",
            "text": fallback_anchor,
            "score": 0.0,
            "rerank_score": 0.0,
            "support_status": "unsupported",
            "citation_jump_url": fallback_jump_url,
        }
    )
