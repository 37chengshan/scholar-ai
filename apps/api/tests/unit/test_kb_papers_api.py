"""Unit tests for KB papers API compatibility paths."""

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.api.kb.kb_papers import list_kb_papers
from app.models.knowledge_base import KnowledgeBase


class _ScalarResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value

    def scalar(self):
        return self._value


class _RowsResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows

    def fetchall(self):
        return self._rows


@pytest.mark.asyncio
async def test_list_kb_papers_selects_compatible_columns_only():
    db = AsyncMock()
    now = datetime(2026, 4, 29, tzinfo=timezone.utc)
    kb = KnowledgeBase(
        id="kb-123",
        user_id="user-123",
        name="Test KB",
        description="",
        category="其他",
        embedding_model="bge-m3",
        parse_engine="docling",
        chunk_strategy="by-paragraph",
        enable_graph=False,
        enable_imrad=True,
        enable_chart_understanding=False,
        enable_multimodal_search=False,
        enable_comparison=False,
        paper_count=1,
        chunk_count=0,
        entity_count=0,
    )
    paper_row = SimpleNamespace(
        id="paper-123",
        title="Attention is All you Need",
        authors=["Ashish Vaswani"],
        year=2017,
        venue="NeurIPS",
        status="completed",
        created_at=now,
        updated_at=now,
    )

    db.execute.side_effect = [
        _ScalarResult(kb),
        _RowsResult([paper_row]),
        _ScalarResult(1),
        _RowsResult([("paper-123", 15)]),
    ]

    response = await list_kb_papers(
        "kb-123",
        limit=20,
        offset=0,
        user_id="user-123",
        db=db,
    )

    assert response.data["total"] == 1
    assert response.data["papers"] == [
        {
            "id": "paper-123",
            "title": "Attention is All you Need",
            "authors": ["Ashish Vaswani"],
            "year": 2017,
            "venue": "NeurIPS",
            "status": "completed",
            "chunkCount": 15,
            "entityCount": 0,
            "createdAt": now.isoformat(),
            "updatedAt": now.isoformat(),
        }
    ]
