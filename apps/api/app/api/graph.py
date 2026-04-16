"""Graph query API endpoints for knowledge graph visualization.

Provides REST endpoints for:
- /api/graph/nodes - Get graph nodes for G6 visualization
- /api/graph/neighbors/{node_id} - Get node neighbors for layered loading
- /api/graph/subgraph - Get focused subgraph for specific papers
- /api/graph/pagerank - Get Top-N papers by PageRank score
- /api/entities/extract - Extract entities from text
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from app.core.neo4j_service import Neo4jService
from app.core.pagerank_service import PageRankService
from app.utils.logger import logger
from app.utils.problem_detail import Errors

router = APIRouter()


# Response models
class GraphNode(BaseModel):
    """Graph node for G6 visualization."""
    id: Optional[str] = None
    name: str
    type: str
    pagerank: Optional[float] = None


class GraphEdge(BaseModel):
    """Graph edge for G6 visualization."""
    source: str
    target: str
    type: str
    properties: Optional[dict] = None


class GraphDataResponse(BaseModel):
    """Response with nodes and edges for graph visualization."""
    nodes: List[GraphNode]
    edges: List[GraphEdge]


class NodeNeighborsResponse(BaseModel):
    """Response with neighbors of a node."""
    nodes: List[GraphNode]
    edges: List[GraphEdge]


class PageRankResponse(BaseModel):
    """Response with top papers by PageRank."""
    papers: List[dict]
    total: int


@router.get("/nodes", response_model=GraphDataResponse)
async def get_graph_nodes(
    node_type: Optional[str] = Query(None, description="Filter by node type: Paper, Method, Dataset, Metric, Venue, Author"),
    limit: int = Query(100, ge=1, le=500, description="Maximum nodes to return"),
    min_pagerank: Optional[float] = Query(None, ge=0, description="Minimum PageRank score for Paper nodes"),
    search: Optional[str] = Query(None, description="Search nodes by name"),
    offset: int = Query(0, ge=0, description="Offset for pagination")
):
    """Get graph nodes for visualization.

    Returns nodes with their PageRank scores for G6 rendering.
    Use min_pagerank to get influential papers for initial view.
    """
    neo4j = Neo4jService()
    try:
        async with neo4j.driver.session() as session:
            # Build query based on filters
            where_clauses = []
            params: dict = {"limit": limit, "offset": offset}

            if node_type:
                where_clauses.append(f"labels(n)[0] = '{node_type}'")

            if min_pagerank is not None:
                where_clauses.append("n.global_pagerank >= $min_pagerank")
                params["min_pagerank"] = min_pagerank

            if search:
                where_clauses.append("(coalesce(n.title, n.name) CONTAINS $search)")
                params["search"] = search

            where_str = " WHERE " + " AND ".join(where_clauses) if where_clauses else ""

            # Query for multiple node types
            query = f"""
                MATCH (n)
                {where_str}
                RETURN coalesce(n.id, elementId(n)) as id,
                       coalesce(n.title, n.name) as name,
                       labels(n)[0] as type,
                       n.global_pagerank as pagerank
                ORDER BY coalesce(n.global_pagerank, 0) DESC
                SKIP $offset
                LIMIT $limit
            """

            result = await session.run(query, **params)
            nodes_data = await result.data()

            # Get edges between returned nodes
            node_ids = [n["id"] for n in nodes_data if n["id"]]
            edges_query = """
                MATCH (a)-[r]->(b)
                WHERE (coalesce(a.id, elementId(a)) IN $node_ids)
                  AND (coalesce(b.id, elementId(b)) IN $node_ids)
                RETURN coalesce(a.id, elementId(a)) as source,
                       coalesce(b.id, elementId(b)) as target,
                       type(r) as type, properties(r) as properties
                LIMIT 500
            """
            edges_result = await session.run(edges_query, node_ids=node_ids)
            edges_data = await edges_result.data()

            return {
                "nodes": [
                    {
                        "id": n["id"],
                        "name": n["name"] or "Unnamed",
                        "type": n["type"],
                        "pagerank": n["pagerank"]
                    }
                    for n in nodes_data
                ],
                "edges": [
                    {
                        "source": e["source"],
                        "target": e["target"],
                        "type": e["type"],
                        "properties": e.get("properties", {})
                    }
                    for e in edges_data
                ]
            }
    except Exception as e:
        logger.error("Failed to get graph nodes", error=str(e))
        raise HTTPException(status_code=500, detail=Errors.internal(f"Graph query failed: {str(e)}"))
    finally:
        await neo4j.close()


@router.get("/neighbors/{node_id}", response_model=NodeNeighborsResponse)
async def get_node_neighbors(
        node_id: str,
        hops: int = Query(1, ge=1, le=2, description="Number of hops from node"),
        limit: int = Query(50, ge=1, le=200),
        relationship_type: Optional[str] = Query(None, description="Filter by relationship type")
    ):
    """Get neighbors of a node for layered graph expansion.

    Used by G6 when user clicks a node to expand its neighbors.
    """
    neo4j = Neo4jService()
    try:
        async with neo4j.driver.session() as session:
            # Find center node first
            center_result = await session.run(
                "MATCH (n) WHERE coalesce(n.id, elementId(n)) = $node_id RETURN labels(n)[0] as type, coalesce(n.title, n.name) as name",
                node_id=node_id
            )
            center_record = await center_result.single()

            if not center_record:
                raise HTTPException(status_code=404, detail=Errors.not_found("Node not found"))

            # Query neighbors with variable hops
            path_query = f"""
                MATCH path = (center)-[:*1..{hops}]-(neighbor)
                WHERE coalesce(center.id, elementId(center)) = $node_id
                  AND coalesce(neighbor.id, elementId(neighbor)) <> $node_id
                RETURN DISTINCT coalesce(neighbor.id, elementId(neighbor)) as id,
                       coalesce(neighbor.title, neighbor.name) as name,
                       labels(neighbor)[0] as type,
                       neighbor.global_pagerank as pagerank,
                       length(path) as distance
                ORDER BY distance, coalesce(neighbor.global_pagerank, 0) DESC
                LIMIT $limit
            """

            result = await session.run(
                path_query,
                node_id=node_id,
                limit=limit
            )
            nodes_data = await result.data()

            # Get edges connecting center to these neighbors
            neighbor_ids = [n["id"] for n in nodes_data]

            if relationship_type:
                edges_query = f"""
                    MATCH (center)-[r:{relationship_type}]-(n)
                    WHERE coalesce(center.id, elementId(center)) = $center_id
                      AND coalesce(n.id, elementId(n)) IN $neighbor_ids
                    RETURN coalesce(center.id, elementId(center)) as source,
                           coalesce(n.id, elementId(n)) as target,
                           type(r) as type, properties(r) as properties
                """
            else:
                edges_query = """
                    MATCH (center)-[r]-(n)
                    WHERE coalesce(center.id, elementId(center)) = $center_id
                      AND coalesce(n.id, elementId(n)) IN $neighbor_ids
                    RETURN coalesce(center.id, elementId(center)) as source,
                           coalesce(n.id, elementId(n)) as target,
                           type(r) as type, properties(r) as properties
                """

            edges_result = await session.run(
                edges_query,
                center_id=node_id,
                neighbor_ids=neighbor_ids
            )
            edges_data = await edges_result.data()

            return {
                "nodes": [
                    {
                        "id": n["id"],
                        "name": n["name"] or "Unnamed",
                        "type": n["type"],
                        "pagerank": n["pagerank"]
                    }
                    for n in nodes_data
                ],
                "edges": [
                    {
                        "source": e["source"],
                        "target": e["target"],
                        "type": e["type"],
                        "properties": e.get("properties", {})
                    }
                    for e in edges_data
                ]
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get node neighbors", node_id=node_id, error=str(e))
        raise HTTPException(status_code=500, detail=Errors.internal(f"Neighbor query failed: {str(e)}"))
    finally:
        await neo4j.close()


@router.get("/subgraph", response_model=GraphDataResponse)
async def get_subgraph(
    paper_ids: str = Query(..., description="Comma-separated list of paper IDs"),
    depth: int = Query(1, ge=0, le=2, description="Depth of relationships to include")
):
    """Get focused subgraph for specific papers.

    Returns subgraph containing specified papers and their connections.
    """
    if not paper_ids:
        raise HTTPException(status_code=400, detail=Errors.validation("paper_ids parameter is required"))

    paper_id_list = [pid.strip() for pid in paper_ids.split(",")]

    neo4j = Neo4jService()
    try:
        async with neo4j.driver.session() as session:
            # Get the specified papers and their neighbors up to depth
            if depth == 0:
                # Just the papers themselves
                query = """
                    MATCH (p:Paper)
                    WHERE p.id IN $paper_ids
                    RETURN p.id as id,
                           p.title as name,
                           labels(p)[0] as type,
                           p.global_pagerank as pagerank
                """
                result = await session.run(query, paper_ids=paper_id_list)
                nodes_data = await result.data()

                # Get edges between these papers
                edges_query = """
                    MATCH (a:Paper)-[r]->(b:Paper)
                    WHERE a.id IN $paper_ids AND b.id IN $paper_ids
                    RETURN a.id as source, b.id as target,
                           type(r) as type, properties(r) as properties
                """
                edges_result = await session.run(edges_query, paper_ids=paper_id_list)
                edges_data = await edges_result.data()
            else:
                # Papers and their neighbors
                query = f"""
                    MATCH (p:Paper)
                    WHERE p.id IN $paper_ids
                    OPTIONAL MATCH path = (p)-[:*1..{depth}]-(neighbor)
                    WITH p, neighbor
                    RETURN DISTINCT coalesce(neighbor.id, p.id) as id,
                           coalesce(neighbor.title, p.title) as name,
                           coalesce(labels(neighbor)[0], labels(p)[0]) as type,
                           coalesce(neighbor.global_pagerank, p.global_pagerank) as pagerank
                    LIMIT 200
                """
                result = await session.run(query, paper_ids=paper_id_list)
                nodes_data = await result.data()

                node_ids = [n["id"] for n in nodes_data]
                edges_query = """
                    MATCH (a)-[r]->(b)
                    WHERE a.id IN $node_ids AND b.id IN $node_ids
                    RETURN a.id as source, b.id as target,
                           type(r) as type, properties(r) as properties
                    LIMIT 500
                """
                edges_result = await session.run(edges_query, node_ids=node_ids)
                edges_data = await edges_result.data()

            return {
                "nodes": [
                    {
                        "id": n["id"],
                        "name": n["name"] or "Unnamed",
                        "type": n["type"],
                        "pagerank": n["pagerank"]
                    }
                    for n in nodes_data if n["id"]
                ],
                "edges": [
                    {
                        "source": e["source"],
                        "target": e["target"],
                        "type": e["type"],
                        "properties": e.get("properties", {})
                    }
                    for e in edges_data
                ]
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get subgraph", error=str(e))
        raise HTTPException(status_code=500, detail=Errors.internal(f"Subgraph query failed: {str(e)}"))
    finally:
        await neo4j.close()


@router.get("/pagerank", response_model=PageRankResponse)
async def get_pagerank_top(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    recalculate: bool = Query(False, description="Force PageRank recalculation"),
    min_year: Optional[int] = Query(None),
    max_year: Optional[int] = Query(None),
    domain: Optional[str] = Query(None, description="Domain-specific PageRank")
):
    """Get top papers by PageRank score.

    Returns most influential papers based on citation network analysis.
    """
    pagerank = PageRankService()
    try:
        if recalculate:
            # Trigger recalculation
            if domain:
                await pagerank.calculate_domain(domain=domain, limit=limit)
            else:
                await pagerank.calculate_global(limit=limit)

        # Get top papers
        papers = await pagerank.get_top_papers(
            limit=limit,
            min_year=min_year,
            max_year=max_year
        )

        return {
            "papers": papers,
            "total": len(papers)
        }
    except Exception as e:
        logger.error("Failed to get PageRank", error=str(e))
        raise HTTPException(status_code=500, detail=Errors.internal(f"PageRank query failed: {str(e)}"))
    finally:
        await pagerank.close()
