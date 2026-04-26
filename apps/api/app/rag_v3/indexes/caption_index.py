from __future__ import annotations


class CaptionIndex:
    def __init__(self) -> None:
        self._captions: dict[str, str] = {}

    def upsert(self, source_chunk_id: str, caption: str) -> None:
        self._captions = {**self._captions, source_chunk_id: caption}

    def search(self, query: str, top_k: int = 20) -> list[str]:
        query_lower = (query or "").lower()
        scored = []
        for source_chunk_id, caption in self._captions.items():
            if not caption:
                continue
            score = 1 if query_lower in caption.lower() else 0
            scored.append((score, source_chunk_id))
        scored.sort(reverse=True)
        return [item[1] for item in scored[: max(1, top_k)] if item[0] > 0]
