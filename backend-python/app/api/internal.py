"""内部API端点

用于Node.js Gateway与Python AI Service之间的内部通信
所有端点需要JWT认证
"""

from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional

from app.core.auth import verify_internal_token, get_current_service
from app.core.notes_generator import NotesGenerator
from app.core.database import postgres_db
from app.utils.logger import logger
from app.workers.pdf_download_worker import download_external_pdf
from app.utils.problem_detail import Errors

router = APIRouter()

# Notes generator instance
notes_generator = NotesGenerator()


class RegenerateNotesRequest(BaseModel):
    """Request body for notes regeneration."""
    paperId: str
    modificationRequest: str = ""
    storageKey: str


class ProcessExternalRequest(BaseModel):
    """Request body for processing external paper."""
    paperId: str
    pdfUrl: str
    source: str  # 'arxiv' or 'semantic-scholar'
    externalId: Optional[str] = None  # arXiv ID or S2 paper ID


@router.get("/health")
async def internal_health_check(
    request: Request,
    service: dict = Depends(get_current_service)
):
    """内部健康检查端点 (需要JWT认证)

    Returns:
        Health status with service info
    """
    request_id = request.headers.get("X-Request-ID", "unknown")
    calling_service = service.get("sub", "unknown")

    logger.info(
        "Internal health check",
        extra={
            "request_id": request_id,
            "calling_service": calling_service,
            "endpoint": "/internal/health"
        }
    )

    return {
        "status": "healthy",
        "service": "python-ai-service",
        "caller": calling_service,
        "request_id": request_id
    }


@router.post("/parse")
async def internal_parse_pdf(
    request: Request,
    service: dict = Depends(get_current_service)
):
    """PDF解析端点 (Phase 2实现)

    接收PDF文件，使用Docling解析IMRaD结构

    Args:
        request: FastAPI request with PDF file
        service: JWT payload from verify_internal_token

    Returns:
        Parsed PDF structure

    Note:
        Phase 2实现 - 当前返回placeholder
    """
    request_id = request.headers.get("X-Request-ID", "unknown")
    calling_service = service.get("sub", "unknown")

    logger.info(
        "PDF parse request received",
        extra={
            "request_id": request_id,
            "calling_service": calling_service,
            "endpoint": "/internal/parse"
        }
    )

    # Phase 2: 实现PDF解析
    return {
        "status": "not_implemented",
        "message": "PDF parsing will be implemented in Phase 2",
        "request_id": request_id
    }


@router.post("/rag")
async def internal_rag_query(
    request: Request,
    service: dict = Depends(get_current_service)
):
    """RAG问答端点 (Phase 3实现)

    基于PaperQA2的RAG问答服务

    Args:
        request: FastAPI request with query
        service: JWT payload from verify_internal_token

    Returns:
        RAG response with citations

    Note:
        Phase 3实现 - 当前返回placeholder
    """
    request_id = request.headers.get("X-Request-ID", "unknown")
    calling_service = service.get("sub", "unknown")

    logger.info(
        "RAG query request received",
        extra={
            "request_id": request_id,
            "calling_service": calling_service,
            "endpoint": "/internal/rag"
        }
    )

    # Phase 3: 实现RAG问答
    return {
        "status": "not_implemented",
        "message": "RAG Q&A will be implemented in Phase 3",
        "request_id": request_id
    }


@router.post("/entities")
async def internal_extract_entities(
    request: Request,
    service: dict = Depends(get_current_service)
):
    """实体抽取端点 (Phase 5实现)

    从论文中抽取实体并构建知识图谱

    Args:
        request: FastAPI request with text
        service: JWT payload from verify_internal_token

    Returns:
        Extracted entities and relationships

    Note:
        Phase 5实现 - 当前返回placeholder
    """
    request_id = request.headers.get("X-Request-ID", "unknown")
    calling_service = service.get("sub", "unknown")

    logger.info(
        "Entity extraction request received",
        extra={
            "request_id": request_id,
            "calling_service": calling_service,
            "endpoint": "/internal/entities"
        }
    )

    # Phase 5: 实现实体抽取
    return {
        "status": "not_implemented",
        "message": "Entity extraction will be implemented in Phase 5",
        "request_id": request_id
    }


