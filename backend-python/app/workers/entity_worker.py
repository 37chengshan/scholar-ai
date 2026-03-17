"""Entity extraction worker.

Async worker for extracting academic entities from papers:
- Runs entity extraction as background task
- Integrates with PDF processing pipeline
- Stores extracted entities for graph building

Usage:
    # Process single paper
    result = await process_entity_extraction(paper_id, paper_text)

    # Run worker loop
    await run_entity_worker()
"""

import asyncio
from typing import Any, Dict, Optional

from app.core.entity_extractor import EntityExtractor
from app.core.graph_builder import GraphBuilder
from app.core.neo4j_service import Neo4jService
from app.utils.logger import logger


async def process_entity_extraction(
    paper_id: str,
    paper_text: str,
    paper_metadata: Optional[Dict] = None,
    extractor: Optional[EntityExtractor] = None,
    graph_builder: Optional[GraphBuilder] = None,
    neo4j: Optional[Neo4jService] = None
) -> Dict[str, Any]:
    """Extract entities from paper and build knowledge graph.

    Args:
        paper_id: UUID of the paper
        paper_text: Full text content for extraction
        paper_metadata: Optional dict with authors, references for relationship building
        extractor: EntityExtractor instance
        graph_builder: GraphBuilder instance
        neo4j: Neo4jService instance

    Returns:
        Dict with extraction results and graph construction status
    """
    extractor = extractor or EntityExtractor()
    neo4j = neo4j or Neo4jService()
    graph_builder = graph_builder or GraphBuilder(neo4j_service=neo4j)

    try:
        # Extract entities
        logger.info("Starting entity extraction", paper_id=paper_id)
        entities = await extractor.extract(paper_text)

        # Build entity graph
        entity_counts = await graph_builder.build_paper_entities(
            paper_id=paper_id,
            entities=entities
        )

        # Build coauthor relationships if authors provided
        coauthor_count = 0
        if paper_metadata and paper_metadata.get("authors"):
            coauthor_count = await graph_builder.build_coauthor_relationships(
                authors=paper_metadata["authors"],
                paper_id=paper_id
            )

        # Build citation network if references provided
        citation_count = 0
        if paper_metadata and paper_metadata.get("references"):
            citation_count = await graph_builder.build_citation_network(
                paper_id=paper_id,
                references=paper_metadata["references"]
            )

        total_entities = sum(entity_counts.values())
        logger.info("Entity extraction and graph building complete",
                   paper_id=paper_id,
                   entities=total_entities,
                   coauthor_relationships=coauthor_count,
                   citation_relationships=citation_count)

        return {
            "status": "success",
            "paper_id": paper_id,
            "entities": entities,
            "entity_counts": entity_counts,
            "coauthor_count": coauthor_count,
            "citation_count": citation_count
        }
    except Exception as e:
        logger.error("Entity extraction failed", paper_id=paper_id, error=str(e))
        return {
            "status": "error",
            "paper_id": paper_id,
            "error": str(e)
        }
    finally:
        await neo4j.close()


async def run_entity_worker():
    """Run entity extraction worker (polls for pending tasks)."""
    logger.info("Entity extraction worker started")
    while True:
        await asyncio.sleep(60)


if __name__ == "__main__":
    asyncio.run(run_entity_worker())
