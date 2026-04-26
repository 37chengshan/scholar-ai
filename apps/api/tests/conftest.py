"""
Pytest fixtures and configuration for backend-python tests.
"""

import os
import sys
import tempfile
from pathlib import Path
from typing import AsyncGenerator, Generator, Dict, Any
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import AsyncClient

# Set test environment before importing app
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("JWT_PUBLIC_KEY", "test-public-key")
os.environ.setdefault("ZHIPU_API_KEY", "sk-test-zhipu")
# Point LOCAL_STORAGE_PATH at a writable temp dir so ObjectStorage.__init__ does not
# try to mkdir /app/uploads (read-only in local dev / CI).
_TEST_STORAGE_TMP = tempfile.mkdtemp(prefix="scholar_test_uploads_")
os.environ.setdefault("LOCAL_STORAGE_PATH", _TEST_STORAGE_TMP)

# Set correct Qwen model path (absolute path from project root)
# The model is at /Users/cc/scholar-ai-deploy/schlar ai/Qwen/Qwen3-VL-Embedding-2B
# From backend-python, we need to go up 2 levels to reach project root
project_root = Path(__file__).parent.parent.parent.parent  # Go up from tests/ -> apps/api/ -> scholar-ai/ -> project root
qwen_model_path = project_root / "Qwen" / "Qwen3-VL-Embedding-2B"
if qwen_model_path.exists():
    os.environ.setdefault("QWEN3VL_EMBEDDING_MODEL_PATH", str(qwen_model_path))
    os.environ.setdefault("QWEN3VL_RERANKER_MODEL_PATH", str(project_root / "Qwen" / "Qwen3-VL-Reranker-2B"))

# Mock qwen_vl_utils module to avoid import errors during tests
# This module is required by Qwen model scripts but not needed for most tests
if 'qwen_vl_utils' not in sys.modules:
    sys.modules['qwen_vl_utils'] = MagicMock()
    sys.modules['qwen_vl_utils.vision_process'] = MagicMock()
    sys.modules['qwen_vl_utils.vision_process'].process_vision_info = MagicMock(return_value=None)

# Mock ZhipuAI client to avoid API key validation errors during tests
# The real ZhipuAI client raises ValueError if ZHIPU_API_KEY is empty
if 'app.utils.zhipu_client' not in sys.modules:
    mock_zhipu_module = MagicMock()
    mock_zhipu_module.ZhipuAI = MagicMock()
    sys.modules['app.utils.zhipu_client'] = mock_zhipu_module

# Mock Qwen3VL service to avoid model loading errors in CI
# The actual model files are not present in CI environment
if 'app.core.qwen3vl_service' not in sys.modules:
    mock_qwen_module = MagicMock()
    mock_qwen_module.Qwen3VLMultimodalEmbedding = MagicMock()
    mock_qwen_module.get_qwen3vl_service = MagicMock(return_value=MagicMock())
    sys.modules['app.core.qwen3vl_service'] = mock_qwen_module

# Set fallback paths for Qwen models (used by embedding config tests)
# These are only used during import, actual model loading is mocked above
os.environ.setdefault("QWEN3VL_EMBEDDING_MODEL_PATH", "/tmp/qwen3-vl-embedding")
os.environ.setdefault("QWEN3VL_RERANKER_MODEL_PATH", "/tmp/qwen3-vl-reranker")


@pytest.fixture(scope="session")
def app() -> FastAPI:
    """Create a test FastAPI application."""
    from app.main import app as fastapi_app
    return fastapi_app


@pytest.fixture
async def client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """Create an async HTTP client for testing."""
    from httpx import ASGITransport
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
def sync_client(app: FastAPI) -> Generator:
    """Create a synchronous HTTP client for testing."""
    from fastapi.testclient import TestClient
    with TestClient(app) as client:
        yield client


@pytest.fixture
def mock_internal_token() -> str:
    """Generate a mock internal service token for testing."""
    # This is a placeholder - actual implementation would use JWT signing
    return "test-internal-token"


@pytest.fixture
def mock_auth_headers(mock_internal_token: str) -> dict:
    """Return headers with internal auth token for protected endpoints."""
    return {
        "Authorization": f"Bearer {mock_internal_token}",
        "X-Internal-Service": "test-service",
    }


# =============================================================================
# Phase 2: PDF Upload & AI Parsing Fixtures
# =============================================================================


