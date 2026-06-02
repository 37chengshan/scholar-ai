"""Community detection for knowledge graphs.

Detects communities in Neo4j graphs using:
- Primary: GDS Louvain algorithm
- Fallback: Cypher native connected components
"""

from __future__ import annotations

from typing import Any

import structlog

from app.core.neo4j_service import Neo4jService

logger = structlog.get_logger()


class CommunityDetector:
    """Detects communities in the Neo4j knowledge graph."""

    def __init__(self, neo4j_service: Neo4jService | None = None):
        self.neo4j = neo4j_service or Neo4jService()

    async def detect_communities(
        self,
        *,
        user_id: str,
        paper_ids: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Detect communities in the knowledge graph.

        Args:
            user_id: User ID for isolation
            paper_ids: Optional paper ID filter

        Returns:
            List of community dicts with entity memberships
        """
        # Try GDS Louvain first
        communities = await self._louvain_detection(user_id=user_id, paper_ids=paper_ids)
        if communities:
            return communities

        # Fallback to connected components
        logger.info("GDS unavailable, falling back to connected components")
        return await self._connected_components_detection(user_id=user_id, paper_ids=paper_ids)

    async def _louvain_detection(
        self,
        *,
        user_id: str,
        paper_ids: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Detect communities using GDS Louvain algorithm."""
        try:
            async with self.neo4j.driver.session() as session:
                # Check if GDS is available
                check_result = await session.run(
                    "CALL gds.list() YIELD name RETURN name LIMIT 1"
                )
                check_record = await check_result.single()
                if not check_record:
                    return []

                # Build paper filter
                paper_filter = ""
                if paper_ids:
                    paper_filter = "WHERE p.paper_id IN $paper_ids"

                # Project graph and run Louvain
                query = f"""
                MATCH (n)-[r]-(m)
                WHERE n.user_id = $user_id AND m.user_id = $user_id
                {paper_filter}
                WITH gds.graph.project('communities', n, m) AS g
                CALL gds.louvain.stream(g)
                YIELD nodeId, communityId
                WITH gds.util.asNode(nodeId) AS node, communityId
                RETURN
                    node.id AS entity_id,
                    node.name AS entity_name,
                    labels(node)[0] AS entity_type,
                    communityId AS community_id
                ORDER BY communityId
                """

                result = await session.run(
                    query,
                    user_id=user_id,
                    paper_ids=paper_ids or [],
                )
                records = await result.data()

                # Group by community
                communities: dict[int, list[dict[str, Any]]] = {}
                for record in records:
                    cid = record["community_id"]
                    communities.setdefault(cid, []).append({
                        "entity_id": record["entity_id"],
                        "entity_name": record["entity_name"],
                        "entity_type": record["entity_type"],
                    })

                # Clean up projection
                try:
                    await session.run("CALL gds.graph.drop('communities')")
                except Exception:
                    pass

                return [
                    {"community_id": cid, "entities": entities}
                    for cid, entities in communities.items()
                ]

        except Exception as exc:
            logger.debug("Louvain detection failed", error=str(exc))
            return []

    async def _connected_components_detection(
        self,
        *,
        user_id: str,
        paper_ids: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Detect communities using Cypher connected components."""
        try:
            async with self.neo4j.driver.session() as session:
                paper_filter = ""
                if paper_ids:
                    paper_filter = "AND p.paper_id IN $paper_ids"

                # Simple connected components via path finding
                query = f"""
                MATCH (n)-[r]-(m)
                WHERE n.user_id = $user_id AND m.user_id = $user_id
                {paper_filter}
                WITH n, collect(DISTINCT m) AS neighbors
                RETURN
                    n.id AS entity_id,
                    n.name AS entity_name,
                    labels(n)[0] AS entity_type,
                    [neigh IN neighbors | neigh.id] AS neighbor_ids
                """

                result = await session.run(
                    query,
                    user_id=user_id,
                    paper_ids=paper_ids or [],
                )
                records = await result.data()

                # Build adjacency and find components
                parent: dict[str, str] = {}

                def find(x: str) -> str:
                    while parent.get(x, x) != x:
                        parent[x] = parent.get(parent[x], parent[x])
                        x = parent[x]
                    return x

                def union(x: str, y: str) -> None:
                    px, py = find(x), find(y)
                    if px != py:
                        parent[px] = py

                entities = {}
                for record in records:
                    eid = record["entity_id"]
                    entities[eid] = {
                        "entity_id": eid,
                        "entity_name": record["entity_name"],
                        "entity_type": record["entity_type"],
                    }
                    for nid in (record.get("neighbor_ids") or []):
                        if nid:
                            union(eid, nid)

                # Group by component
                components: dict[str, list[dict[str, Any]]] = {}
                for eid in entities:
                    root = find(eid)
                    components.setdefault(root, []).append(entities[eid])

                return [
                    {"community_id": i, "entities": members}
                    for i, members in enumerate(components.values())
                ]

        except Exception as exc:
            logger.warning("Connected components detection failed", error=str(exc))
            return []

    async def close(self):
        """Close Neo4j connection."""
        await self.neo4j.close()


_community_detector: CommunityDetector | None = None


def get_community_detector() -> CommunityDetector:
    """Get or create community detector singleton."""
    global _community_detector
    if _community_detector is None:
        _community_detector = CommunityDetector()
    return _community_detector
