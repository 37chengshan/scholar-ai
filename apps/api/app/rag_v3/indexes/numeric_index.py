from __future__ import annotations

import re


NUMERIC_PATTERN = re.compile(r"[-+]?\d+(?:\.\d+)?%?")


class NumericIndex:
    def __init__(self) -> None:
        self._values: dict[str, list[str]] = {}

    def upsert(self, source_chunk_id: str, text: str) -> None:
        values = NUMERIC_PATTERN.findall(text or "")
        self._values = {**self._values, source_chunk_id: values}

    def search(self, query: str, top_k: int = 20) -> list[str]:
        needles = set(NUMERIC_PATTERN.findall(query or ""))
        if not needles:
            return []
        scored = []
        for source_chunk_id, values in self._values.items():
            hit = len(needles & set(values))
            scored.append((hit, source_chunk_id))
        scored.sort(reverse=True)
        return [item[1] for item in scored[: max(1, top_k)] if item[0] > 0]
