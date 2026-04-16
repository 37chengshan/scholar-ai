"""
Pytest fixtures for Knowledge Graph tests.

Provides mock data and fixtures for testing entity extraction,
graph building, PageRank calculation, and API endpoints.
"""

from typing import Any, Dict, List, Tuple
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio


# =============================================================================
# Neo4j Driver Fixtures
# =============================================================================


@pytest.fixture
def mock_neo4j_driver():
    """
    Mock Neo4j async driver with session context manager.

    Returns:
        Tuple of (driver, session) mocks for Neo4j operations.
    """
    driver = AsyncMock()
    session = AsyncMock()

    # Configure session context manager - session() returns a context manager
    session_context = AsyncMock()
    session_context.__aenter__ = AsyncMock(return_value=session)
    session_context.__aexit__ = AsyncMock(return_value=False)
    driver.session = MagicMock(return_value=session_context)

    # Configure session methods
    session.run = AsyncMock()
    session.execute_read = AsyncMock()
    session.execute_write = AsyncMock()

    return driver, session


@pytest.fixture
def mock_neo4j_session(mock_neo4j_driver):
    """
    Get the mock session from the Neo4j driver fixture.

    Returns:
        Mock session object.
    """
    _, session = mock_neo4j_driver
    return session


# =============================================================================
# Paper Data Fixtures
# =============================================================================


@pytest.fixture
def sample_paper_data() -> Dict[str, Any]:
    """
    Sample paper metadata dictionary.

    Returns:
        Dict with paper_id, title, authors, year, doi.
    """
    return {
        "paper_id": "paper-12345",
        "title": "Deep Learning for Medical Image Analysis: A Comprehensive Study",
        "authors": ["Zhang San", "Li Si", "Wang Wu"],
        "year": 2024,
        "doi": "10.1000/test.123",
        "abstract": "This paper presents a novel approach to medical image analysis using deep learning.",
    }


@pytest.fixture
def sample_paper_list() -> List[Dict[str, Any]]:
    """
    List of sample papers for graph testing.

    Returns:
        List of paper dictionaries.
    """
    return [
        {
            "paper_id": "paper-001",
            "title": "Transformer Architecture for NLP",
            "authors": ["Ashish Vaswani", "Noam Shazeer"],
            "year": 2017,
            "doi": "10.1000/trans.001",
        },
        {
            "paper_id": "paper-002",
            "title": "Attention Is All You Need",
            "authors": ["Ashish Vaswani", "Noam Shazeer", "Niki Parmar"],
            "year": 2017,
            "doi": "10.1000/attention.002",
        },
        {
            "paper_id": "paper-003",
            "title": "BERT: Pre-training of Deep Bidirectional Transformers",
            "authors": ["Jacob Devlin", "Ming-Wei Chang"],
            "year": 2019,
            "doi": "10.1000/bert.003",
        },
    ]


# =============================================================================
# Entity Fixtures
# =============================================================================


@pytest.fixture
def sample_entities() -> Dict[str, List[Dict[str, Any]]]:
    """
    Sample extracted entities from a paper.

    Returns:
        Dict with methods, datasets, metrics, venues lists.
    """
    return {
        "methods": [
            {"name": "Transformer", "context": "We use the Transformer architecture for sequence modeling", "confidence": 0.95},
            {"name": "Convolutional Neural Network", "context": "CNN is used for feature extraction", "confidence": 0.90},
            {"name": "YOLO", "context": "YOLO is used for real-time object detection", "confidence": 0.92},
        ],
        "datasets": [
            {"name": "ImageNet", "context": "trained on ImageNet-1K dataset", "confidence": 0.95},
            {"name": "COCO", "context": "evaluated on COCO validation set", "confidence": 0.93},
            {"name": "MNIST", "context": "tested on MNIST benchmark", "confidence": 0.88},
        ],
        "metrics": [
            {"name": "mAP@0.5", "context": "achieved 45.2 mAP@0.5", "confidence": 0.91},
            {"name": "F1 Score", "context": "F1 score of 0.87", "confidence": 0.89},
            {"name": "Accuracy", "context": "accuracy of 95.3%", "confidence": 0.92},
        ],
        "venues": [
            {"name": "CVPR", "type": "conference", "context": "published at CVPR 2024"},
            {"name": "NeurIPS", "type": "conference", "context": "accepted to NeurIPS"},
        ],
    }


