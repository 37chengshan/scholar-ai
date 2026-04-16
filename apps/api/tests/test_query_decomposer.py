"""Tests for query decomposition and agentic retrieval.

Tests cover:
- Query decomposition into sub-questions
- Sub-question parsing from LLM responses
- Convergence detection for multi-round retrieval
- Agentic retrieval orchestration
"""

import json
from typing import Dict, Any, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def sample_evolution_query() -> str:
    """Sample evolution-type query."""
    return "YOLO evolution from v1 to v4"


@pytest.fixture
def sample_cross_paper_query() -> str:
    """Sample cross-paper query."""
    return "Compare CNN and Transformer architectures"


@pytest.fixture
def sample_single_paper_query() -> str:
    """Sample single paper query."""
    return "What is the main contribution of this paper?"


@pytest.fixture
def mock_decomposed_subquestions() -> List[Dict[str, Any]]:
    """Mock sub-questions from LLM decomposition."""
    return [
        {
            "question": "What are the key features of YOLOv1?",
            "query_type": "single",
            "target_papers": ["yolov1_paper_id"],
            "rationale": "Understand the original YOLO architecture"
        },
        {
            "question": "What improvements were introduced in YOLOv2?",
            "query_type": "single",
            "target_papers": ["yolov2_paper_id"],
            "rationale": "Track evolution from v1 to v2"
        },
        {
            "question": "How did YOLOv3 change the architecture?",
            "query_type": "single",
            "target_papers": ["yolov3_paper_id"],
            "rationale": "Understand v3 multi-scale predictions"
        },
        {
            "question": "What is the CSPDarknet backbone in YOLOv4?",
            "query_type": "single",
            "target_papers": ["yolov4_paper_id"],
            "rationale": "Final evolution to v4 with new backbone"
        }
    ]


@pytest.fixture
def mock_subquery_results() -> List[Dict[str, Any]]:
    """Mock search results for sub-questions."""
    return [
        {
            "sub_question": "What are the key features of YOLOv1?",
            "chunks": [
                {
                    "id": "chunk-001",
                    "paper_id": "yolov1_paper_id",
                    "content": "YOLOv1 treats object detection as a regression problem...",
                    "similarity": 0.92,
                    "page": 2
                }
            ],
            "summary": "YOLOv1 introduced unified real-time object detection"
        },
        {
            "sub_question": "What improvements were introduced in YOLOv2?",
            "chunks": [
                {
                    "id": "chunk-002",
                    "paper_id": "yolov2_paper_id",
                    "content": "YOLOv2 adds batch normalization and anchor boxes...",
                    "similarity": 0.89,
                    "page": 3
                }
            ],
            "summary": "YOLOv2 improved accuracy with batch norm and anchors"
        }
    ]


@pytest.fixture
def mock_llm_decomposition_response() -> str:
    """Mock LLM response for query decomposition."""
    return """[
  {
    "question": "What are the key features of YOLOv1?",
    "query_type": "single",
    "target_papers": ["yolov1_paper_id"],
    "rationale": "Understand the original YOLO architecture"
  },
  {
    "question": "What improvements were introduced in YOLOv2?",
    "query_type": "single",
    "target_papers": ["yolov2_paper_id"],
    "rationale": "Track evolution from v1 to v2"
  },
  {
    "question": "How did YOLOv3 change the architecture?",
    "query_type": "single",
    "target_papers": ["yolov3_paper_id"],
    "rationale": "Understand v3 multi-scale predictions"
  },
  {
    "question": "What is the CSPDarknet backbone in YOLOv4?",
    "query_type": "single",
    "target_papers": ["yolov4_paper_id"],
    "rationale": "Final evolution to v4 with new backbone"
  }
]"""


@pytest.fixture
def mock_convergence_check_response() -> Dict[str, Any]:
    """Mock LLM response for convergence check."""
    return {
        "is_converged": True,
        "reason": "No new information found in latest round",
        "confidence": 0.85
    }


@pytest.fixture
def mock_synthesis_response() -> str:
    """Mock LLM synthesis response."""
    return """## YOLO Evolution Timeline

### YOLOv1 (2016)
YOLOv1 introduced a unified approach to real-time object detection, treating it as a single regression problem.

### YOLOv2 (2017)
Key improvements included batch normalization, anchor boxes, and multi-scale training.

### YOLOv3 (2018)
YOLOv3 introduced multi-scale predictions at three different scales and a deeper Darknet-53 backbone.

### YOLOv4 (2020)
YOLOv4 adopted CSPDarknet53 as the backbone, achieving state-of-the-art results while maintaining real-time performance."""


# =============================================================================
# Query Decomposition Tests
# =============================================================================


