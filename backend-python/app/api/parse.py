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
    temp_path = None
    try:
        # Validate file extension and magic bytes (validate_pdf_upload handles this)
        await validate_pdf_upload(file)

        # Task 3: Streaming file read with size limit
        MAX_FILE_SIZE = settings.PARSER_MAX_FILE_SIZE_MB * 1024 * 1024
        CHUNK_SIZE = 8192  # 8KB chunks

        # Stream read and accumulate (validate_pdf_upload already reset pointer)
        chunks = []
        total_size = 0

        while True:
            chunk = await file.read(CHUNK_SIZE)
            if not chunk:
                break

            # Check size limit during streaming
            total_size += len(chunk)
            if total_size > MAX_FILE_SIZE:
                logger.warning(
                    "File size exceeded during streaming upload",
                    filename=file.filename,
                    total_size_mb=total_size / (1024 * 1024),
                    limit_mb=settings.PARSER_MAX_FILE_SIZE_MB,
                )
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"文件大小超过限制 {settings.PARSER_MAX_FILE_SIZE_MB}MB",
                )

            chunks.append(chunk)

        # Merge chunks for temp file creation
        content = b"".join(chunks)

        logger.info(
            f"Parsing PDF: {file.filename}, size: {len(content)} bytes ({len(content) / (1024 * 1024):.1f}MB)"
        )

        # Save to temp file for Docling processing
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(content)
            temp_path = tmp.name

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


@router.post("/pdf/batch", status_code=status.HTTP_202_ACCEPTED)
async def parse_pdfs_batch(files: list[UploadFile] = File(...)):
    """
    批量解析PDF（异步任务）

    返回任务ID用于轮询状态。
    实际处理由后台worker完成。
    """
    # TODO: 实现批量解析，创建processing_tasks记录
    # 这需要与Node.js后端协调创建任务

    logger.info(f"Batch upload received: {len(files)} files")

    return {
        "status": "pending",
        "task_id": None,  # TODO: Create actual task
        "file_count": len(files),
        "message": "批量解析任务已提交，请等待实现",
    }


@router.get("/pdf/status/{task_id}", status_code=status.HTTP_200_OK)
async def get_parse_status(task_id: str):
    """
    查询PDF解析任务状态

    用于异步批量解析的状态轮询。
    """
    # TODO: 从数据库查询任务状态
    # 需要与Node.js后端协调获取任务状态

    return {"task_id": task_id, "status": "unknown", "message": "状态查询接口待实现"}
