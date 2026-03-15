"""PDF解析路由"""

import os
import tempfile
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.utils.logger import logger

router = APIRouter()


@router.post("/pdf", status_code=status.HTTP_200_OK)
async def parse_pdf(file: UploadFile = File(...)):
    """
    解析PDF文件

    - 使用Docling解析PDF
    - 提取结构化内容（IMRaD格式）
    - 返回Markdown和结构化JSON
    """
    try:
        # 验证文件类型
        if not file.filename.endswith('.pdf'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="只接受PDF文件"
            )

        # 保存上传的文件
        content = await file.read()
        if len(content) > settings.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"文件大小超过限制 ({settings.MAX_FILE_SIZE / 1024 / 1024}MB)"
            )

        logger.info(f"Parsing PDF: {file.filename}, size: {len(content)} bytes")

        # TODO: 集成Docling进行PDF解析
        # from docling.document_converter import DocumentConverter
        # converter = DocumentConverter()
        # result = converter.convert(temp_path)
        # markdown = result.document.export_to_markdown()

        # 模拟返回
        return {
            "status": "success",
            "filename": file.filename,
            "pages": 0,  # TODO: 实际页数
            "markdown": "",  # TODO: Docling解析结果
            "imrad": {
                "introduction": "",
                "method": "",
                "results": "",
                "conclusion": ""
            },
            "metadata": {
                "title": "",
                "authors": [],
                "abstract": "",
                "keywords": []
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"PDF parsing error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"PDF解析失败: {str(e)}"
        )


@router.post("/pdf/batch", status_code=status.HTTP_200_OK)
async def parse_pdfs_batch(files: list[UploadFile] = File(...)):
    """批量解析PDF（异步任务）"""
    # TODO: 实现批量解析，使用消息队列
    return {
        "status": "pending",
        "task_id": "task-1",
        "file_count": len(files),
        "message": "批量解析任务已提交"
    }
