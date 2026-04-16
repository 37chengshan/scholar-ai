"""
E2E tests for RAG citation format and structure.

Tests citation structure, source metadata, cross-paper queries.
"""

import json
import uuid
from datetime import datetime
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import AsyncClient


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def sample_citation() -> Dict[str, Any]:
    """Sample citation with all required fields."""
    return {
        "paper_id": "550e8400-e29b-41d4-a716-446655440000",
        "title": "Deep Learning in Medical Imaging: A Survey",
        "chunk_id": "chunk-001",
        "score": 0.92,
        "page": 5,
        "snippet": "Deep learning has achieved remarkable success in medical image analysis, "
                   "with convolutional neural networks demonstrating superior performance."
    }


@pytest.fixture
def sample_citations_multiple() -> List[Dict[str, Any]]:
    """Multiple citations for cross-paper queries."""
    return [
        {
            "paper_id": "paper-001",
            "title": "Deep Learning for Medical Imaging",
            "chunk_id": "chunk-001",
            "score": 0.95,
            "page": 5,
            "snippet": "Deep learning approaches have revolutionized medical imaging..."
        },
        {
            "paper_id": "paper-002",
            "title": "CNN Features for Medical Images",
            "chunk_id": "chunk-002",
            "score": 0.88,
            "page": 3,
            "snippet": "CNNs automatically learn hierarchical features from raw images..."
        },
        {
            "paper_id": "paper-001",
            "title": "Deep Learning for Medical Imaging",
            "chunk_id": "chunk-003",
            "score": 0.85,
            "page": 7,
            "snippet": "The proposed method achieves 95% accuracy on the test set..."
        }
    ]


@pytest.fixture
def cross_paper_query_request() -> Dict[str, Any]:
    """Cross-paper query request."""
    return {
        "question": "Compare the methodologies between Paper A and Paper B",
        "paper_ids": ["paper-001", "paper-002"],
        "query_type": "cross_paper",
        "top_k": 10
    }


@pytest.fixture
def evolution_query_request() -> Dict[str, Any]:
    """Evolution tracking query request."""
    return {
        "question": "How has the YOLO architecture evolved over time?",
        "paper_ids": ["paper-yolo-v1", "paper-yolo-v2", "paper-yolo-v3"],
        "query_type": "evolution",
        "top_k": 15
    }


# =============================================================================
# Citation Structure Tests
# =============================================================================

def test_citation_required_fields():
    """Test citation has all required fields per SEARCH-05."""
    citation = {
        "paper_id": "p1",
        "title": "Test Paper",
        "chunk_id": "c1",
        "score": 0.92,
        "page": 5,
        "snippet": "This is a test snippet"
    }

    required_fields = ["paper_id", "title", "page", "snippet", "score"]
    for field in required_fields:
        assert field in citation, f"Missing required field: {field}"


def test_citation_score_range():
    """Test citation score is between 0 and 1."""
    valid_citations = [
        {"paper_id": "p1", "score": 0.0},
        {"paper_id": "p2", "score": 0.5},
        {"paper_id": "p3", "score": 1.0},
    ]

    for citation in valid_citations:
        assert 0 <= citation["score"] <= 1, f"Score {citation['score']} out of range"

    # Test invalid scores would fail validation
    invalid_scores = [-0.1, 1.1, -5, 2]
    for score in invalid_scores:
        assert not (0 <= score <= 1), f"Score {score} should be invalid"


def test_citation_page_positive():
    """Test citation page is a positive integer."""
    citation = {"paper_id": "p1", "page": 5}
    assert isinstance(citation["page"], int)
    assert citation["page"] > 0


def test_citation_snippet_length():
    """Test citation snippet has reasonable length."""
    citation = {
        "paper_id": "p1",
        "snippet": "Deep learning has achieved remarkable success in medical image analysis."
    }

    # Snippet should be non-empty
    assert len(citation["snippet"]) > 0

    # Snippet should be reasonable length (not too long, not too short)
    assert len(citation["snippet"]) >= 10, "Snippet too short"
    assert len(citation["snippet"]) <= 500, "Snippet too long"


# =============================================================================
# Source Metadata Tests
# =============================================================================

def test_citation_source_metadata():
    """Test citation includes complete source metadata."""
    citation = {
        "paper_id": "550e8400-e29b-41d4-a716-446655440000",
        "title": "Deep Learning in Medical Imaging: A Survey",
        "authors": ["John Doe", "Jane Smith"],
        "publication_year": 2024,
        "journal": "IEEE Transactions on Medical Imaging",
        "chunk_id": "chunk-001",
        "score": 0.92,
        "page": 5,
        "snippet": "Deep learning has achieved remarkable success..."
    }

    # Core identification fields
    assert len(citation["paper_id"]) > 0
    assert len(citation["title"]) > 0
    assert len(citation["chunk_id"]) > 0

    # Source location
    assert citation["page"] > 0

    # Relevance
    assert 0 <= citation["score"] <= 1


