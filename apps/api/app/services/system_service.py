"""System service for diagnostics and health checks."""

from datetime import datetime
from typing import Any, Dict

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import engine
from app.models import Paper


async def get_storage_info(db: AsyncSession) -> Dict[str, Dict[str, Any]]:
    """Get storage usage metrics with graceful fallback data."""
    result = await db.execute(select(func.count()).select_from(Paper))
    paper_count = result.scalar() or 0

    avg_file_size = 2 * 1024 * 1024  # 2MB per paper estimate
    estimated_file_storage = paper_count * avg_file_size

    used_file_storage_gb = round(estimated_file_storage / (1024 * 1024 * 1024), 1)
    total_file_storage_gb = 50
    file_storage_percentage = min(
        100,
        round((estimated_file_storage / (total_file_storage_gb * 1024 * 1024 * 1024)) * 100),
    )

    return {
        "vectorDB": {
            "used": "1.2",
            "total": "5",
            "percentage": 24,
        },
        "fileStorage": {
            "used": str(used_file_storage_gb),
            "total": str(total_file_storage_gb),
            "percentage": file_storage_percentage,
        },
    }


async def get_services_health() -> Dict[str, Any]:
    """Check health status for all runtime dependencies."""
    services_status: Dict[str, Dict[str, str]] = {}

    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        services_status["postgres"] = {"status": "healthy"}
    except Exception as exc:
        services_status["postgres"] = {"status": "unhealthy", "error": str(exc)}

    try:
        import redis.asyncio as redis

        redis_client = redis.from_url(settings.REDIS_URL, socket_connect_timeout=2)
        await redis_client.ping()
        await redis_client.close()
        services_status["redis"] = {"status": "healthy"}
    except Exception as exc:
        services_status["redis"] = {"status": "unhealthy", "error": str(exc)[:100]}

    try:
        from app.core.neo4j_service import Neo4jService

        neo4j = Neo4jService()
        async with neo4j.driver.session() as session:
            await session.run("RETURN 1")
        await neo4j.close()
        services_status["neo4j"] = {"status": "healthy"}
    except Exception as exc:
        services_status["neo4j"] = {"status": "unhealthy", "error": str(exc)[:100]}

    try:
        from app.core.milvus_service import get_milvus_service

        milvus = get_milvus_service()
        if not milvus.has_collection(settings.MILVUS_COLLECTION_CONTENTS_V2):
            raise RuntimeError(
                f"Missing collection: {settings.MILVUS_COLLECTION_CONTENTS_V2}"
            )
        services_status["milvus"] = {"status": "healthy"}
    except Exception as exc:
        services_status["milvus"] = {"status": "unhealthy", "error": str(exc)[:100]}

    overall_status = "healthy" if all(
        svc.get("status") == "healthy" for svc in services_status.values()
    ) else "degraded"

    return {
        "status": overall_status,
        "services": services_status,
        "timestamp": datetime.now().isoformat(),
    }
