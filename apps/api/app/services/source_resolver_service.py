"""Source resolver service - unified dispatcher for source adapters.

Per D-02: Dispatches to correct adapter based on source type.
Per gpt意见.md Section 2.2: resolve and resolve-batch endpoints.

Provides:
- Auto-detection of source type from input format
- resolve(): Single source resolution with metadata preview
- resolve_batch(): Batch resolution for multiple inputs
"""

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from app.services.source_adapters import (
    ArxivAdapter,
    S2Adapter,
    DoiAdapter,
    PdfUrlAdapter,
    SourceResolution,
    MetadataPreview,
)
from app.utils.logger import logger


@dataclass
class ResolveResult:
    """Combined resolution + metadata result.

    Note: Uses field(default_factory) for mutable defaults per Python best practices.
    """

    resolution: SourceResolution
    metadata: MetadataPreview


@dataclass
class BatchResolveItem:
    """Single item in batch resolution result.

    Note: Uses field(default_factory) for mutable defaults.
    """

    input: str
    resolved: bool
    source_type: str
    normalized: Dict[str, Optional[str]] = field(default_factory=dict)
    preview: Dict[str, Optional[str]] = field(default_factory=dict)
    error_code: Optional[str] = None
    error_message: Optional[str] = None


class SourceResolverService:
    """Unified source resolution dispatcher.

    Per D-02: ADAPTER_MAP dispatches to correct adapter.
    Per gpt意见.md Section 2.2: Frontend calls resolve() for preview before import.
    """

    # Adapter registry - maps source type to adapter class
    ADAPTER_MAP = {
        "arxiv": ArxivAdapter,
        "semantic_scholar": S2Adapter,
        "doi": DoiAdapter,
        "pdf_url": PdfUrlAdapter,
    }

    def detect_source_type(self, input: str) -> str:
        """Auto-detect source type from input format.

        Per gpt意见.md Section 2.2: Detect type without user specifying.

        Detection rules:
        - arXiv: matches arxiv ID/URL patterns
        - DOI: matches 10.xxxx/xxxxx
        - S2: matches semanticscholar.org URL or 40-char hex
        - PDF URL: matches https://... ending with .pdf or contains 'pdf'
        - Fallback: unknown

        Args:
            input: User input string

        Returns:
            Detected source type string
        """
        input = input.strip()

        # arXiv patterns
        arxiv_patterns = [
            r"^(?:arXiv:)?(\d{4}\.\d{4,5})(?:v\d+)?$",  # ID format
            r"arxiv\.org/(?:abs|pdf)/\d{4}\.\d{4,5}",  # URL format
        ]
        for pattern in arxiv_patterns:
            if re.search(pattern, input, re.IGNORECASE):
                return "arxiv"

        # DOI pattern
        if re.search(r"^10\.\d{4,}/.+$", input) or re.search(r"doi\.org/10\.\d{4,}", input, re.IGNORECASE):
            return "doi"

        # Semantic Scholar patterns
        s2_patterns = [
            r"semanticscholar\.org/paper/",  # URL
            r"^[a-f0-9]{40}$",  # paperId (40-char hex)
            r"^CorpusId:\d+$",  # CorpusId
        ]
        for pattern in s2_patterns:
            if re.search(pattern, input, re.IGNORECASE):
                return "semantic_scholar"

        # PDF URL pattern
        if re.match(r"^https://", input, re.IGNORECASE):
            # Check if URL looks like PDF
            if input.lower().endswith(".pdf") or "pdf" in input.lower():
                return "pdf_url"
            # Could still be PDF URL - return pdf_url for HEAD validation
            return "pdf_url"

        # Fallback
        return "unknown"

    async def resolve(
        self, input: str, source_type: Optional[str] = None
    ) -> ResolveResult:
        """Resolve source and fetch metadata preview.

        Per gpt意见.md Section 2.2:
        - Auto-detect source type if not specified
        - Dispatch to correct adapter
        - Return resolution + metadata

        Args:
            input: User input (arXiv ID, DOI, URL, paperId, etc.)
            source_type: Optional explicit source type

        Returns:
            ResolveResult with resolution and metadata
        """
        if not source_type:
            source_type = self.detect_source_type(input)

        # Get adapter
        adapter_cls = self.ADAPTER_MAP.get(source_type)
        if not adapter_cls:
            logger.warning("Unknown source type", input=input[:50], source_type=source_type)
            return ResolveResult(
                resolution=SourceResolution(
                    resolved=False,
                    source_type="unknown",
                    error_code="UNKNOWN_SOURCE_TYPE",
                    error_message=f"Cannot determine source type for input: {input[:100]}",
                ),
                metadata=MetadataPreview(),
            )

        # Create adapter and resolve
        adapter = adapter_cls()

        try:
            resolution = await adapter.resolve(input)

            if resolution.resolved:
                metadata = await adapter.fetch_metadata(resolution)
            else:
                metadata = MetadataPreview()

            logger.info(
                "Source resolved",
                input=input[:50],
                source_type=source_type,
                resolved=resolution.resolved,
                pdf_available=metadata.pdf_available,
            )

            return ResolveResult(resolution=resolution, metadata=metadata)

        except Exception as e:
            logger.error(
                "Source resolution failed",
                input=input[:50],
                source_type=source_type,
                error=str(e),
            )
            return ResolveResult(
                resolution=SourceResolution(
                    resolved=False,
                    source_type=source_type,
                    error_code="RESOLUTION_FAILED",
                    error_message=str(e),
                ),
                metadata=MetadataPreview(),
            )

    async def resolve_batch(self, inputs: List[str]) -> List[BatchResolveItem]:
        """Batch resolve multiple inputs.

        Per gpt意见.md Section 2.2.2:
        - Accept list of inputs
        - Return list of results with normalized source info

        Args:
            inputs: List of user inputs

        Returns:
            List of BatchResolveItem with resolution results
        """
        results = []

        for input in inputs:
            result = await self.resolve(input)

            # Convert to BatchResolveItem format
            item = BatchResolveItem(
                input=input,
                resolved=result.resolution.resolved,
                source_type=result.resolution.source_type,
                normalized={
                    "canonicalId": result.resolution.canonical_id,
                    "canonicalPdfUrl": result.resolution.canonical_pdf_url,
                    "externalIds": result.resolution.external_ids,
                },
                preview={
                    "title": result.metadata.title,
                    "authors": result.metadata.authors,
                    "year": result.metadata.year,
                    "pdfAvailable": result.metadata.pdf_available,
                    "pdfSource": result.metadata.pdf_source,
                },
                error_code=result.resolution.error_code,
                error_message=result.resolution.error_message,
            )

            results.append(item)

        logger.info(
            "Batch resolution complete",
            total=len(inputs),
            resolved=sum(1 for r in results if r.resolved),
        )

        return results


# Singleton instance
_source_resolver_service: Optional[SourceResolverService] = None


def get_source_resolver_service() -> SourceResolverService:
    """Get or create SourceResolverService singleton."""
    global _source_resolver_service
    if _source_resolver_service is None:
        _source_resolver_service = SourceResolverService()
    return _source_resolver_service


__all__ = [
    "SourceResolverService",
    "ResolveResult",
    "BatchResolveItem",
    "get_source_resolver_service",
]