"""SSE Progress Streaming for ImportJob.

Wave 5: Real-time progress updates via SSE.

Per gpt意见.md: Frontend receives real-time progress updates via SSE.
Events:
- status_update: Current status
- stage_change: Stage transition
- progress: Progress percentage update
- error: Error details
- completed: Final completion with paperId
"""

import asyncio
import json
from typing import Optional

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.deps import CurrentUserId
from app.models.import_job import ImportJob
from app.services.import_job_service import ImportJobService
from app.utils.logger import logger


router = APIRouter()


@router.get("/import-jobs/{job_id}/stream")
async def stream_import_progress(
    job_id: str,
    user_id: str = CurrentUserId,
):
    """SSE stream for import job progress.

    Per plan: Real-time progress updates for frontend.
    Emits events: status_update, stage_change, progress, error, completed.

    Args:
        job_id: ImportJob ID to stream
        user_id: User ID for ownership check

    Returns:
        StreamingResponse with SSE events
    """

    async def event_generator():
        service = ImportJobService()
        last_stage: Optional[str] = None
        last_progress: int = 0

        # Max streaming time: 2 hours (prevent infinite loops)
        max_stream_seconds = 7200
        stream_start = asyncio.get_event_loop().time()

        while True:
            # Check stream timeout
            elapsed = asyncio.get_event_loop().time() - stream_start
            if elapsed > max_stream_seconds:
                yield f"event: error\ndata: {json.dumps({'message': 'Stream timeout exceeded'})}\n\n"
                break

            async with AsyncSessionLocal() as db:
                try:
                    # Get job with ownership check
                    job = await service.get_job(job_id, user_id, db)

                    if not job:
                        yield f"event: error\ndata: {json.dumps({'message': 'Job not found'})}\n\n"
                        break

                    # Send stage change event
                    if job.stage != last_stage:
                        yield f"event: stage_change\ndata: {json.dumps({'stage': job.stage})}\n\n"
                        last_stage = job.stage
                        logger.debug(
                            "SSE stage_change sent",
                            job_id=job_id,
                            stage=job.stage,
                        )

                    # Send progress update
                    if job.progress != last_progress:
                        yield f"event: progress\ndata: {json.dumps({'progress': job.progress})}\n\n"
                        last_progress = job.progress
                        logger.debug(
                            "SSE progress sent",
                            job_id=job_id,
                            progress=job.progress,
                        )

                    # Send status update (always sent)
                    status_data = {
                        "status": job.status,
                        "stage": job.stage,
                        "progress": job.progress,
                    }
                    yield f"event: status_update\ndata: {json.dumps(status_data)}\n\n"

                    # Terminal states
                    if job.status == "completed":
                        completion_data = {
                            "paperId": job.paper_id,
                            "importJobId": job.id,
                        }
                        yield f"event: completed\ndata: {json.dumps(completion_data)}\n\n"
                        logger.info(
                            "SSE completed sent",
                            job_id=job_id,
                            paper_id=job.paper_id,
                        )
                        break

                    if job.status == "failed":
                        error_data = {
                            "code": job.error_code,
                            "message": job.error_message,
                        }
                        yield f"event: error\ndata: {json.dumps(error_data)}\n\n"
                        logger.info(
                            "SSE error sent",
                            job_id=job_id,
                            error_code=job.error_code,
                        )
                        break

                    if job.status == "cancelled":
                        yield f"event: cancelled\ndata: {json.dumps({'message': 'Job cancelled'})}\n\n"
                        logger.info("SSE cancelled sent", job_id=job_id)
                        break

                except Exception as e:
                    logger.error(
                        "SSE generator error",
                        job_id=job_id,
                        error=str(e),
                    )
                    yield f"event: error\ndata: {json.dumps({'message': str(e)})}\n\n"
                    break

            # Poll interval: 2 seconds
            await asyncio.sleep(2)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )


__all__ = ["router"]