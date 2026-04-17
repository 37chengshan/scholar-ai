"""Dedupe Decision API endpoint.

Per D-06: Prompt user for dedupe decisions when matching existing papers.
Per gpt意见.md Section 2.5.1: POST /import-jobs/{job_id}/dedupe-decision

Decision options:
- reuse_existing: Attach existing Paper to KB (no new Paper)
- import_as_new_version: Create new Paper with version relationship
- force_new_paper: Force create new Paper ignoring match
- cancel: Cancel this import job
"""

from datetime import datetime, timezone
from typing import Any, Dict, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import CurrentUserId
from app.models.paper import Paper
from app.services.import_job_service import ImportJobService
from app.utils.problem_detail import Errors
from app.utils.logger import logger


router = APIRouter()


# =============================================================================
# Request/Response Models
# =============================================================================


class KBResponse(BaseModel):
    """Response wrapper for KB endpoints per D-36-02-03."""

    success: bool = True
    data: Dict[str, Any]


class DedupeDecisionRequest(BaseModel):
    """Request to submit dedupe decision."""

    decision: Literal["reuse_existing", "import_as_new_version", "force_new_paper", "cancel"]
    matchedPaperId: Optional[str] = None  # Required for reuse_existing


class DedupeDecisionData(BaseModel):
    """Response data for dedupe decision."""

    importJobId: str
    status: str
    action: str


# =============================================================================
# Dedupe Decision Endpoint
# =============================================================================


@router.post("/import-jobs/{job_id}/dedupe-decision", response_model=KBResponse)
async def submit_dedupe_decision(
    job_id: str,
    request: DedupeDecisionRequest,
    user_id: str = CurrentUserId,
    db: AsyncSession = Depends(get_db),
):
    """Submit user's dedupe decision.

    Per D-06: User chooses from 4 options:
    - reuse_existing: Attach matched Paper to KB (no new Paper)
    - import_as_new_version: Create new Paper with version link
    - force_new_paper: Create new Paper ignoring match
    - cancel: Cancel this import job

    Uses ImportJob model fields: dedupe_decision, paper_id (NOT job.resolution)

    Args:
        job_id: ImportJob ID
        request: Dedupe decision request
        user_id: Current user ID
        db: Database session

    Returns:
        KBResponse with updated job status
    """
    try:
        service = ImportJobService()
        job = await service.get_job(job_id, user_id, db)

        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=Errors.not_found("Import job not found"),
            )

        if job.status != "awaiting_user_action" or job.stage != "awaiting_dedupe_decision":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=Errors.validation(
                    f"Job not awaiting dedupe decision (status={job.status}, stage={job.stage})"
                ),
            )

        if request.decision == "reuse_existing":
            # Attach existing Paper to KB, no new Paper created
            # Use ImportJob.paper_id field to store matched paper reference
            if not request.matchedPaperId:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=Errors.validation("matchedPaperId required for reuse_existing decision"),
                )

            if job.dedupe_match_paper_id and request.matchedPaperId != job.dedupe_match_paper_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=Errors.validation(
                        "matchedPaperId does not match dedupe candidate for this import job"
                    ),
                )

            paper_result = await db.execute(
                select(Paper).where(
                    Paper.id == request.matchedPaperId,
                    Paper.user_id == user_id,
                )
            )
            matched_paper = paper_result.scalar_one_or_none()
            if not matched_paper:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=Errors.not_found("Matched paper not found"),
                )

            if matched_paper.knowledge_base_id != job.knowledge_base_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=Errors.validation(
                        "Matched paper belongs to a different knowledge base"
                    ),
                )

            job.paper_id = request.matchedPaperId
            job.dedupe_decision = "reuse_existing"
            job.dedupe_status = "resolved"
            job.status = "completed"
            job.stage = "completed"
            job.progress = 100
            job.completed_at = datetime.now(timezone.utc)
            job.next_action = None
            # Note: KnowledgeBasePaper link will be created by KB service in worker
            # This is handled in materialize_paper_task or a separate attachment task

        elif request.decision == "import_as_new_version":
            # Create new Paper with version relationship (future enhancement)
            job.dedupe_decision = "import_as_new_version"
            job.dedupe_status = "resolved"
            job.status = "queued"
            job.stage = "materializing_paper"
            job.progress = 30
            job.next_action = None

        elif request.decision == "force_new_paper":
            # Force create new Paper, ignore match
            job.dedupe_decision = "force_new_paper"
            job.dedupe_status = "resolved"
            job.status = "queued"
            job.stage = "materializing_paper"
            job.progress = 30
            job.next_action = None

        elif request.decision == "cancel":
            job.dedupe_decision = "cancel"
            job.status = "cancelled"
            job.stage = "cancelled"
            job.cancelled_at = datetime.now(timezone.utc)
            job.next_action = None

        job.updated_at = datetime.now(timezone.utc)
        await db.commit()

        logger.info(
            "Dedupe decision submitted",
            job_id=job_id,
            decision=request.decision,
            status=job.status,
        )

        if request.decision in {"import_as_new_version", "force_new_paper"}:
            try:
                from app.workers.import_worker import process_import_job
                process_import_job.delay(job_id)
            except Exception as queue_error:
                # Revert to awaiting decision to avoid queued orphan jobs.
                job.status = "awaiting_user_action"
                job.stage = "awaiting_dedupe_decision"
                job.progress = 35
                job.next_action = {
                    "type": "awaiting_dedupe_decision",
                    "matchedPaperId": job.dedupe_match_paper_id,
                    "matchType": job.dedupe_match_type,
                }
                job.updated_at = datetime.now(timezone.utc)
                await db.commit()
                logger.error(
                    "Failed to enqueue import job after dedupe decision",
                    job_id=job_id,
                    decision=request.decision,
                    error=str(queue_error),
                )
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=Errors.internal("Failed to enqueue import job, please retry decision"),
                )

        return KBResponse(
            success=True,
            data={
                "importJobId": job_id,
                "status": job.status,
                "action": request.decision,
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to submit dedupe decision", error=str(e), job_id=job_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=Errors.internal(f"Failed to submit dedupe decision: {str(e)}"),
        )


__all__ = ["router"]