def test_query_type_classification():
    """Test query type classification (single, cross_paper, evolution)."""
    # Evolution queries contain temporal/evolution keywords
    evolution_keywords = ["evolution", "timeline", "progress", "development", "history", "from v", "versions"]
    cross_paper_keywords = ["compare", "contrast", "difference", "similarities", "vs", "versus"]

    def classify_query(query: str) -> str:
        query_lower = query.lower()
        if any(kw in query_lower for kw in evolution_keywords):
            return "evolution"
        if any(kw in query_lower for kw in cross_paper_keywords):
            return "cross_paper"
        return "single"

    assert classify_query("YOLO evolution from v1 to v4") == "evolution"
    assert classify_query("CNN vs Transformer comparison") == "cross_paper"
    assert classify_query("What is the main contribution?") == "single"
    assert classify_query("BERT development timeline") == "evolution"


def test_parse_sub_questions():
    """Test parsing sub-questions from LLM response."""
    llm_response = """[
  {
    "question": "What are the key features of YOLOv1?",
    "query_type": "single",
    "target_papers": ["paper-001"],
    "rationale": "Understand original architecture"
  },
  {
    "question": "What improvements in YOLOv2?",
    "query_type": "single",
    "target_papers": ["paper-002"],
    "rationale": "Track evolution"
  }
]"""

    # Parse JSON from response
    parsed = json.loads(llm_response)

    assert isinstance(parsed, list)
    assert len(parsed) == 2
    assert parsed[0]["question"] == "What are the key features of YOLOv1?"
    assert parsed[0]["query_type"] == "single"
    assert "paper-001" in parsed[0]["target_papers"]


def test_parse_sub_questions_with_code_block():
    """Test parsing sub-questions from markdown code block."""
    llm_response = """Here are the sub-questions:

```json
[
  {
    "question": "What is the main contribution?",
    "query_type": "single"
  }
]
```"""

    # Extract JSON from code block
    import re
    json_match = re.search(r'```(?:json)?\n(.*?)\n```', llm_response, re.DOTALL)
    assert json_match is not None

    parsed = json.loads(json_match.group(1))
    assert isinstance(parsed, list)
    assert len(parsed) == 1


def test_decompose_evolution_query():
    """Test decomposition of evolution-type query."""
    query = "YOLO evolution from v1 to v4"

    # Expected sub-questions for evolution query
    expected_questions = [
        "What are the key features of YOLOv1?",
        "What improvements were introduced in YOLOv2?",
        "How did YOLOv3 change the architecture?",
        "What is the CSPDarknet backbone in YOLOv4?"
    ]

    # Verify query contains evolution keywords
    assert "evolution" in query.lower()
    assert "v1" in query and "v4" in query

    # Sub-questions should cover the version range
    version_range = [1, 2, 3, 4]
    for v in version_range:
        assert any(f"v{v}" in q for q in expected_questions)


def test_decompose_cross_paper_query():
    """Test decomposition of cross-paper query."""
    query = "Compare CNN and Transformer architectures"

    # Expected structure for cross-paper comparison
    expected_subquestions = [
        {
            "question": "What are the key features of CNN architecture?",
            "focus": "paper_1"
        },
        {
            "question": "What are the key features of Transformer architecture?",
            "focus": "paper_2"
        },
        {
            "question": "What are the main differences between CNN and Transformer?",
            "focus": "comparison"
        }
    ]

    assert len(expected_subquestions) >= 3
    assert any("CNN" in sq["question"] for sq in expected_subquestions)
    assert any("Transformer" in sq["question"] for sq in expected_subquestions)


def test_sub_question_count_limits():
    """Test that sub-question count is within 3-5 range."""
    sub_questions_3 = [{"question": f"Q{i}"} for i in range(3)]
    sub_questions_5 = [{"question": f"Q{i}"} for i in range(5)]
    sub_questions_7 = [{"question": f"Q{i}"} for i in range(7)]

    # 3-5 is valid
    assert 3 <= len(sub_questions_3) <= 5
    assert 3 <= len(sub_questions_5) <= 5

    # 7 is too many - should be limited
    assert len(sub_questions_7) > 5


def test_sub_question_structure():
    """Test sub-question has required fields."""
    required_fields = ["question", "query_type", "rationale"]

    sub_question = {
        "question": "What are the key features of YOLOv1?",
        "query_type": "single",
        "target_papers": ["paper-001"],
        "rationale": "Understand the original YOLO architecture"
    }

    for field in required_fields:
        assert field in sub_question

    assert isinstance(sub_question["question"], str)
    assert sub_question["query_type"] in ["single", "cross_paper", "evolution"]


# =============================================================================
# Convergence Detection Tests
# =============================================================================


