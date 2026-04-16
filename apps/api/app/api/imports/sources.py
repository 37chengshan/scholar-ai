"""Import source resolution API endpoints.

Per D-02: Source resolution for preview before import.
Per gpt意见.md Section 2.2: resolve and resolve-batch endpoints.

Endpoints:
- POST /import-sources/resolve - Resolve single source
- POST /import-sources/resolve-batch - Resolve multiple sources

These endpoints allow frontend to preview paper info before creating ImportJob.
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body
from pydantic import BaseModel, Field

from app.services.source_resolver_service import (
    get_source_resolver_service,
    ResolveResult,
    BatchResolveItem,
)
from app.utils.logger import logger


router = APIRouter()


# =============================================================================
# Request/Response Models
# =============================================================================


class ResolveRequest(BaseModel):
    """Request to resolve a single source."""

    input: str = Field(..., description="User input (arXiv ID, DOI, URL, paperId, etc.)")
    sourceType: Optional[str] = Field(
        None, description="Explicit source type (arxiv/semantic_scholar/doi/pdf_url)"
    )


class ResolveResponse(BaseModel):
    """Response wrapper per D-36-02-03."""

    success: bool = True
    data: Dict[str, Any]


class ResolveBatchRequest(BaseModel):
    """Request to resolve multiple sources."""

    items: List[str] = Field(
        ..., description="List of user inputs to resolve", min_length=1, max_length=50
    )


class ResolveBatchResponse(BaseModel):
    """Response wrapper for batch resolution."""

    success: bool = True
    data: Dict[str, Any]


# =============================================================================
# Resolve Single Source Endpoint
# =============================================================================


@router.post("/resolve", response_model=ResolveResponse)
async def resolve_source(request: ResolveRequest) -> Dict[str, Any]:
    """Resolve source and return preview.

    Per gpt意见.md Section 2.2.1:
    - Parse input and detect source type
    - Fetch metadata preview
    - Return normalized source info and availability

    Example:
        POST /import-sources/resolve
        {
            "input": "https://arxiv.org/abs/2501.01234"
        }
        Returns:
        {
            "success": true,
            "data": {
                "resolved": true,
                "normalizedSource": {
                    "sourceType": "arxiv",
                    "canonicalId": "2501.01234",
                    "canonicalPdfUrl": "https://arxiv.org/pdf/2501.01234.pdf"
                },
                "preview": {
                    "title": "Example Paper Title",
                    "authors": ["A", "B"],
                    "year": 2025,
                    "pdfAvailable": true
                }
            }
        }
    """
    try:
        service = get_source_resolver_service()
        result: ResolveResult = await service.resolve(
            input=request.input, source_type=request.sourceType
        )

        # Build response
        response_data = {
            "resolved": result.resolution.resolved,
            "normalizedSource": {
                "sourceType": result.resolution.source_type,
                "canonicalId": result.resolution.canonical_id,
                "canonicalPdfUrl": result.resolution.canonical_pdf_url,
                "version": result.resolution.version,
                "externalIds": result.resolution.external_ids,
            },
            "preview": {
                "title": result.metadata.title,
                "authors": result.metadata.authors,
                "year": result.metadata.year,
                "abstract": result.metadata.abstract,
                "venue": result.metadata.venue,
                "pdfAvailable": result.metadata.pdf_available,
                "pdfSource": result.metadata.pdf_source,
                "citationCount": result.metadata.citation_count,
            },
            "availability": {
                "pdfAvailable": result.metadata.pdf_available,
                "pdfSource": result.metadata.pdf_source,
            },
        }

        # Add error info if not resolved
        if not result.resolution.resolved:
            response_data["errorCode"] = result.resolution.error_code
            response_data["errorMessage"] = result.resolution.error_message

        logger.info(
            "Source resolved via API",
            input=request.input[:50],
            resolved=result.resolution.resolved,
            source_type=result.resolution.source_type,
        )

        return ResolveResponse(success=True, data=response_data)

    except Exception as e:
        logger.error("Resolve endpoint failed", input=request.input[:50], error=str(e))
        return ResolveResponse(
            success=False,
            data={
                "resolved": False,
                "errorCode": "RESOLUTION_FAILED",
                "errorMessage": str(e),
            },
        )


# =============================================================================
# Resolve Batch Sources Endpoint
# =============================================================================


@router.post("/resolve-batch", response_model=ResolveBatchResponse)
async def resolve_batch_sources(
    request: ResolveBatchRequest,
) -> Dict[str, Any]:
    """Resolve multiple sources in batch.

    Per gpt意见.md Section 2.2.2:
    - Accept list of inputs
    - Return list of resolution results
    - Used for batch paste of arXiv/DOI/URL lines

    Example:
        POST /import-sources/resolve-batch
        {
            "items": ["2501.01234", "10.48550/arXiv.1706.03762", "https://..."]
        }
    """
    try:
        service = get_source_resolver_service()
        results: List[BatchResolveItem] = await service.resolve_batch(request.items)

        # Build response
        items_data = []
        for item in results:
            item_data = {
                "input": item.input,
                "resolved": item.resolved,
                "sourceType": item.source_type,
                "normalized": item.normalized,
                "preview": item.preview,
            }
            if not item.resolved:
                item_data["errorCode"] = item.error_code
                item_data["errorMessage"] = item.error_message
            items_data.append(item_data)

        response_data = {
            "items": items_data,
            "total": len(results),
            "resolvedCount": sum(1 for r in results if r.resolved),
        }

        logger.info(
            "Batch resolve via API",
            total=len(results),
            resolved=sum(1 for r in results if r.resolved),
        )

        return ResolveBatchResponse(success=True, data=response_data)

    except Exception as e:
        logger.error("Batch resolve endpoint failed", error=str(e))
        return ResolveBatchResponse(
            success=False,
            data={
                "items": [],
                "total": len(request.items),
                "error": str(e),
            },
        )


__all__ = ["router"]