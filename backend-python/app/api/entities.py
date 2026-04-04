"""Entity extraction and knowledge graph API routes.

Provides:
- POST /api/entities/extract - Extract academic entities from text
- POST /api/entities/{paper_id}/build - Build knowledge graph for a paper
- GET /api/entities/{paper_id}/status - Get entity extraction status
"""

from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.core.entity_extractor import EntityExtractor
from app.core.neo4j_service import Neo4jService
from app.utils.logger import logger
from app.workers.entity_worker import process_entity_extraction
from app.utils.problem_detail import Errors

router = APIRouter()


class EntityExtractionRequest(BaseModel):
    """Entity extraction request."""
    text: str = Field(..., min_length=10, description="Paper text to analyze")
    entity_types: List[str] = Field(
        default=["method", "dataset", "metric", "venue"],
        description="Types of entities to extract"
    )


class EntityExtractionResponse(BaseModel):
    """Entity extraction response with methods, datasets, metrics, venues."""
    methods: List[Dict] = []
    datasets: List[Dict] = []
    metrics: List[Dict] = []
    venues: List[Dict] = []
    total_count: int = 0


class BuildGraphRequest(BaseModel):
    """Request to build knowledge graph for a paper."""
    paper_text: str = Field(..., min_length=10, description="Full paper text")
    authors: Optional[List[str]] = Field(default=[], description="Paper authors")
    references: Optional[List[Dict]] = Field(default=[], description="Citation references")


class BuildGraphResponse(BaseModel):
    """Response from graph building operation."""
    status: str
    paper_id: str
    message: str
    entity_counts: Optional[Dict[str, int]] = None


class EntityStatusResponse(BaseModel):
    """Entity extraction status for a paper."""
    paper_id: str
    has_entities: bool
    entity_counts: Dict[str, int]
    last_updated: Optional[str] = None


@router.post("/extract", response_model=EntityExtractionResponse)
async def extract_entities(request: EntityExtractionRequest):
    """Extract academic entities from text using LLM.

    Extracts methods, datasets, evaluation metrics, and venue mentions.
    """
    try:
        extractor = EntityExtractor()
        result = await extractor.extract(request.text)

        total_count = sum(
            len(result.get(key, []))
            for key in ['methods', 'datasets', 'metrics', 'venues']
        )

        logger.info("Entity extraction API complete",
                   text_length=len(request.text),
                   total_entities=total_count)

        return {
            "methods": result.get("methods", []),
            "datasets": result.get("datasets", []),
            "metrics": result.get("metrics", []),
            "venues": result.get("venues", []),
            "total_count": total_count
        }

    except Exception as e:
        logger.error("Entity extraction API failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=Errors.internal(f"Extraction failed: {str(e)}")
        )


@router.post("/{paper_id}/build", response_model=BuildGraphResponse)
async def build_paper_graph(
        paper_id: str,
        request: BuildGraphRequest
    ):
    """Build knowledge graph for a paper from extracted entities.

    Creates nodes for methods, datasets, metrics, venues.
    Creates relationships: USES, EVALUATED_ON, PUBLISHED_IN, COAUTHOR.
    """
    try:
        metadata = {
            "authors": request.authors or [],
            "references": request.references or []
        }

        result = await process_entity_extraction(
            paper_id=paper_id,
            paper_text=request.paper_text,
            paper_metadata=metadata
        )

        if result["status"] == "success":
            return {
                "status": "success",
                "paper_id": paper_id,
                "message": "Knowledge graph built successfully",
                "entity_counts": result.get("entity_counts", {})
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=Errors.internal(f"Graph building failed: {result.get('error', 'Unknown error')}")
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Build graph API failed", paper_id=paper_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=Errors.internal(f"Graph building failed: {str(e)}")
        )


@router.get("/{paper_id}/status", response_model=EntityStatusResponse)
async def get_entity_status(paper_id: str):
    """Get entity extraction status for a paper.

    Returns counts of extracted entities stored in Neo4j.
    """
    neo4j = Neo4jService()
    try:
        async with neo4j.driver.session() as session:
            # Check paper exists
            paper_result = await session.run(
                "MATCH (p:Paper {id: $paper_id}) RETURN p.id as id",
                paper_id=paper_id
            )
            paper_record = await paper_result.single()

            if not paper_record:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=Errors.not_found(f"Paper {paper_id} not found")
                )

            # Count entities for this paper
            counts_result = await session.run("""
                MATCH (p:Paper {id: $paper_id})
                OPTIONAL MATCH (p)-[:USES]->(m:Method)
                OPTIONAL MATCH (p)-[:PUBLISHED_IN]->(v:Venue)
                OPTIONAL MATCH (m)-[:EVALUATED_ON]->(d:Dataset)
                RETURN count(m) as methods,
                       count(d) as datasets,
                       count(v) as venues
            """, paper_id=paper_id)

            counts_record = await counts_result.single()

            return {
                "paper_id": paper_id,
                "has_entities": counts_record["methods"] > 0 or counts_record["datasets"] > 0,
                "entity_counts": {
                    "methods": counts_record["methods"],
                    "datasets": counts_record["datasets"],
                    "venues": counts_record["venues"]
                },
                "last_updated": None  # Could add timestamp to relationships
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Get entity status failed", paper_id=paper_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=Errors.internal(f"Status query failed: {str(e)}")
        )
    finally:
        await neo4j.close()
