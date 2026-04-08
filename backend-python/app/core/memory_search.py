"""Memory Search Service for long-term memory retrieval.

Per D-11, D-12: Vector-based retrieval of user preferences, patterns, and feedback.
Uses Milvus for vector storage (Phase 13 architecture).
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import json

from app.utils.logger import logger
from app.core.bge_m3_service import BGEM3Service
from app.core.milvus_service import MilvusService
from app.core.database import get_db_connection


@dataclass
class Memory:
    """User memory object.

    Attributes:
        id: Memory ID
        content: Memory text content
        memory_type: Type of memory (preference, pattern, feedback)
        metadata: Additional metadata
        similarity: Vector similarity score (0-1)
        created_at: Creation timestamp
    """

    id: str
    content: str
    memory_type: str
    metadata: Optional[Dict[str, Any]] = None
    similarity: float = 0.0
    created_at: Optional[str] = None


class MemorySearch:
    """Vector-based memory retrieval service.

    Uses BGE-M3 for embeddings and Milvus for vector search.
    Stores user preferences, patterns, and feedback for context enrichment.
    """

    COLLECTION_NAME = "user_memories"

    def __init__(
        self,
        db_pool: Any = None,
        embedding_service: Optional[BGEM3Service] = None,
        milvus_service: Optional[MilvusService] = None,
    ):
        """Initialize MemorySearch service.

        Args:
            db_pool: Database connection pool
            embedding_service: BGE-M3 embedding service
            milvus_service: Milvus vector database service
        """
        self.db_pool = db_pool
        self.embedding_service = embedding_service
        self.milvus_service = milvus_service

    async def search_memories(
        self,
        query: str,
        user_id: str,
        top_k: int = 5,
        memory_types: Optional[List[str]] = None,
    ) -> List[Memory]:
        """Search user's long-term memories using vector similarity.

        Args:
            query: Search query
            user_id: User ID
            top_k: Number of results to return
            memory_types: Optional filter by memory types (preference, pattern, feedback)

        Returns:
            List of Memory objects sorted by similarity

        Raises:
            Exception: If search fails
        """
        try:
            logger.info(
                "Searching memories",
                user_id=user_id,
                query=query[:100],
                top_k=top_k,
            )

            # Generate query embedding using BGE-M3
            if not self.embedding_service:
                self.embedding_service = BGEM3Service()

            query_embedding = await self.embedding_service.encode(query)

            # Search in Milvus
            if not self.milvus_service:
                self.milvus_service = MilvusService()
                await self.milvus_service.connect()

            # Build filter expression
            filter_expr = f'user_id == "{user_id}"'
            if memory_types:
                types_str = ", ".join([f'"{t}"' for t in memory_types])
                filter_expr += f" and memory_type in [{types_str}]"

            # Search Milvus
            results = await self.milvus_service.search(
                collection_name=self.COLLECTION_NAME,
                query_vector=query_embedding,
                top_k=top_k,
                filter_expr=filter_expr,
            )

            # Fetch full memory data from PostgreSQL
            memories = []
            if results:
                memory_ids = [r.get("id") for r in results]

                async with get_db_connection() as conn:
                    rows = await conn.fetch(
                        """
                        SELECT id, content, memory_type, metadata, created_at
                        FROM user_memories
                        WHERE id = ANY($1)
                        """,
                        memory_ids,
                    )

                    # Create Memory objects with similarity scores
                    row_map = {str(row["id"]): row for row in rows}
                    for result in results:
                        memory_id = result.get("id")
                        if memory_id in row_map:
                            row = row_map[memory_id]
                            memories.append(
                                Memory(
                                    id=str(row["id"]),
                                    content=row["content"],
                                    memory_type=row["memory_type"],
                                    metadata=json.loads(row["metadata"])
                                    if row["metadata"]
                                    else None,
                                    similarity=result.get("distance", 0.0),
                                    created_at=str(row["created_at"]),
                                )
                            )

            logger.info(
                "Found memories",
                user_id=user_id,
                count=len(memories),
                top_similarity=memories[0].similarity if memories else 0.0,
            )

            return memories

        except Exception as e:
            logger.error("Failed to search memories", error=str(e), user_id=user_id)
            # Return empty list on error
            return []

    async def store_memory(
        self,
        user_id: str,
        content: str,
        memory_type: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Store a new memory with vector embedding.

        Args:
            user_id: User ID
            content: Memory content text
            memory_type: Type of memory (preference, pattern, feedback)
            metadata: Optional metadata

        Returns:
            Memory ID

        Raises:
            Exception: If storage fails
        """
        try:
            logger.info(
                "Storing memory",
                user_id=user_id,
                memory_type=memory_type,
                content_length=len(content),
            )

            # Generate embedding using BGE-M3
            if not self.embedding_service:
                self.embedding_service = BGEM3Service()

            embedding = await self.embedding_service.encode(content)

            # Insert into PostgreSQL
            async with get_db_connection() as conn:
                row = await conn.fetchrow(
                    """
                    INSERT INTO user_memories (user_id, content, memory_type, metadata)
                    VALUES ($1, $2, $3, $4)
                    RETURNING id
                    """,
                    user_id,
                    content,
                    memory_type,
                    json.dumps(metadata) if metadata else None,
                )

                memory_id = str(row["id"])

            # Insert into Milvus
            if not self.milvus_service:
                self.milvus_service = MilvusService()
                await self.milvus_service.connect()

            await self.milvus_service.insert(
                collection_name=self.COLLECTION_NAME,
                data=[
                    {
                        "id": memory_id,
                        "user_id": user_id,
                        "content": content[:500],  # Truncate for Milvus metadata
                        "memory_type": memory_type,
                        "embedding": embedding,
                    }
                ],
            )

            logger.info(
                "Stored memory successfully",
                memory_id=memory_id,
                user_id=user_id,
            )

            return memory_id

        except Exception as e:
            logger.error(
                "Failed to store memory",
                error=str(e),
                user_id=user_id,
                memory_type=memory_type,
            )
            raise

    async def get_user_preferences(self, user_id: str) -> Dict[str, Any]:
        """Get user preferences from long-term memory.

        Args:
            user_id: User ID

        Returns:
            Dict of user preferences
        """
        try:
            memories = await self.search_memories(
                query="user preferences settings",
                user_id=user_id,
                top_k=10,
                memory_types=["preference"],
            )

            preferences = {}
            for memory in memories:
                if memory.metadata and "key" in memory.metadata:
                    preferences[memory.metadata["key"]] = memory.metadata.get("value")

            return preferences

        except Exception as e:
            logger.error(
                "Failed to get user preferences", error=str(e), user_id=user_id
            )
            return {}


__all__ = ["MemorySearch", "Memory"]
