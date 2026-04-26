from __future__ import annotations

from app.rag_v3.indexes.section_index import SectionSummaryIndex
from app.rag_v3.schemas import SectionSummaryArtifact


class SectionRetriever:
    def __init__(self, index: SectionSummaryIndex) -> None:
        self._index = index

    def retrieve(self, query: str, top_k: int) -> list[SectionSummaryArtifact]:
        return self._index.search(query=query, top_k=top_k)