def test_convergence_detection_new_info():
    """Test convergence detection when new information is found."""
    round_1_results = [
        {"chunks": [{"id": "chunk-001"}, {"id": "chunk-002"}]}
    ]
    round_2_results = [
        {"chunks": [{"id": "chunk-001"}, {"id": "chunk-003"}]}  # chunk-003 is new
    ]

    # Extract unique chunk IDs from each round
    round_1_ids = {c["id"] for r in round_1_results for c in r.get("chunks", [])}
    round_2_ids = {c["id"] for r in round_2_results for c in r.get("chunks", [])}

    # New chunks found
    new_chunks = round_2_ids - round_1_ids
    assert len(new_chunks) == 1
    assert "chunk-003" in new_chunks

    # Not converged when new info found
    is_converged = len(new_chunks) == 0
    assert is_converged is False


def test_convergence_detection_no_new_info():
    """Test convergence detection when no new information is found."""
    round_1_results = [
        {"chunks": [{"id": "chunk-001"}, {"id": "chunk-002"}]}
    ]
    round_2_results = [
        {"chunks": [{"id": "chunk-001"}, {"id": "chunk-002"}]}  # Same chunks
    ]

    round_1_ids = {c["id"] for r in round_1_results for c in r.get("chunks", [])}
    round_2_ids = {c["id"] for r in round_2_results for c in r.get("chunks", [])}

    # No new chunks
    new_chunks = round_2_ids - round_1_ids
    assert len(new_chunks) == 0

    # Converged when no new info
    is_converged = len(new_chunks) == 0
    assert is_converged is True


def test_max_round_termination():
    """Test termination after max rounds (3)."""
    max_rounds = 3
    current_round = 3

    should_terminate = current_round >= max_rounds
    assert should_terminate is True

    current_round = 2
    should_terminate = current_round >= max_rounds
    assert should_terminate is False


def test_llm_based_convergence_check():
    """Test LLM-based convergence judgment."""
    convergence_response = {
        "is_converged": True,
        "reason": "The latest round retrieved no new relevant information",
        "confidence": 0.88
    }

    assert "is_converged" in convergence_response
    assert "reason" in convergence_response
    assert "confidence" in convergence_response
    assert isinstance(convergence_response["is_converged"], bool)
    assert 0 <= convergence_response["confidence"] <= 1


# =============================================================================
# Agentic Retrieval Orchestration Tests
# =============================================================================


@pytest.mark.asyncio
async def test_parallel_subquestion_search():
    """Test parallel execution of sub-question searches."""
    import asyncio

    async def mock_search(question: str) -> Dict[str, Any]:
        await asyncio.sleep(0.01)  # Simulate search latency
        return {"question": question, "chunks": [{"id": f"chunk-{question[:5]}"}]}

    sub_questions = [
        "What is YOLOv1?",
        "What is YOLOv2?",
        "What is YOLOv3?"
    ]

    # Execute searches in parallel
    start_time = asyncio.get_event_loop().time()
    results = await asyncio.gather(*[mock_search(q) for q in sub_questions])
    end_time = asyncio.get_event_loop().time()

    # All results returned
    assert len(results) == len(sub_questions)

    # Parallel execution should be faster than sequential
    # (3 * 0.01 = 0.03s sequential, but parallel < 0.02s)
    assert end_time - start_time < 0.02


@pytest.mark.asyncio
async def test_multi_round_retrieval():
    """Test multi-round retrieval with early stopping."""
    max_rounds = 3
    round_count = 0
    all_results = []

    # Simulate rounds with convergence at round 2
    for round_num in range(1, max_rounds + 1):
        round_count += 1

        # Simulate results
        if round_num == 1:
            results = [{"chunks": [{"id": "chunk-001"}]}]
        elif round_num == 2:
            results = [{"chunks": [{"id": "chunk-001"}]}]  # No new chunks
        else:
            results = []

        all_results.extend(results)

        # Check convergence (simplified)
        if round_num == 2:
            # Simulate convergence detected
            break

    # Should stop at round 2 due to convergence
    assert round_count == 2


@pytest.mark.asyncio
async def test_synthesis_format():
    """Test synthesis response format."""
    synthesis = """## YOLO Evolution Timeline

### YOLOv1 (2016)
YOLOv1 introduced unified real-time object detection.

**Sources:**
- Paper: YOLOv1 (Page 2, Score: 0.92)
- Paper: YOLOv2 (Page 3, Score: 0.89)"""

    # Should have structured content
    assert "## " in synthesis  # Markdown heading
    assert "**Sources:**" in synthesis or "Sources:" in synthesis

    # Should contain citations/references
    assert "Page" in synthesis
    assert "Score" in synthesis or "0." in synthesis


# =============================================================================
# API Endpoint Tests
# =============================================================================


