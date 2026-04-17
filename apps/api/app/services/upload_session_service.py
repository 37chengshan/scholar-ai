"""Service layer for resumable upload sessions."""

from __future__ import annotations

import hashlib
import math
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aiofiles
from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.import_job import ImportJob
from app.models.upload_session import UploadSession
from app.schemas.upload_session import CreateUploadSessionRequest
from app.services.import_job_service import ImportJobService
from app.utils.logger import logger
from app.workers.import_worker import process_import_job


class UploadSessionService:
    """Coordinates chunked upload state and ImportJob transitions."""

    def __init__(self) -> None:
        self._import_job_service = ImportJobService()

    def _local_storage_root(self) -> Path:
        return Path(os.getenv("LOCAL_STORAGE_PATH", "./uploads"))

    def _parts_dir(self, session_id: str) -> Path:
        return self._local_storage_root() / "sessions" / session_id / "parts"

    def _part_path(self, session_id: str, part_number: int) -> Path:
        return self._parts_dir(session_id) / f"{part_number}.part"

    def _upload_storage_key(self, user_id: str, import_job_id: str) -> str:
        now = datetime.now(timezone.utc)
        return f"uploads/{user_id}/{now.strftime('%Y/%m/%d')}/{import_job_id}.pdf"

    async def create_session(
        self,
        import_job_id: str,
        user_id: str,
        payload: CreateUploadSessionRequest,
        db: AsyncSession,
    ) -> dict[str, Any]:
        job = await self._import_job_service.get_job(import_job_id, user_id, db)
        if not job:
            raise ValueError("Import job not found")
        if job.source_type != "local_file":
            raise ValueError("Only local_file jobs support upload sessions")
        if job.status not in {"created", "failed"}:
            raise ValueError(f"Job status does not allow upload session: {job.status}")

        if payload.sha256:
            matched_job = await self._find_completed_match(job, payload.sha256, payload.size_bytes, db)
            if matched_job:
                await self._apply_instant_reuse(job, matched_job, payload, db)
                return {
                    "instantImport": True,
                    "importJobId": job.id,
                    "paperId": matched_job.paper_id,
                    "matchedImportJobId": matched_job.id,
                    "status": "completed",
                }

        existing = await self._find_active_session(job.id, db)
        if existing:
            return {
                "instantImport": False,
                "session": self._to_state(existing),
            }

        total_parts = max(1, math.ceil(payload.size_bytes / payload.chunk_size))
        now = datetime.now(timezone.utc)
        session = UploadSession(
            import_job_id=job.id,
            user_id=user_id,
            knowledge_base_id=job.knowledge_base_id,
            filename=payload.filename,
            mime_type=payload.mime_type,
            file_sha256=payload.sha256,
            size_bytes=payload.size_bytes,
            chunk_size=payload.chunk_size,
            total_parts=total_parts,
            uploaded_parts=[],
            uploaded_bytes=0,
            status="created",
            created_at=now,
            updated_at=now,
        )
        db.add(session)

        # Keep next_action type stable with API contract and attach session context.
        job.next_action = {
            "type": "create_upload_session",
            "createSessionUrl": f"/api/v1/import-jobs/{job.id}/upload-sessions",
            "uploadSessionId": session.id,
            "completeUrl": f"/api/v1/upload-sessions/{session.id}/complete",
        }
        job.updated_at = now

        await db.commit()
        await db.refresh(session)

        return {
            "instantImport": False,
            "session": self._to_state(session),
        }

    async def get_session(
        self,
        session_id: str,
        user_id: str,
        db: AsyncSession,
        for_update: bool = False,
    ) -> UploadSession:
        stmt = select(UploadSession).where(
            and_(UploadSession.id == session_id, UploadSession.user_id == user_id)
        )
        if for_update:
            stmt = stmt.with_for_update()

        result = await db.execute(stmt)
        session = result.scalar_one_or_none()
        if not session:
            raise ValueError("Upload session not found")
        return session

    def serialize_session(self, session: UploadSession) -> dict[str, Any]:
        """Public serializer used by API layer."""
        return self._to_state(session)

    async def register_part(
        self,
        session_id: str,
        user_id: str,
        part_number: int,
        content: bytes,
        db: AsyncSession,
    ) -> dict[str, Any]:
        if not content:
            raise ValueError("Part content is empty")

        session = await self.get_session(session_id, user_id, db, for_update=True)
        self._ensure_writable(session, part_number)

        parts_dir = self._parts_dir(session.id)
        parts_dir.mkdir(parents=True, exist_ok=True)
        part_path = self._part_path(session.id, part_number)

        async with aiofiles.open(part_path, "wb") as f:
            await f.write(content)

        uploaded_parts = sorted(set([*session.uploaded_parts, part_number]))
        session.uploaded_parts = uploaded_parts
        session.uploaded_bytes = self._calculate_uploaded_bytes(session.id, uploaded_parts)
        session.status = "uploading"
        session.error_message = None
        session.updated_at = datetime.now(timezone.utc)

        await db.commit()
        await db.refresh(session)

        return self._to_state(session)

    async def complete_session(
        self,
        session_id: str,
        user_id: str,
        db: AsyncSession,
    ) -> dict[str, Any]:
        session = await self.get_session(session_id, user_id, db, for_update=True)
        if session.status == "completed":
            # Idempotent completion: do not enqueue duplicate processing.
            return self._to_state(session)

        self._ensure_completable(session)

        missing = self._missing_parts(session)
        if missing:
            raise ValueError(f"Upload session incomplete, missing parts: {missing}")

        final_storage_key = self._upload_storage_key(user_id, session.import_job_id)
        final_path = self._local_storage_root() / final_storage_key
        final_path.parent.mkdir(parents=True, exist_ok=True)

        with open(final_path, "wb") as out_file:
            for part_number in range(1, session.total_parts + 1):
                part_path = self._part_path(session.id, part_number)
                if not part_path.exists():
                    raise ValueError(f"Missing upload part file: {part_number}")
                with open(part_path, "rb") as in_file:
                    out_file.write(in_file.read())

        computed_sha256 = self._compute_sha256(final_path)
        if session.file_sha256 and computed_sha256 != session.file_sha256:
            session.status = "failed"
            session.error_message = "SHA256 mismatch while completing upload"
            session.updated_at = datetime.now(timezone.utc)
            await db.commit()
            raise ValueError("SHA256 mismatch")

        job = await self._import_job_service.get_job(session.import_job_id, user_id, db)
        if not job:
            raise ValueError("Import job not found")

        await self._import_job_service.set_file_info(
            job=job,
            storage_key=final_storage_key,
            sha256=computed_sha256,
            size_bytes=session.size_bytes,
            filename=session.filename,
            mime_type=session.mime_type,
            db=db,
        )

        session.storage_key = final_storage_key
        session.status = "completed"
        session.uploaded_bytes = session.size_bytes
        session.completed_at = datetime.now(timezone.utc)
        session.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(session)

        process_import_job.delay(job.id)

        logger.info(
            "Upload session completed and import job queued",
            session_id=session.id,
            import_job_id=job.id,
            storage_key=final_storage_key,
        )

        return self._to_state(session)

    async def abort_session(
        self,
        session_id: str,
        user_id: str,
        db: AsyncSession,
    ) -> dict[str, Any]:
        session = await self.get_session(session_id, user_id, db, for_update=True)
        if session.status == "completed":
            raise ValueError("Cannot abort a completed upload session")

        session.status = "aborted"
        session.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(session)

        return self._to_state(session)

    async def _find_active_session(self, import_job_id: str, db: AsyncSession) -> UploadSession | None:
        result = await db.execute(
            select(UploadSession)
            .where(
                and_(
                    UploadSession.import_job_id == import_job_id,
                    UploadSession.status.in_(["created", "uploading"]),
                )
            )
            .order_by(desc(UploadSession.created_at))
        )
        return result.scalars().first()

    async def _find_completed_match(
        self,
        current_job: ImportJob,
        sha256: str,
        size_bytes: int,
        db: AsyncSession,
    ) -> ImportJob | None:
        result = await db.execute(
            select(ImportJob)
            .where(
                and_(
                    ImportJob.id != current_job.id,
                    ImportJob.user_id == current_job.user_id,
                    ImportJob.knowledge_base_id == current_job.knowledge_base_id,
                    ImportJob.status == "completed",
                    ImportJob.paper_id.is_not(None),
                    ImportJob.file_sha256 == sha256,
                    ImportJob.size_bytes == size_bytes,
                )
            )
            .order_by(desc(ImportJob.updated_at))
        )
        return result.scalars().first()

    async def _apply_instant_reuse(
        self,
        target_job: ImportJob,
        matched_job: ImportJob,
        payload: CreateUploadSessionRequest,
        db: AsyncSession,
    ) -> None:
        now = datetime.now(timezone.utc)
        target_job.filename = payload.filename
        target_job.mime_type = payload.mime_type
        target_job.file_sha256 = payload.sha256 or matched_job.file_sha256
        target_job.size_bytes = payload.size_bytes
        target_job.storage_key = matched_job.storage_key
        target_job.paper_id = matched_job.paper_id
        target_job.status = "completed"
        target_job.stage = "completed"
        target_job.progress = 100
        target_job.next_action = None
        target_job.completed_at = now
        target_job.updated_at = now
        await db.commit()

    def _ensure_writable(self, session: UploadSession, part_number: int) -> None:
        if session.status in {"aborted", "completed"}:
            raise ValueError(f"Upload session is {session.status}")
        if part_number < 1 or part_number > session.total_parts:
            raise ValueError("Part number out of range")

    def _ensure_completable(self, session: UploadSession) -> None:
        if session.status in {"aborted", "failed"}:
            raise ValueError(f"Upload session is {session.status}")

    def _missing_parts(self, session: UploadSession) -> list[int]:
        uploaded = set(session.uploaded_parts)
        return [part for part in range(1, session.total_parts + 1) if part not in uploaded]

    def _calculate_uploaded_bytes(self, session_id: str, parts: list[int]) -> int:
        total = 0
        for part_number in parts:
            path = self._part_path(session_id, part_number)
            if path.exists():
                total += path.stat().st_size
        return total

    def _compute_sha256(self, file_path: Path) -> str:
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()

    def _to_state(self, session: UploadSession) -> dict[str, Any]:
        missing = self._missing_parts(session)
        progress = min(100, int((session.uploaded_bytes / max(session.size_bytes, 1)) * 100))
        return {
            "uploadSessionId": session.id,
            "importJobId": session.import_job_id,
            "status": session.status,
            "chunkSize": session.chunk_size,
            "totalParts": session.total_parts,
            "uploadedParts": session.uploaded_parts,
            "missingParts": missing,
            "uploadedBytes": session.uploaded_bytes,
            "sizeBytes": session.size_bytes,
            "progress": progress,
            "expiresAt": session.expires_at.isoformat() if session.expires_at else None,
            "completedAt": session.completed_at.isoformat() if session.completed_at else None,
        }


__all__ = ["UploadSessionService"]
