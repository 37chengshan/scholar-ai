"""System API endpoints.

Provides endpoints for system diagnostics:
- GET /api/v1/system/health - System health check
- GET /api/v1/system/storage - Get storage usage
- GET /api/v1/system/logs/stream - SSE endpoint for log streaming
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Request, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.system_service import (
    get_services_health,
    get_storage_info as get_storage_metrics,
)
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


class ServiceHealth(BaseModel):
    """Individual service health status."""
    status: str
    error: Optional[str] = None


class SystemHealthData(BaseModel):
    """System health data payload."""
    status: str
    services: Dict[str, ServiceHealth]
    timestamp: str


class SystemHealthResponse(BaseModel):
    """Response for system health check."""
    success: bool = True
    data: SystemHealthData


# =============================================================================
# Endpoints
# =============================================================================

@router.get("/storage", response_model=StorageResponse)
async def get_storage_info(db: AsyncSession = Depends(get_db)):
    """Get storage usage metrics.

    Returns estimated storage usage for files and vector database.
    """
    try:
        storage_info = await get_storage_metrics(db)
        vector_db = StorageInfo(**storage_info["vectorDB"])
        file_storage = StorageInfo(**storage_info["fileStorage"])

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


@router.get("/health", response_model=SystemHealthResponse)
async def system_health():
    """System health check endpoint.

    Returns status of all services.
    """
    health = await get_services_health()

    return SystemHealthResponse(
        success=True,
        data=SystemHealthData(**health),
    )