"""PDF解析路由

提供PDF解析API端点，使用Docling进行结构化内容提取。
"""

import os
import tempfile
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.docling_service import DoclingParser
from app.core.imrad_extractor import extract_imrad_structure, extract_metadata
from app.middleware.file_validation import validate_pdf_upload
from app.utils.logger import logger
from app.utils.problem_detail import Errors

router = APIRouter()


@router.post("/pdf", status_code=status.HTTP_200_OK)
async def parse_pdf(file: UploadFile = File(...)):
    """
    解析PDF文件

    - 使用Docling解析PDF
    - 提取结构化内容（IMRaD格式）
    - 返回Markdown和结构化JSON

    Security:
    - Validates file extension
    - Validates PDF magic bytes
    - Enforces file size limit
    """
    temp_path = None
    try:
        # Validate file (extension + magic bytes + size)
        # Per D-05: Check magic bytes to prevent file masquerading
        await validate_pdf_upload(file)

        # Read content after validation
        content = await file.read()

        logger.info(f"Parsing PDF: {file.filename}, size: {len(content)} bytes")

        # Save to temp file for Docling processing
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            tmp.write(content)
            temp_path = tmp.name

        # Parse with Docling
        parser = DoclingParser()
        result = await parser.parse_pdf(temp_path)

        # Extract IMRaD structure using dedicated extractor
        imrad = extract_imrad_structure(result["items"])
        metadata = extract_metadata(result["items"])

        return {
            "status": "success",
            "filename": file.filename,
            "pages": result["page_count"],
            "markdown": result["markdown"],
            "items": result["items"],
            "imrad": imrad,
            "metadata": metadata,
        }

    except HTTPException:
        # Re-raise HTTPExceptions (including validation errors)
        raise

    except FileNotFoundError as e:
        logger.error(f"PDF file not found: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=Errors.not_found("PDF文件不存在")
        )

    except Exception as e:
        logger.error(f"PDF parsing error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=Errors.internal(f"PDF解析失败: {str(e)}")
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
        "message": "批量解析任务已提交，请等待实现"
    }


@router.get("/pdf/status/{task_id}", status_code=status.HTTP_200_OK)
async def get_parse_status(task_id: str):
    """
    查询PDF解析任务状态

    用于异步批量解析的状态轮询。
    """
    # TODO: 从数据库查询任务状态
    # 需要与Node.js后端协调获取任务状态

    return {
        "task_id": task_id,
        "status": "unknown",
        "message": "状态查询接口待实现"
    }
