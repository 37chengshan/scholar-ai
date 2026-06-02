"""Unified verifier with 4-stage verification pipeline.

Stages:
1. Fast lexical check (~5ms)
2. Citation surface check (~5ms)
3. NLI entailment (~50-80ms)
4. Fusion decision

Feature flag: NLI_ENABLED (default off)
"""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from typing import Any

import structlog

from app.core.claim_schema import AnswerClaim, ClaimSupportLevel
from app.core.claim_verifier import ClaimVerifier, get_claim_verifier
from app.core.citation_verifier import CitationVerifier, get_citation_verifier
from app.core.nli_verifier import NLIResult, get_nli_verifier
from app.core.redis_client import get_redis
from app.rag_v3.schemas import EvidenceBlock

logger = structlog.get_logger()

NLI_ENABLED = os.getenv("NLI_ENABLED", "false").lower() in {"true", "1", "yes"}
NLI_CACHE_TTL_SECONDS = 3600  # 1 hour

# Fusion weights
WEIGHT_LEXICAL = 0.4
WEIGHT_NLI_ENTAILMENT = 0.3
WEIGHT_CITATION_COVERAGE = 0.2
WEIGHT_NUMERIC_ALIGNMENT = 0.1
PENALTY_NLI_CONTRADICTION = 0.3


@dataclass(frozen=True)
class VerificationResult:
    """Result of unified verification."""
    claim_id: str
    text: str
    claim_type: str
    support_level: str
    support_score: float
    evidence_ids: list[str]
    reason: str
    nli_entailment: float = 0.0
    nli_contradiction: float = 0.0
    nli_neutral: float = 0.0
    nli_degraded: bool = True
    lexical_score: float = 0.0
    citation_coverage: float = 0.0
    numeric_alignment: float = 0.0


def _nli_cache_key(claim: str, evidence: str) -> str:
    """Generate Redis cache key for NLI result."""
    combined = f"{claim}|||{evidence}"
    return f"nli:{hashlib.sha256(combined.encode()).hexdigest()[:16]}"


async def _get_cached_nli(claim: str, evidence: str) -> NLIResult | None:
    """Get cached NLI result from Redis."""
    try:
        redis = get_redis()
        key = _nli_cache_key(claim, evidence)
        cached = await redis.get(key)
        if cached:
            import json
            data = json.loads(cached)
            return NLIResult(
                entailment=data.get("entailment", 0.0),
                contradiction=data.get("contradiction", 0.0),
                neutral=data.get("neutral", 0.0),
                label=data.get("label", "neutral"),
                degraded=data.get("degraded", True),
            )
    except Exception:
        pass
    return None


async def _cache_nli(claim: str, evidence: str, result: NLIResult) -> None:
    """Cache NLI result in Redis."""
    try:
        redis = get_redis()
        key = _nli_cache_key(claim, evidence)
        import json
        data = {
            "entailment": result.entailment,
            "contradiction": result.contradiction,
            "neutral": result.neutral,
            "label": result.label,
            "degraded": result.degraded,
        }
        await redis.setex(key, NLI_CACHE_TTL_SECONDS, json.dumps(data))
    except Exception:
        pass


