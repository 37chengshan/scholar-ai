from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class ClaimSupportLevel(str, Enum):
    supported = "supported"
    weakly_supported = "weakly_supported"
    # Legacy alias kept for backward compatibility.
    weak = "weakly_supported"
    partially_supported = "partially_supported"
    unsupported = "unsupported"


class AnswerMode(str, Enum):
    full = "full"
    partial = "partial"
    abstain = "abstain"


class AnswerClaim(BaseModel):
    claim_id: str = Field(..., min_length=1)
    text: str = Field(..., min_length=1)
    claim_type: str = Field(..., min_length=1)
    citations: List[str] = Field(default_factory=list)


class ClaimUnit(BaseModel):
    claim_id: str = Field(..., min_length=1)
    claim_text: str = Field(..., min_length=1)
    claim_type: str = Field(..., min_length=1)
    surface_context: Optional[str] = None
    source_sentence_index: Optional[int] = Field(default=None, ge=0)
    support_status: ClaimSupportLevel = ClaimSupportLevel.unsupported
    support_score: float = Field(0.0, ge=0.0, le=1.0)
    supporting_evidence_ids: List[str] = Field(default_factory=list)
    repairable: bool = True
    repair_hint: Optional[str] = None


class EvidenceAnchor(BaseModel):
    evidence_id: str = Field(..., min_length=1)
    paper_id: str = Field(..., min_length=1)
    source_chunk_id: str = Field(..., min_length=1)
    quote_text: str = Field(..., min_length=1)
    source_offset_start: Optional[int] = Field(default=None, ge=0)
    source_offset_end: Optional[int] = Field(default=None, ge=0)
    page_num: Optional[int] = Field(default=None, ge=1)
    section_path: Optional[str] = None
    content_type: Optional[str] = None
    citation_jump_url: Optional[str] = None


class ClaimVerificationResult(BaseModel):
    claim_id: str = Field(..., min_length=1)
    text: str = Field(..., min_length=1)
    claim_type: str = Field(..., min_length=1)
    support_level: ClaimSupportLevel
    evidence_ids: List[str] = Field(default_factory=list)
    support_score: float = Field(0.0, ge=0.0, le=1.0)
    reason: Optional[str] = None
    verification_mode: str = Field(default="claim_level")


class AbstainDecision(BaseModel):
    answer_mode: AnswerMode
    abstained: bool = False
    abstain_reason: Optional[str] = None
    unsupported_claim_rate: float = Field(0.0, ge=0.0, le=1.0)
    citation_coverage: float = Field(0.0, ge=0.0, le=1.0)
    answer_evidence_consistency: float = Field(0.0, ge=0.0, le=1.0)
    supported_claim_count: int = Field(0, ge=0)
    unsupported_claim_count: int = Field(0, ge=0)
    weakly_supported_claim_count: int = Field(0, ge=0)
