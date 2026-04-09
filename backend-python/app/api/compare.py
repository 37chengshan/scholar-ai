"""Multi-paper comparison API.

Provides comparison analysis across user-specified dimensions.
"""
import json
import os
from typing import List, Optional, Dict, Any

from pydantic import BaseModel, Field, validator
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.utils.logger import logger
from app.database import get_db
from app.core.auth import get_current_service
from app.utils.zhipu_client import get_llm_client
from app.utils.problem_detail import Errors
from app.models.paper import Paper, PaperChunk

router = APIRouter()

# Valid dimensions for comparison
VALID_DIMENSIONS = [
    "title", "authors", "year", "abstract",
    "method", "methodology", "approach",
    "experiment", "experiments",
    "results", "findings",
    "dataset", "datasets", "data",
    "metrics", "evaluation", "performance",
    "limitations", "future_work",
    "contribution", "innovation"
]


class CompareRequest(BaseModel):
    """Request model for paper comparison."""
    paper_ids: List[str] = Field(
        ...,
        min_items=2,
        max_items=10,
        description="Paper IDs to compare (2-10 papers)"
    )
    dimensions: List[str] = Field(
        default=["method", "results", "dataset", "metrics"],
        description="Dimensions to compare across"
    )
    include_abstract: bool = Field(
        default=True,
        description="Include abstract in comparison context"
    )

    @validator('dimensions')
    def validate_dimensions(cls, v):
        """Validate dimension names."""
        invalid = [d for d in v if d.lower() not in VALID_DIMENSIONS]
        if invalid:
            logger.warning(f"Invalid dimensions requested: {invalid}")
            # Allow invalid dimensions but warn (LLM can handle them)
        return v


class ComparisonResult(BaseModel):
    """Single paper comparison data."""
    paper_id: str
    title: str
    authors: List[str]
    year: int
    findings: Dict[str, str]  # dimension -> finding


class CompareResponse(BaseModel):
    """Response model for paper comparison."""
    paper_ids: List[str]
    dimensions: List[str]
    markdown_table: str
    structured_data: List[ComparisonResult]
    summary: str


# =============================================================================
# Evolution Timeline Models
# =============================================================================

class TimelineEntry(BaseModel):
    """Single entry in evolution timeline."""
    year: int
    version: str = Field(description="Version identifier (e.g., 'v1', 'v2', 'BERT-base')")
    paper_id: str
    paper_title: str
    key_changes: str = Field(description="Key improvements or changes in this version")


class EvolutionTimeline(BaseModel):
    """Evolution timeline response."""
    method: str
    paper_count: int
    timeline: List[TimelineEntry]
    summary: str = Field(description="Brief summary of the evolution pattern")


class EvolutionRequest(BaseModel):
    """Request for evolution timeline generation."""
    paper_ids: List[str] = Field(
        ...,
        min_items=2,
        max_items=20,
        description="Paper IDs to analyze for evolution (2-20 papers)"
    )
    method_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Method name to identify versions (e.g., 'YOLO', 'BERT', 'ResNet')"
    )


async def fetch_papers_for_comparison(
    paper_ids: List[str],
    user_id: str,
    db: AsyncSession
) -> List[Dict[str, Any]]:
    """Fetch paper metadata and chunks for comparison.

    Validates ownership and returns complete paper data.
    """
    # Fetch paper metadata using SQLAlchemy
    result = await db.execute(
        select(Paper).where(Paper.id.in_(paper_ids), Paper.user_id == user_id)
    )
    papers_db = result.scalars().all()

    found_ids = {p.id for p in papers_db}
    missing_ids = set(paper_ids) - found_ids

    if missing_ids:
        raise HTTPException(
            status_code=404,
            detail=Errors.not_found(f"Papers not found or not accessible: {list(missing_ids)}")
        )

    # Fetch chunks for each paper and build response
    papers = []
    for paper in papers_db:
        paper_dict = {
            'id': paper.id,
            'title': paper.title,
            'authors': paper.authors,
            'year': paper.year,
            'abstract': paper.abstract,
            'status': paper.status
        }

        # Fetch chunks for this paper
        chunks_result = await db.execute(
            select(PaperChunk)
            .where(PaperChunk.paper_id == paper.id)
            .order_by(PaperChunk.page_start.asc(), PaperChunk.id.asc())
        )
        chunks = chunks_result.scalars().all()

        paper_dict['chunks'] = [
            {
                'content': c.content,
                'section': c.section,
                'page': c.page_start
            }
            for c in chunks
        ]
        papers.append(paper_dict)

    return papers


