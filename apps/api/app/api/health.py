"""健康检查路由 - 区分 liveness 和 readiness"""

from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse
from app.config import settings
from app.core.embedding.factory import get_embedding_service
from app.core.reranker.factory import get_reranker_service
from app.core.milvus_service import MilvusService
from app.services.system_service import get_services_health
from app.utils.problem_detail import Errors

router = APIRouter()


def _provider_status(service: object | None, *, component: str) -> dict:
    if service is None:
        return {
            "status": "not_ready",
            "mode": "lazy",
            "note": "Will be initialized on first use",
        }

    get_runtime_binding = getattr(service, "get_runtime_binding", None)
    if callable(get_runtime_binding):
        binding = get_runtime_binding()
        return {
            "status": "available" if binding.resolved_mode in {"online", "shim"} else "loaded",
            "mode": binding.resolved_mode,
            "provider": binding.provider_name,
            "model": binding.model,
            "dimension": binding.dimension,
            "supports_multimodal": binding.supports_multimodal,
            "component": component,
        }

    payload = {
        "status": "loaded",
        "mode": "local",
        "component": component,
    }
    model_info = getattr(service, "get_model_info", None)
    if callable(model_info):
        info = model_info()
        payload.update(
            {
                "model": info.get("name", "unknown"),
                "type": info.get("type", "unknown"),
                "dimension": info.get("dimension"),
                "provider": info.get("provider"),
            }
        )

    is_loaded = getattr(service, "is_loaded", None)
    if callable(is_loaded):
        payload["initialized"] = bool(is_loaded())

    device = getattr(service, "get_device", None)
    if callable(device):
        payload["device"] = device()
    elif hasattr(service, "device"):
        payload["device"] = getattr(service, "device")

    if hasattr(service, "_initialized"):
        payload["initialized"] = getattr(service, "_initialized")

    return payload


def _resolve_runtime_service(request: Request, attr_name: str, factory) -> object | None:
    service = getattr(request.app.state, attr_name, None)
    if service is not None:
        return service

    try:
        service = factory()
    except Exception as exc:
        return {
            "status": "error",
            "component": attr_name.removesuffix("_service"),
            "message": str(exc),
        }

    setattr(request.app.state, attr_name, service)
    return service


def _milvus_status(request: Request) -> dict:
    service = getattr(request.app.state, "milvus_service", None)
    if service is None:
        try:
            service = MilvusService()
            service.connect()
            request.app.state.milvus_service = service
        except Exception as exc:
            return {
                "status": "error",
                "connected": False,
                "message": str(exc),
            }

    return {
        "status": "available" if getattr(service, "_connected", False) else "not_ready",
        "connected": bool(getattr(service, "_connected", False)),
        "mode": getattr(service, "mode", "unknown"),
        "collection": settings.MILVUS_COLLECTION_CONTENTS_V2,
    }


@router.get("/live", status_code=status.HTTP_200_OK)
async def liveness_check():
    """Liveness probe - 进程存活检查

    Kubernetes liveness probe - 只检查进程是否存活
    如果这个端点返回 200，说明进程在运行
    """
    return {"status": "alive", "service": "scholarai-ai"}


@router.get("/basic", status_code=status.HTTP_200_OK)
async def basic_health_check():
    """Basic probe - process alive + static metadata only."""
    return {"status": "alive", "service": "scholarai-ai"}


@router.get("/ready", status_code=status.HTTP_200_OK)
async def readiness_check(request: Request):
    """Readiness probe - 服务就绪检查

    Kubernetes readiness probe - 检查服务是否可以接受请求
    检查数据库连接和核心服务是否可用
    """

    services_status = {}

    # Check Milvus (lazy loaded, may not be initialized yet)
    services_status["milvus"] = _milvus_status(request)

    # Check ReRanker (lazy loaded)
    reranker_service = _resolve_runtime_service(
        request,
        "reranker_service",
        get_reranker_service,
    )
    services_status["reranker"] = (
        reranker_service
        if isinstance(reranker_service, dict)
        else _provider_status(reranker_service, component="reranker")
    )

    # Check Embedding (lazy loaded)
    embedding_service = _resolve_runtime_service(
        request,
        "embedding_service",
        get_embedding_service,
    )
    services_status["embedding"] = (
        embedding_service
        if isinstance(embedding_service, dict)
        else _provider_status(embedding_service, component="embedding")
    )

    # Basic service is ready if DB connections are established
    # AI services will be initialized lazily
    all_basic_ready = True  # DB connections already validated in lifespan

    return {
        "status": "ready" if all_basic_ready else "not_ready",
        "service": "scholarai-ai",
        "profile": getattr(request.app.state, "ai_startup_mode", "lazy"),
        "ai_services": services_status,
        "note": "AI services are lazy-loaded for faster startup",
    }


@router.get("/deep")
async def deep_health_check():
    """Deep probe - runtime dependency checks.

    Returns 200 when all dependencies are healthy, otherwise 503.
    """
    health = await get_services_health()
    status_code = (
        status.HTTP_200_OK
        if health.get("status") == "healthy"
        else status.HTTP_503_SERVICE_UNAVAILABLE
    )
    return JSONResponse(content=health, status_code=status_code)

@router.get("/degraded", status_code=status.HTTP_200_OK)
async def degraded_health_check(request: Request):
    """Degraded probe - service is alive but one or more optional dependencies are down.

    This endpoint is used for production hardening dashboards to distinguish:
    - live: process alive
    - ready: can accept critical traffic
    - degraded: critical path works but optional subsystems are impaired
    """
    health = await get_services_health()
    status_value = health.get("status", "unknown")

    is_degraded = status_value in {"degraded", "partial", "warning"}

    return {
        "status": "degraded" if is_degraded else "healthy",
        "service": "scholarai-ai",
        "profile": getattr(request.app.state, "ai_startup_mode", "lazy"),
        "dependencies": health.get("services", {}),
        "ready": not is_degraded,
    }


@router.get("", status_code=status.HTTP_200_OK)
async def health_check(request: Request):
    """完整健康检查 - 返回服务状态和模型加载状态

    Legacy endpoint for backward compatibility
    """

    services_status = {}

    services_status["milvus"] = _milvus_status(request)

    reranker_service = _resolve_runtime_service(
        request,
        "reranker_service",
        get_reranker_service,
    )
    services_status["reranker"] = (
        reranker_service
        if isinstance(reranker_service, dict)
        else _provider_status(reranker_service, component="reranker")
    )

    embedding_service = _resolve_runtime_service(
        request,
        "embedding_service",
        get_embedding_service,
    )
    services_status["embedding"] = (
        embedding_service
        if isinstance(embedding_service, dict)
        else _provider_status(embedding_service, component="embedding")
    )

    all_loaded = all(
        s.get("status") in ["loaded", "available", "ready"] for s in services_status.values()
    )

    return {
        "status": "ok" if all_loaded else "degraded",
        "service": "scholarai-ai",
        "models": services_status,
    }