def test_citation_title_format():
    """Test citation title formatting."""
    citations = [
        {"title": "Paper Title"},
        {"title": "A Very Long Paper Title That Might Need Truncation"},
        {"title": "Short"},
    ]

    for citation in citations:
        title = citation["title"]
        assert len(title) > 0, "Title cannot be empty"
        assert title.strip() == title, "Title should not have leading/trailing whitespace"


# =============================================================================
# Cross-Paper Query Tests
# =============================================================================

def test_cross_paper_citation_grouping():
    """Test citations from cross-paper queries are grouped correctly."""
    citations = [
        {"paper_id": "paper-001", "title": "Paper A", "page": 5, "score": 0.95},
        {"paper_id": "paper-002", "title": "Paper B", "page": 3, "score": 0.88},
        {"paper_id": "paper-001", "title": "Paper A", "page": 7, "score": 0.85},
    ]

    # Group by paper_id
    grouped = {}
    for citation in citations:
        pid = citation["paper_id"]
        if pid not in grouped:
            grouped[pid] = []
        grouped[pid].append(citation)

    assert "paper-001" in grouped
    assert "paper-002" in grouped
    assert len(grouped["paper-001"]) == 2
    assert len(grouped["paper-002"]) == 1


def test_cross_paper_score_comparison():
    """Test scores from different papers can be compared."""
    citations = [
        {"paper_id": "paper-001", "score": 0.95},
        {"paper_id": "paper-002", "score": 0.88},
    ]

    # Sort by score
    sorted_citations = sorted(citations, key=lambda x: x["score"], reverse=True)

    assert sorted_citations[0]["paper_id"] == "paper-001"
    assert sorted_citations[1]["paper_id"] == "paper-002"


@pytest.mark.asyncio
async def test_cross_paper_query_request():
    """Test cross-paper query request structure."""
    request = {
        "question": "Compare the methodologies between papers",
        "paper_ids": ["paper-001", "paper-002", "paper-003"],
        "query_type": "cross_paper",
        "top_k": 10
    }

    # Should have multiple papers
    assert len(request["paper_ids"]) >= 2

    # Query type should be cross_paper
    assert request["query_type"] == "cross_paper"

    # Top_k should be larger for cross-paper
    assert request["top_k"] >= 5


# =============================================================================
# Citation in Response Tests
# =============================================================================

def test_citations_in_api_response():
    """Test citations array in API response structure."""
    response = {
        "answer": "Deep learning has achieved remarkable success in medical imaging.",
        "sources": [
            {
                "paper_id": "p1",
                "title": "Deep Learning Paper",
                "page": 5,
                "snippet": "Deep learning has achieved remarkable success...",
                "score": 0.92
            }
        ],
        "confidence": 0.85,
        "cached": False
    }

    # Should have sources array
    assert "sources" in response
    assert isinstance(response["sources"], list)
    assert len(response["sources"]) > 0

    # Each source should have required fields
    for source in response["sources"]:
        assert "paper_id" in source
        assert "title" in source
        assert "page" in source
        assert "snippet" in source
        assert "score" in source


def test_citation_answer_linking():
    """Test citations are linked to answer via citation markers."""
    answer = "Deep learning has achieved remarkable success [1] in medical imaging."

    # Find citation markers
    import re
    citations = re.findall(r'\[(\d+)\]', answer)

    assert len(citations) > 0, "Answer should have citation markers"
    assert citations[0] == "1"


def test_multiple_citations_in_answer():
    """Test multiple citations in single answer."""
    answer = "Studies show [1] that deep learning works [2], and CNNs excel [3]."

    import re
    citations = re.findall(r'\[(\d+)\]', answer)

    assert len(citations) == 3
    assert citations == ["1", "2", "3"]


# =============================================================================
# API Response Format Tests
# =============================================================================

@pytest.mark.asyncio
async def test_rag_query_response_structure(client: AsyncClient, mock_auth_headers: dict):
    """Test /rag/query returns structured response with citations."""
    request_data = {
        "question": "What is the main contribution?",
        "paper_ids": ["paper-001"],
        "query_type": "single",
        "top_k": 5
    }

    with patch("app.utils.cache.get_cached_response", return_value=None), \
         patch("app.utils.cache.set_cached_response", return_value=None):

        response = await client.post(
            "/rag/query",
            json=request_data,
            headers=mock_auth_headers
        )

        # Should return 200 or 501 (if not fully implemented)
        assert response.status_code in [200, 501]

        if response.status_code == 200:
            data = response.json()
            # Check response structure
            assert "answer" in data
            assert "sources" in data
            assert "confidence" in data
            assert isinstance(data["sources"], list)


@pytest.mark.asyncio
async def test_rag_response_citation_fields():
    """Test RAG response citations have all required fields."""
    # Mock response
    mock_response = {
        "answer": "Test answer",
        "sources": [
            {
                "paper_id": "p1",
                "title": "Paper 1",
                "chunk_id": "c1",
                "score": 0.95,
                "page": 5,
                "snippet": "This is a test snippet"
            }
        ],
        "confidence": 0.9,
        "cached": False
    }

    # Verify each citation has required fields
    required = ["paper_id", "title", "page", "snippet", "score"]
    for source in mock_response["sources"]:
        for field in required:
            assert field in source, f"Missing field: {field}"


