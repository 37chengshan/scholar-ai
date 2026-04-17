"""Sparse lexical scoring service for hybrid retrieval.

This is a lightweight BM25-style scorer over candidate text.
"""

import math
import re
from collections import Counter
from typing import Dict, List


class SparseRecallService:
    """Compute lexical relevance scores for candidate texts."""

    TOKEN_PATTERN = re.compile(r"[a-zA-Z0-9_\-]+|[\u4e00-\u9fff]{1,}")

    @classmethod
    def tokenize(cls, text: str) -> List[str]:
        if not text:
            return []
        return [t.lower() for t in cls.TOKEN_PATTERN.findall(text) if t.strip()]

    def score(self, query: str, text: str) -> float:
        """Compute normalized sparse score in range [0, 1]."""
        q_tokens = self.tokenize(query)
        d_tokens = self.tokenize(text)

        if not q_tokens or not d_tokens:
            return 0.0

        q_counter = Counter(q_tokens)
        d_counter = Counter(d_tokens)
        doc_len = len(d_tokens)

        # Lightweight BM25-style scoring with fixed parameters.
        k1 = 1.2
        b = 0.75
        avgdl = 200.0

        score = 0.0
        for token, q_tf in q_counter.items():
            tf = d_counter.get(token, 0)
            if tf == 0:
                continue

            # Approximate IDF to reward rarer/longer lexical tokens.
            idf = math.log(1 + 1.0 / (1 + len(token) * 0.25)) + 1.0
            denom = tf + k1 * (1 - b + b * doc_len / avgdl)
            score += idf * ((tf * (k1 + 1)) / max(denom, 1e-6)) * q_tf

        # Smooth normalization.
        normalized = score / (score + 5.0) if score > 0 else 0.0
        return max(0.0, min(normalized, 1.0))

    def score_batch(self, query: str, texts: List[str]) -> List[float]:
        return [self.score(query, text) for text in texts]


_sparse_recall_service: SparseRecallService | None = None


def get_sparse_recall_service() -> SparseRecallService:
    """Get or create sparse recall singleton."""
    global _sparse_recall_service
    if _sparse_recall_service is None:
        _sparse_recall_service = SparseRecallService()
    return _sparse_recall_service