@router.post("/regenerate-notes")
async def internal_regenerate_notes(
    request: RegenerateNotesRequest,
    service: dict = Depends(get_current_service)
):
    """笔记重新生成端点

    接收论文ID和修改要求，使用NotesGenerator重新生成笔记

    Args:
        request: RegenerateNotesRequest with paperId and modificationRequest
        service: JWT payload from verify_internal_token

    Returns:
        Regenerated notes
    """
    import json

    calling_service = service.get("sub", "unknown")
    logger.info(
        "Notes regeneration request received",
        extra={
            "calling_service": calling_service,
            "paper_id": request.paperId,
            "endpoint": "/internal/regenerate-notes"
        }
    )

    try:
        # Fetch paper data from PostgreSQL
        row = await postgres_db.fetchrow(
            """SELECT title, authors, year, venue, imrad_json, reading_notes
               FROM papers WHERE id = $1""",
            request.paperId
        )

        if not row:
            raise HTTPException(status_code=404, detail=Errors.not_found("Paper not found"))

        imrad_data = row["imrad_json"]
        if not imrad_data:
            raise HTTPException(status_code=400, detail=Errors.validation("Paper not yet parsed"))

        # Parse imrad_json if it's a string
        if isinstance(imrad_data, str):
            imrad_data = json.loads(imrad_data)

        # Prepare paper metadata
        paper_metadata = {
            "title": row["title"] or "Unknown",
            "authors": row["authors"] if row["authors"] else [],
            "year": row["year"] or "",
            "venue": row["venue"] or ""
        }

        # Generate new notes with modification request
        import asyncio
        notes = await notes_generator.regenerate_notes(
            paper_metadata=paper_metadata,
            imrad_structure=imrad_data,
            modification_request=request.modificationRequest
        )

        logger.info(
            "Notes regenerated successfully",
            paper_id=request.paperId,
            calling_service=calling_service
        )

        return {
            "status": "success",
            "paperId": request.paperId,
            "notes": notes,
            "message": "Notes regenerated successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to regenerate notes: {e}",
            extra={"paper_id": request.paperId}
        )
        raise HTTPException(status_code=500, detail=Errors.internal(str(e)))


@router.post("/process-external")
async def internal_process_external(
    request: ProcessExternalRequest,
    service: dict = Depends(get_current_service)
):
    """处理外部论文PDF下载端点

    接收外部论文信息，下载PDF并触发6-state处理流程

    Args:
        request: ProcessExternalRequest with paperId, pdfUrl, source, externalId
        service: JWT payload from verify_internal_token

    Returns:
        Download result with paper_id, download_success, and status
    """
    calling_service = service.get("sub", "unknown")
    logger.info(
        "External paper processing request received",
        extra={
            "calling_service": calling_service,
            "paper_id": request.paperId,
            "source": request.source,
            "external_id": request.externalId,
            "endpoint": "/internal/process-external"
        }
    )

    try:
        # Download PDF asynchronously with fallback
        arxiv_id = request.externalId if request.source == "arxiv" else None

        success = await download_external_pdf(
            paper_id=request.paperId,
            primary_url=request.pdfUrl,
            source=request.source,
            arxiv_id=arxiv_id
        )

        if success:
            logger.info(
                "External paper PDF downloaded successfully",
                paper_id=request.paperId,
                source=request.source,
                calling_service=calling_service
            )
        else:
            logger.warning(
                "External paper PDF download failed, marked as no_pdf",
                paper_id=request.paperId,
                source=request.source,
                calling_service=calling_service
            )

        return {
            "paper_id": request.paperId,
            "download_success": success,
            "status": "pending" if success else "no_pdf"
        }

    except Exception as e:
        logger.error(
            f"Failed to process external paper: {e}",
            extra={
                "paper_id": request.paperId,
                "source": request.source
            }
        )
        raise HTTPException(status_code=500, detail=Errors.internal(str(e)))
