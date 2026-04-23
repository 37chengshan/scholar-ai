"""Multi-index router for Iteration 2 three-tier retrieval.

Maps query intent / family to the appropriate index tier:

  ┌──────────────────┬───────────────────────────────────────────────────┐
  │ Index Tier       │ Content                                           │
  ├──────────────────┼───────────────────────────────────────────────────┤
  │ local_evidence   │ paragraphs, tables, figures, captions            │
  │ structural       │ section / method / dataset / metric / paper_role │
  │ summary          │ section summary / paper summary / topic summary  │
  └──────────────────┴───────────────────────────────────────────────────┘

Routing rules (query_family → index tiers, ordered by priority):

  fact          → local_evidence (primary), structural (secondary)
  compare       → structural (primary), local_evidence (secondary)
  numeric       → local_evidence with content_type=[table,text] filter
  table         → local_evidence with content_type=table filter
  figure        → local_evidence with content_type=image filter
  survey        → summary (primary), local_evidence (secondary)
  evolution     → summary (primary), structural (secondary)
  limitation    → local_evidence with section filter
  critique      → local_evidence + structural

The router also attaches ``content_type`` overrides and ``section_hints`` for
the downstream vector store query.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


# ---------------------------------------------------------------------------
# Route descriptor
# ---------------------------------------------------------------------------

@dataclass
class IndexRoute:
    """Describes how to query one index tier."""

    index_type: str
    """One of 'local_evidence', 'structural', 'summary'."""

    priority: int
    """Lower = queried first.  Priority-1 results are shown before priority-2."""

    content_types: List[str] = field(default_factory=list)
    """If non-empty, restrict the vector search to these content_types."""

    section_hint: Optional[str] = None
    """Preferred section filter (e.g. 'Results' for numeric queries)."""

    top_k_multiplier: float = 1.0
    """Multiply the base top_k by this factor for this route."""


@dataclass
class MultiIndexPlan:
    """Full routing plan for a single query."""

    query_family: str
    routes: List[IndexRoute]
    include_citation_hints: bool = False


# ---------------------------------------------------------------------------
# Routing table
# ---------------------------------------------------------------------------

_ROUTING_TABLE: dict = {
    "fact": [
        IndexRoute("local_evidence", priority=1),
        IndexRoute("structural", priority=2),
    ],
    "compare": [
        IndexRoute("structural", priority=1, top_k_multiplier=1.5),
        IndexRoute("local_evidence", priority=2),
    ],
    "numeric": [
        IndexRoute("local_evidence", priority=1, content_types=["table", "text"], section_hint="Results"),
        IndexRoute("structural", priority=2),
    ],
    "table": [
        IndexRoute("local_evidence", priority=1, content_types=["table"]),
        IndexRoute("local_evidence", priority=2, content_types=["text"]),
    ],
    "figure": [
        IndexRoute("local_evidence", priority=1, content_types=["image"]),
        IndexRoute("local_evidence", priority=2, content_types=["text"]),
    ],
    "survey": [
        IndexRoute("summary", priority=1, top_k_multiplier=2.0),
        IndexRoute("local_evidence", priority=2),
    ],
    "evolution": [
        IndexRoute("summary", priority=1, top_k_multiplier=2.0),
        IndexRoute("structural", priority=2),
        IndexRoute("local_evidence", priority=3),
    ],
    "limitation": [
        IndexRoute("local_evidence", priority=1, section_hint="Discussion"),
        IndexRoute("structural", priority=2),
    ],
    "critique": [
        IndexRoute("local_evidence", priority=1),
        IndexRoute("structural", priority=2),
    ],
}

_DEFAULT_ROUTES: List[IndexRoute] = [
    IndexRoute("local_evidence", priority=1),
]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def route_query(
    query_family: str,
    force_index_type: Optional[str] = None,
) -> MultiIndexPlan:
    """Return a ``MultiIndexPlan`` for the given query family.

    Args:
        query_family: Query family label from ``query_planner.classify_query_family()``.
        force_index_type: When set, override all routing and use exactly this index tier.

    Returns:
        ``MultiIndexPlan`` with ordered ``IndexRoute`` objects.
    """
    if force_index_type:
        return MultiIndexPlan(
            query_family=query_family,
            routes=[IndexRoute(force_index_type, priority=1)],
            include_citation_hints=False,
        )

    routes = _ROUTING_TABLE.get(query_family, _DEFAULT_ROUTES)

    include_hints = query_family in {"fact", "compare", "survey", "evolution", "limitation"}

    return MultiIndexPlan(
        query_family=query_family,
        routes=routes,
        include_citation_hints=include_hints,
    )


def primary_index(query_family: str) -> str:
    """Return the primary index type string for a query family."""
    plan = route_query(query_family)
    if plan.routes:
        return plan.routes[0].index_type
    return "local_evidence"


def uses_summary_index(query_family: str) -> bool:
    """Return True if the query family's primary route hits the summary index."""
    return primary_index(query_family) == "summary"


def content_type_filters(query_family: str) -> List[str]:
    """Return the content_type filter list for the primary route."""
    plan = route_query(query_family)
    if plan.routes:
        return plan.routes[0].content_types
    return []
