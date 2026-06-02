"""Protocol interfaces for RAG pipeline components.

Defines contracts for retrievers and verifiers to ensure consistent behavior.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from app.rag_v3.schemas import EvidenceCandidate, EvidencePack


@runtime_checkable
class RetrieverProtocol(Protocol):
    """Protocol for evidence retrievers."""

    def retrieve(
        self,
        query: str,
        top_k: int,
        paper_id_filter: list[str] | None = None,
        **kwargs: Any,
    ) -> list[EvidenceCandidate]:
        """Retrieve evidence candidates for a query.

        Args:
            query: The search query
            top_k: Maximum number of results
            paper_id_filter: Optional paper ID filter

        Returns:
            List of EvidenceCandidate
        """
        ...


@runtime_checkable
class VerifierProtocol(Protocol):
    """Protocol for claim verifiers."""

    def verify(
        self,
        claims: list[Any],
        sources: list[dict[str, Any]],
    ) -> list[Any]:
        """Verify claims against evidence sources.

        Args:
            claims: List of claims to verify
            sources: List of evidence source dicts

        Returns:
            List of verification results
        """
        ...


@runtime_checkable
class TreeBuilderProtocol(Protocol):
    """Protocol for tree builders."""

    async def build_tree(
        self,
        *,
        paper_id: str,
        user_id: str,
        chunks: list[dict[str, Any]],
    ) -> Any:
        """Build a tree structure from chunks.

        Args:
            paper_id: The paper ID
            user_id: The user ID
            chunks: List of chunk dicts

        Returns:
            Tree build result
        """
        ...
