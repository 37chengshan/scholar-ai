"""ParseArtifact contract and helpers."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from hashlib import sha256
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class ParseMode(str, Enum):
    DOCLING_NATIVE = "docling_native"
    DOCLING_OCR = "docling_ocr"
    PYPDF_FALLBACK = "pypdf_fallback"


class ParseQualityLevel(str, Enum):
    FULL = "full"
    TEXT_ONLY = "text_only"
    DEGRADED = "degraded"


class ParseArtifact(BaseModel):
    """Canonical parse output artifact shared by downstream flows."""

    artifact_type: Literal["parse_artifact"] = "parse_artifact"
    contract_version: Literal["v1"] = "v1"
    parse_id: str
    paper_id: str
    source_uri: str
    parser_name: str = "docling"
    parser_version: Optional[str] = None
    parse_mode: ParseMode
    quality_level: ParseQualityLevel
    ocr_used: bool = False
    page_count: int = 0
    markdown: str = ""
    items: List[Dict[str, Any]] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    supports_tables: bool = False
    supports_figures: bool = False
    created_at: str


def _normalize_parse_mode(raw_mode: str, ocr_used: bool) -> ParseMode:
    mode = (raw_mode or "").strip().lower()
    if mode in {"native", "docling_native"}:
        return ParseMode.DOCLING_NATIVE
    if mode in {"force_ocr", "ocr_fallback", "docling_ocr"}:
        return ParseMode.DOCLING_OCR
    if mode == "pypdf_fallback":
        return ParseMode.PYPDF_FALLBACK
    return ParseMode.DOCLING_OCR if ocr_used else ParseMode.DOCLING_NATIVE


def _derive_quality_level(parse_mode: ParseMode, warnings: List[str]) -> ParseQualityLevel:
    if parse_mode == ParseMode.PYPDF_FALLBACK:
        return ParseQualityLevel.TEXT_ONLY
    lowered = " ".join(warnings).lower()
    if "failed" in lowered or "timeout" in lowered:
        return ParseQualityLevel.DEGRADED
    return ParseQualityLevel.FULL


def build_parse_id(paper_id: str, source_uri: str, created_at: str) -> str:
    seed = f"{paper_id}|{source_uri}|{created_at}".encode("utf-8")
    return sha256(seed).hexdigest()[:32]


def build_parse_artifact(
    *,
    paper_id: str,
    source_uri: str,
    parse_result: Dict[str, Any],
    parser_name: str = "docling",
    parser_version: Optional[str] = None,
) -> ParseArtifact:
    metadata = parse_result.get("metadata") or {}
    ocr_used = bool(metadata.get("ocr_used", False))
    parse_mode = _normalize_parse_mode(str(metadata.get("parse_mode", "")), ocr_used)
    warnings: List[str] = list(metadata.get("parse_warnings") or [])
    created_at = datetime.now(timezone.utc).isoformat()

    supports_tables = parse_mode != ParseMode.PYPDF_FALLBACK
    supports_figures = parse_mode != ParseMode.PYPDF_FALLBACK

    if parse_mode == ParseMode.PYPDF_FALLBACK:
        supports_tables = False
        supports_figures = False

    artifact = ParseArtifact(
        parse_id=build_parse_id(paper_id=paper_id, source_uri=source_uri, created_at=created_at),
        paper_id=paper_id,
        source_uri=source_uri,
        parser_name=parser_name,
        parser_version=parser_version,
        parse_mode=parse_mode,
        quality_level=_derive_quality_level(parse_mode, warnings),
        ocr_used=ocr_used,
        page_count=int(parse_result.get("page_count") or 0),
        markdown=str(parse_result.get("markdown") or ""),
        items=list(parse_result.get("items") or []),
        warnings=warnings,
        supports_tables=supports_tables,
        supports_figures=supports_figures,
        created_at=created_at,
    )
    return artifact
