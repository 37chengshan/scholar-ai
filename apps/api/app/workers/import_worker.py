"""ImportJob processing worker with CORRECT state machine.

CRITICAL FIX per GPT review:
- ImportJob is NOT marked completed immediately after triggering ProcessingTask
- ImportJob tracks parsing/chunking/embedding/indexing stages by polling ProcessingTask
- ImportJob is marked completed ONLY when ProcessingTask.status == 'completed'

State machine flow (per gpt意见.md):
- created -> queued -> running -> awaiting_user_action -> completed/failed/cancelled
- Stage progression: awaiting_input -> resolving_source -> fetching_metadata -> downloading_pdf
  -> validating_pdf -> hashing_file -> dedupe_check -> awaiting_dedupe_decision ->
  materializing_paper -> attaching_to_kb -> triggering_processing -> parsing -> chunking
  -> embedding -> indexing -> finalizing -> completed
"""

import os
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, update

from app.config import settings
from app.core.celery_config import celery_app
from app.core.worker_async import run_async_in_worker_loop
from app.database import AsyncSessionLocal
from app.models.import_job import ImportJob
from app.models.paper import Paper
from app.models.task import ProcessingTask
from app.services.import_job_service import ImportJobService
from app.services.import_dedupe_service import ImportDedupeService
from app.workers.import_worker_helpers import (
    attach_paper_to_kb,
    compute_hash,
    create_paper_from_job,
    get_adapter,
    set_metadata,
    set_resolution,
)
from app.utils.logger import logger


