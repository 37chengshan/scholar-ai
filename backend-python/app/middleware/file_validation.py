"""PDF file upload validation with magic bytes checking.

Validates:
1. File extension (.pdf)
2. Magic bytes (%PDF- header)
3. File size (configurable)

Prevents file masquerading attacks where malicious files are renamed to .pdf
"""

from fastapi import UploadFile, HTTPException
from typing import Optional
from app.config import settings
from app.utils.logger import logger

# PDF magic bytes: %PDF- (hex: 25 50 44 46 2D)
# Source: https://en.wikipedia.org/wiki/List_of_file_signatures
PDF_MAGIC_BYTES = b'%PDF-'
MAX_PDF_SIZE = getattr(settings, 'MAX_FILE_SIZE', 50 * 1024 * 1024)  # 50 MB default


async def validate_pdf_upload(
    file: UploadFile,
    max_size: Optional[int] = None
) -> None:
    """Validate PDF file upload with security checks.

    Checks:
    1. File extension
    2. Magic bytes (file header)
    3. File size (if Content-Length provided)

    Args:
        file: FastAPI UploadFile to validate
        max_size: Maximum file size in bytes (default: settings.MAX_FILE_SIZE)

    Raises:
        HTTPException: If validation fails with RFC 7807 ProblemDetail
    """
    max_size = max_size or MAX_PDF_SIZE

    # Check 1: File extension
    if not file.filename or not file.filename.lower().endswith('.pdf'):
        raise HTTPException(
            status_code=400,
            detail={
                "type": "/errors/invalid-file-format",
                "title": "Invalid File Format",
                "status": 400,
                "detail": "File must have .pdf extension"
            }
        )

    # Check 2: Magic bytes (security: prevents file masquerading)
    try:
        file_header = await file.read(5)
        await file.seek(0)  # CRITICAL: Reset pointer after reading header

        if file_header != PDF_MAGIC_BYTES:
            logger.warning(
                "Invalid PDF magic bytes",
                filename=file.filename,
                header_hex=file_header.hex() if file_header else "empty"
            )
            raise HTTPException(
                status_code=400,
                detail={
                    "type": "/errors/invalid-file-format",
                    "title": "Invalid PDF File",
                    "status": 400,
                    "detail": "File header does not match PDF format. The file may be corrupted or masquerading."
                }
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to validate file header: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "type": "/errors/internal-error",
                "title": "Validation Error",
                "status": 500,
                "detail": f"Failed to validate file: {str(e)}"
            }
        )

    # Check 3: File size (if known)
    if file.size and file.size > max_size:
        raise HTTPException(
            status_code=400,
            detail={
                "type": "/errors/file-too-large",
                "title": "File Too Large",
                "status": 400,
                "detail": f"File size ({file.size / 1024 / 1024:.1f}MB) exceeds limit ({max_size / 1024 / 1024:.1f}MB)"
            }
        )

    logger.info(
        "PDF validation passed",
        filename=file.filename,
        size=file.size
    )