from __future__ import annotations

from app.rag_v3.indexes.paper_index import PaperSummaryIndex
from app.rag_v3.schemas import PaperSummaryArtifact


class PaperRetriever:
    def __init__(self, index: PaperSummaryIndex) -> None:
        self._index = index

    def retrieve(self, query: str, top_k: int) -> list[PaperSummaryArtifact]:
        return self._index.search(query=query, top_k=top_k)