class UnifiedVerifier:
    """4-stage unified verification pipeline."""

    def __init__(self):
        self._claim_verifier = get_claim_verifier()
        self._citation_verifier = get_citation_verifier()

    async def verify_claims(
        self,
        *,
        claims: list[AnswerClaim],
        evidence_blocks: list[EvidenceBlock],
    ) -> dict[str, Any]:
        """Run unified verification on claims against evidence.

        Args:
            claims: List of claims to verify
            evidence_blocks: List of evidence blocks

        Returns:
            Verification report dict
        """
        if not claims:
            return self._empty_report()

        # Prepare sources for lexical verifier
        sources = [self._block_to_source(block) for block in evidence_blocks]

        # Stage 1: Fast lexical check
        lexical_results = self._claim_verifier.verify(claims, sources)

        # Stage 2: Citation surface check
        citation_report = self._citation_verifier.verify("", sources)
        citation_coverage = citation_report.get("citation_coverage", 0.0)

        # Stage 3: NLI entailment (if enabled)
        nli_results: dict[str, NLIResult] = {}
        if NLI_ENABLED:
            nli_verifier = get_nli_verifier()
            for claim in claims:
                best_nli = NLIResult(entailment=0.0, contradiction=0.0, neutral=1.0, label="neutral", degraded=True)
                for source in sources[:3]:
                    evidence_text = source.get("text", "")
                    if not evidence_text:
                        continue

                    # Check cache first
                    cached = await _get_cached_nli(claim.text, evidence_text)
                    if cached:
                        nli_result = cached
                    else:
                        nli_result = await nli_verifier.verify(claim.text, evidence_text)
                        await _cache_nli(claim.text, evidence_text, nli_result)

                    if nli_result.entailment > best_nli.entailment:
                        best_nli = nli_result

                nli_results[claim.claim_id] = best_nli

        # Stage 4: Fusion decision
        verification_results: list[VerificationResult] = []
        for claim_result in lexical_results:
            claim_id = claim_result.claim_id
            nli = nli_results.get(claim_id)

            # Extract lexical details
            lexical_score = claim_result.support_score
            numeric_alignment = 0.0
            if hasattr(claim_result, 'reason') and claim_result.reason:
                # Try to extract numeric alignment from reason
                pass

            # Calculate fusion score
            nli_entailment = nli.entailment if nli and not nli.degraded else 0.0
            nli_contradiction = nli.contradiction if nli and not nli.degraded else 0.0

            if NLI_ENABLED and nli and not nli.degraded:
                # Full fusion with NLI
                fusion_score = (
                    WEIGHT_LEXICAL * lexical_score
                    + WEIGHT_NLI_ENTAILMENT * nli_entailment
                    + WEIGHT_CITATION_COVERAGE * citation_coverage
                    + WEIGHT_NUMERIC_ALIGNMENT * numeric_alignment
                    - PENALTY_NLI_CONTRADICTION * nli_contradiction
                )
                fusion_score = max(0.0, min(1.0, fusion_score))
            else:
                # Degraded fusion without NLI
                fusion_score = (
                    WEIGHT_LEXICAL * lexical_score
                    + (WEIGHT_NLI_ENTAILMENT + WEIGHT_CITATION_COVERAGE + WEIGHT_NUMERIC_ALIGNMENT) * citation_coverage
                )
                fusion_score = max(0.0, min(1.0, fusion_score))

            # Determine support level from fusion score
            if fusion_score >= 0.72:
                support_level = ClaimSupportLevel.supported
            elif fusion_score >= 0.5:
                support_level = ClaimSupportLevel.weakly_supported
            elif fusion_score >= 0.28:
                support_level = ClaimSupportLevel.partially_supported
            else:
                support_level = ClaimSupportLevel.unsupported

            verification_results.append(
                VerificationResult(
                    claim_id=claim_id,
                    text=claim_result.text,
                    claim_type=claim_result.claim_type,
                    support_level=support_level.value,
                    support_score=round(fusion_score, 4),
                    evidence_ids=claim_result.evidence_ids,
                    reason=self._build_fusion_reason(
                        lexical_score=lexical_score,
                        nli_entailment=nli_entailment,
                        nli_contradiction=nli_contradiction,
                        citation_coverage=citation_coverage,
                        nli_degraded=nli.degraded if nli else True,
                    ),
                    nli_entailment=nli_entailment,
                    nli_contradiction=nli_contradiction,
                    nli_neutral=nli.neutral if nli else 1.0,
                    nli_degraded=nli.degraded if nli else True,
                    lexical_score=lexical_score,
                    citation_coverage=citation_coverage,
                    numeric_alignment=numeric_alignment,
                )
            )

        return self._build_report(verification_results)

    @staticmethod
    def _block_to_source(block: EvidenceBlock) -> dict[str, Any]:
        return {
            "source_id": block.source_chunk_id or block.evidence_id,
            "text": block.text or block.quote_text or "",
            "anchor_text": block.quote_text or block.text or "",
            "text_preview": block.text or "",
        }

    @staticmethod
    def _build_fusion_reason(
        *,
        lexical_score: float,
        nli_entailment: float,
        nli_contradiction: float,
        citation_coverage: float,
        nli_degraded: bool,
    ) -> str:
        if nli_degraded:
            return (
                f"Lexical verification: score={lexical_score:.3f}, "
                f"citation_coverage={citation_coverage:.3f}. "
                "NLI unavailable (degraded mode)."
            )
        return (
            f"Fusion: lexical={lexical_score:.3f}, "
            f"nli_entailment={nli_entailment:.3f}, "
            f"nli_contradiction={nli_contradiction:.3f}, "
            f"citation_coverage={citation_coverage:.3f}"
        )

    @staticmethod
    def _build_report(results: list[VerificationResult]) -> dict[str, Any]:
        total = len(results)
        supported = sum(1 for r in results if r.support_level == ClaimSupportLevel.supported.value)
        weakly = sum(1 for r in results if r.support_level == ClaimSupportLevel.weakly_supported.value)
        partially = sum(1 for r in results if r.support_level == ClaimSupportLevel.partially_supported.value)
        unsupported = sum(1 for r in results if r.support_level == ClaimSupportLevel.unsupported.value)

        nli_used = any(not r.nli_degraded for r in results)

        return {
            "verifierBackend": "unified_verifier_nli" if nli_used else "unified_verifier_lexical",
            "verificationStyle": "unified_4_stage",
            "totalClaims": total,
            "supportedClaimCount": supported,
            "weaklySupportedClaimCount": weakly,
            "partiallySupportedClaimCount": partially,
            "unsupportedClaimCount": unsupported,
            "unsupportedClaimRate": round((unsupported / total) if total else 0.0, 4),
            "nliEnabled": NLI_ENABLED,
            "nliUsed": nli_used,
            "results": [
                {
                    "claim_id": r.claim_id,
                    "text": r.text,
                    "claim_type": r.claim_type,
                    "support_level": r.support_level,
                    "support_score": r.support_score,
                    "evidence_ids": r.evidence_ids,
                    "reason": r.reason,
                    "nli_entailment": r.nli_entailment,
                    "nli_contradiction": r.nli_contradiction,
                    "nli_degraded": r.nli_degraded,
                    "lexical_score": r.lexical_score,
                    "citation_coverage": r.citation_coverage,
                }
                for r in results
            ],
        }

    @staticmethod
    def _empty_report() -> dict[str, Any]:
        return {
            "verifierBackend": "unified_verifier",
            "verificationStyle": "unified_4_stage",
            "totalClaims": 0,
            "supportedClaimCount": 0,
            "weaklySupportedClaimCount": 0,
            "partiallySupportedClaimCount": 0,
            "unsupportedClaimCount": 0,
            "unsupportedClaimRate": 0.0,
            "nliEnabled": NLI_ENABLED,
            "nliUsed": False,
            "results": [],
        }


_unified_verifier: UnifiedVerifier | None = None


def get_unified_verifier() -> UnifiedVerifier:
    """Get or create unified verifier singleton."""
    global _unified_verifier
    if _unified_verifier is None:
        _unified_verifier = UnifiedVerifier()
    return _unified_verifier
