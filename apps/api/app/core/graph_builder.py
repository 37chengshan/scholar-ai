"""Graph builder service for constructing knowledge graphs from extracted entities.

Provides:
- Orchestration of entity node creation
- Relationship building between papers, methods, datasets, metrics, venues
- Citation network construction
- Coauthor relationship building
"""

from typing import Dict, List, Optional

from app.core.neo4j_service import Neo4jService
from app.core.entity_extractor import EntityAligner
from app.utils.logger import logger


class GraphBuilder:
    """Build knowledge graph from extracted entities."""

    def __init__(
        self,
        neo4j_service: Optional[Neo4jService] = None,
        entity_aligner: Optional[EntityAligner] = None
    ):
        """
        Initialize graph builder.

        Args:
            neo4j_service: Neo4jService instance for database operations
            entity_aligner: EntityAligner instance for entity deduplication
        """
        self.neo4j = neo4j_service or Neo4jService()
        self.aligner = entity_aligner or EntityAligner(self.neo4j)

    async def build_paper_entities(
        self,
        paper_id: str,
        entities: Dict[str, List[Dict]]
    ) -> Dict[str, int]:
        """Create all entity nodes and relationships for a paper.

        Args:
            paper_id: Paper UUID
            entities: Dict with methods, datasets, metrics, venues lists

        Returns:
            Dict with counts of created nodes/relationships
        """
        counts = {"methods": 0, "datasets": 0, "metrics": 0, "venues": 0}

        # Build method relationships
        for method in entities.get("methods", []):
            await self._build_method_relationship(paper_id, method)
            counts["methods"] += 1

        # Build dataset relationships
        for dataset in entities.get("datasets", []):
            await self._build_dataset_relationship(paper_id, dataset)
            counts["datasets"] += 1

        # Build venue relationship
        for venue in entities.get("venues", []):
            await self._build_venue_relationship(paper_id, venue)
            counts["venues"] += 1

        logger.info("Built paper entity graph",
                   paper_id=paper_id, **counts)
        return counts

    async def _build_method_relationship(
        self,
        paper_id: str,
        method: Dict
    ) -> None:
        """Create Method node and USES relationship."""
        name = method["name"]
        context = method.get("context", "")

        # Use aligner to check for existing entity
        existing_id = await self.aligner.align_entity(name, "Method")

        if existing_id:
            method_id = existing_id
        else:
            # Create new method node
            method_id = await self.neo4j.create_method_node(
                name=name,
                category=method.get("category")
            )

        # Create USES relationship
        await self.neo4j.create_uses_relationship(
            paper_id=paper_id,
            method_canonical=method_id,
            confidence=method.get("confidence", 0.9),
            context=context[:500] if context else None
        )

    async def _build_dataset_relationship(
        self,
        paper_id: str,
        dataset: Dict
    ) -> None:
        """Create Dataset node and relationships to methods."""
        name = dataset["name"]
        context = dataset.get("context", "")

        # Check alignment
        existing_id = await self.aligner.align_entity(name, "Dataset")

        if existing_id:
            dataset_id = existing_id
        else:
            dataset_id = await self.neo4j.create_dataset_node(
                name=name,
                domain=dataset.get("domain")
            )

        # Note: EVALUATED_ON relationship is between Method and Dataset
        # This requires knowing which method was evaluated on this dataset
        # For now, we just create the dataset node
        # Full implementation would link to specific methods mentioned in context

    async def _build_venue_relationship(
        self,
        paper_id: str,
        venue: Dict
    ) -> None:
        """Create Venue node and PUBLISHED_IN relationship."""
        name = venue["name"]
        venue_type = venue.get("type", "conference")

        existing_id = await self.aligner.align_entity(name, "Venue")

        if existing_id:
            venue_id = existing_id
        else:
            venue_id = await self.neo4j.create_venue_node(
                name=name,
                venue_type=venue_type,
                abbreviation=venue.get("abbreviation")
            )

        await self.neo4j.create_published_in_relationship(
            paper_id=paper_id,
            venue_canonical=venue_id
        )

    async def build_coauthor_relationships(
        self,
        authors: List[str],
        paper_id: Optional[str] = None
    ) -> int:
        """Create COAUTHOR relationships between all author pairs.

        Args:
            authors: List of author names
            paper_id: Optional paper ID for context

        Returns:
            Number of relationships created
        """
        count = 0
        for i, author1 in enumerate(authors):
            for author2 in authors[i+1:]:
                await self.neo4j.create_coauthor_relationship(
                    author1=author1,
                    author2=author2,
                    paper_id=paper_id
                )
                count += 1
        return count

    async def build_citation_network(
        self,
        paper_id: str,
        references: List[Dict]
    ) -> int:
        """Create CITES relationships from paper to its references.

        Args:
            paper_id: Source paper UUID
            references: List of reference dicts with paper_id, context

        Returns:
            Number of citation relationships created
        """
        count = 0
        for ref in references:
            target_id = ref.get("paper_id")
            if target_id:
                await self.neo4j.create_citation_relationship(
                    from_paper_id=paper_id,
                    to_paper_id=target_id,
                    context=ref.get("context", "")[:500]
                )
                count += 1
        return count

    async def close(self):
        """Close Neo4j connection."""
        await self.neo4j.close()
        await self.aligner.close()
