"""RAPTOR tree node index backed by Milvus.

Stores RAPTOR tree nodes in a dedicated Milvus collection
for multi-granularity retrieval.
"""

from __future__ import annotations

from typing import Any

import structlog

from app.rag_v3.indexes.raptor_tree_builder import TreeNode
from app.rag_v3.input_validation import validate_paper_id, validate_user_id

logger = structlog.get_logger()

COLLECTION_NAME = "rag_v3_raptor_nodes"


class RaptorTreeIndex:
    """Manages RAPTOR tree nodes in a Milvus collection."""

    def __init__(self, *, milvus_alias: str = "default", collection_name: str = COLLECTION_NAME):
        self._milvus_alias = milvus_alias
        self._collection_name = collection_name

    def ensure_collection(self) -> None:
        """Create the Milvus collection if it doesn't exist."""
        from pymilvus import Collection, FieldSchema, CollectionSchema, DataType

        try:
            col = Collection(self._collection_name, using=self._milvus_alias)
            col.load()
            return
        except Exception:
            pass

        fields = [
            FieldSchema(name="node_id", dtype=DataType.VARCHAR, is_primary=True, max_length=128),
            FieldSchema(name="paper_id", dtype=DataType.VARCHAR, max_length=64),
            FieldSchema(name="user_id", dtype=DataType.VARCHAR, max_length=64),
            FieldSchema(name="level", dtype=DataType.INT64),
            FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=4096),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=1024),
            FieldSchema(name="cluster_label", dtype=DataType.INT64),
        ]
        schema = CollectionSchema(fields, description="RAPTOR tree nodes for multi-granularity retrieval")
        col = Collection(self._collection_name, schema=schema, using=self._milvus_alias)

        # Create index for vector search
        col.create_index(
            field_name="embedding",
            index_params={
                "index_type": "IVF_FLAT",
                "metric_type": "COSINE",
                "params": {"nlist": 128},
            },
        )
        col.load()
        logger.info("RAPTOR tree collection created", collection=self._collection_name)

    def insert_nodes(self, nodes: list[TreeNode]) -> int:
        """Insert tree nodes into the Milvus collection.

        Returns:
            Number of nodes inserted.
        """
        if not nodes:
            return 0

        self.ensure_collection()
        from pymilvus import Collection

        col = Collection(self._collection_name, using=self._milvus_alias)

        data = [
            [n.node_id for n in nodes],
            [n.paper_id for n in nodes],
            [n.user_id for n in nodes],
            [n.level for n in nodes],
            [n.text[:4096] for n in nodes],
            [n.embedding for n in nodes],
            [n.cluster_label for n in nodes],
        ]

        col.insert(data)
        col.flush()
        logger.info("RAPTOR nodes inserted", count=len(nodes))
        return len(nodes)

    def search(
        self,
        *,
        query_embedding: list[float],
        user_id: str,
        paper_ids: list[str] | None = None,
        top_k: int = 10,
        level: int | None = None,
    ) -> list[dict[str, Any]]:
        """Search for similar RAPTOR nodes.

        Args:
            query_embedding: The query vector
            user_id: User ID for isolation
            paper_ids: Optional paper ID filter
            top_k: Maximum results
            level: Optional level filter

        Returns:
            List of matching node dicts
        """
        # Validate inputs to prevent Milvus filter injection (before any Milvus calls)
        safe_user_id = validate_user_id(user_id)
        safe_paper_ids = [validate_paper_id(pid) for pid in paper_ids if pid] if paper_ids else []

        self.ensure_collection()
        from pymilvus import Collection

        col = Collection(self._collection_name, using=self._milvus_alias)
        col.load()

        # Build filter expression with validated inputs
        parts = [f'user_id == "{safe_user_id}"']
        if safe_paper_ids:
            quoted = ", ".join(f'"{pid}"' for pid in safe_paper_ids)
            if quoted:
                parts.append(f"paper_id in [{quoted}]")
        if level is not None:
            parts.append(f"level == {level}")

        expr = " && ".join(parts)

        results = col.search(
            data=[query_embedding],
            anns_field="embedding",
            param={"metric_type": "COSINE", "params": {"nprobe": 10}},
            limit=top_k,
            expr=expr,
            output_fields=["node_id", "paper_id", "user_id", "level", "text", "cluster_label"],
        )

        hits = []
        for batch in results:
            for hit in batch:
                entity = hit.entity
                hits.append({
                    "node_id": entity.get("node_id", ""),
                    "paper_id": entity.get("paper_id", ""),
                    "user_id": entity.get("user_id", ""),
                    "level": entity.get("level", 0),
                    "text": entity.get("text", ""),
                    "cluster_label": entity.get("cluster_label", -1),
                    "score": float(1 - hit.distance),
                })
        return hits

    def delete_by_paper(self, paper_id: str, user_id: str) -> int:
        """Delete all nodes for a specific paper.

        Returns:
            Number of nodes deleted.
        """
        # Validate inputs to prevent Milvus filter injection
        safe_paper_id = validate_paper_id(paper_id)
        safe_user_id = validate_user_id(user_id)

        self.ensure_collection()
        from pymilvus import Collection

        col = Collection(self._collection_name, using=self._milvus_alias)
        expr = f'paper_id == "{safe_paper_id}" && user_id == "{safe_user_id}"'
        col.delete(expr)
        col.flush()
        return 0
