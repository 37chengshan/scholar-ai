from __future__ import annotations

import re


class LexicalIndex:
    def __init__(self) -> None:
        self._docs: dict[str, str] = {}

    def upsert(self, source_chunk_id: str, text: str) -> None:
        self._docs = {**self._docs, source_chunk_id: text}

    def search(self, query: str, top_k: int = 20) -> list[str]:
        terms = set(re.findall(r"[a-z0-9]+", query.lower()))
        scored = []
        for source_chunk_id, text in self._docs.items():
            tokens = set(re.findall(r"[a-z0-9]+", text.lower()))
            score = len(terms & tokens)
            scored.append((score, source_chunk_id))
        scored.sort(reverse=True)
        return [item[1] for item in scored[: max(1, top_k)] if item[0] > 0]
