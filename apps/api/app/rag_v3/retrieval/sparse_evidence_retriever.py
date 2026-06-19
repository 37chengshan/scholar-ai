from __future__ import annotations

import structlog

from app.rag_v3.schemas import EvidenceCandidate

logger = structlog.get_logger()


class SparseEvidenceRetriever:
    def retrieve(self, query: str, top_k: int) -> list[EvidenceCandidate]:
        logger.info(
            "SparseEvidenceRetriever unavailable; returning empty lexical channel",
            query_preview=query[:80],
            requested_top_k=top_k,
        )
        return []