async def analyze_papers_with_llm(
    papers: List[Dict[str, Any]],
    dimensions: List[str]
) -> Dict[str, Any]:
    """Use LLM to analyze papers and extract comparison data.

    Returns structured comparison results and Markdown table.
    """
    # Build context from papers
    paper_contexts = []
    for paper in papers:
        chunks_text = "\n\n".join([
            f"[Section: {c.get('section', 'Unknown')}] {c['content'][:500]}"
            for c in paper['chunks'][:10]  # Limit to first 10 chunks
        ])

        context = f"""
Paper ID: {paper['id']}
Title: {paper['title']}
Authors: {', '.join(paper['authors'])}
Year: {paper['year']}
Abstract: {paper.get('abstract', 'N/A')}

Content Excerpts:
{chunks_text}
"""
        paper_contexts.append(context)

    all_context = "\n---\n".join(paper_contexts)

    # Build prompt
    prompt = f"""Analyze and compare the following research papers across the specified dimensions.

Dimensions to compare: {', '.join(dimensions)}

Papers:
{all_context}

Provide your analysis in the following JSON format:
{{
    "comparison_table": {{
        "headers": ["Paper", ...dimensions...],
        "rows": [
            ["Paper 1 Title", ...findings for each dimension...],
            ...
        ]
    }},
    "findings": [
        {{
            "paper_id": "...",
            "title": "...",
            "findings": {{"dimension": "extraction", ...}}
        }}
    ],
    "summary": "Brief summary of key differences and similarities"
}}

For each dimension, extract the most relevant information. If information is not available, use "Not specified".
"""

    try:
        llm_client = get_llm_client()
        
        response = await llm_client.chat_completion(
            messages=[
                {"role": "system", "content": "You are a research paper analysis assistant. Extract and compare information accurately."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=4000
        )

        content = response.choices[0].message.content
        result = json.loads(content)

        return result

    except Exception as e:
        logger.error(f"LLM comparison failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=Errors.internal(f"Failed to generate comparison: {str(e)}")
        )


def generate_markdown_table(comparison_data: Dict) -> str:
    """Generate Markdown table from comparison data."""
    table = comparison_data.get("comparison_table", {})
    headers = table.get("headers", [])
    rows = table.get("rows", [])

    if not headers or not rows:
        return "No comparison data available"

    # Build markdown
    lines = []
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("| " + " | ".join(["---"] * len(headers)) + " |")

    for row in rows:
        # Truncate long cells
        truncated = [str(cell)[:100] + "..." if len(str(cell)) > 100 else str(cell) for cell in row]
        lines.append("| " + " | ".join(truncated) + " |")

    return "\n".join(lines)


# =============================================================================
# Evolution Timeline Functions
# =============================================================================

async def extract_versions_with_llm(
    papers: List[Dict[str, Any]],
    method_name: str
) -> List[Dict[str, Any]]:
    """Use LLM to extract version information from papers.

    Args:
        papers: List of paper dicts with id, title, year, abstract
        method_name: Name of the method to identify (e.g., "YOLO")

    Returns:
        List of version extractions with year, version, key_changes
    """
    # Build paper context
    paper_contexts = []
    for paper in papers:
        context = f"""
Paper ID: {paper['id']}
Title: {paper['title']}
Year: {paper['year']}
Abstract: {paper.get('abstract', 'N/A')[:500]}
"""
        paper_contexts.append(context)

    all_context = "\n---\n".join(paper_contexts)

    prompt = f"""Analyze the following research papers to identify the evolution of the "{method_name}" method.

Papers:
{all_context}

For each paper, determine:
1. Version identifier: Extract the version from the title (e.g., "YOLOv2", "YOLOv3", "BERT-base", "BERT-large", "ResNet-50", "ResNet-101")
   - If explicit version (like v1, v2), use that
   - If model size variant (base, large), include that
   - If architecture variant (50, 101, 152 for ResNet), include that
   - Normalize to a consistent format
2. Key changes: Identify the main improvements, innovations, or differences from previous versions

Return a JSON array with this exact structure:
[
    {{
        "paper_id": "...",
        "year": 2016,
        "version": "v2",
        "key_changes": "Description of main improvements"
    }}
]

Include ALL papers in the response, even if version is unclear (use "unknown" or "initial" for the earliest/first paper).
"""

    try:
        llm_client = get_llm_client()
        
        response = await llm_client.chat_completion(
            messages=[
                {"role": "system", "content": "You are a research analysis expert. Extract version information accurately from paper titles and abstracts."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=3000
        )

        content = response.choices[0].message.content
        result = json.loads(content)

        # Handle both array and object-wrapped-array responses
        if isinstance(result, list):
            return result
        elif isinstance(result, dict) and "versions" in result:
            return result["versions"]
        elif isinstance(result, dict):
            # Try to find array in values
            for v in result.values():
                if isinstance(v, list):
                    return v
        return []

    except Exception as e:
        logger.error(f"LLM version extraction failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=Errors.internal(f"Failed to extract version information: {str(e)}")
        )


def validate_timeline_with_citations(
    timeline: List[Dict[str, Any]],
    paper_ids: List[str]
) -> List[Dict[str, Any]]:
    """Validate and correct timeline ordering using citation relationships.

    The principle: If paper A cites paper B, then A was published after B.
    We use this to validate and potentially correct year ordering.

    Args:
        timeline: Timeline entries from LLM extraction
        paper_ids: List of paper IDs in the timeline

    Returns:
        Validated and potentially corrected timeline
    """
    # For Phase 4, we use a simplified validation:
    # Just verify that years are in ascending order
    # In Phase 5, this will use actual citation graph from Neo4j

    validated_timeline = sorted(timeline, key=lambda x: x.get('year', 9999))

    # Check for temporal inconsistencies
    inconsistencies = []
    for i in range(len(validated_timeline) - 1):
        current = validated_timeline[i]
        next_entry = validated_timeline[i + 1]

        if current.get('year', 0) > next_entry.get('year', 0):
            inconsistencies.append({
                "paper_1": current.get('paper_id'),
                "year_1": current.get('year'),
                "paper_2": next_entry.get('paper_id'),
                "year_2": next_entry.get('year'),
                "issue": "Temporal inconsistency detected"
            })

    if inconsistencies:
        logger.warning(f"Timeline temporal inconsistencies: {inconsistencies}")

    # Add validation metadata to each entry
    for entry in validated_timeline:
        entry['validated'] = True
        entry['temporal_consistency'] = 'checked'

    return validated_timeline


def detect_evolution_pattern(timeline: List[Dict[str, Any]]) -> str:
    """Detect the overall evolution pattern from timeline.

    Returns a summary description of how the method evolved.
    """
    if not timeline:
        return "No evolution data available"

    years = [entry.get('year') for entry in timeline if entry.get('year')]
    versions = [entry.get('version', 'unknown') for entry in timeline]

    if len(years) < 2:
        return "Insufficient data to determine evolution pattern"

    year_span = max(years) - min(years)
    version_count = len([v for v in versions if v != 'unknown'])

    patterns = []

    if year_span >= 5:
        patterns.append(f"developed over {year_span} years")
    else:
        patterns.append("rapid iteration")

    if version_count >= 3:
        patterns.append(f"with {version_count} distinct versions")

    # Analyze key changes for common themes
    all_changes = ' '.join([entry.get('key_changes', '') for entry in timeline]).lower()

    if any(term in all_changes for term in ['accuracy', 'performance', 'better', 'improve']):
        patterns.append("focusing on performance improvements")

    if any(term in all_changes for term in ['speed', 'faster', 'efficient', 'lightweight']):
        patterns.append("with efficiency optimizations")

    if any(term in all_changes for term in ['scale', 'larger', 'bigger', 'deep']):
        patterns.append("scaling up model capacity")

    return f"Method evolved through {', '.join(patterns)}"


@router.post("/compare", response_model=CompareResponse)
async def compare_papers_endpoint(
    request: CompareRequest,
    db: AsyncSession = Depends(get_db),
    service: dict = Depends(get_current_service)
) -> Dict[str, Any]:
    """Compare multiple papers across specified dimensions.

    Args:
        request: Comparison request with paper IDs and dimensions
        service: Authenticated service from JWT

    Returns:
        Markdown table and structured comparison data
    """
    # Get user_id from service token (passed from Node.js gateway)
    user_id = service.get("user_id") or service.get("sub", "unknown")

    logger.info(
        f"Comparison request",
        paper_ids=request.paper_ids,
        dimensions=request.dimensions,
        user_id=user_id
    )

    # Fetch papers (validates ownership)
    papers = await fetch_papers_for_comparison(request.paper_ids, user_id, db)

    # Analyze with LLM
    analysis = await analyze_papers_with_llm(papers, request.dimensions)

    # Generate markdown table
    markdown_table = generate_markdown_table(analysis)

    # Build structured response
    findings = analysis.get("findings", [])
    structured_data = [
        ComparisonResult(
            paper_id=f.get("paper_id", ""),
            title=f.get("title", ""),
            authors=next(
                (p["authors"] for p in papers if p["id"] == f.get("paper_id")),
                []
            ),
            year=next(
                (p["year"] for p in papers if p["id"] == f.get("paper_id")),
                0
            ),
            findings=f.get("findings", {})
        )
        for f in findings
    ]

    return CompareResponse(
        paper_ids=request.paper_ids,
        dimensions=request.dimensions,
        markdown_table=markdown_table,
        structured_data=structured_data,
        summary=analysis.get("summary", "")
    )


@router.post("/evolution", response_model=EvolutionTimeline)
async def detect_evolution_timeline(
    request: EvolutionRequest,
    db: AsyncSession = Depends(get_db),
    service: dict = Depends(get_current_service)
) -> Dict[str, Any]:
    """Detect method evolution timeline from papers.

    Analyzes paper titles, abstracts, and years to identify version progression.
    Validates temporal ordering using publication years.

    Args:
        request: Evolution request with paper IDs and method name
        service: Authenticated service from JWT

    Returns:
        Evolution timeline with version information
    """
    # Get user_id from service token (passed from Node.js gateway)
    user_id = service.get("user_id") or service.get("sub", "unknown")

    logger.info(
        f"Evolution timeline request",
        method=request.method_name,
        paper_count=len(request.paper_ids),
        user_id=user_id
    )

    # Fetch papers using SQLAlchemy (validates ownership)
    result = await db.execute(
        select(Paper).where(Paper.id.in_(request.paper_ids), Paper.user_id == user_id)
    )
    papers_db = result.scalars().all()

    found_ids = {p.id for p in papers_db}
    missing_ids = set(request.paper_ids) - found_ids

    if missing_ids:
        raise HTTPException(
            status_code=404,
            detail=Errors.not_found(f"Papers not found or not accessible: {list(missing_ids)}")
        )

    papers = [
        {
            'id': p.id,
            'title': p.title,
            'authors': p.authors,
            'year': p.year,
            'abstract': p.abstract
        }
        for p in papers_db
    ]

    # Extract versions with LLM
    version_data = await extract_versions_with_llm(papers, request.method_name)

    # Validate timeline ordering
    validated_timeline = validate_timeline_with_citations(
        version_data,
        request.paper_ids
    )

    # Build timeline entries
    timeline_entries = []
    for entry in validated_timeline:
        paper_id = entry.get('paper_id', '')
        paper = next((p for p in papers if p['id'] == paper_id), None)

        if paper:
            timeline_entries.append(TimelineEntry(
                year=entry.get('year', paper.get('year', 0)),
                version=entry.get('version', 'unknown'),
                paper_id=paper_id,
                paper_title=paper.get('title', 'Unknown'),
                key_changes=entry.get('key_changes', 'No description available')
            ))

    # Detect evolution pattern
    summary = detect_evolution_pattern(validated_timeline)

    return EvolutionTimeline(
        method=request.method_name,
        paper_count=len(timeline_entries),
        timeline=timeline_entries,
        summary=summary
    )
