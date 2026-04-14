"""Deduplication service for import jobs.

Per gpt意见.md Section 9: Check in order:
1. External ID match (DOI, arXiv, S2 paperId) - on Paper table
2. File SHA256 hash match - on ImportJob table (NOT storage_key.contains!)
3. Title + first_author + year fuzzy match - on Paper table (with constraints)

CRITICAL: Paper model does NOT have file_sha256 field.
Hash matching must query ImportJob table for same hash where paper_id IS NOT NULL.
"""

from dataclasses import dataclass
from typing import Optional, List, Any

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from rapidfuzz import fuzz

from app.models.paper import Paper
from app.models.import_job import ImportJob


@dataclass
class DedupeResult:
    """Result of deduplication check."""
    match_type: Optional[str]  # doi, arxiv_id, s2_id, pdf_sha256, title_fuzzy
    matched_paper_id: Optional[str]
    matched_import_job_id: Optional[str] = None  # For hash match, reference the ImportJob
    confidence: int = 100  # 100 for exact matches, fuzzy score for title match


class ImportDedupeService:
    """Deduplication service with CORRECT hash matching logic.

    Three-tier matching order per gpt意见.md Section 9:
    1. External ID (DOI/arXiv/S2) on Paper table - exact match
    2. File SHA256 hash on ImportJob table - same hash, has paper_id
    3. Title + first_author + year fuzzy match with threshold 85%

    CRITICAL CORRECTION per GPT review:
    - _match_by_hash() must query ImportJob table (NOT Paper.storage_key.contains!)
    - Paper model does NOT have file_sha256 field
    - Correct: Check ImportJob table for same file_sha256 where paper_id IS NOT NULL
    """

    async def check_dedup(self, job: ImportJob, db: AsyncSession) -> DedupeResult:
        """Check if imported paper matches existing paper.

        Tier 1: External ID (DOI/arXiv/S2) on Paper table
        Tier 2: File SHA256 hash on ImportJob table (same hash, has paper_id)
        Tier 3: Title + first_author + year fuzzy on Paper table

        Args:
            job: ImportJob with resolved metadata and file_sha256
            db: Database session

        Returns:
            DedupeResult with match info or no match
        """
        # Tier 1: External ID match (exact, highest confidence)
        if job.external_paper_id and job.external_source:
            match = await self._match_by_external_id(job, db)
            if match:
                return DedupeResult(
                    match_type=f"{job.external_source}_id",
                    matched_paper_id=match.id,
                    confidence=100
                )

        # Tier 2: File hash match on ImportJob table (CORRECTED!)
        if job.file_sha256:
            match = await self._match_by_hash(job.file_sha256, job.user_id, db)
            if match:
                return DedupeResult(
                    match_type="pdf_sha256",
                    matched_paper_id=match.paper_id,
                    matched_import_job_id=match.id,
                    confidence=100
                )

        # Tier 3: Title + author + year fuzzy match (with constraints)
        if job.resolved_title:
            match = await self._match_by_title_fuzzy(job, db, threshold=85)
            if match:
                return match  # Already returns DedupeResult

        return DedupeResult(match_type=None, matched_paper_id=None)

    async def _match_by_external_id(
        self,
        job: ImportJob,
        db: AsyncSession
    ) -> Optional[Paper]:
        """Match by DOI, arXiv ID, or S2 paperId on Paper table.

        Args:
            job: ImportJob with external_source and external_paper_id
            db: Database session

        Returns:
            Paper if exact match found, None otherwise
        """
        if job.external_source == "doi":
            query = select(Paper).where(
                and_(
                    Paper.doi == job.external_paper_id,
                    Paper.user_id == job.user_id
                )
            )
        elif job.external_source == "arxiv":
            query = select(Paper).where(
                and_(
                    Paper.arxiv_id == job.external_paper_id,
                    Paper.user_id == job.user_id
                )
            )
        elif job.external_source == "s2":
            query = select(Paper).where(
                and_(
                    Paper.s2_paper_id == job.external_paper_id,
                    Paper.user_id == job.user_id
                )
            )
        else:
            return None

        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def _match_by_hash(
        self,
        file_sha256: str,
        user_id: str,
        db: AsyncSession
    ) -> Optional[ImportJob]:
        """Match by PDF file SHA256 hash on ImportJob table.

        CRITICAL: Paper model does NOT have file_sha256.
        We must query ImportJob table for:
        - Same file_sha256
        - paper_id IS NOT NULL (meaning paper was successfully created)
        - Same user_id (user's own imports)
        - status == completed (only completed jobs have valid papers)

        Args:
            file_sha256: SHA256 hash of uploaded PDF
            user_id: User ID to scope search
            db: Database session

        Returns:
            ImportJob that has same hash and paper_id, or None
        """
        # CORRECTED: Query ImportJob table, NOT Paper.storage_key.contains()
        query = select(ImportJob).where(
            and_(
                ImportJob.file_sha256 == file_sha256,
                ImportJob.paper_id.isnot(None),  # Has successfully created a paper
                ImportJob.user_id == user_id,
                ImportJob.status == "completed"  # Only completed jobs have valid papers
            )
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def _match_by_title_fuzzy(
        self,
        job: ImportJob,
        db: AsyncSession,
        threshold: int = 85
    ) -> Optional[DedupeResult]:
        """Fuzzy match by title similarity with author+year constraints.

        Per GPT review: Title-only matching has high false positive rate.
        Must add constraints:
        - Same first author (if resolved_authors has data)
        - Same year (if resolved_year has data)

        Args:
            job: ImportJob with resolved_title, resolved_authors, resolved_year
            db: Database session
            threshold: Minimum similarity score (85% default)

        Returns:
            DedupeResult with matched paper and confidence score
        """
        # Get candidate papers for user
        candidates = await db.execute(
            select(Paper).where(Paper.user_id == job.user_id)
        )
        papers = candidates.scalars().all()

        # Extract first author if available
        first_author = None
        if job.resolved_authors:
            # resolved_authors can be a list or a dict
            if isinstance(job.resolved_authors, list):
                if len(job.resolved_authors) > 0:
                    first_author = job.resolved_authors[0]
            elif isinstance(job.resolved_authors, dict):
                first_author = job.resolved_authors.get("first") or job.resolved_authors.get("name")

        job_title_lower = job.resolved_title.lower()

        best_match = None
        best_score = 0

        for paper in papers:
            # Calculate title similarity
            score = fuzz.ratio(job_title_lower, paper.title.lower())

            # Apply constraints to reduce false positives
            if score < threshold:
                continue

            # Author constraint: if we have first author, check match
            author_match = True
            if first_author and paper.authors and len(paper.authors) > 0:
                paper_first_author = paper.authors[0]
                if isinstance(paper_first_author, str):
                    paper_first_author_lower = paper_first_author.lower()
                else:
                    paper_first_author_lower = str(paper_first_author).lower()

                author_match = fuzz.ratio(first_author.lower(), paper_first_author_lower) > 70

            # Year constraint: if we have year, check within +/- 1 year tolerance
            year_match = True
            if job.resolved_year and paper.year:
                year_match = abs(job.resolved_year - paper.year) <= 1

            # Combined confidence: title score reduced if constraints don't match
            if author_match and year_match:
                combined_score = score
            elif author_match or year_match:
                combined_score = score * 0.85  # Reduce confidence
            else:
                combined_score = score * 0.7  # Significant reduction

            if combined_score >= threshold and combined_score > best_score:
                best_match = paper
                best_score = combined_score

        if best_match:
            return DedupeResult(
                match_type="title_fuzzy",
                matched_paper_id=best_match.id,
                confidence=int(best_score)  # Return confidence=int(best_score), NOT match.confidence
            )
        return None


__all__ = ["ImportDedupeService", "DedupeResult"]