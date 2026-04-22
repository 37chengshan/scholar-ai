from __future__ import annotations

import re
from typing import Dict, List

from app.core.claim_schema import AnswerClaim, ClaimSupportLevel, ClaimVerificationResult


_TOKEN_PATTERN = re.compile(r"[a-zA-Z0-9_\-]+")


class ClaimVerifier:
    """Verify each extracted claim against retrieval evidence chunks."""

    def verify(self, claims: List[AnswerClaim], sources: List[Dict]) -> List[ClaimVerificationResult]:
        if not claims:
            return []

        source_index = self._prepare_sources(sources)
        verification: List[ClaimVerificationResult] = []
        for claim in claims:
            best_score = 0.0
            evidence_ids: List[str] = []
            claim_tokens = self._tokenize(claim.text)
            for source in source_index:
                overlap = self._overlap_ratio(claim_tokens, source["tokens"])
                if overlap >= 0.45:
                    evidence_ids.append(source["source_id"])
                if overlap > best_score:
                    best_score = overlap

            if best_score >= 0.45:
                support_level = ClaimSupportLevel.supported
            elif best_score >= 0.20:
                support_level = ClaimSupportLevel.weak
            else:
                support_level = ClaimSupportLevel.unsupported

            verification.append(
                ClaimVerificationResult(
                    claim_id=claim.claim_id,
                    text=claim.text,
                    claim_type=claim.claim_type,
                    support_level=support_level,
                    evidence_ids=evidence_ids[:3],
                    support_score=round(best_score, 4),
                )
            )

        return verification

    @staticmethod
    def build_report(results: List[ClaimVerificationResult]) -> Dict:
        total = len(results)
        supported = [item for item in results if item.support_level == ClaimSupportLevel.supported]
        weak = [item for item in results if item.support_level == ClaimSupportLevel.weak]
        unsupported = [item for item in results if item.support_level == ClaimSupportLevel.unsupported]
        return {
            "totalClaims": total,
            "supportedClaimCount": len(supported),
            "weaklySupportedClaimCount": len(weak),
            "unsupportedClaimCount": len(unsupported),
            "unsupportedClaimRate": round((len(unsupported) / total) if total else 0.0, 4),
            "results": [item.model_dump() for item in results],
        }

    @staticmethod
    def _prepare_sources(sources: List[Dict]) -> List[Dict]:
        indexed = []
        for source in sources:
            source_id = str(source.get("source_id") or source.get("id") or source.get("paper_id") or "unknown")
            evidence_text = " ".join(
                [
                    str(source.get("anchor_text") or ""),
                    str(source.get("text") or ""),
                    str(source.get("text_preview") or ""),
                    str(source.get("metric_sentence") or ""),
                    str(source.get("caption_text") or ""),
                ]
            )
            indexed.append(
                {
                    "source_id": source_id,
                    "tokens": ClaimVerifier._tokenize(evidence_text),
                }
            )
        return indexed

    @staticmethod
    def _tokenize(text: str) -> set[str]:
        return {token.lower() for token in _TOKEN_PATTERN.findall(text or "") if len(token) >= 3}

    @staticmethod
    def _overlap_ratio(claim_tokens: set[str], source_tokens: set[str]) -> float:
        if not claim_tokens or not source_tokens:
            return 0.0
        overlap = len(claim_tokens & source_tokens)
        return overlap / max(len(claim_tokens), 1)


_claim_verifier: ClaimVerifier | None = None


def get_claim_verifier() -> ClaimVerifier:
    global _claim_verifier
    if _claim_verifier is None:
        _claim_verifier = ClaimVerifier()
    return _claim_verifier
