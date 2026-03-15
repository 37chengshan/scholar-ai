"""内部API端点

用于Node.js Gateway与Python AI Service之间的内部通信
所有端点需要JWT认证
"""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from app.core.auth import verify_internal_token, get_current_service
from app.utils.logger import logger

router = APIRouter()


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
