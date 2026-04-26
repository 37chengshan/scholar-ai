from __future__ import annotations

from app.rag_v3.schemas import RelationArtifact


class RelationIndex:
    def __init__(self) -> None:
        self._relations: dict[str, RelationArtifact] = {}

    def upsert(self, relation: RelationArtifact) -> None:
        self._relations = {**self._relations, relation.relation_id: relation}

    def search(self, predicate: str, top_k: int = 20) -> list[RelationArtifact]:
        matches = [
            relation
            for relation in self._relations.values()
            if relation.predicate == predicate
        ]
        return matches[: max(1, top_k)]