@pytest.fixture
def sample_entity_variants() -> Dict[str, List[str]]:
    """
    Sample entity name variants for alignment testing.

    Returns:
        Dict mapping canonical names to variants.
    """
    return {
        "YOLO": ["YOLOv3", "YOLOv4", "You Only Look Once", "yolo"],
        "Transformer": ["transformer", "Transformers", "Self-Attention"],
        "Convolutional Neural Network": ["CNN", "ConvNet", "convolutional network"],
        "ImageNet": ["ImageNet-1K", "ImageNet 1K", "imagenet"],
    }


# =============================================================================
# Relationship Fixtures
# =============================================================================


@pytest.fixture
def sample_relationships() -> List[Dict[str, Any]]:
    """
    Sample relationships for graph building.

    Returns:
        List of relationship dicts with source, target, type, properties.
    """
    return [
        {"source": "paper-001", "target": "paper-002", "type": "CITES", "context": "cited in introduction"},
        {"source": "paper-002", "target": "paper-003", "type": "CITES", "context": "referenced for methodology"},
        {"source": "paper-001", "target": "Transformer", "type": "USES", "confidence": 0.95},
        {"source": "paper-001", "target": "ImageNet", "type": "EVALUATED_ON", "confidence": 0.93},
        {"source": "ImageNet", "target": "mAP@0.5", "type": "HAS_METRIC", "value": "45.2"},
        {"source": "Zhang San", "target": "Li Si", "type": "COAUTHOR", "count": 3},
        {"source": "paper-001", "target": "CVPR", "type": "PUBLISHED_IN"},
    ]


# =============================================================================
# LiteLLM Mock Fixtures
# =============================================================================


@pytest.fixture
def mock_litellm_entity_response():
    """
    Mock LiteLLM JSON response for entity extraction.

    Returns:
        Mock response object with entity extraction result.
    """
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(
            message=MagicMock(
                content='''{
                    "methods": [
                        {"name": "Transformer", "context": "We use the Transformer architecture", "confidence": 0.95},
                        {"name": "BERT", "context": "BERT pre-training approach", "confidence": 0.92}
                    ],
                    "datasets": [
                        {"name": "ImageNet", "context": "trained on ImageNet", "confidence": 0.94},
                        {"name": "COCO", "context": "evaluated on COCO", "confidence": 0.91}
                    ],
                    "metrics": [
                        {"name": "mAP", "context": "achieved high mAP", "confidence": 0.90},
                        {"name": "F1", "context": "F1 score reported", "confidence": 0.89}
                    ],
                    "venues": [
                        {"name": "CVPR", "type": "conference", "context": "published at CVPR 2024"}
                    ]
                }'''
            )
        )
    ]
    mock_response.usage = MagicMock(total_tokens=500)
    return mock_response


@pytest.fixture
def mock_litellm_similarity_response():
    """
    Mock LiteLLM response for entity similarity checking.

    Returns:
        Mock response for LLM-based entity alignment.
    """
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(
            message=MagicMock(
                content='''{"is_same_entity": true, "confidence": 0.92, "reason": "YOLOv3 is a version of YOLO"}'''
            )
        )
    ]
    return mock_response


@pytest.fixture
def mock_litellm_empty_response():
    """
    Mock LiteLLM response with empty entities.

    Returns:
        Mock response with empty entity lists.
    """
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(
            message=MagicMock(
                content='''{"methods": [], "datasets": [], "metrics": [], "venues": []}'''
            )
        )
    ]
    return mock_response


@pytest.fixture
def mock_litellm_malformed_response():
    """
    Mock LiteLLM response with malformed JSON.

    Returns:
        Mock response with invalid JSON content.
    """
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(
            message=MagicMock(
                content='''This is not valid JSON: {methods: [invalid]}'''
            )
        )
    ]
    return mock_response


# =============================================================================
# PageRank Fixtures
# =============================================================================


@pytest.fixture
def mock_gds_result() -> List[Dict[str, Any]]:
    """
    Mock Neo4j GDS PageRank calculation result.

    Returns:
        List of PageRank results with paper_id, title, score.
    """
    return [
        {"paper_id": "paper-001", "title": "Highly Cited Paper", "score": 0.5234},
        {"paper_id": "paper-002", "title": "Well Known Paper", "score": 0.4123},
        {"paper_id": "paper-003", "title": "Recent Paper", "score": 0.3456},
        {"paper_id": "paper-004", "title": "Standard Paper", "score": 0.2345},
        {"paper_id": "paper-005", "title": "Less Cited Paper", "score": 0.1234},
    ]


