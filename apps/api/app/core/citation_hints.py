"""Lightweight citation relation hints for Iteration 2 retrieval.

This module provides *retrieval-hint* level citation signals — not a heavy
knowledge-graph platform.  The goal is to surface citation context that helps
the search orchestrator rank or expand results:

  - forward_citations:   papers that cite the current paper
  - backward_citations:  papers cited by the current paper
  - same_method_cluster: papers using the same method (inferred from chunk metadata)
  - evolution_hint:      chronological sibling papers on the same topic

All functions are designed to be called at **query time** from within the
search service after the first-pass retrieval.  They return lightweight dicts
rather than full ``RetrievedChunk`` objects so the caller can decide how to
weight or display the hints.

No database writes happen here; hints are computed from existing metadata
stored in PostgreSQL and Milvus ``raw_data`` fields.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

class CitationHint:
    """Lightweight citation relation descriptor."""

    __slots__ = (
        "paper_id",
        "relation_type",
        "cited_by_count",
        "method_overlap",
        "year",
        "title",
        "hint_text",
    )

    def __init__(
        self,
        paper_id: str,
        relation_type: str,
        cited_by_count: int = 0,
        method_overlap: float = 0.0,
        year: Optional[int] = None,
        title: Optional[str] = None,
        hint_text: str = "",
    ) -> None:
        self.paper_id = paper_id
        self.relation_type = relation_type  # "forward" | "backward" | "same_method" | "evolution"
        self.cited_by_count = cited_by_count
        self.method_overlap = method_overlap
        self.year = year
        self.title = title
        self.hint_text = hint_text

    def to_dict(self) -> Dict[str, Any]:
        return {
            "paper_id": self.paper_id,
            "relation_type": self.relation_type,
            "cited_by_count": self.cited_by_count,
            "method_overlap": self.method_overlap,
            "year": self.year,
            "title": self.title,
            "hint_text": self.hint_text,
        }


# ---------------------------------------------------------------------------
# Hint derivation helpers
# ---------------------------------------------------------------------------

def _method_overlap_score(
    methods_a: List[str],
    methods_b: List[str],
) -> float:
    """Jaccard overlap between two method token sets."""
    set_a = {m.lower() for m in methods_a if m}
    set_b = {m.lower() for m in methods_b if m}
    if not set_a or not set_b:
        return 0.0
    return len(set_a & set_b) / len(set_a | set_b)


def build_forward_hints(
    retrieved_chunks: List[Dict[str, Any]],
    citing_papers_meta: List[Dict[str, Any]],
    max_hints: int = 5,
) -> List[CitationHint]:
    """Build forward-citation hints from papers that cite the retrieved ones.

    Args:
        retrieved_chunks: First-pass retrieval results (each a dict with paper_id, etc.).
        citing_papers_meta: List of ``{"paper_id", "title", "year", "cited_by_count"}``
            dicts, e.g. fetched from PostgreSQL or Semantic Scholar cache.
        max_hints: Maximum hints to return.

    Returns:
        List of forward-citation ``CitationHint`` objects, ranked by cited_by_count.
    """
    target_paper_ids = {c.get("paper_id") for c in retrieved_chunks if c.get("paper_id")}
    hints: List[CitationHint] = []

    for meta in citing_papers_meta:
        if meta.get("paper_id") in target_paper_ids:
            continue
        hints.append(
            CitationHint(
                paper_id=meta["paper_id"],
                relation_type="forward",
                cited_by_count=int(meta.get("cited_by_count", 0)),
                year=meta.get("year"),
                title=meta.get("title"),
                hint_text=f"cites papers in result set (cited_by={meta.get('cited_by_count', 0)})",
            )
        )

    hints.sort(key=lambda h: h.cited_by_count, reverse=True)
    return hints[:max_hints]


def build_backward_hints(
    retrieved_chunks: List[Dict[str, Any]],
    reference_entries: List[Dict[str, Any]],
    max_hints: int = 5,
) -> List[CitationHint]:
    """Build backward-citation hints from papers cited by the retrieved ones.

    Args:
        retrieved_chunks: First-pass retrieval results.
        reference_entries: List of ``{"source_paper_id", "cited_paper_id", "title", "year"}``
            dicts extracted from PDF reference sections.
        max_hints: Maximum hints to return.

    Returns:
        List of backward-citation ``CitationHint`` objects.
    """
    target_paper_ids = {c.get("paper_id") for c in retrieved_chunks if c.get("paper_id")}
    cited_ids_seen: set = set()
    hints: List[CitationHint] = []

    for ref in reference_entries:
        if ref.get("source_paper_id") not in target_paper_ids:
            continue
        cited_id = ref.get("cited_paper_id", "")
        if cited_id in cited_ids_seen or not cited_id:
            continue
        cited_ids_seen.add(cited_id)
        hints.append(
            CitationHint(
                paper_id=cited_id,
                relation_type="backward",
                year=ref.get("year"),
                title=ref.get("title"),
                hint_text=f"referenced by {ref.get('source_paper_id', 'unknown')[:8]}",
            )
        )

    return hints[:max_hints]


def build_same_method_hints(
    retrieved_chunks: List[Dict[str, Any]],
    candidate_chunks: List[Dict[str, Any]],
    min_overlap: float = 0.25,
    max_hints: int = 5,
) -> List[CitationHint]:
    """Build same-method cluster hints by method name overlap.

    Args:
        retrieved_chunks: First-pass retrieval results with ``method`` fields.
        candidate_chunks: Broader candidate pool to search for method overlap.
        min_overlap: Minimum Jaccard overlap to qualify.
        max_hints: Maximum hints to return.

    Returns:
        List of same-method ``CitationHint`` objects.
    """
    retrieved_methods: List[str] = []
    for chunk in retrieved_chunks:
        if chunk.get("method"):
            retrieved_methods.append(chunk["method"])
        raw = chunk.get("raw_data") or {}
        if raw.get("method"):
            retrieved_methods.append(raw["method"])

    if not retrieved_methods:
        return []

    seen_papers = {c.get("paper_id") for c in retrieved_chunks if c.get("paper_id")}
    hints: List[CitationHint] = []

    for chunk in candidate_chunks:
        pid = chunk.get("paper_id", "")
        if pid in seen_papers:
            continue
        candidate_methods = []
        if chunk.get("method"):
            candidate_methods.append(chunk["method"])
        raw = chunk.get("raw_data") or {}
        if raw.get("method"):
            candidate_methods.append(raw["method"])

        overlap = _method_overlap_score(retrieved_methods, candidate_methods)
        if overlap < min_overlap:
            continue

        hints.append(
            CitationHint(
                paper_id=pid,
                relation_type="same_method",
                method_overlap=overlap,
                title=chunk.get("paper_title"),
                hint_text=f"method overlap={overlap:.2f}: {','.join(candidate_methods[:2])}",
            )
        )
        seen_papers.add(pid)

    hints.sort(key=lambda h: h.method_overlap, reverse=True)
    return hints[:max_hints]


def build_evolution_hints(
    retrieved_chunks: List[Dict[str, Any]],
    all_paper_meta: List[Dict[str, Any]],
    year_window: int = 3,
    max_hints: int = 5,
) -> List[CitationHint]:
    """Build chronological evolution hints for survey / evolution queries.

    Returns papers published within ``year_window`` years of the retrieved set
    that share topic keywords, ordered by year.

    Args:
        retrieved_chunks: First-pass retrieval results.
        all_paper_meta: List of ``{"paper_id", "title", "year", "keywords"}`` dicts.
        year_window: Year radius for sibling detection.
        max_hints: Maximum hints to return.

    Returns:
        List of evolution ``CitationHint`` objects ordered by year.
    """
    retrieved_paper_ids = {c.get("paper_id") for c in retrieved_chunks if c.get("paper_id")}

    # Extract year range from retrieved set
    retrieved_meta = [m for m in all_paper_meta if m.get("paper_id") in retrieved_paper_ids]
    years = [int(m["year"]) for m in retrieved_meta if m.get("year")]
    if not years:
        return []

    min_year, max_year = min(years), max(years)

    # Collect keyword sets from retrieved chunks
    retrieved_keywords: set = set()
    for m in retrieved_meta:
        for kw in (m.get("keywords") or []):
            retrieved_keywords.add(kw.lower())

    hints: List[CitationHint] = []
    for meta in all_paper_meta:
        if meta.get("paper_id") in retrieved_paper_ids:
            continue
        paper_year = meta.get("year")
        if not paper_year:
            continue
        try:
            py = int(paper_year)
        except (TypeError, ValueError):
            continue
        if not (min_year - year_window <= py <= max_year + year_window):
            continue

        # Keyword overlap
        paper_kws = {kw.lower() for kw in (meta.get("keywords") or [])}
        overlap = len(retrieved_keywords & paper_kws) / max(len(retrieved_keywords | paper_kws), 1)
        if overlap < 0.05 and abs(py - max_year) > 1:
            continue

        hints.append(
            CitationHint(
                paper_id=meta["paper_id"],
                relation_type="evolution",
                year=py,
                title=meta.get("title"),
                hint_text=f"year={py}, keyword_overlap={overlap:.2f}",
            )
        )

    hints.sort(key=lambda h: (h.year or 0))
    return hints[:max_hints]


# ---------------------------------------------------------------------------
# Convenience orchestrator
# ---------------------------------------------------------------------------

def build_all_hints(
    retrieved_chunks: List[Dict[str, Any]],
    query_family: str,
    citing_papers_meta: Optional[List[Dict[str, Any]]] = None,
    reference_entries: Optional[List[Dict[str, Any]]] = None,
    candidate_chunks: Optional[List[Dict[str, Any]]] = None,
    all_paper_meta: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, List[Dict[str, Any]]]:
    """Convenience wrapper that builds appropriate hints for a given query family.

    Args:
        retrieved_chunks: First-pass retrieval results.
        query_family: From query_planner (fact/compare/evolution/survey/…).
        citing_papers_meta: Optional — for forward hints.
        reference_entries: Optional — for backward hints.
        candidate_chunks: Optional — for same-method hints.
        all_paper_meta: Optional — for evolution hints.

    Returns:
        Dict with keys ``"forward"``, ``"backward"``, ``"same_method"``, ``"evolution"``
        each containing a list of hint dicts.
    """
    result: Dict[str, List[Dict[str, Any]]] = {
        "forward": [],
        "backward": [],
        "same_method": [],
        "evolution": [],
    }

    # Forward citations — useful for fact / compare / critique families
    if citing_papers_meta and query_family in {"fact", "compare", "critique"}:
        result["forward"] = [
            h.to_dict() for h in build_forward_hints(retrieved_chunks, citing_papers_meta)
        ]

    # Backward citations — useful for fact / limitation families
    if reference_entries and query_family in {"fact", "limitation"}:
        result["backward"] = [
            h.to_dict() for h in build_backward_hints(retrieved_chunks, reference_entries)
        ]

    # Same-method cluster — useful for compare / numeric families
    if candidate_chunks and query_family in {"compare", "numeric"}:
        result["same_method"] = [
            h.to_dict() for h in build_same_method_hints(retrieved_chunks, candidate_chunks)
        ]

    # Evolution — useful for survey / evolution families
    if all_paper_meta and query_family in {"survey", "evolution"}:
        result["evolution"] = [
            h.to_dict() for h in build_evolution_hints(retrieved_chunks, all_paper_meta)
        ]

    return result
