"""Base source adapter interface.

Per D-02: Abstract adapter with resolve/fetch_metadata/acquire_pdf methods.
Per gpt意见.md Section 4: Source adapter rules for each external source.

Note: Uses field(default_factory) for mutable defaults per Python best practices.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class SourceResolution:
    """Result of source resolution (input parsing).

    Contains canonical identifiers and URLs for the source.

    Note: Uses field(default_factory) for mutable defaults per Python best practices.
    """

    resolved: bool
    source_type: str
    canonical_id: Optional[str] = None
    canonical_pdf_url: Optional[str] = None
    version: Optional[int] = None  # For arXiv versions
    external_ids: Dict[str, str] = field(default_factory=dict)
    error_code: Optional[str] = None
    error_message: Optional[str] = None


@dataclass
class MetadataPreview:
    """Paper metadata preview for frontend display.

    Note: Uses field(default_factory) for mutable defaults per Python best practices.
    """

    title: Optional[str] = None
    authors: List[str] = field(default_factory=list)
    year: Optional[int] = None
    abstract: Optional[str] = None
    venue: Optional[str] = None
    pdf_available: bool = False
    pdf_source: Optional[str] = None
    citation_count: Optional[int] = None
    external_ids: Dict[str, str] = field(default_factory=dict)


class BaseSourceAdapter(ABC):
    """Abstract base for source acquisition adapters.

    Per D-02: Each adapter implements:
    - resolve(): Parse input and return canonical source reference
    - fetch_metadata(): Get paper metadata from external source
    - acquire_pdf(): Download PDF to storage

    All external API calls must use import domain rate limiter (NOT search domain).
    """

    @abstractmethod
    async def resolve(self, input: str) -> SourceResolution:
        """Parse input and return canonical source reference.

        Args:
            input: User input (arXiv ID, DOI, URL, paperId, etc.)

        Returns:
            SourceResolution with canonical identifiers and PDF URL
        """
        pass

    @abstractmethod
    async def fetch_metadata(self, resolution: SourceResolution) -> MetadataPreview:
        """Get paper metadata from external source.

        Args:
            resolution: Source resolution from resolve()

        Returns:
            MetadataPreview with title, authors, year, abstract, PDF availability
        """
        pass

    @abstractmethod
    async def acquire_pdf(
        self, resolution: SourceResolution, storage_path: str, storage_key: str
    ) -> str:
        """Download PDF to storage, return storage_key.

        Args:
            resolution: Source resolution with canonical PDF URL
            storage_path: Base path for storage (e.g., "./uploads")
            storage_key: Storage key for the file (e.g., "uploads/user_id/2024/04/14/job.pdf")

        Returns:
            storage_key of downloaded file

        Raises:
            Exception: If PDF download fails or not available
        """
        pass


__all__ = [
    "BaseSourceAdapter",
    "SourceResolution",
    "MetadataPreview",
]