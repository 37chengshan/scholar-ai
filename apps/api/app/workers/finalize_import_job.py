"""Unified finalize path for ImportJob terminal states.

Both import worker and PDF task callbacks should go through this module.
"""

from app.core.celery_config import celery_app
from app.services.import_job_service import ImportJobService
from app.utils.logger import logger
from app.workers.db import run_async, with_db_session
from app.workers.repositories.import_job_repo import ImportJobWorkerRepository

_import_job_repo = ImportJobWorkerRepository()
_import_job_service = ImportJobService()


async def _finalize_success(processing_task_id: str, paper_id: str | None = None) -> None:
    async def _run(db):
        job = await _import_job_repo.get_by_processing_task_id(processing_task_id, db)
        if not job:
            logger.warning(
                "No ImportJob found while finalizing success",
                processing_task_id=processing_task_id,
                paper_id=paper_id,
            )
            return

        await _import_job_service.update_status(
            job,
            status="completed",
            stage="completed",
            progress=100,
            db=db,
        )
        logger.info(
            "ImportJob marked completed by unified finalize helper",
            import_job_id=job.id,
            processing_task_id=processing_task_id,
            paper_id=paper_id,
        )

    await with_db_session(_run)


async def _finalize_failure(processing_task_id: str, error_message: str) -> None:
    async def _run(db):
        job = await _import_job_repo.get_by_processing_task_id(processing_task_id, db)
        if not job:
            logger.warning(
                "No ImportJob found while finalizing failure",
                processing_task_id=processing_task_id,
                error_message=error_message,
            )
            return

        await _import_job_service.set_error(
            job,
            error_code="PROCESSING_FAILED",
            error_message=error_message,
            db=db,
        )
        logger.info(
            "ImportJob marked failed by unified finalize helper",
            import_job_id=job.id,
            processing_task_id=processing_task_id,
        )

    await with_db_session(_run)


@celery_app.task
def finalize_import_job_success_task(processing_task_id: str, paper_id: str | None = None):
    """Finalize import job with completed state."""
    run_async(_finalize_success(processing_task_id, paper_id))


@celery_app.task
def finalize_import_job_failure_task(processing_task_id: str, error_message: str):
    """Finalize import job with failed state."""
    run_async(_finalize_failure(processing_task_id, error_message))


__all__ = [
    "finalize_import_job_success_task",
    "finalize_import_job_failure_task",
]
