from __future__ import annotations

import structlog

from app.rag_v3.schemas import EvidenceCandidate

logger = structlog.get_logger()


class CaptionRetriever:
    def retrieve(self, query: str, top_k: int) -> list[EvidenceCandidate]:
        logger.warning("STUB RETRIEVER CALLED: CaptionRetriever returning fabricated data")
        _ = query
        return [
            EvidenceCandidate(
                source_chunk_id=f"caption-{idx:04d}",
                paper_id=f"p-{(idx % 6) + 1:03d}",
                section_id=f"s-{(idx % 4) + 1:03d}",
                content_type="caption",
                candidate_sources=["caption"],
                caption_score=max(0.0, 1.0 - (idx / max(top_k, 1))),
            )
            for idx in range(1, max(top_k, 1) + 1)
        ]
