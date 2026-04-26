"""Citation support validator for content_type-specific evidence validation."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class CitationSupportResult:
    citation_id: str
    source_chunk_id: str
    content_type: str
    support_status: str
    reason: str


def validate_citation_support(
    claim: str,
    citation: dict[str, Any],
    evidence_block: dict[str, Any],
) -> CitationSupportResult:
    """Validate whether citation truly supports the claim based on content_type."""
    citation_id = citation.get("citation_id", "")
    source_chunk_id = citation.get("source_chunk_id", "")
    content_type = evidence_block.get("content_type", "text")

    result = CitationSupportResult(
        citation_id=citation_id,
        source_chunk_id=source_chunk_id,
        content_type=content_type,
        support_status="unsupported",
        reason="unknown",
    )

    if content_type == "table":
        result = _validate_table_citation(claim, evidence_block)
    elif content_type == "figure":
        result = _validate_figure_citation(claim, evidence_block)
    else:
        result = _validate_text_citation(claim, evidence_block)

    return result


def _validate_table_citation(claim: str, evidence: dict[str, Any]) -> CitationSupportResult:
    """Validate table content_type citation."""
    _ = claim
    table_text = evidence.get("anchor_text", "") or evidence.get("text", "")
    table_caption = evidence.get("caption", "")
    page_context = evidence.get("page_context", "")
    adjacent_text = evidence.get("adjacent_text", "")

    has_content = any([
        table_text and len(table_text) > 10,
        table_caption and len(table_caption) > 5,
        page_context and len(page_context) > 10,
        adjacent_text and len(adjacent_text) > 10,
    ])

    if has_content:
        return CitationSupportResult(
            citation_id=evidence.get("source_chunk_id", ""),
            source_chunk_id=evidence.get("source_chunk_id", ""),
            content_type="table",
            support_status="supported",
            reason="ok",
        )

    return CitationSupportResult(
        citation_id=evidence.get("source_chunk_id", ""),
        source_chunk_id=evidence.get("source_chunk_id", ""),
        content_type="table",
        support_status="unsupported",
        reason="missing_caption_or_table_text",
    )


def _validate_figure_citation(claim: str, evidence: dict[str, Any]) -> CitationSupportResult:
    """Validate figure content_type citation."""
    _ = claim
    figure_caption = evidence.get("caption", "") or evidence.get("figure_caption", "")
    page_context = evidence.get("page_context", "")
    nearby_caption = evidence.get("nearby_caption", "")
    adjacent_text = evidence.get("adjacent_text", "")

    has_content = any([
        figure_caption and len(figure_caption) > 5,
        page_context and len(page_context) > 10,
        nearby_caption and len(nearby_caption) > 5,
        adjacent_text and len(adjacent_text) > 10,
    ])

    if has_content:
        return CitationSupportResult(
            citation_id=evidence.get("source_chunk_id", ""),
            source_chunk_id=evidence.get("source_chunk_id", ""),
            content_type="figure",
            support_status="supported",
            reason="ok",
        )

    return CitationSupportResult(
        citation_id=evidence.get("source_chunk_id", ""),
        source_chunk_id=evidence.get("source_chunk_id", ""),
        content_type="figure",
        support_status="unsupported",
        reason="missing_caption",
    )


def _validate_text_citation(claim: str, evidence: dict[str, Any]) -> CitationSupportResult:
    """Validate text content_type citation."""
    _ = claim
    anchor = evidence.get("anchor_text", "") or evidence.get("text", "")

    if anchor and len(anchor) > 10:
        return CitationSupportResult(
            citation_id=evidence.get("source_chunk_id", ""),
            source_chunk_id=evidence.get("source_chunk_id", ""),
            content_type="text",
            support_status="supported",
            reason="ok",
        )

    return CitationSupportResult(
        citation_id=evidence.get("source_chunk_id", ""),
        source_chunk_id=evidence.get("source_chunk_id", ""),
        content_type="text",
        support_status="unsupported",
        reason="missing_content",
    )
