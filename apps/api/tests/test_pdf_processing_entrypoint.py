"""Tests confirming the canonical PDF processing entrypoint is PDFCoordinator.

Per Task F of Backend Pipeline Cleanup v1:
- PDFProcessor.process_pdf_task() delegates to PDFCoordinator.process()
- Legacy methods emit DeprecationWarning when called
"""

import warnings
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.workers.pdf_worker import PDFProcessor


@pytest.mark.asyncio
async def test_process_pdf_task_delegates_to_coordinator():
    """PDFProcessor.process_pdf_task() must call PDFCoordinator.process()."""
    processor = PDFProcessor()
    mock_coordinator = MagicMock()
    mock_coordinator.init_db = AsyncMock()
    mock_coordinator.process = AsyncMock(return_value=True)

    with patch("app.workers.pdf_worker.get_pdf_coordinator", return_value=mock_coordinator):
        result = await processor.process_pdf_task("task-1")

    mock_coordinator.process.assert_called_once_with("task-1")
    assert result is True


@pytest.mark.asyncio
async def test_process_pdf_task_returns_false_on_coordinator_failure():
    """process_pdf_task propagates coordinator failure as False."""
    processor = PDFProcessor()
    mock_coordinator = MagicMock()
    mock_coordinator.init_db = AsyncMock()
    mock_coordinator.process = AsyncMock(return_value=False)

    with patch("app.workers.pdf_worker.get_pdf_coordinator", return_value=mock_coordinator):
        result = await processor.process_pdf_task("task-1")

    assert result is False


def test_process_pdf_main_chain_emits_deprecation_warning():
    """process_pdf_main_chain must emit DeprecationWarning."""
    processor = PDFProcessor()
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        try:
            import asyncio
            asyncio.run(
                processor.process_pdf_main_chain(
                    task_id="t1", temp_path="/tmp/x.pdf", user_id="u1"
                )
            )
        except Exception:
            pass  # We only care about the warning, not the result
    categories = [w.category for w in caught]
    assert DeprecationWarning in categories


def test_process_pdf_enhancement_chain_emits_deprecation_warning():
    """process_pdf_enhancement_chain must emit DeprecationWarning."""
    processor = PDFProcessor()
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        try:
            import asyncio
            asyncio.run(
                processor.process_pdf_enhancement_chain(task_id="t1", paper_id="p1")
            )
        except Exception:
            pass
    categories = [w.category for w in caught]
    assert DeprecationWarning in categories


def test_parse_pdf_emits_deprecation_warning():
    """_parse_pdf must emit DeprecationWarning."""
    processor = PDFProcessor()
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        try:
            import asyncio
            asyncio.run(processor._parse_pdf("/tmp/fake.pdf"))
        except Exception:
            pass
    categories = [w.category for w in caught]
    assert DeprecationWarning in categories


def test_chunk_content_emits_deprecation_warning():
    """_chunk_content must emit DeprecationWarning."""
    processor = PDFProcessor()
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        try:
            import asyncio
            asyncio.run(processor._chunk_content({}))
        except Exception:
            pass
    categories = [w.category for w in caught]
    assert DeprecationWarning in categories


def test_embed_text_chunks_emits_deprecation_warning():
    """_embed_text_chunks must emit DeprecationWarning."""
    processor = PDFProcessor()
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        try:
            import asyncio
            asyncio.run(processor._embed_text_chunks([]))
        except Exception:
            pass
    categories = [w.category for w in caught]
    assert DeprecationWarning in categories


def test_store_chunks_emits_deprecation_warning():
    """_store_chunks must emit DeprecationWarning."""
    processor = PDFProcessor()
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        try:
            import asyncio
            asyncio.run(
                processor._store_chunks(
                    chunks=[], embeddings=[], user_id="u1", paper_id="p1"
                )
            )
        except Exception:
            pass
    categories = [w.category for w in caught]
    assert DeprecationWarning in categories
