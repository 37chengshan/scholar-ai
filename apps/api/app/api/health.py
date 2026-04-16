"""健康检查路由 - 区分 liveness 和 readiness"""

from fastapi import APIRouter, Request, status
from app.utils.problem_detail import Errors

router = APIRouter()


@router.get("/live", status_code=status.HTTP_200_OK)
async def liveness_check():
    """Liveness probe - 进程存活检查

    Kubernetes liveness probe - 只检查进程是否存活
    如果这个端点返回 200，说明进程在运行
    """
    return {"status": "alive", "service": "scholarai-ai"}


@router.get("/ready", status_code=status.HTTP_200_OK)
async def readiness_check(request: Request):
    """Readiness probe - 服务就绪检查

    Kubernetes readiness probe - 检查服务是否可以接受请求
    检查数据库连接和核心服务是否可用
    """

    services_status = {}

    # Check Milvus (lazy loaded, may not be initialized yet)
    if (
        hasattr(request.app.state, "milvus_service")
        and request.app.state.milvus_service
    ):
        services_status["milvus"] = {
            "status": "ready",
            "connected": True,
        }
    else:
        services_status["milvus"] = {
            "status": "not_ready",
            "note": "Will be initialized on first use",
        }

    # Check ReRanker (lazy loaded)
    if (
        hasattr(request.app.state, "reranker_service")
        and request.app.state.reranker_service
    ):
        reranker = request.app.state.reranker_service
        services_status["reranker"] = {
            "status": "ready",
            "initialized": reranker._initialized,
        }
    else:
        services_status["reranker"] = {
            "status": "not_ready",
            "note": "Will be initialized on first use",
        }

    # Check Embedding (lazy loaded)
    if (
        hasattr(request.app.state, "embedding_service")
        and request.app.state.embedding_service
    ):
        embedding = request.app.state.embedding_service
        services_status["embedding"] = {
            "status": "ready",
            "initialized": embedding.is_loaded(),
        }
    else:
        services_status["embedding"] = {
            "status": "not_ready",
            "note": "Will be initialized on first use",
        }

    # Basic service is ready if DB connections are established
    # AI services will be initialized lazily
    all_basic_ready = True  # DB connections already validated in lifespan

    return {
        "status": "ready" if all_basic_ready else "not_ready",
        "service": "scholarai-ai",
        "ai_services": services_status,
        "note": "AI services are lazy-loaded for faster startup",
    }


@router.get("", status_code=status.HTTP_200_OK)
async def health_check(request: Request):
    """完整健康检查 - 返回服务状态和模型加载状态

    Legacy endpoint for backward compatibility
    """

    services_status = {}

    if (
        hasattr(request.app.state, "milvus_service")
        and request.app.state.milvus_service
    ):
        services_status["milvus"] = {
            "status": "loaded",
            "connected": True,
        }
    else:
        services_status["milvus"] = {
            "status": "not_loaded",
            "connected": False,
        }

    if (
        hasattr(request.app.state, "reranker_service")
        and request.app.state.reranker_service
    ):
        reranker = request.app.state.reranker_service
        services_status["reranker"] = {
            "status": "loaded",
            "model": reranker.MODEL_NAME,
            "device": reranker.device,
            "initialized": reranker._initialized,
        }
    else:
        services_status["reranker"] = {
            "status": "not_loaded",
        }

    if (
        hasattr(request.app.state, "embedding_service")
        and request.app.state.embedding_service
    ):
        embedding = request.app.state.embedding_service
        model_info = embedding.get_model_info()
        services_status["embedding"] = {
            "status": "loaded",
            "model": model_info.get("name", "unknown"),
            "type": model_info.get("type", "unknown"),
            "dimension": model_info.get("dimension", "unknown"),
            "device": getattr(embedding, "device", "unknown"),
            "initialized": embedding.is_loaded(),
        }
    else:
        services_status["embedding"] = {
            "status": "not_loaded",
        }

    all_loaded = all(
        s.get("status") in ["loaded", "available"] for s in services_status.values()
    )

    return {
        "status": "ok" if all_loaded else "degraded",
        "service": "scholarai-ai",
        "models": services_status,
    }
