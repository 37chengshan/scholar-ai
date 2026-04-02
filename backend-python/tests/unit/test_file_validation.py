import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi import UploadFile, HTTPException
from app.middleware.file_validation import validate_pdf_upload, PDF_MAGIC_BYTES


@pytest.fixture
def valid_pdf_file():
    """Create a mock valid PDF file."""
    file = MagicMock(spec=UploadFile)
    file.filename = "paper.pdf"
    file.size = 1024 * 1024  # 1 MB
    file.read = AsyncMock(return_value=PDF_MAGIC_BYTES)
    file.seek = AsyncMock()
    return file


@pytest.fixture
def invalid_extension_file():
    """Create a file with wrong extension."""
    file = MagicMock(spec=UploadFile)
    file.filename = "paper.txt"
    file.size = 1024
    return file


@pytest.fixture
def masquerading_file():
    """Create a file with .pdf extension but wrong magic bytes."""
    file = MagicMock(spec=UploadFile)
    file.filename = "malware.pdf"
    file.size = 1024
    file.read = AsyncMock(return_value=b'PK\x03\x04')  # ZIP magic bytes
    file.seek = AsyncMock()
    return file


@pytest.mark.asyncio
async def test_valid_pdf_passes_validation(valid_pdf_file):
    """Test that valid PDF files pass validation."""
    # Should not raise any exception
    await validate_pdf_upload(valid_pdf_file)
    valid_pdf_file.read.assert_called_once_with(5)
    valid_pdf_file.seek.assert_called_once_with(0)  # Pointer reset


@pytest.mark.asyncio
async def test_invalid_extension_rejected(invalid_extension_file):
    """Test that files without .pdf extension are rejected."""
    with pytest.raises(HTTPException) as exc_info:
        await validate_pdf_upload(invalid_extension_file)

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail["type"] == "/errors/invalid-file-format"
    assert "extension" in exc_info.value.detail["detail"].lower()


@pytest.mark.asyncio
async def test_masquerading_file_rejected(masquerading_file):
    """Test that files with wrong magic bytes are rejected (file masquerading attack)."""
    with pytest.raises(HTTPException) as exc_info:
        await validate_pdf_upload(masquerading_file)

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail["type"] == "/errors/invalid-file-format"
    assert "masquerading" in exc_info.value.detail["detail"].lower() or "header" in exc_info.value.detail["detail"].lower()
    masquerading_file.seek.assert_called_once_with(0)  # Pointer still reset on error


@pytest.mark.asyncio
async def test_file_too_large_rejected():
    """Test that files exceeding size limit are rejected."""
    large_file = MagicMock(spec=UploadFile)
    large_file.filename = "large.pdf"
    large_file.size = 100 * 1024 * 1024  # 100 MB (exceeds 50 MB limit)
    large_file.read = AsyncMock(return_value=PDF_MAGIC_BYTES)
    large_file.seek = AsyncMock()

    with pytest.raises(HTTPException) as exc_info:
        await validate_pdf_upload(large_file)

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail["type"] == "/errors/file-too-large"


@pytest.mark.asyncio
async def test_pointer_reset_after_header_read(valid_pdf_file):
    """Test that file pointer is reset after reading header (critical for subsequent reads)."""
    await validate_pdf_upload(valid_pdf_file)

    # Verify seek(0) was called to reset pointer
    valid_pdf_file.seek.assert_called_once_with(0)