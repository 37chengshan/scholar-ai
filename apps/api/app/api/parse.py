"""PDF解析路由

提供PDF解析API端点，使用Docling进行结构化内容提取。

Per Sprint 4 Task 3:
- Streaming file upload (no full file in memory)
- File size limit enforcement
- Timeout protection
- Magic bytes validation
"""

import asyncio
import os
import tempfile
import io
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse

from app.config import settings
from app.core.docling_service import DoclingParser, FileTooLargeError, ParseTimeoutError
from app.core.imrad_extractor import extract_imrad_structure, extract_metadata
from app.middleware.file_validation import validate_pdf_upload
from app.utils.logger import logger
from app.utils.problem_detail import Errors

router = APIRouter()


@router.post("/pdf", status_code=status.HTTP_200_OK)
async def parse_pdf(
    file: UploadFile = File(...),
    arxiv_id: Optional[str] = Form(None),
    force_ocr: bool = Form(False),
):
    """
    解析PDF文件

    - 使用Docling解析PDF
    - 提取结构化内容（IMRaD格式）
    - 返回Markdown和结构化JSON

    Security:
    - Validates file extension
    - Validates PDF magic bytes
    - Enforces file size limit (streaming)
    - Timeout protection

    Per Sprint 4 Task 3:
    - Stream-based upload (chunks, not full file)
    - File size check during streaming
    - Magic bytes validation at start
    - Timeout protection
    """
    # Task 1: Streaming file upload with tempfile per D-11
    # Per D-11: Memory-stable for large files using streaming write
    MAX_FILE_SIZE = settings.PARSER_MAX_FILE_SIZE_MB * 1024 * 1024
    CHUNK_SIZE = 8 * 1024  # 8KB per Sprint 4 D-04

    temp_path = None
    try:
        # Validate file extension and magic bytes
        await validate_pdf_upload(file)

        # Per D-11: Streaming write to tempfile (no b"".join())
        total_size = 0

        with tempfile.NamedTemporaryFile(
            suffix=".pdf",
            delete=False,  # Keep file for processing
            dir=settings.UPLOAD_DIR if os.path.exists(settings.UPLOAD_DIR) else None
        ) as tmp:
            try:
                while True:
                    chunk = await file.read(CHUNK_SIZE)
                    if not chunk:
                        break

                    # Per D-11: Size check during streaming (not after)
                    total_size += len(chunk)
                    if total_size > MAX_FILE_SIZE:
                        # Clean up tempfile before raising
                        tmp.close()
                        os.unlink(tmp.name)
                        logger.warning(
                            "File size exceeded during streaming upload",
                            filename=file.filename,
                            total_size_mb=total_size / (1024 * 1024),
                            limit_mb=settings.PARSER_MAX_FILE_SIZE_MB,
                        )
                        raise HTTPException(
                            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                            detail=f"File too large: {total_size / (1024*1024):.1f}MB exceeds {settings.PARSER_MAX_FILE_SIZE_MB}MB",
                        )

                    tmp.write(chunk)

                temp_path = tmp.name

            except Exception as e:
                # Clean up on error
                tmp.close()
                if os.path.exists(tmp.name):
                    os.unlink(tmp.name)
                raise

        logger.info(
            "Streaming upload complete",
            filename=file.filename,
            size_mb=total_size / (1024 * 1024),
            temp_path=temp_path,
        )

        # Parse with Docling
        parser = DoclingParser()

        # Task 3: Timeout protection
        try:
            result = await asyncio.wait_for(
                parser.parse_pdf(temp_path, force_ocr=force_ocr),
                timeout=settings.PARSER_TIMEOUT_SECONDS,
            )
        except asyncio.TimeoutError:
            logger.error(
                "PDF parsing timeout",
                filename=file.filename,
                timeout_seconds=settings.PARSER_TIMEOUT_SECONDS,
            )
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail=f"解析超时（超过 {settings.PARSER_TIMEOUT_SECONDS} 秒）",
            )

        # Extract IMRaD structure using dedicated extractor
        imrad = extract_imrad_structure(result["items"])
        metadata = extract_metadata(result["items"], arxiv_id=arxiv_id)

        return {
            "status": "success",
            "filename": file.filename,
            "page_count": result["page_count"],  # Task 2: Unified field
            "markdown": result["markdown"],
            "items": result["items"],
            "imrad": imrad,
            "metadata": metadata,
        }

    except FileTooLargeError as e:
        logger.error(f"File size exceeded: {e}")
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=str(e)
        )

    except ParseTimeoutError as e:
        logger.error(f"Parsing timeout: {e}")
        raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail=str(e))

    except HTTPException:
        # Re-raise HTTPExceptions (including validation errors)
        raise

    except FileNotFoundError as e:
        logger.error(f"PDF file not found: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=Errors.not_found("PDF文件不存在"),
        )

    except Exception as e:
        logger.error(f"PDF parsing error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=Errors.internal(f"PDF解析失败: {str(e)}"),
        )

    finally:
        # Cleanup temp file
        if temp_path:
            try:
                Path(temp_path).unlink(missing_ok=True)
            except Exception as e:
                logger.warning(f"Failed to cleanup temp file: {e}")


# NOTE(PR22-A): batch/status stubs are intentionally removed.
# They previously exposed placeholder behavior and violated contract reliability.