@pytest.fixture(scope="session")
def test_data_dir() -> Path:
    """Return the path to test data directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def docling_converter():
    """Returns DocumentConverter with OCR enabled."""
    try:
        from docling.document_converter import DocumentConverter
        from docling.datamodel.document import ConversionResult
        from docling.datamodel.base_models import InputFormat
        from docling.datamodel.document import InputDocument

        # Create converter with OCR enabled
        converter = DocumentConverter()
        return converter
    except ImportError:
        # Return mock if docling not installed
        mock_converter = MagicMock()
        mock_converter.convert.return_value = MagicMock(
            document=MagicMock(export_to_markdown=lambda: "# Test Document\n\nThis is test content."),
            status="success"
        )
        return mock_converter


@pytest.fixture
def sample_pdf_digital(test_data_dir: Path) -> Path:
    """Path to digital PDF test file (with text layer)."""
    pdf_path = test_data_dir / "sample_digital.pdf"
    if pdf_path.exists():
        return pdf_path
    # Return a temp file path for testing - actual file creation is handled separately
    return pdf_path


@pytest.fixture
def sample_pdf_scanned(test_data_dir: Path) -> Path:
    """Path to scanned PDF test file (image-based, requires OCR)."""
    pdf_path = test_data_dir / "sample_scanned.pdf"
    if pdf_path.exists():
        return pdf_path
    return pdf_path


@pytest.fixture
def sample_pdf_multicolumn(test_data_dir: Path) -> Path:
    """Path to multi-column academic layout PDF."""
    pdf_path = test_data_dir / "sample_multicolumn.pdf"
    if pdf_path.exists():
        return pdf_path
    return pdf_path


@pytest.fixture
def sample_pdf_chinese(test_data_dir: Path) -> Path:
    """Path to Chinese academic paper PDF."""
    pdf_path = test_data_dir / "sample_chinese.pdf"
    if pdf_path.exists():
        return pdf_path
    return pdf_path


@pytest.fixture
def sample_pdf_with_tables(test_data_dir: Path) -> Path:
    """Path to PDF containing tables."""
    pdf_path = test_data_dir / "sample_with_tables.pdf"
    if pdf_path.exists():
        return pdf_path
    return pdf_path


@pytest.fixture
def sample_pdf_with_formulas(test_data_dir: Path) -> Path:
    """Path to PDF with mathematical formulas."""
    pdf_path = test_data_dir / "sample_with_formulas.pdf"
    if pdf_path.exists():
        return pdf_path
    return pdf_path


@pytest.fixture
def mock_litellm():
    """Mock LiteLLM responses for notes generation."""
    mock = AsyncMock()

    # Mock response for notes generation
    mock_response = {
        "choices": [
            {
                "message": {
                    "content": """# 研究背景

本文研究了人工智能在医学影像分析中的应用。

# 研究方法

使用深度学习模型对医学影像进行分类。

# 研究结果

模型准确率达到95%，显著优于传统方法。

# 结论

