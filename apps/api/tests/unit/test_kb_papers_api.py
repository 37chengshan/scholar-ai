"""Unit tests for KB papers API compatibility paths."""

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.api.evidence import get_evidence_source
from app.api.kb.kb_papers import kb_search, list_kb_papers
from app.models.paper import PaperChunk
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


@pytest.mark.asyncio
async def test_kb_search_returns_sdk_compatible_results():
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
        chunk_count=15,
        entity_count=0,
    )

    db = AsyncMock()
    db.execute = AsyncMock(
        side_effect=[
            _ScalarResult(kb),
            _RowsResult([("paper-123",)]),
            _RowsResult([("paper-123", "Attention Is All You Need")]),
            _RowsResult([]),
        ]
    )

    service = SimpleNamespace(
        search=AsyncMock(
            return_value={
                "results": [
                    {
                        "id": "chunk-1",
                        "paper_id": "paper-123",
                        "text": "Self-attention replaces recurrence.",
                        "section": "abstract",
                        "page_num": 1,
                        "score": 0.97,
                    }
                ]
            }
        )
    )

    with patch(
        "app.core.multimodal_search_service.get_multimodal_search_service",
        return_value=service,
    ):
        response = await kb_search(
            "kb-123",
            request=SimpleNamespace(query="核心创新", topK=5),
            user_id="user-123",
            db=db,
        )

    assert response.data == {
        "results": [
            {
                "id": "chunk-1",
                "paperId": "paper-123",
                "paperTitle": "Attention Is All You Need",
                "content": "Self-attention replaces recurrence.",
                "section": "abstract",
                "page": 1,
                "sourceChunkId": "chunk-1",
                "score": 0.97,
            }
        ],
        "total": 1,
    }


@pytest.mark.asyncio
async def test_kb_search_prefers_canonical_source_chunk_id_over_vector_primary_id():
    kb = KnowledgeBase(
        id="kb-123",
        user_id="user-123",
        name="Test KB",
        description="",
        category="其他",
        embedding_model="qwen_flash",
        parse_engine="docling",
        chunk_strategy="by-paragraph",
        enable_graph=False,
        enable_imrad=True,
        enable_chart_understanding=False,
        enable_multimodal_search=False,
        enable_comparison=False,
        paper_count=1,
        chunk_count=15,
        entity_count=0,
    )

    db = AsyncMock()
    db.execute = AsyncMock(
        side_effect=[
            _ScalarResult(kb),
            _RowsResult([("paper-123",)]),
            _RowsResult([("paper-123", "Attention Is All You Need")]),
        ]
    )

    service = SimpleNamespace(
        search=AsyncMock(
            return_value={
                "results": [
                    {
                        "id": "466045819771396907",
                        "paper_id": "paper-123",
                        "text": "Stable chunks power evidence jumps.",
                        "section": "method",
                        "page_num": 2,
                        "score": 0.91,
                        "raw_data": {
                            "source_chunk_id": "chunk-stable-123",
                            "chunk_id": "chunk-stable-123",
                        },
                    }
                ]
            }
        )
    )

    with patch(
        "app.core.multimodal_search_service.get_multimodal_search_service",
        return_value=service,
    ):
        response = await kb_search(
            "kb-123",
            request=SimpleNamespace(query="证据跳转", topK=5),
            user_id="user-123",
            db=db,
        )

    assert response.data["results"][0]["id"] == "466045819771396907"
    assert response.data["results"][0]["sourceChunkId"] == "chunk-stable-123"


@pytest.mark.asyncio
async def test_kb_search_resolves_summary_hits_to_representative_chunk_ids():
    kb = KnowledgeBase(
        id="kb-123",
        user_id="user-123",
        name="Test KB",
        description="",
        category="其他",
        embedding_model="qwen_flash",
        parse_engine="docling",
        chunk_strategy="by-paragraph",
        enable_graph=False,
        enable_imrad=True,
        enable_chart_understanding=False,
        enable_multimodal_search=False,
        enable_comparison=False,
        paper_count=1,
        chunk_count=15,
        entity_count=0,
    )

    db = AsyncMock()
    db.execute = AsyncMock(
        side_effect=[
            _ScalarResult(kb),
            _RowsResult([("paper-123",)]),
            _RowsResult([("paper-123", "Attention Is All You Need")]),
            _RowsResult([("paper-123", "chunk-intro-1", "introduction", 1)]),
        ]
    )

    service = SimpleNamespace(
        search=AsyncMock(
            return_value={
                "results": [
                    {
                        "id": "466045819771396907",
                        "source_id": "466045819771396907",
                        "paper_id": "paper-123",
                        "text": "Summary branch content.",
                        "section": "introduction",
                        "page_num": 1,
                        "score": 0.88,
                        "index_type": "summary",
                    }
                ]
            }
        )
    )

    with patch(
        "app.core.multimodal_search_service.get_multimodal_search_service",
        return_value=service,
    ):
        response = await kb_search(
            "kb-123",
            request=SimpleNamespace(query="总结贡献", topK=5),
            user_id="user-123",
            db=db,
        )

    assert response.data["results"][0]["sourceChunkId"] == "chunk-intro-1"


@pytest.mark.asyncio
async def test_get_evidence_source_reads_from_paper_chunks_before_artifact_fallback():
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

    response = await get_evidence_source(
        "chunk-stable-123",
        user_id="user-123",
        db=db,
    )

    assert response["source_chunk_id"] == "chunk-stable-123"
    assert response["paper_id"] == "paper-123"
    assert response["page_num"] == 4
    assert response["section_path"] == "method"
    assert response["content"] == "Evidence content from SQL chunk rows."
    assert response["citation_jump_url"] == "/read/paper-123?page=4&source=evidence&source_id=chunk-stable-123"
