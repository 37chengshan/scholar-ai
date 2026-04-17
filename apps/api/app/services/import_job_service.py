"""ImportJob CRUD Service.

Provides CRUD operations for ImportJob with next_action management.
Per D-01: ImportJob-first pattern - create ImportJob before Paper entity.
Per D-08: State machine with status/stage/progress tracking.

Methods:
- create_job: Create ImportJob with appropriate initial next_action
- get_job: Get job with ownership check
- update_status: Update state machine with optional next_action
- list_jobs: List jobs with filters
- set_file_info: Set file info after upload
- set_error: Set error state with retry next_action
- set_awaiting_dedupe: Set awaiting_user_action with dedupe decision next_action
- set_resolution: Store source resolution (Wave 5)
- set_metadata: Store resolved metadata (Wave 5)
- create_processing_task: Create ProcessingTask (Wave 5)
- track_processing_stages: Poll ProcessingTask status (Wave 5)
- add_event: Log event for debugging (Wave 5)
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.import_job import ImportJob
from app.utils.logger import logger


class ImportJobService:
    """ImportJob CRUD service with next_action guidance."""

    def _generate_job_id(self) -> str:
        """Generate job ID with imp_ prefix."""
        return f"imp_{uuid.uuid4().hex[:24]}"

    async def create_job(
        self,
        user_id: str,
        kb_id: str,
        source_type: str,
        source_ref_raw: str,
        db: AsyncSession,
        options: Dict[str, Any] = None,
        batch_id: Optional[str] = None,
        auto_commit: bool = True,
    ) -> ImportJob:
        """Create ImportJob with appropriate initial next_action.

        Args:
            user_id: User ID
            kb_id: Knowledge base ID
            source_type: Source type (local_file/arxiv/pdf_url/doi/semantic_scholar)
            source_ref_raw: User's raw input (filename or external reference)
            options: Import options (autoAttachToKb, dedupePolicy, etc.)
            batch_id: Optional batch ID for batch imports (Wave 3)
            db: Database session

        Returns:
            ImportJob instance with appropriate initial state

        Raises:
            ValueError: If source_type is invalid
        """
        if options is None:
            options = {}

        # Validate source_type
        valid_types = ["local_file", "arxiv", "pdf_url", "doi", "semantic_scholar"]
        if source_type not in valid_types:
            raise ValueError(f"Invalid source_type: {source_type}")

        job_id = self._generate_job_id()

        # Set initial state based on source type
        if source_type == "local_file":
            # Local file needs upload first
            initial_status = "created"
            initial_stage = "awaiting_input"
            next_action = {
                "type": "upload_file",
                "uploadUrl": f"/api/v1/import-jobs/{job_id}/file",
            }
        else:
            # External sources start in queued/resolving_source
            initial_status = "queued"
            initial_stage = "resolving_source"
            next_action = None  # Worker handles next steps

        now = datetime.now(timezone.utc)
        job = ImportJob(
            id=job_id,
            user_id=user_id,
            knowledge_base_id=kb_id,
            batch_id=batch_id,  # Wave 3 linkage
            source_type=source_type,
            source_ref_raw=source_ref_raw,
            status=initial_status,
            stage=initial_stage,
            progress=0,
            next_action=next_action,
            auto_attach_to_kb=options.get("autoAttachToKb", True),
            dedupe_policy=options.get("dedupePolicy", "prompt"),
            import_mode=options.get("importMode", "single"),
            version_policy=options.get("versionPolicy", "latest_if_unspecified"),
            created_at=now,
            updated_at=now,
        )

        db.add(job)
        if auto_commit:
            await db.commit()
            await db.refresh(job)
        else:
            await db.flush()
            await db.refresh(job)

        logger.info(
            "ImportJob created",
            job_id=job_id,
            user_id=user_id,
            kb_id=kb_id,
            source_type=source_type,
            status=initial_status,
            stage=initial_stage,
        )

        return job

    async def get_job(
        self, job_id: str, user_id: str, db: AsyncSession
    ) -> Optional[ImportJob]:
        """Get job with ownership check.

        Args:
            job_id: ImportJob ID
            user_id: User ID for ownership check
            db: Database session

        Returns:
            ImportJob if found and owned by user, None otherwise
        """
        result = await db.execute(
            select(ImportJob).where(
                ImportJob.id == job_id, ImportJob.user_id == user_id
            )
        )
        return result.scalar_one_or_none()

    async def get_job_by_id(self, job_id: str, db: AsyncSession) -> Optional[ImportJob]:
        """Get job by ID without ownership check (for worker use).

        Args:
            job_id: ImportJob ID
            db: Database session

        Returns:
            ImportJob if found, None otherwise
        """
        result = await db.execute(select(ImportJob).where(ImportJob.id == job_id))
        return result.scalar_one_or_none()

    async def update_status(
        self,
        job: ImportJob,
        stage: str,
        progress: int,
        db: AsyncSession,
        status: Optional[str] = None,
        next_action: Optional[Dict[str, Any]] = None,
    ) -> ImportJob:
        """Update state machine with optional next_action.

        Args:
            job: ImportJob instance
            status: New status
            stage: New stage
            progress: New progress (0-100)
            next_action: Optional next_action dict
            db: Database session

        Returns:
            Updated ImportJob
        """
        new_status = status or job.status
        job.status = new_status
        job.stage = stage
        job.progress = progress
        job.updated_at = datetime.now(timezone.utc)

        if next_action is not None:
            job.next_action = next_action

        # Update timestamp fields based on status
        if new_status == "running" and job.started_at is None:
            job.started_at = datetime.now(timezone.utc)
        elif new_status == "completed":
            job.completed_at = datetime.now(timezone.utc)
        elif new_status == "cancelled":
            job.cancelled_at = datetime.now(timezone.utc)

        await db.commit()
        await db.refresh(job)

        logger.info(
            "ImportJob status updated",
            job_id=job.id,
            status=new_status,
            stage=stage,
            progress=progress,
            next_action=next_action,
        )

        return job

    async def list_jobs(
        self,
        user_id: str,
        db: AsyncSession,
        kb_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[ImportJob]:
        """List jobs with filters.

        Args:
            user_id: User ID for ownership filter
            kb_id: Optional knowledge base ID filter
            status: Optional status filter
            limit: Maximum results
            offset: Offset for pagination
            db: Database session

        Returns:
            List of ImportJob instances
        """
        query = select(ImportJob).where(ImportJob.user_id == user_id)

        if kb_id:
            query = query.where(ImportJob.knowledge_base_id == kb_id)
        if status:
            query = query.where(ImportJob.status == status)

        query = query.order_by(ImportJob.created_at.desc()).limit(limit).offset(offset)
        result = await db.execute(query)
        return list(result.scalars().all())

    async def set_file_info(
        self,
        job: ImportJob,
        storage_key: str,
        sha256: str,
        size_bytes: int,
        db: AsyncSession,
        filename: Optional[str] = None,
        mime_type: Optional[str] = None,
    ) -> ImportJob:
        """Set file info after upload, update next_action to null.

        Per D-01: After file upload, job enters queued state for worker processing.

        Args:
            job: ImportJob instance
            storage_key: Storage key for uploaded file
            sha256: SHA256 hash of file
            size_bytes: File size in bytes
            filename: Optional filename
            mime_type: Optional MIME type
            db: Database session

        Returns:
            Updated ImportJob
        """
        job.storage_key = storage_key
        job.file_sha256 = sha256
        job.size_bytes = size_bytes
        if filename:
            job.filename = filename
        if mime_type:
            job.mime_type = mime_type

        # Update state
        job.status = "queued"
        job.stage = "uploaded"
        job.progress = 10
        job.next_action = None  # Worker handles next steps
        job.updated_at = datetime.now(timezone.utc)

        await db.commit()
        await db.refresh(job)

        logger.info(
            "ImportJob file info set",
            job_id=job.id,
            storage_key=storage_key,
            sha256=sha256,
            size_bytes=size_bytes,
        )

        return job

    async def set_error(
        self,
        job: ImportJob,
        error_code: str,
        error_message: str,
        db: AsyncSession,
        error_detail: Optional[Dict[str, Any]] = None,
    ) -> ImportJob:
        """Set error state with next_action for retry.

        Args:
            job: ImportJob instance
            error_code: Error code
            error_message: Error message
            error_detail: Optional error details dict
            db: Database session

        Returns:
            Updated ImportJob with retry next_action
        """
        job.status = "failed"
        job.stage = "failed"
        job.error_code = error_code
        job.error_message = error_message
        job.error_detail = error_detail
        job.next_action = {"type": "retry", "message": error_message}
        job.updated_at = datetime.now(timezone.utc)

        await db.commit()
        await db.refresh(job)

        logger.error(
            "ImportJob error set",
            job_id=job.id,
            error_code=error_code,
            error_message=error_message,
        )

        return job

    async def set_awaiting_dedupe(
        self,
        job: ImportJob,
        matched_paper_id: str,
        match_type: str,
        db: AsyncSession,
    ) -> ImportJob:
        """Set awaiting_user_action with next_action for dedupe decision.

        Args:
            job: ImportJob instance
            matched_paper_id: ID of matched paper
            match_type: Type of match (paper_id/doi/arxiv_same_version/pdf_sha256/...)
            db: Database session

        Returns:
            Updated ImportJob with dedupe decision next_action
        """
        job.status = "awaiting_user_action"
        job.stage = "awaiting_dedupe_decision"
        job.dedupe_status = "match_found"
        job.dedupe_match_type = match_type
        job.dedupe_match_paper_id = matched_paper_id
        job.next_action = {
            "type": "awaiting_dedupe_decision",
            "matchedPaperId": matched_paper_id,
            "matchType": match_type,
        }
        job.updated_at = datetime.now(timezone.utc)

        await db.commit()
        await db.refresh(job)

        logger.info(
            "ImportJob awaiting dedupe decision",
            job_id=job.id,
            matched_paper_id=matched_paper_id,
            match_type=match_type,
        )

        return job

    async def set_completed(
        self,
        job: ImportJob,
        paper_id: str,
        db: AsyncSession,
        processing_task_id: Optional[str] = None,
    ) -> ImportJob:
        """Set completed state after paper creation.

        Args:
            job: ImportJob instance
            paper_id: Created paper ID
            processing_task_id: Optional processing task ID
            db: Database session

        Returns:
            Updated ImportJob with completed state
        """
        job.status = "completed"
        job.stage = "completed"
        job.progress = 100
        job.paper_id = paper_id
        if processing_task_id:
            job.processing_task_id = processing_task_id
        job.completed_at = datetime.now(timezone.utc)
        job.updated_at = datetime.now(timezone.utc)
        job.next_action = None

        await db.commit()
        await db.refresh(job)

        logger.info(
            "ImportJob completed",
            job_id=job.id,
            paper_id=paper_id,
            processing_task_id=processing_task_id,
        )

        return job

    async def set_cancelled(
        self, job: ImportJob, db: AsyncSession
    ) -> ImportJob:
        """Set cancelled state.

        Args:
            job: ImportJob instance
            db: Database session

        Returns:
            Updated ImportJob with cancelled state
        """
        job.status = "cancelled"
        job.stage = "cancelled"
        job.cancelled_at = datetime.now(timezone.utc)
        job.updated_at = datetime.now(timezone.utc)
        job.next_action = None

        await db.commit()
        await db.refresh(job)

        logger.info("ImportJob cancelled", job_id=job.id)

        return job

    # =============================================================================
    # Wave 5 Helper Methods: ProcessingTask Stage Tracking
    # =============================================================================

    async def set_resolution(
        self,
        job: ImportJob,
        resolution: Any,
        db: AsyncSession,
    ) -> ImportJob:
        """Store source resolution on ImportJob fields (NOT job.resolution - undefined).

        Args:
            job: ImportJob instance
            resolution: SourceResolution from adapter
            db: Database session

        Returns:
            Updated ImportJob
        """
        job.source_ref_normalized = resolution.canonical_id

        if resolution.external_ids:
            job.external_ids = resolution.external_ids

            if resolution.external_ids.get("arxiv"):
                job.external_source = "arxiv"
                job.external_paper_id = resolution.external_ids["arxiv"]
                job.external_version = str(resolution.version) if resolution.version else None
            elif resolution.external_ids.get("doi"):
                job.external_source = "doi"
                job.external_paper_id = resolution.external_ids["doi"]
            elif resolution.external_ids.get("s2"):
                job.external_source = "s2"
                job.external_paper_id = resolution.external_ids["s2"]

        job.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(job)

        logger.info(
            "ImportJob resolution stored",
            job_id=job.id,
            canonical_id=resolution.canonical_id,
            external_source=job.external_source,
        )

        return job

    async def set_metadata(
        self,
        job: ImportJob,
        metadata: Any,
        db: AsyncSession,
    ) -> ImportJob:
        """Store resolved metadata on ImportJob fields.

        Args:
            job: ImportJob instance
            metadata: MetadataPreview from adapter
            db: Database session

        Returns:
            Updated ImportJob
        """
        if metadata:
            job.resolved_title = metadata.title
            job.resolved_authors = metadata.authors
            job.resolved_year = metadata.year
            job.resolved_abstract = metadata.abstract
            job.resolved_venue = metadata.venue

            if metadata.external_ids:
                # Merge external IDs
                if job.external_ids:
                    job.external_ids = {**job.external_ids, **metadata.external_ids}
                else:
                    job.external_ids = metadata.external_ids

        job.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(job)

        logger.info(
            "ImportJob metadata stored",
            job_id=job.id,
            title=job.resolved_title[:50] if job.resolved_title else None,
        )

        return job

    async def create_processing_task(
        self,
        job: ImportJob,
        paper_id: str,
        db: AsyncSession,
    ) -> str:
        """Create ProcessingTask for paper parsing.

        Args:
            job: ImportJob instance
            paper_id: Paper ID for the task
            db: Database session

        Returns:
            ProcessingTask ID
        """
        from app.models.task import ProcessingTask
        import uuid

        task_id = str(uuid.uuid4())
        task = ProcessingTask(
            id=task_id,
            paper_id=paper_id,
            status="pending",
            storage_key=job.storage_key or "",
        )
        db.add(task)
        await db.commit()

        logger.info(
            "ProcessingTask created",
            task_id=task_id,
            paper_id=paper_id,
            import_job_id=job.id,
        )

        return task_id

    async def track_processing_stages(
        self,
        job: ImportJob,
        processing_task_id: str,
        db: AsyncSession,
    ) -> None:
        """Poll ProcessingTask and update ImportJob stages.

        CRITICAL: ImportJob tracks parsing/chunking/embedding/indexing stages
        based on ProcessingTask checkpoint/status.
        ImportJob is NOT completed until ProcessingTask.status == 'completed'.
        The final completion is done by on_processing_task_complete callback.

        Args:
            job: ImportJob instance
            processing_task_id: ProcessingTask ID to track
            db: Database session
        """
        from app.models.task import ProcessingTask
        import asyncio

        max_wait_seconds = 3600  # 1 hour max
        poll_interval = 5  # 5 seconds between polls
        waited = 0

        while waited < max_wait_seconds:
            # Get ProcessingTask status
            result = await db.execute(
                select(ProcessingTask).where(ProcessingTask.id == processing_task_id)
            )
            task = result.scalar_one_or_none()

            if not task:
                logger.error(f"ProcessingTask {processing_task_id} not found")
                await self.set_error(
                    job,
                    error_code="TASK_NOT_FOUND",
                    error_message="ProcessingTask disappeared",
                    db=db,
                )
                return

            # Update ImportJob stage based on ProcessingTask checkpoint_stage
            checkpoint = task.checkpoint_stage

            if checkpoint == "parsed":
                await self.update_status(job, stage="parsing", progress=60, db=db)
            elif checkpoint == "chunked":
                await self.update_status(job, stage="chunking", progress=70, db=db)
            elif checkpoint == "embedded":
                await self.update_status(job, stage="embedding", progress=80, db=db)
            elif checkpoint == "indexed":
                await self.update_status(job, stage="indexing", progress=90, db=db)

            # Check if completed
            if task.status == "completed":
                await self.update_status(job, stage="finalizing", progress=95, db=db)
                # Final completion is done by callback, not here
                logger.info(
                    f"ImportJob {job.id} finalizing - ProcessingTask completed",
                    processing_task_id=processing_task_id,
                )
                return

            # Check if failed
            if task.status == "failed":
                await self.set_error(
                    job,
                    error_code="PROCESSING_FAILED",
                    error_message=task.error_message or "Processing failed",
                    db=db,
                )
                return

            await asyncio.sleep(poll_interval)
            waited += poll_interval

            # Refresh job from DB to check for cancellation
            await db.refresh(job)
            if job.status == "cancelled":
                logger.info(f"ImportJob {job.id} cancelled during processing")
                return

        # Timeout
        await self.set_error(
            job,
            error_code="PROCESSING_TIMEOUT",
            error_message="Processing took too long (>1 hour)",
            db=db,
        )

    async def add_event(
        self,
        job: ImportJob,
        level: str,
        event_type: str,
        message: str,
        db: AsyncSession,
        payload: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log ImportJob event for debugging.

        Wave 3 deferred import_job_events table, so this logs to logger for now.

        Args:
            job: ImportJob instance
            level: Log level (info/warn/error)
            event_type: Event type (source_resolved, pdf_downloaded, dedupe_hit, etc.)
            message: Event message
            db: Database session
            payload: Optional event payload
        """
        # For now, just log to logger. import_job_events table deferred.
        log_method = logger.info if level == "info" else logger.warning if level == "warn" else logger.error
        log_method(
            f"ImportJob event: {event_type}",
            job_id=job.id,
            level=level,
            event_type=event_type,
            message=message,
            payload=payload,
        )


__all__ = ["ImportJobService"]