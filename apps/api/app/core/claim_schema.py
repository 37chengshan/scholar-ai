from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class ClaimSupportLevel(str, Enum):
    supported = "supported"
    weak = "weak"
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


class ClaimVerificationResult(BaseModel):
    claim_id: str = Field(..., min_length=1)
    text: str = Field(..., min_length=1)
    claim_type: str = Field(..., min_length=1)
    support_level: ClaimSupportLevel
    evidence_ids: List[str] = Field(default_factory=list)
    support_score: float = Field(0.0, ge=0.0, le=1.0)


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
