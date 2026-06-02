"""Graph retriever for RAG pipeline.

Upgraded from stub to real Neo4j queries. Provides graph-based evidence
candidates for review draft generation (review_only=True).

Feature flag: GRAPH_SYNTHESIS_ENABLED (default off)
"""

from __future__ import annotations

import os
from typing import Any

import structlog

from app.core.graph_retrieval_service import get_graph_retrieval_service
from app.core.community_detector import get_community_detector
from app.core.community_summarizer import get_community_summarizer
from app.rag_v3.schemas import EvidenceCandidate

logger = structlog.get_logger()

GRAPH_SYNTHESIS_ENABLED = os.getenv("GRAPH_SYNTHESIS_ENABLED", "false").lower() in {"true", "1", "yes"}


class GraphRetriever:
    """Graph-based retriever backed by Neo4j with community detection."""

    def __init__(self, *, review_only: bool = True):
        self._review_only = review_only
        self._graph_service = get_graph_retrieval_service()
        self._community_detector = get_community_detector()
        self._community_summarizer = get_community_summarizer()

    async def retrieve(
        self,
        *,
        query: str,
        user_id: str,
        paper_ids: list[str],
        top_k: int = 8,
    ) -> list[EvidenceCandidate]:
        """Retrieve graph-based evidence candidates.

        Args:
            query: The search query
            user_id: User ID for isolation
            paper_ids: Paper IDs to scope the search
            top_k: Maximum results

        Returns:
            List of EvidenceCandidate from graph
        """
        if not GRAPH_SYNTHESIS_ENABLED:
            return []
        if not paper_ids:
            return []

        candidates: list[EvidenceCandidate] = []

        # Get graph context from Neo4j
        try:
            graph_hint = {"query_family": "survey"}
            graph_results = await self._graph_service.expand_graph_context(
                graph_hint=graph_hint,
                paper_ids=paper_ids,
                query=query,
            )

            for idx, result in enumerate(graph_results[:top_k]):
                candidates.append(
                    EvidenceCandidate(
                        source_chunk_id=result.get("graph_candidate_id", f"graph-{idx}"),
                        paper_id=result.get("paper_id", ""),
                        section_id="graph_context",
                        content_type="text",
                        anchor_text=f"Graph relation: {result.get('relation', 'unknown')}",
                        candidate_sources=["graph"],
                        graph_score=float(result.get("score", 0.5)),
                    )
                )
        except Exception as exc:
            logger.warning("Graph retrieval failed", error=str(exc))

        return candidates

    async def get_community_summaries(
        self,
        *,
        user_id: str,
        paper_ids: list[str],
    ) -> dict[int, str]:
        """Get community summaries for review draft integration.

        Args:
            user_id: User ID for isolation
            paper_ids: Paper IDs to scope

        Returns:
            Dict mapping community_id to summary text
        """
        if not GRAPH_SYNTHESIS_ENABLED:
            return {}

        try:
            communities = await self._community_detector.detect_communities(
                user_id=user_id,
                paper_ids=paper_ids,
            )
            if not communities:
                return {}

            summaries = await self._community_summarizer.summarize_communities(
                communities=communities,
                user_id=user_id,
            )
            return summaries
        except Exception as exc:
            logger.warning("Community summary retrieval failed", error=str(exc))
            return {}

    @property
    def review_only(self) -> bool:
        """Whether this retriever is restricted to review draft generation."""
        return self._review_only


_graph_retriever: GraphRetriever | None = None


def get_graph_retriever(*, review_only: bool = True) -> GraphRetriever:
    """Get or create graph retriever singleton."""
    global _graph_retriever
    if _graph_retriever is None:
        _graph_retriever = GraphRetriever(review_only=review_only)
    return _graph_retriever
