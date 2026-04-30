from __future__ import annotations

import re
from typing import Any, Dict, List

from app.core.claim_schema import AnswerClaim, ClaimSupportLevel, ClaimVerificationResult


_TOKEN_PATTERN = re.compile(r"[a-zA-Z0-9_\-]+")
_NUMBER_PATTERN = re.compile(r"\d+(?:\.\d+)?")
_SENTENCE_SPLIT_PATTERN = re.compile(r"(?<=[.!?])\s+")
_NEGATION_TOKENS = {
    "no",
    "not",
    "never",
    "without",
    "lack",
    "lacks",
    "fail",
    "fails",
    "failed",
    "cannot",
    "unable",
}


class ClaimVerifier:
    """Verify each extracted claim against retrieval evidence chunks."""

    backend_name = "rarr_cove_scifact_lite"

    def verify(self, claims: List[AnswerClaim], sources: List[Dict]) -> List[ClaimVerificationResult]:
        if not claims:
            return []

        source_index = self._prepare_sources(sources)
        verification: List[ClaimVerificationResult] = []
        for claim in claims:
            best_score = 0.0
            claim_tokens = self._tokenize(claim.text)
            scored_sources: list[tuple[float, dict[str, Any]]] = []
            for source in source_index:
                score, details = self._score_source(claim=claim, claim_tokens=claim_tokens, source=source)
                if score > 0.12:
                    scored_sources.append((score, {"source_id": source["source_id"], "details": details}))
                if score > best_score:
                    best_score = score

            scored_sources.sort(key=lambda item: item[0], reverse=True)
            evidence_ids = [item[1]["source_id"] for item in scored_sources[:3]]
            best_details = scored_sources[0][1]["details"] if scored_sources else {
                "lexical": 0.0,
                "coverage": 0.0,
                "sentence_alignment": 0.0,
                "numeric_alignment": 0.0,
                "contradiction_penalty": 0.0,
            }

            if best_score >= 0.72:
                support_level = ClaimSupportLevel.supported
                reason = self._build_reason(support_level.value, best_details)
            elif best_score >= 0.5:
                support_level = ClaimSupportLevel.weakly_supported
                reason = self._build_reason(support_level.value, best_details)
            elif best_score >= 0.28:
                support_level = ClaimSupportLevel.partially_supported
                reason = self._build_reason(support_level.value, best_details)
            else:
                support_level = ClaimSupportLevel.unsupported
                reason = self._build_reason(support_level.value, best_details)

            verification.append(
                ClaimVerificationResult(
                    claim_id=claim.claim_id,
                    text=claim.text,
                    claim_type=claim.claim_type,
                    support_level=support_level,
                    evidence_ids=evidence_ids[:3],
                    support_score=round(best_score, 4),
                    reason=reason,
                )
            )

        return verification

    @staticmethod
    def build_report(results: List[ClaimVerificationResult]) -> Dict:
        total = len(results)
        supported = [item for item in results if item.support_level == ClaimSupportLevel.supported]
        weak = [item for item in results if item.support_level == ClaimSupportLevel.weakly_supported]
        partial = [item for item in results if item.support_level == ClaimSupportLevel.partially_supported]
        unsupported = [item for item in results if item.support_level == ClaimSupportLevel.unsupported]
        return {
            "verifierBackend": ClaimVerifier.backend_name,
            "verificationStyle": "claim_level_multi_signal",
            "totalClaims": total,
            "supportedClaimCount": len(supported),
            "weaklySupportedClaimCount": len(weak),
            "partiallySupportedClaimCount": len(partial),
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
                    "text": evidence_text,
                    "tokens": ClaimVerifier._tokenize(evidence_text),
                    "numbers": ClaimVerifier._extract_numbers(evidence_text),
                    "sentences": ClaimVerifier._split_sentences(evidence_text),
                }
            )
        return indexed

    @staticmethod
    def _score_source(
        *,
        claim: AnswerClaim,
        claim_tokens: set[str],
        source: dict[str, Any],
    ) -> tuple[float, dict[str, float]]:
        lexical = ClaimVerifier._overlap_ratio(claim_tokens, source["tokens"])
        coverage = ClaimVerifier._coverage_ratio(claim_tokens, source["tokens"])
        sentence_alignment = ClaimVerifier._best_sentence_alignment(claim_tokens, source["sentences"])
        numeric_alignment = ClaimVerifier._numeric_alignment(claim.text, source["numbers"])
        contradiction_penalty = ClaimVerifier._contradiction_penalty(claim.text, source["text"], lexical)

        numeric_weight = 0.25 if claim.claim_type == "numeric" else 0.05
        base_score = (
            lexical * 0.4
            + coverage * 0.25
            + sentence_alignment * 0.2
            + numeric_alignment * numeric_weight
        )
        score = max(0.0, min(1.0, base_score - contradiction_penalty))
        return score, {
            "lexical": round(lexical, 4),
            "coverage": round(coverage, 4),
            "sentence_alignment": round(sentence_alignment, 4),
            "numeric_alignment": round(numeric_alignment, 4),
            "contradiction_penalty": round(contradiction_penalty, 4),
        }

    @staticmethod
    def _build_reason(support_level: str, details: dict[str, float]) -> str:
        if support_level == ClaimSupportLevel.supported.value:
            return (
                "multi-signal verifier found aligned lexical, sentence, and numeric support "
                f"(lexical={details['lexical']}, coverage={details['coverage']})"
            )
        if support_level == ClaimSupportLevel.weakly_supported.value:
            return (
                "multi-signal verifier found useful support but evidence remains incomplete "
                f"(sentence_alignment={details['sentence_alignment']}, coverage={details['coverage']})"
            )
        if support_level == ClaimSupportLevel.partially_supported.value:
            return (
                "evidence partially overlaps the claim but lacks full claim coverage "
                f"(lexical={details['lexical']}, contradiction_penalty={details['contradiction_penalty']})"
            )
        return (
            "no reliable evidence alignment after multi-signal verification "
            f"(lexical={details['lexical']}, numeric_alignment={details['numeric_alignment']})"
        )

    @staticmethod
    def _tokenize(text: str) -> set[str]:
        return {token.lower() for token in _TOKEN_PATTERN.findall(text or "") if len(token) >= 3}

    @staticmethod
    def _overlap_ratio(claim_tokens: set[str], source_tokens: set[str]) -> float:
        if not claim_tokens or not source_tokens:
            return 0.0
        overlap = len(claim_tokens & source_tokens)
        return overlap / max(len(claim_tokens), 1)

    @staticmethod
    def _coverage_ratio(claim_tokens: set[str], source_tokens: set[str]) -> float:
        if not claim_tokens or not source_tokens:
            return 0.0
        overlap = len(claim_tokens & source_tokens)
        return overlap / max(min(len(claim_tokens), len(source_tokens)), 1)

    @staticmethod
    def _split_sentences(text: str) -> list[str]:
        return [segment.strip() for segment in _SENTENCE_SPLIT_PATTERN.split(text or "") if segment.strip()]

    @staticmethod
    def _best_sentence_alignment(claim_tokens: set[str], sentences: list[str]) -> float:
        if not sentences:
            return 0.0
        return max(ClaimVerifier._overlap_ratio(claim_tokens, ClaimVerifier._tokenize(sentence)) for sentence in sentences)

    @staticmethod
    def _extract_numbers(text: str) -> set[str]:
        return set(_NUMBER_PATTERN.findall(text or ""))

    @staticmethod
    def _numeric_alignment(claim_text: str, source_numbers: set[str]) -> float:
        claim_numbers = ClaimVerifier._extract_numbers(claim_text)
        if not claim_numbers:
            return 0.0
        if not source_numbers:
            return 0.0
        overlap = len(claim_numbers & source_numbers)
        return overlap / max(len(claim_numbers), 1)

    @staticmethod
    def _contradiction_penalty(claim_text: str, source_text: str, lexical: float) -> float:
        claim_tokens = ClaimVerifier._tokenize(claim_text)
        source_tokens = ClaimVerifier._tokenize(source_text)
        claim_has_negation = bool(claim_tokens & _NEGATION_TOKENS)
        source_has_negation = bool(source_tokens & _NEGATION_TOKENS)
        if claim_has_negation == source_has_negation:
            return 0.0
        if lexical < 0.2:
            return 0.0
        return 0.18


_claim_verifier: ClaimVerifier | None = None


def get_claim_verifier() -> ClaimVerifier:
    global _claim_verifier
    if _claim_verifier is None:
        _claim_verifier = ClaimVerifier()
    return _claim_verifier
