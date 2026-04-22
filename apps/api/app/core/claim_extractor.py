from __future__ import annotations

import re
from typing import List

from app.core.claim_schema import AnswerClaim


_CITATION_PATTERN = re.compile(r"\[[^\[\],]+,\s*[^\[\]]+\]")
_SENTENCE_SPLIT_PATTERN = re.compile(r"(?<=[。！？.!?])\s+")


class ClaimExtractor:
    """Extract claim list from draft answer text."""

    def extract(self, answer: str) -> List[AnswerClaim]:
        text = (answer or "").strip()
        if not text:
            return []

        claims: List[AnswerClaim] = []
        raw_sentences = _SENTENCE_SPLIT_PATTERN.split(text)
        for idx, sentence in enumerate(raw_sentences, start=1):
            cleaned = sentence.strip()
            if len(cleaned) < 20:
                continue
            citations = _CITATION_PATTERN.findall(cleaned)
            claim_text = _CITATION_PATTERN.sub("", cleaned).strip()
            if not claim_text:
                continue
            claims.append(
                AnswerClaim(
                    claim_id=f"claim-{idx}",
                    text=claim_text,
                    claim_type=self._classify_claim_type(claim_text),
                    citations=citations,
                )
            )
        return claims

    @staticmethod
    def _classify_claim_type(claim_text: str) -> str:
        lower = claim_text.lower()
        if any(token in lower for token in ("compared", "better", "worse", "than", "outperform")):
            return "comparative"
        if any(token in lower for token in ("%", "score", "accuracy", "f1", "auc", "bleu", "rouge")):
            return "numeric"
        if any(token in lower for token in ("because", "due to", "leads to", "causes", "therefore")):
            return "causal"
        if any(token in lower for token in ("limitation", "fails", "weak", "challenging", "failure")):
            return "limitation"
        return "factual"


_claim_extractor: ClaimExtractor | None = None


def get_claim_extractor() -> ClaimExtractor:
    global _claim_extractor
    if _claim_extractor is None:
        _claim_extractor = ClaimExtractor()
    return _claim_extractor