@celery_app.task(
    bind=True,
    max_retries=3,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
)
def process_import_job(self, job_id: str):
    """Process ImportJob through full state machine with ProcessingTask sync.

    Per D-08: Stage progression from awaiting_input to completed.
    CRITICAL: completed is set ONLY after ProcessingTask finishes.

    Args:
        self: Celery task instance
        job_id: ImportJob ID to process
    """

    async def _process():
        async with AsyncSessionLocal() as db:
            service = ImportJobService()
            dedupe_service = ImportDedupeService()

            # Get job by ID (no ownership check for worker)
            job = await service.get_job_by_id(job_id, db)
            if not job:
                logger.error(f"ImportJob {job_id} not found")
                return

            if job.status in {"completed", "cancelled"}:
                logger.info(
                    f"Skip ImportJob {job_id}: terminal status",
                    status=job.status,
                )
                return

            if (
                job.processing_task_id
                and job.status in {"queued", "running"}
                and job.stage in {
                    "triggering_processing",
                    "parsing",
                    "chunking",
                    "embedding",
                    "indexing",
                    "finalizing",
                }
            ):
                logger.info(
                    f"Skip ImportJob {job_id}: processing task already linked",
                    processing_task_id=job.processing_task_id,
                    stage=job.stage,
                )
                return

            if job.status in {"queued", "created"}:
                claim_result = await db.execute(
                    update(ImportJob)
                    .where(
                        ImportJob.id == job_id,
                        ImportJob.status.in_(["queued", "created"]),
                    )
                    .values(
                        status="running",
                        updated_at=datetime.now(timezone.utc),
                    )
                    .returning(ImportJob.id)
                )
                claimed_job_id = claim_result.scalar_one_or_none()
                await db.commit()

                if not claimed_job_id:
                    await db.refresh(job)
                    logger.info(
                        f"Skip ImportJob {job_id}: claimed by another worker",
                        status=job.status,
                    )
                    return

                await db.refresh(job)
                if job.started_at is None:
                    job.started_at = datetime.now(timezone.utc)
                    await db.commit()
            elif job.status == "running":
                if job.processing_task_id:
                    logger.info(
                        f"Skip ImportJob {job_id}: already running with processing task",
                        processing_task_id=job.processing_task_id,
                    )
                    return
                logger.info(
                    f"Resume ImportJob {job_id}: running without processing task",
                    stage=job.stage,
                )

            try:
                logger.info(
                    f"Processing ImportJob {job_id}",
                    job_id=job_id,
                    source_type=job.source_type,
                    status=job.status,
                    stage=job.stage,
                )

                resume_from_materialization = (
                    job.stage in {"materializing_paper", "attaching_to_kb", "triggering_processing"}
                    or job.dedupe_decision in {"import_as_new_version", "force_new_paper"}
                )

                # Stage: resolving_source (skip for local_file and dedupe resume path)
                if job.source_type != "local_file" and not resume_from_materialization:
                    await service.update_status(
                        job, status="running", stage="resolving_source", progress=5, db=db
                    )

                    adapter = get_adapter(job.source_type)
                    if not adapter:
                        await service.set_error(
                            job,
                            error_code="INVALID_SOURCE_TYPE",
                            error_message=f"No adapter for source_type: {job.source_type}",
                            db=db,
                        )
                        return

                    resolution = await adapter.resolve(job.source_ref_raw)

                    if not resolution.resolved:
                        await service.set_error(
                            job,
                            error_code="RESOLVE_FAILED",
                            error_message=resolution.error_message or "Source resolution failed",
                            db=db,
                        )
                        return

                    # Store resolution on ImportJob fields (NOT job.resolution - undefined!)
                    await set_resolution(service, job, resolution, db)

                metadata = None
                if not resume_from_materialization:
                    # Stage: fetching_metadata
                    await service.update_status(
                        job, stage="fetching_metadata", progress=10, db=db
                    )

                    if job.source_type != "local_file":
                        adapter = get_adapter(job.source_type)
                        resolution = await adapter.resolve(job.source_ref_raw)
                        metadata = await adapter.fetch_metadata(resolution)

                        # Store metadata on ImportJob fields
                        await set_metadata(service, job, metadata, db)

                    # Stage: downloading_pdf (for external sources)
                    if job.source_type != "local_file":
                        if not metadata or not metadata.pdf_available:
                            tried_sources = []
                            source_errors = {}
                            if job.external_ids:
                                tried_sources_raw = job.external_ids.get("doi_tried_sources")
                                source_errors_raw = job.external_ids.get("doi_source_errors")
                                if tried_sources_raw:
                                    try:
                                        import json
                                        tried_sources = json.loads(tried_sources_raw)
                                    except Exception:
                                        tried_sources = []
                                if source_errors_raw:
                                    try:
                                        import json
                                        source_errors = json.loads(source_errors_raw)
                                    except Exception:
                                        source_errors = {}

                            job.status = "awaiting_user_action"
                            job.stage = "awaiting_user_action"
                            job.progress = 20
                            job.error_code = "NO_PDF"
                            job.error_message = "PDF not available, please upload manually"
                            job.next_action = {
                                "type": "upload_local_pdf",
                                "createSessionUrl": f"/api/v1/import-jobs/{job.id}/upload-sessions",
                                "message": "PDF not available, please upload manually",
                                "triedSources": tried_sources,
                                "sourceErrors": source_errors,
                            }
                            job.updated_at = datetime.now(timezone.utc)
                            await db.commit()
                            return

                        await service.update_status(
                            job, stage="downloading_pdf", progress=20, db=db
                        )

                        # Generate storage key
                        storage_key = f"uploads/{job.user_id}/{datetime.now(timezone.utc).strftime('%Y/%m/%d')}/{job_id}.pdf"
                        local_storage_path = settings.LOCAL_STORAGE_PATH
                        file_path = os.path.join(local_storage_path, storage_key)
                        os.makedirs(os.path.dirname(file_path), exist_ok=True)

                        try:
                            adapter = get_adapter(job.source_type)
                            resolution = await adapter.resolve(job.source_ref_raw)
                            await adapter.acquire_pdf(resolution, local_storage_path, storage_key)

                            # Set file info
                            job.storage_key = storage_key
                            await db.commit()
                        except Exception as e:
                            await service.set_error(
                                job,
                                error_code="PDF_DOWNLOAD_FAILED",
                                error_message=str(e),
                                db=db,
                            )
                            return

                    # Stage: validating_pdf
                    await service.update_status(job, stage="validating_pdf", progress=25, db=db)

                    # Validate magic bytes %PDF-
                    if job.storage_key:
                        local_storage_path = settings.LOCAL_STORAGE_PATH
                        file_path = os.path.join(local_storage_path, job.storage_key)
                        if os.path.exists(file_path):
                            with open(file_path, "rb") as f:
                                header = f.read(5)
                                if not header.startswith(b"%PDF-"):
                                    await service.set_error(
                                        job,
                                        error_code="INVALID_PDF",
                                        error_message="PDF magic bytes validation failed",
                                        db=db,
                                    )
                                    return

                    # Stage: hashing_file
                    await service.update_status(job, stage="hashing_file", progress=30, db=db)

                    if job.storage_key:
                        sha256 = await compute_hash(job.storage_key)
                        job.file_sha256 = sha256
                        await db.commit()

                    # Stage: dedupe_check
                    await service.update_status(job, stage="dedupe_check", progress=35, db=db)
                    if job.dedupe_decision in {"import_as_new_version", "force_new_paper"}:
                        # User explicitly chose to continue with a new paper, skip second dedupe hit.
                        job.dedupe_status = "resolved"
                        await db.commit()
                    else:
                        dedupe_result = await dedupe_service.check_dedup(job, db)

                        if dedupe_result.matched_paper_id:
                            await service.set_awaiting_dedupe(
                                job,
                                matched_paper_id=dedupe_result.matched_paper_id,
                                match_type=dedupe_result.match_type,
                                db=db,
                            )
                            logger.info(
                                f"ImportJob {job_id} paused for dedupe decision",
                                matched_paper_id=dedupe_result.matched_paper_id,
                                match_type=dedupe_result.match_type,
                            )
                            return  # Pause for user decision

                        # No match, proceed to materialize paper
                        job.dedupe_status = "no_match"
                        await db.commit()
                else:
                    logger.info(
                        f"Resume ImportJob {job_id} from materialization stage",
                        stage=job.stage,
                        decision=job.dedupe_decision,
                    )

                # Stage: materializing_paper
                await service.update_status(job, stage="materializing_paper", progress=40, db=db)
                paper_id: Optional[str] = None
                if job.paper_id:
                    existing_paper = await db.execute(
                        select(Paper).where(Paper.id == job.paper_id)
                    )
                    found_paper = existing_paper.scalar_one_or_none()
                    if found_paper:
                        paper_id = found_paper.id

                if not paper_id:
                    paper_id = await create_paper_from_job(job, db)
                    job.paper_id = paper_id
                    await db.commit()

                # Stage: attaching_to_kb
                await service.update_status(job, stage="attaching_to_kb", progress=45, db=db)
                await attach_paper_to_kb(job, paper_id, db)

                # Stage: triggering_processing - Create ProcessingTask
                await service.update_status(
                    job, stage="triggering_processing", progress=50, db=db
                )

                # Reuse existing ProcessingTask for this paper when present.
                # Retries can revisit this stage and must not violate unique paper_id.
                existing_task_result = await db.execute(
                    select(ProcessingTask).where(ProcessingTask.paper_id == paper_id)
                )
                existing_task = existing_task_result.scalar_one_or_none()

                if existing_task:
                    processing_task_id = existing_task.id
                    if existing_task.status == "completed":
                        job.processing_task_id = processing_task_id
                        await service.update_status(
                            job,
                            status="completed",
                            stage="completed",
                            progress=100,
                            db=db,
                        )
                        logger.info(
                            f"ImportJob {job_id} completed via existing ProcessingTask {processing_task_id}",
                            paper_id=paper_id,
                        )
                        return

                    if existing_task.status in {"pending", "running", "parsing", "chunking", "embedding", "indexing", "finalizing"}:
                        job.processing_task_id = processing_task_id
                        await db.commit()
                        logger.info(
                            "Reusing in-flight ProcessingTask without requeue",
                            job_id=job_id,
                            processing_task_id=processing_task_id,
                            task_status=existing_task.status,
                        )
                        return

                    if existing_task.status in {"failed", "cancelled", "error"}:
                        existing_task.status = "pending"
                        existing_task.error_message = None
                        existing_task.completed_at = None
                        existing_task.storage_key = job.storage_key or existing_task.storage_key
                        job.processing_task_id = processing_task_id
                        await db.commit()
                    else:
                        job.processing_task_id = processing_task_id
                        await db.commit()
                        logger.info(
                            "Reusing existing ProcessingTask in unknown non-terminal state",
                            job_id=job_id,
                            processing_task_id=processing_task_id,
                            task_status=existing_task.status,
                        )
                        return
                else:
                    processing_task_id = str(uuid.uuid4())
                    task = ProcessingTask(
                        id=processing_task_id,
                        paper_id=paper_id,
                        status="pending",
                        storage_key=job.storage_key or "",
                    )
                    db.add(task)
                    job.processing_task_id = processing_task_id
                    await db.commit()

                # Trigger existing PDF worker (via Celery)
                from app.tasks.pdf_tasks import process_single_pdf_task
                process_single_pdf_task.delay(paper_id, processing_task_id)

                logger.info(
                    f"ProcessingTask {processing_task_id} prepared for ImportJob {job_id}",
                    job_id=job_id,
                    stage=job.stage,
                    source_type=job.source_type,
                    processing_task_id=processing_task_id,
                    paper_id=paper_id,
                )
                # Return immediately to avoid blocking single-concurrency Celery workers.
                return

            except Exception as e:
                logger.exception(f"ImportJob {job_id} failed: {e}")
                logger.error(
                    "ImportJob failed with stage context",
                    job_id=job_id,
                    stage=getattr(job, "stage", None),
                    source_type=getattr(job, "source_type", None),
                    processing_task_id=getattr(job, "processing_task_id", None),
                    error_code="IMPORT_FAILED",
                    error_message=str(e),
                )
                try:
                    await db.rollback()
                except Exception:
                    pass
                await service.set_error(
                    job,
                    error_code="IMPORT_FAILED",
                    error_message=str(e),
                    db=db,
                )

    # Run async function in sync Celery task
    run_async_in_worker_loop(_process())


