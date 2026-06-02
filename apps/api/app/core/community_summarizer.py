"""Community summary generation for knowledge graphs.

Generates LLM summaries for each detected community.
Stores summaries in Neo4j node properties and Redis cache.
"""

from __future__ import annotations

from typing import Any

import structlog

from app.core.redis_client import get_redis
from app.utils.zhipu_client import ZhipuLLMClient

logger = structlog.get_logger()

CACHE_TTL_SECONDS = 3600  # 1 hour


class CommunitySummarizer:
    """Generates and caches summaries for graph communities."""

    def __init__(self, llm_client: ZhipuLLMClient | None = None):
        self._llm_client = llm_client or ZhipuLLMClient()

    async def summarize_community(
        self,
        *,
        community_id: int,
        entities: list[dict[str, Any]],
        user_id: str,
    ) -> str:
        """Generate a summary for a community of entities.

        Args:
            community_id: The community ID
            entities: List of entity dicts with entity_name, entity_type
            user_id: User ID for cache isolation

        Returns:
            Summary text
        """
        if not entities:
            return ""

        # Check cache first
        cache_key = f"community_summary:{user_id}:{community_id}"
        cached = await self._get_cached(cache_key)
        if cached:
            return cached

        # Build prompt
        entity_lines = []
        for entity in entities[:20]:  # Limit to avoid token overflow
            entity_lines.append(
                f"- {entity.get('entity_name', 'unknown')} ({entity.get('entity_type', 'unknown')})"
            )

        prompt = (
            f"以下是一个学术知识图谱中的社区（community_id={community_id}），"
            f"包含以下实体：\n\n" + "\n".join(entity_lines) + "\n\n"
            f"请用中文生成一个简洁的综合摘要（3-5句话），概括这个社区的核心研究主题、"
            f"主要方法和关键发现。"
        )

        try:
            summary = await self._llm_client.simple_completion(
                prompt=prompt,
                temperature=0.3,
                max_tokens=300,
            )
            summary_text = str(summary or "").strip()

            # Cache the result
            if summary_text:
                await self._set_cached(cache_key, summary_text)

            return summary_text
        except Exception as exc:
            logger.warning("Community summary generation failed", community_id=community_id, error=str(exc))
            return ""

    async def summarize_communities(
        self,
        *,
        communities: list[dict[str, Any]],
        user_id: str,
    ) -> dict[int, str]:
        """Summarize multiple communities.

        Args:
            communities: List of community dicts with community_id and entities
            user_id: User ID for cache isolation

        Returns:
            Dict mapping community_id to summary text
        """
        summaries: dict[int, str] = {}
        for community in communities:
            cid = community.get("community_id", -1)
            entities = community.get("entities", [])
            summary = await self.summarize_community(
                community_id=cid,
                entities=entities,
                user_id=user_id,
            )
            if summary:
                summaries[cid] = summary
        return summaries

    async def _get_cached(self, key: str) -> str | None:
        """Get cached summary from Redis."""
        try:
            redis = get_redis()
            cached = await redis.get(key)
            return cached.decode() if cached else None
        except Exception:
            return None

    async def _set_cached(self, key: str, value: str) -> None:
        """Set cached summary in Redis."""
        try:
            redis = get_redis()
            await redis.setex(key, CACHE_TTL_SECONDS, value)
        except Exception:
            pass


_community_summarizer: CommunitySummarizer | None = None


def get_community_summarizer() -> CommunitySummarizer:
    """Get or create community summarizer singleton."""
    global _community_summarizer
    if _community_summarizer is None:
        _community_summarizer = CommunitySummarizer()
    return _community_summarizer
