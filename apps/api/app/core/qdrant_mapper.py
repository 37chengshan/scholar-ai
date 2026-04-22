"""Normalize Qdrant payloads into repository-friendly dicts."""

from __future__ import annotations

from typing import Any, Dict


class QdrantMapper:
    """Map Qdrant search results to the canonical retrieval dict format."""

    @staticmethod
    def to_hit(record: Dict[str, Any]) -> Dict[str, Any]:
        if isinstance(record, dict):
            payload = record.get("payload") or {}
            record_id = record.get("id")
            record_score = record.get("score", 0.0)
            paper_id = record.get("paper_id")
            paper_title = record.get("paper_title")
            text = record.get("text")
            page_num = record.get("page_num")
            section = record.get("section")
            content_type = record.get("content_type")
        else:
            payload = getattr(record, "payload", None) or {}
            record_id = getattr(record, "id", None)
            record_score = getattr(record, "score", 0.0)
            paper_id = getattr(record, "paper_id", None)
            paper_title = getattr(record, "paper_title", None)
            text = getattr(record, "text", None)
            page_num = getattr(record, "page_num", None)
            section = getattr(record, "section", None)
            content_type = getattr(record, "content_type", None)

        return {
            "id": record_id,
            "paper_id": payload.get("paper_id") or paper_id,
            "paper_title": payload.get("paper_title") or paper_title,
            "text": payload.get("text") or text or "",
            "score": record_score,
            "page_num": payload.get("page_num") or page_num,
            "section": payload.get("section") or section,
            "content_type": payload.get("content_type") or content_type or "text",
            "section_path": payload.get("section_path"),
            "content_subtype": payload.get("content_subtype"),
            "anchor_text": payload.get("anchor_text"),
            "quality_score": payload.get("quality_score"),
            "raw_data": payload.get("raw_data") or payload,
            "backend": "qdrant",
        }