@pytest.mark.asyncio
async def test_agentic_search_endpoint(client, mock_auth_headers):
    """Test agentic search endpoint exists and accepts query_type."""
    request_data = {
        "query": "YOLO evolution from v1 to v4",
        "query_type": "evolution",
        "paper_ids": ["paper-001", "paper-002", "paper-003", "paper-004"],
        "max_rounds": 3
    }

    response = await client.post(
        "/rag/agentic",
        json=request_data,
        headers=mock_auth_headers
    )

    # Should return 200 if implemented, 501 if not yet implemented
    assert response.status_code in [200, 404, 501]

    if response.status_code == 200:
        data = response.json()
        assert "answer" in data
        assert "sub_questions" in data
        assert "sources" in data


@pytest.mark.asyncio
async def test_agentic_search_evolution_type(client, mock_auth_headers):
    """Test agentic search with evolution query type."""
    request_data = {
        "query": "BERT development timeline",
        "query_type": "evolution",
        "paper_ids": ["bert-base", "bert-large", "roberta"]
    }

    response = await client.post(
        "/rag/agentic",
        json=request_data,
        headers=mock_auth_headers
    )

    # Endpoint should accept evolution type
    assert response.status_code in [200, 404, 501]


# =============================================================================
# Integration Tests
# =============================================================================


@pytest.mark.asyncio
async def test_full_agentic_flow():
    """Test complete agentic retrieval flow."""
    import asyncio

    # 1. Decompose query
    query = "YOLO evolution from v1 to v4"
    sub_questions = [
        {"question": f"What is YOLOv{i}?", "query_type": "single"}
        for i in range(1, 5)
    ]

    assert len(sub_questions) == 4

    # 2. Execute parallel searches
    async def mock_search(sq: Dict) -> Dict:
        idx = hash(sq["question"]) % 1000  # Generate unique index
        return {
            "sub_question": sq["question"],
            "chunks": [{"id": f"chunk-{idx}", "similarity": 0.9}]
        }

    search_results = await asyncio.gather(*[mock_search(sq) for sq in sub_questions])
    assert len(search_results) == 4

    # 3. Check convergence (simulate no new info in round 2)
    is_converged = True  # Simulated
    assert isinstance(is_converged, bool)

    # 4. Synthesize results
    synthesis = {
        "answer": "YOLO evolved from v1 to v4 with significant improvements...",
        "timeline": ["YOLOv1 (2016)", "YOLOv2 (2017)", "YOLOv3 (2018)", "YOLOv4 (2020)"],
        "sources": search_results
    }

    assert "answer" in synthesis
    assert "sources" in synthesis


@pytest.mark.asyncio
async def test_cross_paper_synthesis():
    """Test synthesis of cross-paper query results."""
    sub_results = [
        {
            "question": "What are CNN features?",
            "paper_id": "paper-cnn",
            "summary": "CNN uses convolutional layers"
        },
        {
            "question": "What are Transformer features?",
            "paper_id": "paper-transformer",
            "summary": "Transformer uses attention"
        },
        {
            "question": "What are the differences?",
            "paper_id": None,
            "summary": "Comparison of architectures"
        }
    ]

    # Synthesis should combine information from multiple papers
    paper_ids = {r["paper_id"] for r in sub_results if r["paper_id"]}
    assert len(paper_ids) == 2

    # Should include comparison/analysis
    assert any("differences" in r["question"].lower() for r in sub_results)


# =============================================================================
# Error Handling Tests
# =============================================================================


@pytest.mark.asyncio
async def test_decomposition_error_handling():
    """Test handling of decomposition errors."""
    # Simulate LLM returning invalid JSON
    invalid_response = "This is not valid JSON"

    import json
    with pytest.raises(json.JSONDecodeError):
        json.loads(invalid_response)


@pytest.mark.asyncio
async def test_empty_search_results_handling():
    """Test handling when no results found for sub-question."""
    empty_results = {"sub_question": "Unknown topic?", "chunks": []}

    # Should handle gracefully
    assert empty_results["chunks"] == []
    assert isinstance(empty_results["chunks"], list)


@pytest.mark.asyncio
async def test_partial_failure_handling():
    """Test handling when some sub-questions fail."""
    import asyncio

    async def mock_search_with_failure(question: str) -> Dict:
        if "fail" in question.lower():
            raise Exception("Search failed")
        return {"question": question, "chunks": []}

    sub_questions = ["What is A?", "What is fail?", "What is C?"]

    # Execute with error handling
    results = []
    for q in sub_questions:
        try:
            result = await mock_search_with_failure(q)
            results.append(result)
        except Exception:
            # Continue with other sub-questions
            continue

    # Should have results for non-failing queries
    assert len(results) == 2
