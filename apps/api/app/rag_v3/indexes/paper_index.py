from __future__ import annotations

import math
import re
from typing import Any

from app.rag_v3.schemas import PaperSummaryArtifact


def _tokenize(text: str) -> list[str]:
    return re.findall(r"\b[a-z]{3,}\b", text.lower())


def _tf_idf_score(query_tokens: list[str], doc_tokens: list[str]) -> float:
    if not query_tokens or not doc_tokens:
        return 0.0
    doc_set = set(doc_tokens)
    freq: dict[str, int] = {}
    for t in doc_tokens:
        freq[t] = freq.get(t, 0) + 1
    total = len(doc_tokens)
    score = 0.0
    for qt in set(query_tokens):
        if qt in doc_set:
            tf = freq.get(qt, 0) / total
            idf = math.log(1 + 1.0)  # simplified; single-doc idf
            score += tf * idf
    return score


class PaperSummaryIndex:
    def __init__(self) -> None:
        self._records: dict[str, PaperSummaryArtifact] = {}
        self._doc_tokens: dict[str, list[str]] = {}

    def upsert(self, artifact: PaperSummaryArtifact) -> None:
        self._records = {**self._records, artifact.paper_id: artifact}
        doc_text = " ".join(
            filter(
                None,
                [
                    artifact.title,
                    artifact.abstract,
                    artifact.paper_summary,
                    artifact.method_summary,
                    artifact.experiment_summary,
                    " ".join(artifact.methods),
                    " ".join(artifact.datasets),
                    " ".join(artifact.metrics),
                    " ".join(artifact.tasks),
                ],
            )
        )
        self._doc_tokens = {**self._doc_tokens, artifact.paper_id: _tokenize(doc_text)}

    def search(self, query: str, top_k: int = 10) -> list[PaperSummaryArtifact]:
        query_tokens = _tokenize(query)
        scored = [
            (pid, _tf_idf_score(query_tokens, self._doc_tokens.get(pid, [])))
            for pid in self._records
        ]
        scored.sort(key=lambda x: x[1], reverse=True)
        return [self._records[pid] for pid, _ in scored[:max(1, top_k)]]

    def get(self, paper_id: str) -> PaperSummaryArtifact | None:
        return self._records.get(paper_id)

    def all_paper_ids(self) -> list[str]:
        return list(self._records.keys())

    def __len__(self) -> int:
        return len(self._records)
