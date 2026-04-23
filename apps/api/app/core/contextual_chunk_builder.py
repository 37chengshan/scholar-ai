"""Contextual chunk builder for Iteration 2 evidence enrichment.

Upgrades bare text chunks to contextual chunks that carry:
- Paper title
- Section / subsection path
- Method / dataset / metric hints extracted from the chunk
- Page / table / figure reference
- Neighbouring context window (prev + next sentences)

The enriched ``content_data`` text is then used for:
- Dense embedding (single pass)
- Sparse BM25 indexing
- Reranker document construction

This is a pure-function module with no side-effects so it can be safely used
from both the storage pipeline (ingestion) and unit tests.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Pattern libraries
# ---------------------------------------------------------------------------

_METRIC_PATTERN = re.compile(
    r"\b(accuracy|f1|precision|recall|bleu|rouge|auc|ndcg|mrr|map|perplexity"
    r"|score|ap@\d+|hit@\d+|recall@\d+)\b",
    re.IGNORECASE,
)

_DATASET_PATTERN = re.compile(
    r"\b([A-Z]{2,}(?:-[0-9A-Z]+)?(?:\d{2,4})?)\b",
)

_METHOD_PATTERN = re.compile(
    r"\b([A-Z][A-Za-z0-9\-]{2,}(?:\s[A-Z][A-Za-z0-9\-]{2,})?)\b",
)

_FIGURE_PATTERN = re.compile(r"\b(?:figure|fig\.?)\s*(\d+)\b", re.IGNORECASE)
_TABLE_PATTERN = re.compile(r"\btable\s*(\d+)\b", re.IGNORECASE)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _extract_metric_hints(text: str) -> List[str]:
    return list(dict.fromkeys(m.group(0).lower() for m in _METRIC_PATTERN.finditer(text)))[:3]


def _extract_method_hints(text: str) -> List[str]:
    raw = [m.group(0) for m in _METHOD_PATTERN.finditer(text)]
    # Filter very short tokens, numbers, section-header noise
    filtered = [t for t in raw if len(t) > 3 and not t.isnumeric()]
    return list(dict.fromkeys(filtered))[:3]


def _extract_dataset_hints(text: str) -> List[str]:
    raw = [m.group(0) for m in _DATASET_PATTERN.finditer(text)]
    filtered = [t for t in raw if len(t) >= 3]
    return list(dict.fromkeys(filtered))[:3]


def _extract_figure_refs(text: str) -> List[str]:
    return [f"Fig.{m.group(1)}" for m in _FIGURE_PATTERN.finditer(text)][:2]


def _extract_table_refs(text: str) -> List[str]:
    return [f"Table {m.group(1)}" for m in _TABLE_PATTERN.finditer(text)][:2]


def _window_text(
    items: List[Dict[str, Any]],
    current_idx: int,
    window: int = 1,
) -> str:
    """Return concatenated text of neighbours within the given window radius."""
    parts: List[str] = []
    for offset in range(-window, window + 1):
        if offset == 0:
            continue
        neighbour_idx = current_idx + offset
        if 0 <= neighbour_idx < len(items):
            neighbour = items[neighbour_idx]
            t = neighbour.get("text", "") or neighbour.get("content_data", "") or ""
            if t.strip():
                parts.append(t.strip()[:300])
    return " … ".join(parts)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_contextual_text(
    chunk_text: str,
    paper_title: Optional[str],
    section_path: Optional[str],
    page_num: Optional[int] = None,
    table_ref: Optional[str] = None,
    figure_ref: Optional[str] = None,
    subsection: Optional[str] = None,
    context_window: Optional[str] = None,
    max_total_len: int = 3000,
) -> str:
    """Build the contextual text string used for embedding and BM25 indexing.

    Format (designed for dense + sparse dual use):

        [Paper: <title>]
        [Section: <section_path>]               # optional
        [Subsection: <subsection>]              # optional
        [Page: <page_num> | Table: T3 | Fig: F2]  # optional
        <chunk text>
        [Context: <window text>]                # optional
        [Methods: A, B | Datasets: X | Metrics: f1, accuracy]  # optional

    Args:
        chunk_text: Raw chunk text.
        paper_title: Paper title (used as document-level context).
        section_path: Full section path (e.g. "Methods/Experimental Setup").
        page_num: Page number within the paper.
        table_ref: Table identifier if chunk references a table.
        figure_ref: Figure identifier if chunk references a figure.
        subsection: Leaf subsection label.
        context_window: Neighbouring chunk text from window expansion.
        max_total_len: Hard cap to avoid overly long content_data strings.

    Returns:
        Enriched contextual text ready for embedding.
    """
    lines: List[str] = []

    if paper_title:
        lines.append(f"[Paper: {paper_title.strip()[:200]}]")

    if section_path:
        lines.append(f"[Section: {section_path.strip()[:120]}]")

    if subsection and subsection.strip() != (section_path or "").strip():
        lines.append(f"[Subsection: {subsection.strip()[:80]}]")

    loc_parts: List[str] = []
    if page_num is not None:
        loc_parts.append(f"Page:{page_num}")
    if table_ref:
        loc_parts.append(f"Table:{table_ref}")
    if figure_ref:
        loc_parts.append(f"Figure:{figure_ref}")
    if loc_parts:
        lines.append(f"[{' | '.join(loc_parts)}]")

    # Core text is appended after prefix so downstream callers can keep
    # `content_data = contextual_prefix + raw_text` contract explicit.
    core_text = chunk_text.strip()

    # Context window (neighbours)
    if context_window and context_window.strip():
        lines.append(f"[Context: {context_window.strip()[:400]}]")

    # Extracted hints
    methods = _extract_method_hints(chunk_text)
    datasets = _extract_dataset_hints(chunk_text)
    metrics = _extract_metric_hints(chunk_text)

    hint_parts: List[str] = []
    if methods:
        hint_parts.append("Methods:" + ",".join(methods))
    if datasets:
        hint_parts.append("Datasets:" + ",".join(datasets))
    if metrics:
        hint_parts.append("Metrics:" + ",".join(metrics))

    # Automatically pick up figure/table refs from text if not supplied
    auto_figs = _extract_figure_refs(chunk_text)
    auto_tabs = _extract_table_refs(chunk_text)
    if auto_figs:
        hint_parts.append("Figs:" + ",".join(auto_figs))
    if auto_tabs:
        hint_parts.append("Tables:" + ",".join(auto_tabs))

    if hint_parts:
        lines.append("[" + " | ".join(hint_parts) + "]")

    contextual_prefix = "\n".join(lines).strip()
    if contextual_prefix:
        result = f"{contextual_prefix}\n{core_text}"
    else:
        result = core_text
    return result[:max_total_len]


def build_contextual_prefix(
    chunk_text: str,
    paper_title: Optional[str],
    section_path: Optional[str],
    page_num: Optional[int] = None,
    table_ref: Optional[str] = None,
    figure_ref: Optional[str] = None,
    subsection: Optional[str] = None,
    context_window: Optional[str] = None,
    max_prefix_len: int = 600,
) -> str:
    """Build compact contextual prefix text without duplicating raw chunk text.

    This helper is used by ingestion scripts that need explicit:
        raw_text + contextual_prefix + content_data
    """
    lines: List[str] = []

    if paper_title:
        lines.append(f"[Paper: {paper_title.strip()[:200]}]")

    if section_path:
        lines.append(f"[Section: {section_path.strip()[:120]}]")

    if subsection and subsection.strip() != (section_path or "").strip():
        lines.append(f"[Subsection: {subsection.strip()[:80]}]")

    loc_parts: List[str] = []
    if page_num is not None:
        loc_parts.append(f"Page:{page_num}")
    if table_ref:
        loc_parts.append(f"Table:{table_ref}")
    if figure_ref:
        loc_parts.append(f"Figure:{figure_ref}")
    if loc_parts:
        lines.append(f"[{' | '.join(loc_parts)}]")

    if context_window and context_window.strip():
        lines.append(f"[Context: {context_window.strip()[:320]}]")

    methods = _extract_method_hints(chunk_text)
    datasets = _extract_dataset_hints(chunk_text)
    metrics = _extract_metric_hints(chunk_text)
    auto_figs = _extract_figure_refs(chunk_text)
    auto_tabs = _extract_table_refs(chunk_text)

    hint_parts: List[str] = []
    if methods:
        hint_parts.append("Methods:" + ",".join(methods))
    if datasets:
        hint_parts.append("Datasets:" + ",".join(datasets))
    if metrics:
        hint_parts.append("Metrics:" + ",".join(metrics))
    if auto_figs:
        hint_parts.append("Figs:" + ",".join(auto_figs))
    if auto_tabs:
        hint_parts.append("Tables:" + ",".join(auto_tabs))

    if hint_parts:
        lines.append("[" + " | ".join(hint_parts) + "]")

    return "\n".join(lines)[:max_prefix_len].strip()


def enrich_chunk(
    chunk: Dict[str, Any],
    paper_title: Optional[str],
    all_page_items: Optional[List[Dict[str, Any]]] = None,
    chunk_index: Optional[int] = None,
    window_size: int = 1,
) -> Dict[str, Any]:
    """Return an enriched copy of *chunk* with contextual ``content_data``.

    Args:
        chunk: Raw chunk dict from the parsing pipeline.
        paper_title: Title of the paper being processed.
        all_page_items: Ordered list of all items on the same page, used for
            window expansion.  Pass ``None`` to skip window expansion.
        chunk_index: Position of *chunk* within *all_page_items*.
        window_size: How many neighbours on each side to include.

    Returns:
        New dict with ``content_data`` replaced by the contextual text.
        All other fields are carried through unchanged.
    """
    raw_text = (
        chunk.get("text")
        or chunk.get("content_data")
        or ""
    )

    context_window: Optional[str] = None
    if all_page_items is not None and chunk_index is not None:
        context_window = _window_text(all_page_items, chunk_index, window=window_size)

    section_path = (
        chunk.get("normalized_section_path")
        or chunk.get("section_path")
        or chunk.get("section")
        or None
    )
    subsection = chunk.get("normalized_section_leaf") or chunk.get("subsection")

    contextual_prefix = build_contextual_prefix(
        chunk_text=raw_text,
        paper_title=paper_title,
        section_path=section_path,
        page_num=chunk.get("page_num") or chunk.get("page_start"),
        table_ref=chunk.get("table_ref") or chunk.get("table_id"),
        figure_ref=chunk.get("figure_ref") or chunk.get("figure_id"),
        subsection=subsection,
        context_window=context_window,
    )

    contextual_text = (
        f"{contextual_prefix}\n{raw_text}" if contextual_prefix else raw_text
    )

    enriched = {
        **chunk,
        "content_data": contextual_text,
        "contextual_prefix": contextual_prefix,
    }
    # Keep raw text for downstream quality scoring / BM25 fallback
    if "text" not in enriched or not enriched["text"]:
        enriched["text"] = raw_text
    enriched["raw_text"] = raw_text
    enriched["context_window"] = context_window or ""
    return enriched


def build_section_summary_text(
    section_name: str,
    chunks: List[Dict[str, Any]],
    paper_title: Optional[str] = None,
    max_total_len: int = 4000,
) -> str:
    """Concatenate a section's chunks into a section-level summary document.

    Used to populate the Summary Index so global / survey queries can retrieve
    section-level evidence rather than individual fragments.

    Args:
        section_name: Canonical section label (e.g. "Methods/Experimental Setup").
        chunks: All chunks belonging to this section, in page order.
        paper_title: Paper title for document-level context.
        max_total_len: Character cap for the resulting summary.

    Returns:
        Summary text ready for embedding.
    """
    lines: List[str] = []
    if paper_title:
        lines.append(f"[Paper: {paper_title.strip()[:200]}]")
    lines.append(f"[Section Summary: {section_name}]")

    # Collect unique text fragments from this section
    seen: set = set()
    body_parts: List[str] = []
    for chunk in chunks:
        raw = (
            chunk.get("raw_text")
            or chunk.get("text")
            or chunk.get("content_data")
            or ""
        ).strip()
        key = raw[:200]
        if raw and key not in seen:
            seen.add(key)
            body_parts.append(raw)

    combined = " ".join(body_parts)
    lines.append(combined)

    return "\n".join(lines)[:max_total_len]