@celery_app.task(
    bind=True,
    max_retries=3,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
)
def on_processing_task_complete(self, processing_task_id: str, paper_id: str):
    """Callback when ProcessingTask completes - marks ImportJob as completed.

    This should be called by pdf_worker when ProcessingTask finishes.
    Per plan: ImportJob completed ONLY after ProcessingTask finishes.

    Args:
        processing_task_id: ProcessingTask ID that completed
        paper_id: Paper ID that was processed
    """

    async def _callback():
        async with AsyncSessionLocal() as db:
            # Find ImportJob by processing_task_id
            result = await db.execute(
                select(ImportJob).where(
                    ImportJob.processing_task_id == processing_task_id
                )
            )
            job = result.scalar_one_or_none()

            if job:
                if job.status in {"completed", "cancelled"}:
                    logger.info(
                        f"Skip callback sync for ImportJob {job.id}: terminal status",
                        status=job.status,
                    )
                    return

                service = ImportJobService()
                await service.update_status(
                    job,
                    status="completed",
                    stage="completed",
                    progress=100,
                    db=db,
                )
                logger.info(
                    f"ImportJob {job.id} marked completed after ProcessingTask {processing_task_id}",
                    paper_id=paper_id,
                )
            else:
                logger.warning(
                    f"No ImportJob found for ProcessingTask {processing_task_id}",
                    paper_id=paper_id,
                )

    run_async_in_worker_loop(_callback())


__all__ = [
    "process_import_job",
    "on_processing_task_complete",
]
