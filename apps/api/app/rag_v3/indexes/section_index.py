from __future__ import annotations

import math
import re

from app.rag_v3.schemas import SectionSummaryArtifact


def _tokenize(text: str) -> list[str]:
    return re.findall(r"\b[a-z]{3,}\b", text.lower())


def _tf_idf_score(query_tokens: list[str], doc_tokens: list[str]) -> float:
    if not query_tokens or not doc_tokens:
        return 0.0
    freq: dict[str, int] = {}
    for t in doc_tokens:
        freq[t] = freq.get(t, 0) + 1
    total = len(doc_tokens)
    score = 0.0
    for qt in set(query_tokens):
        if qt in freq:
            tf = freq[qt] / total
            idf = math.log(1 + 1.0)
            score += tf * idf
    return score


class SectionSummaryIndex:
    def __init__(self) -> None:
        self._records: dict[str, SectionSummaryArtifact] = {}
        self._doc_tokens: dict[str, list[str]] = {}

    def upsert(self, artifact: SectionSummaryArtifact) -> None:
        self._records = {**self._records, artifact.section_id: artifact}
        doc_text = " ".join(
            filter(
                None,
                [
                    artifact.section_title,
                    artifact.section_summary,
                    " ".join(artifact.key_terms),
                    " ".join(artifact.methods),
                    " ".join(artifact.datasets),
                    " ".join(artifact.metrics),
                ],
            )
        )
        self._doc_tokens = {**self._doc_tokens, artifact.section_id: _tokenize(doc_text)}

    def search(self, query: str, top_k: int = 10) -> list[SectionSummaryArtifact]:
        query_tokens = _tokenize(query)
        scored = [
            (sid, _tf_idf_score(query_tokens, self._doc_tokens.get(sid, [])))
            for sid in self._records
        ]
        scored.sort(key=lambda x: x[1], reverse=True)
        return [self._records[sid] for sid, _ in scored[:max(1, top_k)]]

    def search_for_paper(self, paper_id: str, query: str, top_k: int = 5) -> list[SectionSummaryArtifact]:
        query_tokens = _tokenize(query)
        scored = [
            (sid, _tf_idf_score(query_tokens, self._doc_tokens.get(sid, [])))
            for sid, art in self._records.items()
            if art.paper_id == paper_id
        ]
        scored.sort(key=lambda x: x[1], reverse=True)
        return [self._records[sid] for sid, _ in scored[:max(1, top_k)]]

    def get(self, section_id: str) -> SectionSummaryArtifact | None:
        return self._records.get(section_id)

    def __len__(self) -> int:
        return len(self._records)
