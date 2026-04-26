from __future__ import annotations

from app.rag_v3.schemas import EvidenceCandidate


class GraphRetriever:
    def retrieve(self, query: str, top_k: int) -> list[EvidenceCandidate]:
        _ = query
        return [
            EvidenceCandidate(
                source_chunk_id=f"graph-{idx:04d}",
                paper_id=f"p-{(idx % 8) + 1:03d}",
                section_id=f"s-{(idx % 5) + 1:03d}",
                content_type="text",
                candidate_sources=["graph"],
                graph_score=max(0.0, 1.0 - (idx / max(top_k, 1))),
            )
            for idx in range(1, max(top_k, 1) + 1)
        ]