人工智能可以有效辅助医学影像诊断。"""
                }
            }
        ],
        "usage": {
            "prompt_tokens": 1000,
            "completion_tokens": 500,
            "total_tokens": 1500
        }
    }

    mock.acompletion.return_value = mock_response
    mock.completion.return_value = mock_response

    return mock


@pytest.fixture
def test_paper_metadata() -> Dict[str, Any]:
    """Sample paper metadata dictionary."""
    return {
        "title": "Test Paper: AI in Medical Imaging",
        "authors": ["Zhang San", "Li Si"],
        "abstract": "This paper studies the application of AI in medical imaging analysis.",
        "doi": "10.1000/test.123",
        "arxiv_id": "2401.12345",
        "publication_year": 2024,
        "journal": "Journal of Medical AI",
        "pages": [1, 10],
    }


@pytest.fixture
def test_imrad_structure() -> Dict[str, Any]:
    """Sample IMRaD structure for testing."""
    return {
        "introduction": {
            "content": "Research background and objectives...",
            "page_start": 1,
            "page_end": 2,
        },
        "methods": {
            "content": "Deep learning approach...",
            "page_start": 3,
            "page_end": 5,
        },
        "results": {
            "content": "95% accuracy achieved...",
            "page_start": 6,
            "page_end": 8,
        },
        "conclusion": {
            "content": "AI is effective...",
            "page_start": 9,
            "page_end": 10,
        }
    }


@pytest_asyncio.fixture
async def async_db_connection():
    """Async PostgreSQL connection for tests."""
    try:
        import asyncpg
        # Use test database configuration
        conn = await asyncpg.connect(
            host=os.getenv("TEST_DB_HOST", "localhost"),
            port=int(os.getenv("TEST_DB_PORT", "5432")),
            user=os.getenv("TEST_DB_USER", "test_user"),
            password=os.getenv("TEST_DB_PASSWORD", "test_password"),
            database=os.getenv("TEST_DB_NAME", "scholar_ai_test")
        )
        yield conn
        await conn.close()
    except Exception:
        # Return mock connection if database not available
        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=[])
        mock_conn.fetchrow = AsyncMock(return_value={})
        mock_conn.execute = AsyncMock(return_value="INSERT 0 1")
        yield mock_conn


@pytest.fixture
def mock_neo4j_driver():
    """Mock Neo4j driver for graph database tests."""
    mock_driver = MagicMock()
    mock_session = MagicMock()
    mock_transaction = MagicMock()

    mock_transaction.run.return_value = MagicMock(
        data=lambda: [{"c": {"id": "chunk-1", "content": "test"}}]
    )

    mock_session.__enter__ = MagicMock(return_value=mock_session)
    mock_session.__exit__ = MagicMock(return_value=None)
    mock_session.execute_write = MagicMock(return_value=[{"id": "chunk-1"}])
    mock_session.execute_read = MagicMock(return_value=[{"id": "chunk-1"}])

    mock_driver.session.return_value = mock_session

    return mock_driver


@pytest.fixture
def sample_pdf_content() -> str:
    """Sample PDF text content for testing parsing without actual files."""
    return """
# Introduction

This paper presents a novel approach to medical image analysis using deep learning.

## Background

Medical imaging has become an essential tool in modern healthcare.

# Methods

We used a convolutional neural network (CNN) architecture.

## Dataset

Our dataset consists of 10,000 medical images.

# Results

The model achieved 95% accuracy on the test set.

## Performance Metrics

- Accuracy: 95%
- Precision: 93%
- Recall: 96%

# Conclusion

Our approach demonstrates significant improvements over existing methods.

## Future Work

Future research will focus on expanding the dataset.
"""


@pytest.fixture
def sample_chunks() -> list:
    """Sample document chunks for embedding tests."""
    return [
        {
            "id": "chunk-001",
            "content": "Introduction: This paper presents a novel approach to medical image analysis.",
            "section": "introduction",
            "page": 1,
            "is_table": False,
            "is_figure": False,
            "is_formula": False,
        },
        {
            "id": "chunk-002",
            "content": "Methods: We used a convolutional neural network architecture.",
            "section": "methods",
            "page": 3,
            "is_table": False,
            "is_figure": False,
            "is_formula": False,
        },
        {
            "id": "chunk-003",
            "content": "Results: The model achieved 95% accuracy.",
            "section": "results",
            "page": 6,
            "is_table": False,
            "is_figure": False,
            "is_formula": False,
        },
        {
            "id": "chunk-004",
            "content": "Table 1: Performance comparison between models",
            "section": "results",
            "page": 7,
            "is_table": True,
            "is_figure": False,
            "is_formula": False,
        },
    ]


@pytest.fixture
def mock_embedding_vector() -> list:
    """Sample embedding vector for tests (768 dimensions, typical for sentence-transformers)."""
    # Create a normalized random vector of 768 dimensions
    import random
    import math

    vector = [random.gauss(0, 1) for _ in range(768)]
    magnitude = math.sqrt(sum(x * x for x in vector))
    return [x / magnitude for x in vector]


@pytest.fixture
def mock_task_status() -> Dict[str, Any]:
    """Sample task status for async processing tests."""
    return {
        "task_id": "task-12345",
        "paper_id": "paper-67890",
        "status": "processing_ocr",  # pending, processing_ocr, parsing, extracting_imrad, generating_notes, completed, failed
        "progress": 25,
        "message": "OCR processing in progress",
        "created_at": "2024-01-15T10:00:00Z",
        "updated_at": "2024-01-15T10:05:00Z",
        "completed_at": None,
        "error": None,
    }