@pytest.fixture
def mock_gds_graph_info() -> Dict[str, Any]:
    """
    Mock GDS graph projection info.

    Returns:
        Dict with graph projection metadata.
    """
    return {
        "graphName": "paper-citations",
        "nodeCount": 1000,
        "relationshipCount": 5000,
        "exists": True,
    }


# =============================================================================
# Graph Data Fixtures (for G6 visualization)
# =============================================================================


@pytest.fixture
def sample_graph_nodes() -> List[Dict[str, Any]]:
    """
    Sample graph nodes for visualization testing.

    Returns:
        List of node dicts with id, name, type, pagerank.
    """
    return [
        {"id": "paper-001", "name": "Attention Is All You Need", "type": "Paper", "pagerank": 0.5234},
        {"id": "paper-002", "name": "BERT Pre-training", "type": "Paper", "pagerank": 0.4123},
        {"id": "author-001", "name": "Ashish Vaswani", "type": "Author", "pagerank": 0.0},
        {"id": "author-002", "name": "Jacob Devlin", "type": "Author", "pagerank": 0.0},
        {"id": "method-001", "name": "Transformer", "type": "Method", "pagerank": 0.0},
        {"id": "dataset-001", "name": "ImageNet", "type": "Dataset", "pagerank": 0.0},
        {"id": "metric-001", "name": "mAP", "type": "Metric", "pagerank": 0.0},
        {"id": "venue-001", "name": "NeurIPS", "type": "Venue", "pagerank": 0.0},
    ]


@pytest.fixture
def sample_graph_edges() -> List[Dict[str, Any]]:
    """
    Sample graph edges for visualization testing.

    Returns:
        List of edge dicts with source, target, type.
    """
    return [
        {"source": "paper-001", "target": "paper-002", "type": "CITES"},
        {"source": "author-001", "target": "paper-001", "type": "WROTE"},
        {"source": "author-002", "target": "paper-002", "type": "WROTE"},
        {"source": "paper-001", "target": "method-001", "type": "USES"},
        {"source": "method-001", "target": "dataset-001", "type": "EVALUATED_ON"},
        {"source": "dataset-001", "target": "metric-001", "type": "HAS_METRIC"},
        {"source": "paper-001", "target": "venue-001", "type": "PUBLISHED_IN"},
        {"source": "author-001", "target": "author-002", "type": "COAUTHOR"},
    ]


@pytest.fixture
def sample_graph_data(sample_graph_nodes, sample_graph_edges) -> Dict[str, List[Dict[str, Any]]]:
    """
    Combined graph data with nodes and edges.

    Returns:
        Dict with nodes and edges lists.
    """
    return {
        "nodes": sample_graph_nodes,
        "edges": sample_graph_edges,
    }


# =============================================================================
# Test Context Fixtures
# =============================================================================


@pytest.fixture
def sample_extraction_text() -> str:
    """
    Sample paper text for entity extraction testing.

    Returns:
        String containing academic paper content.
    """
    return """
    Abstract

    We present a comprehensive study on deep learning approaches for medical image analysis.
    Our method uses the Transformer architecture with Convolutional Neural Networks for
    feature extraction. We evaluate our approach on ImageNet and COCO datasets, achieving
    state-of-the-art results with mAP@0.5 of 45.2% and F1 Score of 0.87.

    1. Introduction

    Deep learning has revolutionized computer vision tasks including object detection and
    classification. In this work, we propose a novel approach combining Transformer models
    with CNN architectures.

    2. Methods

    Our model is based on the YOLO (You Only Look Once) framework for real-time detection.
    We use pre-trained weights from ImageNet-1K and fine-tune on medical imaging data.

    3. Experiments

    We benchmark our model on standard datasets including COCO validation set. Performance
    is measured using mAP metrics at various IoU thresholds.

    4. Results

    Our method achieves 95.3% accuracy on the test set, outperforming previous approaches.
    The results were presented at CVPR 2024 and accepted to NeurIPS.
    """


@pytest.fixture
def empty_text() -> str:
    """
    Empty text for edge case testing.

    Returns:
        Empty string.
    """
    return ""


@pytest.fixture
def short_text() -> str:
    """
    Very short text for edge case testing.

    Returns:
        Short text string.
    """
    return "This is a short text."