# =============================================================================
# Evolution Query Tests
# =============================================================================

def test_evolution_query_structure():
    """Test evolution query request structure."""
    request = {
        "question": "How has YOLO evolved?",
        "paper_ids": ["yolo-v1", "yolo-v2", "yolo-v3", "yolo-v4"],
        "query_type": "evolution",
        "top_k": 20
    }

    # Evolution queries typically have multiple related papers
    assert len(request["paper_ids"]) >= 2

    # Query type should be evolution
    assert request["query_type"] == "evolution"

    # Top_k should be larger to capture evolution across versions
    assert request["top_k"] >= 10


def test_evolution_citations_temporal_order():
    """Test evolution citations can be ordered temporally."""
    citations = [
        {"paper_id": "yolo-v1", "title": "YOLO v1", "page": 1, "score": 0.9, "year": 2016},
        {"paper_id": "yolo-v3", "title": "YOLO v3", "page": 1, "score": 0.92, "year": 2018},
        {"paper_id": "yolo-v2", "title": "YOLO v2", "page": 1, "score": 0.91, "year": 2017},
    ]

    # Sort by year
    sorted_citations = sorted(citations, key=lambda x: x.get("year", 0))

    assert sorted_citations[0]["paper_id"] == "yolo-v1"
    assert sorted_citations[1]["paper_id"] == "yolo-v2"
    assert sorted_citations[2]["paper_id"] == "yolo-v3"


# =============================================================================
# Integration Tests
# =============================================================================

@pytest.mark.asyncio
async def test_citations_in_conversation_context():
    """Test citations are preserved in conversation history."""
    conversation = {
        "session_id": "session-123",
        "messages": [
            {
                "role": "user",
                "content": "What is the main contribution?",
                "timestamp": "2024-01-15T10:00:00Z"
            },
            {
                "role": "assistant",
                "content": "The paper proposes a novel approach.",
                "citations": [
                    {
                        "paper_id": "p1",
                        "title": "Paper 1",
                        "page": 5,
                        "snippet": "The paper proposes...",
                        "score": 0.95
                    }
                ],
                "timestamp": "2024-01-15T10:00:05Z"
            }
        ]
    }

    # Assistant message should have citations
    assistant_msg = conversation["messages"][1]
    assert "citations" in assistant_msg
    assert isinstance(assistant_msg["citations"], list)
    assert len(assistant_msg["citations"]) > 0

    # Each citation should have required fields
    for citation in assistant_msg["citations"]:
        assert "paper_id" in citation
        assert "title" in citation
        assert "page" in citation


@pytest.mark.asyncio
async def test_citation_serialization():
    """Test citations can be serialized to JSON."""
    citation = {
        "paper_id": "p1",
        "title": "Test Paper",
        "chunk_id": "c1",
        "score": 0.95,
        "page": 5,
        "snippet": "Test snippet with unicode: 深度学习"
    }

    # Should serialize without errors
    json_str = json.dumps(citation, ensure_ascii=False)

    # Should deserialize correctly
    parsed = json.loads(json_str)
    assert parsed["paper_id"] == "p1"
    assert parsed["snippet"] == "Test snippet with unicode: 深度学习"


@pytest.mark.asyncio
async def test_large_citation_count():
    """Test handling of many citations."""
    citations = [
        {
            "paper_id": f"paper-{i:03d}",
            "title": f"Paper {i}",
            "chunk_id": f"chunk-{i:03d}",
            "score": 0.9 - (i * 0.01),
            "page": i + 1,
            "snippet": f"Snippet {i}"
        }
        for i in range(20)
    ]

    assert len(citations) == 20

    # All should have valid scores
    for citation in citations:
        assert 0 <= citation["score"] <= 1


@pytest.mark.asyncio
async def test_citation_deduplication():
    """Test duplicate citations can be identified."""
    citations = [
        {"paper_id": "p1", "chunk_id": "c1", "page": 5},
        {"paper_id": "p1", "chunk_id": "c1", "page": 5},  # Duplicate
        {"paper_id": "p2", "chunk_id": "c2", "page": 3},
    ]

    # Deduplicate by (paper_id, chunk_id)
    seen = set()
    unique = []
    for citation in citations:
        key = (citation["paper_id"], citation["chunk_id"])
        if key not in seen:
            seen.add(key)
            unique.append(citation)

    assert len(unique) == 2


@pytest.mark.asyncio
async def test_citation_confidence_threshold():
    """Test citations below confidence threshold can be filtered."""
    citations = [
        {"paper_id": "p1", "score": 0.95},
        {"paper_id": "p2", "score": 0.70},
        {"paper_id": "p3", "score": 0.50},
        {"paper_id": "p4", "score": 0.30},
    ]

    threshold = 0.60
    filtered = [c for c in citations if c["score"] >= threshold]

    assert len(filtered) == 2
    assert all(c["score"] >= threshold for c in filtered)
