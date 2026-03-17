"""Neo4j service for graph database operations.

Provides:
- Paper node creation with metadata
- Chunk nodes with BELONGS_TO relationships
- Author nodes with WROTE relationships
- Section nodes for IMRaD structure
- Graph traversal for paper chunks
"""

import os
from typing import Any, Dict, List, Optional

from app.utils.logger import logger


class Neo4jService:
    """Service for Neo4j graph database operations."""

    def __init__(self, uri: Optional[str] = None, user: Optional[str] = None, password: Optional[str] = None):
        """
        Initialize Neo4j service.

        Args:
            uri: Neo4j URI (defaults to NEO4J_URI env var)
            user: Neo4j username (defaults to NEO4J_USER env var)
            password: Neo4j password (defaults to NEO4J_PASSWORD env var)
        """
        self.uri = uri or os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.user = user or os.getenv("NEO4J_USER", "neo4j")
        self.password = password or os.getenv("NEO4J_PASSWORD", "password")
        self._driver = None

    @property
    def driver(self):
        """Lazy load Neo4j driver."""
        if self._driver is None:
            try:
                from neo4j import AsyncGraphDatabase
                self._driver = AsyncGraphDatabase.driver(
                    self.uri,
                    auth=(self.user, self.password)
                )
                logger.info("Neo4j driver initialized", uri=self.uri)
            except Exception as e:
                logger.error("Failed to initialize Neo4j driver", error=str(e))
                raise
        return self._driver

    async def close(self):
        """Close Neo4j driver connection."""
        if self._driver:
            await self._driver.close()
            self._driver = None
            logger.info("Neo4j driver closed")

    async def create_paper_node(
        self,
        paper_id: str,
        title: str,
        authors: Optional[List[str]] = None,
        year: Optional[int] = None,
        doi: Optional[str] = None
    ) -> None:
        """
        Create Paper node in Neo4j.

        Args:
            paper_id: Paper UUID
            title: Paper title
            authors: List of author names
            year: Publication year
            doi: DOI identifier
        """
        async with self.driver.session() as session:
            # Create paper node
            await session.run(
                """MERGE (p:Paper {id: $paper_id})
                   SET p.title = $title,
                       p.year = $year,
                       p.doi = $doi,
                       p.created_at = datetime()""",
                paper_id=paper_id,
                title=title,
                year=year,
                doi=doi
            )

            # Create author nodes and relationships
            if authors:
                for author in authors[:10]:  # Limit to 10 authors
                    await session.run(
                        """MERGE (a:Author {name: $author})
                           WITH a
                           MATCH (p:Paper {id: $paper_id})
                           MERGE (a)-[:WROTE]->(p)""",
                        author=author,
                        paper_id=paper_id
                    )

            logger.info(
                "Created paper node in Neo4j",
                paper_id=paper_id,
                title=title[:50],
                author_count=len(authors) if authors else 0
            )

    async def create_chunk_nodes(
        self,
        paper_id: str,
        chunks: List[Dict[str, Any]]
    ) -> None:
        """
        Create Chunk nodes with BELONGS_TO relationships.

        Args:
            paper_id: Paper UUID
            chunks: List of chunk dictionaries with id, text, section, page
        """
        async with self.driver.session() as session:
            chunk_count = 0
            prev_chunk_id = None

            for chunk in chunks:
                chunk_id = chunk.get("id")
                if not chunk_id:
                    continue

                # Create chunk node with BELONGS_TO relationship
                await session.run(
                    """MATCH (p:Paper {id: $paper_id})
                       CREATE (c:Chunk {
                           id: $chunk_id,
                           content: $content,
                           section: $section,
                           page: $page,
                           created_at: datetime()
                       })-[:BELONGS_TO]->(p)""",
                    paper_id=paper_id,
                    chunk_id=chunk_id,
                    content=chunk.get("text", "")[:1000],  # Summary only
                    section=chunk.get("section"),
                    page=chunk.get("page_start")
                )

                # Create NEXT_CHUNK relationship for ordering
                if prev_chunk_id:
                    await session.run(
                        """MATCH (c1:Chunk {id: $prev_id})
                           MATCH (c2:Chunk {id: $curr_id})
                           MERGE (c1)-[:NEXT_CHUNK]->(c2)""",
                        prev_id=prev_chunk_id,
                        curr_id=chunk_id
                    )

                prev_chunk_id = chunk_id
                chunk_count += 1

            logger.info(
                "Created chunk nodes in Neo4j",
                paper_id=paper_id,
                chunk_count=chunk_count
            )

    async def create_section_nodes(
        self,
        paper_id: str,
        imrad_structure: Dict[str, Any]
    ) -> None:
        """
        Create Section nodes for IMRaD structure.

        Args:
            paper_id: Paper UUID
            imrad_structure: Dictionary with IMRaD sections
        """
        async with self.driver.session() as session:
            section_count = 0

            for section_name, section_data in imrad_structure.items():
                # Skip metadata keys
                if section_name.startswith("_"):
                    continue

                content = section_data.get("content", "") if isinstance(section_data, dict) else ""
                page_start = section_data.get("page_start") if isinstance(section_data, dict) else None
                page_end = section_data.get("page_end") if isinstance(section_data, dict) else None

                if not content or len(content) < 10:
                    continue

                await session.run(
                    """MATCH (p:Paper {id: $paper_id})
                       MERGE (s:Section {name: $section_name, paper_id: $paper_id})
                       SET s.content_summary = $summary,
                           s.page_start = $page_start,
                           s.page_end = $page_end,
                           s.updated_at = datetime()
                       MERGE (s)-[:PART_OF]->(p)""",
                    paper_id=paper_id,
                    section_name=section_name.capitalize(),
                    summary=content[:500],
                    page_start=page_start,
                    page_end=page_end
                )

                section_count += 1

            logger.info(
                "Created section nodes in Neo4j",
                paper_id=paper_id,
                section_count=section_count
            )

    async def create_citation_relationship(
        self,
        from_paper_id: str,
        to_paper_id: str,
        context: Optional[str] = None
    ) -> None:
        """
        Create CITES relationship between papers.

        Args:
            from_paper_id: Source paper UUID
            to_paper_id: Target paper UUID
            context: Optional citation context
        """
        async with self.driver.session() as session:
            await session.run(
                """MATCH (p1:Paper {id: $from_id})
                   MATCH (p2:Paper {id: $to_id})
                   MERGE (p1)-[r:CITES]->(p2)
                   SET r.context = $context,
                       r.created_at = datetime()""",
                from_id=from_paper_id,
                to_id=to_paper_id,
                context=context
            )

            logger.info(
                "Created citation relationship",
                from_paper=from_paper_id,
                to_paper=to_paper_id
            )

    async def get_paper_chunks(
        self,
        paper_id: str,
        section: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve chunks for a paper via graph traversal.

        Args:
            paper_id: Paper UUID
            section: Optional section filter

        Returns:
            List of chunk dictionaries
        """
        async with self.driver.session() as session:
            if section:
                result = await session.run(
                    """MATCH (c:Chunk)-[:BELONGS_TO]->(p:Paper {id: $paper_id})
                       WHERE c.section = $section
                       RETURN c.id as id, c.content as content,
                              c.section as section, c.page as page
                       ORDER BY c.page""",
                    paper_id=paper_id,
                    section=section
                )
            else:
                result = await session.run(
                    """MATCH (c:Chunk)-[:BELONGS_TO]->(p:Paper {id: $paper_id})
                       RETURN c.id as id, c.content as content,
                              c.section as section, c.page as page
                       ORDER BY c.page""",
                    paper_id=paper_id
                )

            records = await result.data()
            return [dict(record) for record in records]

    async def get_paper_with_chunks(
        self,
        paper_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get paper with all related chunks and sections.

        Args:
            paper_id: Paper UUID

        Returns:
            Dictionary with paper, chunks, and sections
        """
        async with self.driver.session() as session:
            # Get paper
            paper_result = await session.run(
                """MATCH (p:Paper {id: $paper_id})
                   RETURN p.id as id, p.title as title,
                          p.year as year, p.doi as doi""",
                paper_id=paper_id
            )
            paper_data = await paper_result.single()

            if not paper_data:
                return None

            # Get chunks
            chunks_result = await session.run(
                """MATCH (c:Chunk)-[:BELONGS_TO]->(p:Paper {id: $paper_id})
                   RETURN c.id as id, c.content as content,
                          c.section as section, c.page as page
                   ORDER BY c.page""",
                paper_id=paper_id
            )
            chunks = await chunks_result.data()

            # Get sections
            sections_result = await session.run(
                """MATCH (s:Section)-[:PART_OF]->(p:Paper {id: $paper_id})
                   RETURN s.name as name, s.content_summary as summary,
                          s.page_start as page_start, s.page_end as page_end""",
                paper_id=paper_id
            )
            sections = await sections_result.data()

            # Get authors
            authors_result = await session.run(
                """MATCH (a:Author)-[:WROTE]->(p:Paper {id: $paper_id})
                   RETURN a.name as name""",
                paper_id=paper_id
            )
            authors = [r["name"] for r in await authors_result.data()]

            return {
                "paper": dict(paper_data),
                "authors": authors,
                "chunks": [dict(c) for c in chunks],
                "sections": [dict(s) for s in sections],
            }

    async def delete_paper_graph(self, paper_id: str) -> bool:
        """
        Delete all nodes and relationships for a paper.

        Args:
            paper_id: Paper UUID

        Returns:
            True if deleted, False if not found
        """
        async with self.driver.session() as session:
            # Delete chunks, sections, and relationships
            await session.run(
                """MATCH (c:Chunk)-[:BELONGS_TO]->(p:Paper {id: $paper_id})
                   DETACH DELETE c""",
                paper_id=paper_id
            )

            await session.run(
                """MATCH (s:Section)-[:PART_OF]->(p:Paper {id: $paper_id})
                   DETACH DELETE s""",
                paper_id=paper_id
            )

            # Delete paper (authors remain as they may be linked to other papers)
            result = await session.run(
                """MATCH (p:Paper {id: $paper_id})
                   OPTIONAL MATCH (p)-[r]-()
                   DELETE r, p
                   RETURN count(p) as deleted""",
                paper_id=paper_id
            )

            record = await result.single()
            deleted_count = record["deleted"] if record else 0

            logger.info(
                "Deleted paper graph from Neo4j",
                paper_id=paper_id,
                deleted=deleted_count
            )

            return deleted_count > 0

    async def search_by_title(
        self,
        title_query: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search papers by title.

        Args:
            title_query: Title search string
            limit: Maximum results

        Returns:
            List of matching papers
        """
        async with self.driver.session() as session:
            result = await session.run(
                """MATCH (p:Paper)
                   WHERE p.title CONTAINS $query
                   RETURN p.id as id, p.title as title,
                          p.year as year, p.doi as doi
                   LIMIT $limit""",
                query=title_query,
                limit=limit
            )

            records = await result.data()
            return [dict(record) for record in records]

    # Entity Node Methods

    async def create_method_node(self, name: str, category: Optional[str] = None) -> str:
        """Create or merge Method node, return node ID."""
        canonical = name.lower().strip()
        async with self.driver.session() as session:
            result = await session.run("""
                MERGE (m:Method {canonical_name: $canonical})
                SET m.name = $name,
                    m.category = $category,
                    m.updated_at = datetime()
                RETURN m.canonical_name as id
            """, canonical=canonical, name=name, category=category)
            record = await result.single()
            return record["id"] if record else canonical

    async def create_dataset_node(self, name: str, domain: Optional[str] = None) -> str:
        """Create or merge Dataset node, return node ID."""
        canonical = name.lower().strip()
        async with self.driver.session() as session:
            result = await session.run("""
                MERGE (d:Dataset {canonical_name: $canonical})
                SET d.name = $name,
                    d.domain = $domain,
                    d.updated_at = datetime()
                RETURN d.canonical_name as id
            """, canonical=canonical, name=name, domain=domain)
            record = await result.single()
            return record["id"] if record else canonical

    async def create_metric_node(self, name: str, description: Optional[str] = None) -> str:
        """Create or merge Metric node, return node ID."""
        canonical = name.lower().strip()
        async with self.driver.session() as session:
            result = await session.run("""
                MERGE (m:Metric {canonical_name: $canonical})
                SET m.name = $name,
                    m.description = $description,
                    m.updated_at = datetime()
                RETURN m.canonical_name as id
            """, canonical=canonical, name=name, description=description)
            record = await result.single()
            return record["id"] if record else canonical

    async def create_venue_node(
        self,
        name: str,
        venue_type: Optional[str] = None,
        abbreviation: Optional[str] = None
    ) -> str:
        """Create or merge Venue node, return node ID."""
        canonical = name.lower().strip()
        async with self.driver.session() as session:
            result = await session.run("""
                MERGE (v:Venue {canonical_name: $canonical})
                SET v.name = $name,
                    v.type = $venue_type,
                    v.abbreviation = $abbreviation,
                    v.updated_at = datetime()
                RETURN v.canonical_name as id
            """, canonical=canonical, name=name, venue_type=venue_type,
                abbreviation=abbreviation)
            record = await result.single()
            return record["id"] if record else canonical

    # Relationship Methods

    async def create_uses_relationship(
        self,
        paper_id: str,
        method_canonical: str,
        confidence: float = 0.9,
        context: Optional[str] = None
    ) -> None:
        """Create USES relationship from Paper to Method."""
        async with self.driver.session() as session:
            await session.run("""
                MATCH (p:Paper {id: $paper_id})
                MATCH (m:Method {canonical_name: $method_canonical})
                MERGE (p)-[r:USES]->(m)
                SET r.confidence = $confidence,
                    r.context = $context,
                    r.updated_at = datetime()
            """, paper_id=paper_id, method_canonical=method_canonical,
                confidence=confidence, context=context)

    async def create_evaluated_on_relationship(
        self,
        method_canonical: str,
        dataset_canonical: str,
        confidence: float = 0.9
    ) -> None:
        """Create EVALUATED_ON relationship from Method to Dataset."""
        async with self.driver.session() as session:
            await session.run("""
                MATCH (m:Method {canonical_name: $method_canonical})
                MATCH (d:Dataset {canonical_name: $dataset_canonical})
                MERGE (m)-[r:EVALUATED_ON]->(d)
                SET r.confidence = $confidence,
                    r.updated_at = datetime()
            """, method_canonical=method_canonical, dataset_canonical=dataset_canonical,
                confidence=confidence)

    async def create_published_in_relationship(
        self,
        paper_id: str,
        venue_canonical: str
    ) -> None:
        """Create PUBLISHED_IN relationship from Paper to Venue."""
        async with self.driver.session() as session:
            await session.run("""
                MATCH (p:Paper {id: $paper_id})
                MATCH (v:Venue {canonical_name: $venue_canonical})
                MERGE (p)-[r:PUBLISHED_IN]->(v)
                SET r.updated_at = datetime()
            """, paper_id=paper_id, venue_canonical=venue_canonical)

    async def create_coauthor_relationship(
        self,
        author1: str,
        author2: str,
        paper_id: Optional[str] = None
    ) -> None:
        """Create/Update COAUTHOR relationship between authors."""
        async with self.driver.session() as session:
            await session.run("""
                MATCH (a1:Author {name: $author1})
                MATCH (a2:Author {name: $author2})
                MERGE (a1)-[r:COAUTHOR]-(a2)
                SET r.count = coalesce(r.count, 0) + 1,
                    r.updated_at = datetime()
            """, author1=author1, author2=author2)


# Convenience functions
async def create_paper_graph(
    paper_id: str,
    title: str,
    authors: List[str],
    chunks: List[Dict[str, Any]],
    imrad_structure: Dict[str, Any],
    year: Optional[int] = None
) -> None:
    """
    Create complete paper graph in Neo4j.

    Args:
        paper_id: Paper UUID
        title: Paper title
        authors: List of author names
        chunks: List of chunk dictionaries
        imrad_structure: IMRaD section structure
        year: Publication year
    """
    service = Neo4jService()
    try:
        await service.create_paper_node(paper_id, title, authors, year)
        await service.create_chunk_nodes(paper_id, chunks)
        await service.create_section_nodes(paper_id, imrad_structure)
    finally:
        await service.close()
