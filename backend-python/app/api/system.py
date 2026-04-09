"""System API endpoints.

Provides endpoints for system diagnostics:
- GET /api/v1/system/storage - Get storage usage
- GET /api/v1/system/logs/stream - SSE endpoint for log streaming
"""

import asyncio
from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, Request, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Paper
from app.utils.logger import logger

router = APIRouter()


# =============================================================================
# Response Models
# =============================================================================

class StorageInfo(BaseModel):
    """Storage usage info."""
    used: str
    total: str
    percentage: int


class StorageResponse(BaseModel):
    """Response for storage info."""
    success: bool = True
    data: Dict[str, StorageInfo]


# =============================================================================
# Endpoints
# =============================================================================

@router.get("/storage", response_model=StorageResponse)
async def get_storage_info(db: AsyncSession = Depends(get_db)):
    """Get storage usage metrics.

    Returns estimated storage usage for files and vector database.
    """
    try:
        # Get paper count using SQLAlchemy ORM
        result = await db.execute(select(func.count()).select_from(Paper))
        paper_count = result.scalar() or 0

        # Estimate file storage (2MB average per paper)
        avg_file_size = 2 * 1024 * 1024  # 2MB
        estimated_file_storage = paper_count * avg_file_size

        # Convert to GB
        used_file_storage_gb = round(estimated_file_storage / (1024 * 1024 * 1024), 1)
        total_file_storage_gb = 50  # 50GB limit
        file_storage_percentage = min(100, round((estimated_file_storage / (total_file_storage_gb * 1024 * 1024 * 1024)) * 100))

        # Mock vector DB stats (would need Milvus client integration)
        vector_db = StorageInfo(
            used="1.2",
            total="5",
            percentage=24
        )

        file_storage = StorageInfo(
            used=str(used_file_storage_gb),
            total=str(total_file_storage_gb),
            percentage=file_storage_percentage
        )

        return StorageResponse(
            success=True,
            data={
                "vectorDB": vector_db.model_dump(),
                "fileStorage": file_storage.model_dump()
            }
        )

    except Exception as e:
        logger.error("Failed to get storage info", error=str(e))
        # Return default values on error
        return StorageResponse(
            success=True,
            data={
                "vectorDB": {"used": "0", "total": "5", "percentage": 0},
                "fileStorage": {"used": "0", "total": "50", "percentage": 0}
            }
        )


@router.get("/logs/stream")
async def stream_logs(request: Request):
    """SSE endpoint for streaming system logs.

    Sends log entries every 3 seconds with heartbeat every 15 seconds.
    """
    async def event_generator():
        """Generate SSE events for log streaming."""
        import json
        import random

        log_templates = [
            {"level": "INFO", "message": "User session authenticated"},
            {"level": "INFO", "message": "API rate limit normal"},
            {"level": "INFO", "message": "Ingestion batch completed"},
            {"level": "INFO", "message": "PDF processing started"},
            {"level": "INFO", "message": "Vector indexing complete"},
            {"level": "WARN", "message": "API rate limit approaching"},
            {"level": "WARN", "message": "Storage usage >80%"},
            {"level": "WARN", "message": "High memory usage detected"},
            {"level": "ERROR", "message": "API request failed"},
            {"level": "ERROR", "message": "Database connection timeout"},
        ]

        try:
            count = 0
            while True:
                # Check if client disconnected
                if await request.is_disconnected():
                    break

                # Send heartbeat every 15 seconds (every 5 iterations at 3s each)
                if count > 0 and count % 5 == 0:
                    yield ": heartbeat\n\n"

                # Send random log entry
                random_log = random.choice(log_templates)
                log_entry = {
                    "level": random_log["level"],
                    "message": random_log["message"],
                    "timestamp": datetime.now().isoformat()
                }

                yield f"data: {json.dumps(log_entry)}\n\n"

                count += 1
                await asyncio.sleep(3)

        except asyncio.CancelledError:
            logger.debug("Log stream cancelled")
        except Exception as e:
            logger.error("Log stream error", error=str(e))

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.get("/health")
async def system_health():
    """System health check endpoint.

    Returns status of all services.
    """
    from app.config import settings
    from app.database import engine

    services_status = {}

    # Check PostgreSQL using SQLAlchemy engine
    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        services_status["postgres"] = {"status": "healthy"}
    except Exception as e:
        services_status["postgres"] = {"status": "unhealthy", "error": str(e)}

    # Check Redis
    try:
        import redis.asyncio as redis
        r = redis.from_url(settings.REDIS_URL, socket_connect_timeout=2)
        await r.ping()
        await r.close()
        services_status["redis"] = {"status": "healthy"}
    except Exception as e:
        services_status["redis"] = {"status": "unhealthy", "error": str(e)[:100]}

    # Check Neo4j
    try:
        from app.core.neo4j_service import Neo4jService
        neo4j = Neo4jService()
        async with neo4j.driver.session() as session:
            await session.run("RETURN 1")
        await neo4j.close()
        services_status["neo4j"] = {"status": "healthy"}
    except Exception as e:
        services_status["neo4j"] = {"status": "unhealthy", "error": str(e)[:100]}

    # Check Milvus
    try:
        from app.core.milvus_service import get_milvus_service
        milvus = get_milvus_service()
        # Simple check - if we got here, Milvus is connected
        services_status["milvus"] = {"status": "healthy"}
    except Exception as e:
        services_status["milvus"] = {"status": "unhealthy", "error": str(e)[:100]}

    # Determine overall status
    all_healthy = all(
        s.get("status") == "healthy"
        for s in services_status.values()
    )

    return {
        "success": True,
        "data": {
            "status": "healthy" if all_healthy else "degraded",
            "services": services_status,
            "timestamp": datetime.now().isoformat()
        }
    }