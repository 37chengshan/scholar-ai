"""Outline planning for review draft generation.

Extracted from review_draft_service.py to keep files under 800 lines.
"""

from __future__ import annotations

from typing import Any, Optional

from app.core.neo4j_service import Neo4jService
from app.models.paper import Paper
from app.schemas.review_draft import OutlineDoc, OutlineSection
from app.services.phase_i_routing_service import PhaseIRoutingDecision
from app.utils.logger import logger


async def is_graph_available() -> bool:
    """Check if Neo4j graph database is available."""
    neo4j = Neo4jService()
    try:
        async with neo4j.driver.session() as session:
            await session.run("RETURN 1")
        return True
    except Exception:
        return False
    finally:
        await neo4j.close()


def derive_themes_from_titles(titles: list[str]) -> list[str]:
    """Extract common themes from paper titles using token frequency."""
    tokens: dict[str, int] = {}
    for title in titles:
        for token in title.lower().replace(":", " ").replace("-", " ").split():
            clean = token.strip(".,()[]{}")
            if len(clean) < 4:
                continue
            if clean in {"with", "from", "that", "this", "using", "study", "toward", "towards"}:
                continue
            tokens[clean] = tokens.get(clean, 0) + 1
    ordered = sorted(tokens.items(), key=lambda kv: kv[1], reverse=True)
    return [word for word, _ in ordered[:6]]


async def global_discovery(
    *,
    kb_enable_graph: bool,
    papers: list[Paper],
    question: str,
    routing: PhaseIRoutingDecision,
) -> tuple[dict[str, Any], Optional[str]]:
    """Perform global discovery for review outline planning.

    Returns:
        Tuple of (graph_summary, graph_error)
    """
    graph_assist_used = False
    graph_error: Optional[str] = None
    if kb_enable_graph:
        graph_assist_used = await is_graph_available()
        if not graph_assist_used:
            graph_error = "graph_unavailable"

    themes = derive_themes_from_titles([p.title for p in papers])
    candidate_papers = [p.id for p in papers]
    return {
        "query_family": "survey",
        "graph_assist_used": graph_assist_used,
        "themes": themes,
        "candidate_papers": candidate_papers,
        "section_seeds": [
            {
                "title": "Research Landscape",
                "intent": f"Map the literature landscape for: {question}",
                "perspective": "landscape",
                "retrieval_mode": routing.execution_mode,
            },
            {
                "title": "Method Trends",
                "intent": "Compare methods, assumptions, and design patterns across papers",
                "perspective": "methods",
                "retrieval_mode": routing.execution_mode,
            },
            {
                "title": "Conflicting Evidence",
                "intent": "Surface disagreement, boundary conditions, and contradictory findings",
                "perspective": "conflicts",
                "retrieval_mode": routing.execution_mode,
            },
            {
                "title": "Limitations and Gaps",
                "intent": "Summarize weaknesses, missing evidence, and open research gaps",
                "perspective": "gaps",
                "retrieval_mode": routing.execution_mode,
            },
        ],
        "storm_lite_used": routing.review_strategy == "storm_lite",
    }, graph_error


def build_outline(
    *,
    papers: list[Paper],
    question: str,
    graph_summary: dict[str, Any],
    routing: PhaseIRoutingDecision,
    community_summaries: dict[int, str] | None = None,
) -> OutlineDoc:
    """Build the review outline from graph summary and paper metadata.

    Args:
        papers: List of papers
        question: The research question
        graph_summary: Graph discovery results
        routing: Routing decision
        community_summaries: Optional community summaries from graph synthesis
    """
    seeds = graph_summary.get("section_seeds") or []
    themes = graph_summary.get("themes") or []
    paper_ids = [p.id for p in papers]
    sections = []

    for seed in seeds:
        # Inject community summaries into seed evidence if available
        seed_evidence = list(seed.get("seed_evidence") or [])
        if community_summaries:
            for cid, summary in community_summaries.items():
                seed_evidence.append({
                    "type": "community_summary",
                    "community_id": cid,
                    "text": summary,
                })

        sections.append(
            OutlineSection(
                title=seed.get("title", "Section"),
                intent=seed.get("intent", "Synthesize evidence"),
                perspective=seed.get("perspective", "synthesis"),
                retrieval_mode=seed.get("retrieval_mode", routing.execution_mode),
                supporting_paper_ids=paper_ids,
                seed_evidence=seed_evidence,
            )
        )
    return OutlineDoc(
        research_question=question,
        themes=themes,
        sections=sections,
    )
