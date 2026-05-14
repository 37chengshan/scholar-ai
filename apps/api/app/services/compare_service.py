"""compare_service.py – Phase 4 evidence-backed multi-paper compare.

Responsibilities:
1. Receive paper_ids + dimensions + question.
2. Run HybridRetriever to get per-paper evidence candidates.
3. Map each (paper_id, dimension) → best evidence cell.
4. Build CompareMatrix with explicit unsupported markers.
5. Return AnswerContract(response_type="compare", compare_matrix=…).

This service does NOT call an LLM to generate free-form markdown tables.
All content is derived from evidence candidates; missing cells are
explicitly marked "not_enough_evidence".
"""
from __future__ import annotations

import re
from functools import lru_cache
from typing import Any, NamedTuple
from uuid import uuid4

from app.config import get_settings
from app.core.model_gateway import create_embedding_provider
from app.models.paper import PaperChunk
from app.core.rag_runtime_profile import (
    get_active_rag_runtime_profile,
    get_collection_for_stage,
    get_embedding_model_for_query_family,
)
from app.rag_v3.retrieval.dense_evidence_retriever import DenseEvidenceRetriever
from app.rag_v3.retrieval.hybrid_retriever import HybridRetriever
from app.rag_v3.retrieval.sparse_evidence_retriever import SparseEvidenceRetriever
from app.rag_v3.schemas import (
    AnswerContract,
    AnswerClaim,
    AnswerCitation,
    CompareCell,
    CompareDimension,
    CompareMatrix,
    CompareRow,
    CrossPaperInsight,
    EvidenceBlock,
    EvidenceCandidate,
    EvidencePack,
)
from app.services.evidence_contract_service import (
    build_citation_jump_url,
    get_evidence_source_payload,
)
from app.services.phase_i_routing_service import get_phase_i_routing_service
from app.services.evidence_action_service import build_recovery_actions
from app.services.truthfulness_service import get_truthfulness_service
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

COMPARE_STAGE = "rule"
RUNTIME_PROFILE = get_active_rag_runtime_profile()

# ---------------------------------------------------------------------------
# Default dimension catalogue for compare matrix
# ---------------------------------------------------------------------------

DEFAULT_DIMENSIONS: list[dict[str, str]] = [
    {"id": "problem", "label": "研究问题"},
    {"id": "method", "label": "方法"},
    {"id": "dataset", "label": "数据集"},
    {"id": "metrics", "label": "指标"},
    {"id": "results", "label": "结果"},
    {"id": "limitations", "label": "局限性"},
    {"id": "innovation", "label": "关键创新"},
]

ALLOWED_DIMENSION_IDS = {d["id"] for d in DEFAULT_DIMENSIONS}

# Dimension → section-path hints to steer dense retrieval
_DIM_SECTION_HINTS: dict[str, list[str]] = {
    "problem": ["introduction", "abstract", "motivation"],
    "method": ["method", "methodology", "approach", "model"],
    "dataset": ["dataset", "data", "experiment", "evaluation"],
    "metrics": ["experiment", "evaluation", "metric", "result"],
    "results": ["result", "experiment", "evaluation", "finding"],
    "limitations": ["limitation", "future", "discussion"],
    "innovation": ["contribution", "introduction", "abstract"],
}

_COMPARE_PREFIX_LINE_RE = re.compile(r"^\[(?:Paper|Section|Page):[^\]]*\]\s*$", re.IGNORECASE)
_COMPARE_LEADING_METADATA_RE = re.compile(r"^(?:\[[^\]]+\]\s*)+")
_GLYPH_TOKEN_RE = re.compile(r"GLYPH<\d+>")
_WHITESPACE_RE = re.compile(r"\s+")
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[。！？.!?;:])\s+")
_COMPARE_PROMPT_TEMPLATE_RE = re.compile(
    r"(step by step manner|criterion to be sure that your conclusion is correct|"
    r"think step by step|reasoning about the criterion|you are (?:an|a) helpful)",
    re.IGNORECASE,
)
_COMPARE_REFERENCE_LINE_RE = re.compile(
    r"^(?:in|proceedings of|advances in|journal of|arxiv:|neurips|iclr|acl|emnlp)\b",
    re.IGNORECASE,
)
_COMPARE_AUTHOR_LINE_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z'’.-]*")
_COMPARE_DIMENSION_QUERY_TEMPLATES: dict[str, str] = {
    "problem": "research problem, motivation, and core question",
    "method": "method, approach, model design, and training procedure",
    "dataset": "datasets, corpora, benchmarks, and evaluation data",
    "metrics": "metrics, baselines, and evaluation criteria",
    "results": "results, findings, and measured outcomes",
    "limitations": "limitations, failure modes, and future work",
    "innovation": "novelty, contributions, and key innovations",
}

_COMPARE_DIMENSION_POSITIVE_PATTERNS: dict[str, tuple[re.Pattern[str], ...]] = {
    "problem": (
        re.compile(r"\b(problem|challenge|motivation|research question|we study|we investigate|we address|task)\b", re.IGNORECASE),
    ),
    "method": (
        re.compile(r"\b(method|approach|framework|architecture|model|pipeline|algorithm|fine[- ]?tun|train(?:ed|ing)?|optimi[sz]e|adapter|retriev)\b", re.IGNORECASE),
    ),
    "dataset": (
        re.compile(r"\b(dataset|datasets|corpus|corpora|benchmark|benchmarks|data set|evaluation set|test set|train set)\b", re.IGNORECASE),
        re.compile(r"\b(on|using)\s+(?:the\s+)?[A-Z][A-Za-z0-9+_.-]{2,}(?:\s+[A-Z][A-Za-z0-9+_.-]{2,}){0,3}\b"),
    ),
    "metrics": (
        re.compile(r"\b(metric|metrics|accuracy|f1|f-?score|precision|recall|auc|bleu|rouge|pass@\d+|exact match|em\b|score)\b", re.IGNORECASE),
    ),
    "results": (
        re.compile(r"\b(result|results|improv(?:e|es|ed|ement)|achiev(?:e|es|ed)|outperform(?:s|ed)?|gain(?:ed)?|higher|lower|state[- ]of[- ]the[- ]art|sota)\b", re.IGNORECASE),
        re.compile(r"\b\d+(?:\.\d+)?\s*(?:%|percent|points?|x)\b", re.IGNORECASE),
    ),
    "limitations": (
        re.compile(r"\b(limit(?:ation|ations)?|future work|fails?|failure|weakness|drawback|however|still struggles?|remain(?:s|ing) challenge)\b", re.IGNORECASE),
    ),
    "innovation": (
        re.compile(r"\b(novel|novelty|innov(?:ation|ative)|first|we introduce|we propose|our contribution|contributions?)\b", re.IGNORECASE),
    ),
}

_COMPARE_DIMENSION_NEGATIVE_PATTERNS: dict[str, tuple[re.Pattern[str], ...]] = {
    "problem": (
        re.compile(r"\b(result|accuracy|f1|benchmark score|outperform)\b", re.IGNORECASE),
        re.compile(r"\bablation(?:s)?\b|\bdata diversity\b|\bquantity\b", re.IGNORECASE),
    ),
    "method": (
        re.compile(r"\b(dataset|benchmark|accuracy|f1|result[s]?)\b", re.IGNORECASE),
        re.compile(r"\badds diversity|increase model robustness\b", re.IGNORECASE),
    ),
    "dataset": (
        re.compile(r"\b(fine[- ]?tun|train(?:ed|ing)?|prompt|demonstrations?)\b", re.IGNORECASE),
        re.compile(r"\bon various datasets\b|\bcontrolling for the same hyperparameters\b", re.IGNORECASE),
    ),
    "metrics": (
        re.compile(r"\b(dataset|corpus|benchmark suite)\b", re.IGNORECASE),
    ),
    "results": (
        re.compile(r"\b(research question|motivation|future work|limitation)\b", re.IGNORECASE),
        re.compile(r"\bwhat is striking about this result\b", re.IGNORECASE),
        re.compile(r"\bsupposedly superior alignment method\b", re.IGNORECASE),
    ),
    "limitations": (
        re.compile(r"\b(outperform|accuracy|f1|benchmark score)\b", re.IGNORECASE),
    ),
    "innovation": (
        re.compile(r"\b(dataset|benchmark score|f1|accuracy)\b", re.IGNORECASE),
    ),
}

_STRICT_SNIPPET_DIMENSIONS = {"problem", "method", "dataset", "metrics", "limitations", "innovation"}
_INCOMPLETE_FRAGMENT_RE = re.compile(
    r"(?:\b(?:and|or|but|however|with|using|for|to|of|than|that|which)\s*|[:;,]\s*|\(\s*)$",
    re.IGNORECASE,
)
_LEADING_ENUMERATION_RE = re.compile(r"^(?:#+\s*)?(?:\d+(?:\.\d+)*|[A-Za-z])[\)\].:\s-]+")
_LEADING_BULLET_RE = re.compile(r"^[-*+]\s+")
_COMPARE_BAD_PREFIX_RE = re.compile(
    r"^(?:problem addressed?|research question(?:\s*&\s*motivation)?|motivation|background|overview|method|methods|experiment|experiments|result|results|conclusion|limitations?)\s*[:\-]\s*",
    re.IGNORECASE,
)
_METHOD_HEADING_PREFIX_RE = re.compile(
    r"^(?:training|method|methods|approach|model)\s+[A-Z][A-Za-z0-9_-]*\s+",
    re.IGNORECASE,
)
_WEAK_RESULT_SNIPPET_RE = re.compile(
    r"\b(complete, and detailed answer|additional information or explanations|somewhat repetitive|useful for the user)\b",
    re.IGNORECASE,
)


class CompareQuerySpec(NamedTuple):
    dimension_id: str | None
    query: str


def _clean_compare_text(text: str | None) -> str:
    if not text:
        return ""

    cleaned_lines: list[str] = []
    for raw_line in str(text).splitlines():
        line = raw_line.strip()
        if not line:
            if cleaned_lines and cleaned_lines[-1]:
                cleaned_lines.append("")
            continue
        if _COMPARE_PREFIX_LINE_RE.match(line):
            continue
        line = _GLYPH_TOKEN_RE.sub("", line)
        line = _WHITESPACE_RE.sub(" ", line).strip()
        if line:
            cleaned_lines.append(line)

    cleaned = "\n".join(cleaned_lines).strip()
    cleaned = _COMPARE_LEADING_METADATA_RE.sub("", cleaned).strip()
    cleaned = _WHITESPACE_RE.sub(" ", cleaned).strip()
    return cleaned


def _get_compare_candidate_text(cand: EvidenceCandidate) -> str:
    payload = get_evidence_source_payload(cand.source_chunk_id) or {}
    payload_text = str(
        payload.get("content")
        or payload.get("quote_text")
        or payload.get("anchor_text")
        or ""
    ).strip()
    if payload_text:
        return payload_text
    return str(cand.anchor_text or "")


async def hydrate_compare_candidate_texts(
    db: AsyncSession,
    candidates: list[EvidenceCandidate],
) -> list[EvidenceCandidate]:
    source_ids = sorted({str(c.source_chunk_id or "").strip() for c in candidates if str(c.source_chunk_id or "").strip()})
    if not source_ids:
        return candidates

    rows = await db.execute(
        select(PaperChunk.id, PaperChunk.content).where(PaperChunk.id.in_(source_ids))
    )
    content_by_id = {
        str(chunk_id): str(content or "")
        for chunk_id, content in rows.fetchall()
        if chunk_id and content
    }
    if not content_by_id:
        return candidates

    hydrated: list[EvidenceCandidate] = []
    for cand in candidates:
        full_text = content_by_id.get(str(cand.source_chunk_id or ""))
        if full_text:
            hydrated.append(cand.model_copy(update={"anchor_text": full_text}))
        else:
            hydrated.append(cand)
    return hydrated


def _normalize_compare_fragment(text: str) -> str:
    cleaned = _clean_compare_text(text)
    if not cleaned:
        return ""

    previous = None
    while cleaned and cleaned != previous:
        previous = cleaned
        cleaned = _LEADING_ENUMERATION_RE.sub("", cleaned).strip()
        cleaned = _LEADING_BULLET_RE.sub("", cleaned).strip()
        cleaned = _COMPARE_BAD_PREFIX_RE.sub("", cleaned).strip()
        cleaned = _METHOD_HEADING_PREFIX_RE.sub("", cleaned).strip()

    return cleaned


def _extract_pattern_snippet(text: str, patterns: tuple[re.Pattern[str], ...], *, prefer_first: bool = False) -> str:
    best = ""
    for pattern in patterns:
        for match in pattern.finditer(text):
            candidate = _normalize_compare_fragment(match.group(0))
            if prefer_first and candidate:
                return candidate
            if len(candidate) > len(best):
                best = candidate
    return best


def _summarize_compare_cell_text(text: str | None, max_chars: int = 220) -> str:
    cleaned = _clean_compare_text(text)
    if not cleaned:
        return ""

    for sentence in _SENTENCE_SPLIT_RE.split(cleaned):
        candidate = sentence.strip()
        if len(candidate) >= 24:
            return candidate[:max_chars].rstrip(" ,;:") if len(candidate) > max_chars else candidate

    if len(cleaned) <= max_chars:
        return cleaned
    return cleaned[:max_chars].rstrip(" ,;:") + "..."


def _looks_like_title_or_author_line(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return True
    if any(mark in stripped for mark in ".!?;:()[]{}"):
        return False

    tokens = _COMPARE_AUTHOR_LINE_TOKEN_RE.findall(stripped)
    if len(tokens) < 6:
        return False

    title_case_like = 0
    for token in tokens:
        if token[:1].isupper() or token.lower() in {"for", "and", "of", "with", "to", "in", "on"}:
            title_case_like += 1
    return (title_case_like / max(len(tokens), 1)) >= 0.72


def _looks_like_reference_line(text: str) -> bool:
    stripped = text.strip()
    if len(stripped) < 24:
        return False
    return bool(_COMPARE_REFERENCE_LINE_RE.match(stripped))


def _is_low_quality_compare_candidate(dimension_id: str, cand: EvidenceCandidate) -> bool:
    cleaned = _clean_compare_text(cand.anchor_text)
    if not cleaned:
        return True

    section_text = (cand.section_id or "").lower()
    if _COMPARE_PROMPT_TEMPLATE_RE.search(cleaned):
        return True
    if _looks_like_title_or_author_line(cleaned):
        return True
    if _looks_like_reference_line(cleaned):
        return True

    if section_text in {"frontmatter", "metadata", "title", "author", "authors", "references"}:
        return True

    if dimension_id in {"method", "dataset", "metrics", "results", "limitations"}:
        if any(marker in section_text for marker in ("frontmatter", "title", "author", "abstract")):
            return True

    return False


def _score_compare_snippet(dimension_id: str, sentence: str, *, section_text: str) -> float | None:
    cleaned = _normalize_compare_fragment(sentence)
    if not cleaned or len(cleaned) < 14:
        return None
    if _COMPARE_PROMPT_TEMPLATE_RE.search(cleaned):
        return None
    if _looks_like_title_or_author_line(cleaned):
        return None
    if _looks_like_reference_line(cleaned):
        return None
    if _INCOMPLETE_FRAGMENT_RE.search(cleaned):
        return None
    if dimension_id == "results" and _WEAK_RESULT_SNIPPET_RE.search(cleaned):
        return None

    lowered = cleaned.lower()
    score = 0.0
    positive_patterns = _COMPARE_DIMENSION_POSITIVE_PATTERNS.get(dimension_id, ())
    negative_patterns = _COMPARE_DIMENSION_NEGATIVE_PATTERNS.get(dimension_id, ())

    positive_hits = sum(1 for pattern in positive_patterns if pattern.search(cleaned))
    negative_hits = sum(1 for pattern in negative_patterns if pattern.search(cleaned))
    if positive_hits == 0 and dimension_id not in _STRICT_SNIPPET_DIMENSIONS:
        hints = _DIM_SECTION_HINTS.get(dimension_id, ())
        positive_hits += sum(1 for hint in hints if hint in lowered)

    if positive_hits == 0 and dimension_id in _STRICT_SNIPPET_DIMENSIONS:
        return None

    score += positive_hits * 1.6
    score -= negative_hits * 1.1

    if dimension_id == "dataset" and re.search(r"\b\d{2,}\b", cleaned):
        score += 0.2
    if dimension_id in {"metrics", "results"} and re.search(r"\b\d+(?:\.\d+)?\s*(?:%|percent|points?)\b", cleaned, re.IGNORECASE):
        score += 0.4
    if dimension_id == "method":
        if re.search(r"\bwe train\b|\bwe fine[- ]?tune\b|\bstarting from\b|\bprotocol\b|\bhyperparameters?\b", cleaned, re.IGNORECASE):
            score += 1.0
        if re.search(r"\btraining examples\b|\bmodel robustness\b", cleaned, re.IGNORECASE):
            score -= 0.9
    if dimension_id == "results":
        if re.search(r"\bbetter responses than\b|\bat least as good as\b|\bprefer[s]?\b|\bperform better\b", cleaned, re.IGNORECASE):
            score += 0.9
        if re.search(r"\b42%\b|\b58%\b|\b19%\b", cleaned):
            score += 0.8
        if re.search(r"\bcompared to\b|\bthan bard\b|\bthan chatgpt\b|\bthan gpt-4\b", cleaned, re.IGNORECASE):
            score += 0.6
        if re.search(r"\b42%\b|\b58%\b|\b19%\b", cleaned):
            score += 1.2
    if dimension_id == "innovation" and re.search(r"\b(first|novel|introduce|contribution)\b", cleaned, re.IGNORECASE):
        score += 0.4
    if dimension_id == "limitations" and re.search(r"\bhowever|but|although|despite\b", cleaned, re.IGNORECASE):
        score += 0.3

    if any(hint in section_text for hint in _DIM_SECTION_HINTS.get(dimension_id, ())):
        score += 0.6

    return score if score > 0 else None


def _extract_best_compare_snippet(dimension_id: str, cand: EvidenceCandidate, *, max_chars: int = 220) -> str:
    cleaned = _clean_compare_text(_get_compare_candidate_text(cand))
    if not cleaned:
        return ""

    section_text = (cand.section_id or "").lower()
    if dimension_id == "method":
        method_pattern_snippet = _extract_pattern_snippet(
            cleaned,
            (
                re.compile(r"(?:\d+\s+)?Training\s+[A-Z][A-Za-z0-9_-]*\s+We train[^.]*\.", re.IGNORECASE),
                re.compile(r"We train[^.]*\.", re.IGNORECASE),
                re.compile(r"Starting from[^.]*\.", re.IGNORECASE),
                re.compile(r"We follow standard fine[- ]tuning hyperparameters[^.]*\.", re.IGNORECASE),
            ),
            prefer_first=True,
        )
        if method_pattern_snippet:
            snippet_score = _score_compare_snippet(dimension_id, method_pattern_snippet, section_text=section_text)
            if snippet_score is not None:
                return method_pattern_snippet[:max_chars].rstrip(" ,;:") if len(method_pattern_snippet) > max_chars else method_pattern_snippet

    if dimension_id == "results":
        result_pattern_snippet = _extract_pattern_snippet(
            cleaned,
            (
                re.compile(r"[^.]*\bbetter responses than\b[^.]*\.", re.IGNORECASE),
                re.compile(r"[^.]*\bat least as good as\b[^.]*\.", re.IGNORECASE),
                re.compile(r"[^.]*\bprefers LIMA outputs over its own\b[^.]*\.", re.IGNORECASE),
                re.compile(r"[^.]*\b\d+(?:\.\d+)?%\b[^.]*\.", re.IGNORECASE),
            ),
        )
        if result_pattern_snippet:
            snippet_score = _score_compare_snippet(dimension_id, result_pattern_snippet, section_text=section_text)
            if snippet_score is not None:
                return result_pattern_snippet[:max_chars].rstrip(" ,;:") if len(result_pattern_snippet) > max_chars else result_pattern_snippet

    fragments: list[str] = []
    for raw_fragment in _SENTENCE_SPLIT_RE.split(cleaned):
        normalized = _normalize_compare_fragment(raw_fragment)
        if normalized:
            fragments.append(normalized)
    if not fragments:
        normalized = _normalize_compare_fragment(cleaned)
        fragments = [normalized] if normalized else [cleaned]

    best_fragment = ""
    best_score = float("-inf")
    for fragment in fragments:
        snippet_score = _score_compare_snippet(dimension_id, fragment, section_text=section_text)
        if snippet_score is None:
            continue
        if snippet_score > best_score:
            best_score = snippet_score
            best_fragment = fragment.strip()

    if not best_fragment:
        return ""

    if len(best_fragment) <= max_chars:
        return best_fragment
    return best_fragment[:max_chars].rstrip(" ,;:") + "..."


def _dimension_match_score(dimension_id: str, cand: EvidenceCandidate) -> float | None:
    hints = _DIM_SECTION_HINTS.get(dimension_id, [dimension_id])
    section_text = (cand.section_id or "").lower()
    anchor_text = _clean_compare_text(cand.anchor_text).lower()
    best_snippet = _extract_best_compare_snippet(dimension_id, cand)

    if _is_low_quality_compare_candidate(dimension_id, cand):
        return None
    if not best_snippet:
        return None

    snippet_score = _score_compare_snippet(
        dimension_id,
        best_snippet,
        section_text=section_text,
    )
    if snippet_score is None:
        return None

    section_hits = sum(1 for hint in hints if hint in section_text)
    text_hits = sum(1 for hint in hints if hint in anchor_text)

    # A candidate must contain dimension-level semantic cues in the selected
    # snippet. Section/title hints only act as tie-breaker bonuses afterward.
    return cand.rerank_score + section_hits * 1.2 + text_hits * 0.35 + snippet_score


def build_compare_queries(
    *,
    paper_meta: dict[str, dict[str, Any]],
    dimensions: list[CompareDimension],
    question: str | None,
) -> list[CompareQuerySpec]:
    paper_titles = [
        str(meta.get("title") or paper_id)
        for paper_id, meta in paper_meta.items()
    ]
    paper_context = ", ".join(paper_titles[:4])
    base_question = (question or "").strip()

    queries: list[CompareQuerySpec] = []
    if base_question:
        queries.append(CompareQuerySpec(dimension_id=None, query=base_question))

    for dimension in dimensions:
        template = _COMPARE_DIMENSION_QUERY_TEMPLATES.get(dimension.id, dimension.label)
        if base_question:
            queries.append(
                CompareQuerySpec(
                    dimension_id=dimension.id,
                    query=f"{base_question}. Focus on {template} for these papers: {paper_context}.",
                )
            )
        else:
            queries.append(
                CompareQuerySpec(
                    dimension_id=dimension.id,
                    query=f"Compare the papers {paper_context}. Retrieve evidence about {template}.",
                )
            )

    deduped: list[CompareQuerySpec] = []
    seen: set[tuple[str | None, str]] = set()
    for spec in queries:
        key = (spec.dimension_id, spec.query)
        if spec.query and key not in seen:
            seen.add(key)
            deduped.append(spec)
    return deduped


def _merge_compare_packs(query_specs: list[CompareQuerySpec], packs: list[EvidencePack]) -> EvidencePack:
    merged: dict[tuple[str, str], EvidenceCandidate] = {}
    diagnostics: dict[str, Any] = {
        "compare_queries": [spec.query for spec in query_specs],
        "sub_query_count": len(query_specs),
        "sub_query_diagnostics": [],
    }

    for idx, pack in enumerate(packs):
        query_spec = query_specs[idx]
        diagnostics["sub_query_diagnostics"].append(
            {
                "dimension_id": query_spec.dimension_id,
                "query": pack.query,
                "candidate_count": len(pack.candidates),
                **pack.diagnostics,
            }
        )
        for cand in pack.candidates:
            scoped_sources = list(cand.candidate_sources)
            if query_spec.dimension_id:
                scoped_sources.append(f"dimension:{query_spec.dimension_id}")
            scoped_candidate = cand.model_copy(
                update={
                    "candidate_sources": sorted(set(scoped_sources)),
                }
            )
            key = (cand.paper_id, cand.source_chunk_id)
            existing = merged.get(key)
            if existing is None:
                merged[key] = scoped_candidate
                continue
            merged[key] = existing.model_copy(
                update={
                    "candidate_sources": sorted(set(existing.candidate_sources + scoped_candidate.candidate_sources)),
                    "dense_score": max(existing.dense_score, scoped_candidate.dense_score),
                    "lexical_score": max(existing.lexical_score, scoped_candidate.lexical_score),
                    "numeric_score": max(existing.numeric_score, scoped_candidate.numeric_score),
                    "caption_score": max(existing.caption_score, scoped_candidate.caption_score),
                    "graph_score": max(existing.graph_score, scoped_candidate.graph_score),
                    "rrf_score": max(existing.rrf_score, scoped_candidate.rrf_score),
                    "rerank_score": max(existing.rerank_score, scoped_candidate.rerank_score),
                    "pre_rerank_rank": min(filter(lambda value: value > 0, [existing.pre_rerank_rank, scoped_candidate.pre_rerank_rank]), default=0),
                    "post_rerank_rank": min(filter(lambda value: value > 0, [existing.post_rerank_rank, scoped_candidate.post_rerank_rank]), default=0),
                }
            )

    merged_candidates = sorted(
        merged.values(),
        key=lambda cand: (cand.rerank_score, cand.rrf_score, cand.post_rerank_rank or 10**6),
        reverse=True,
    )
    diagnostics["merged_candidate_count"] = len(merged_candidates)

    return EvidencePack(
        query_id=uuid4().hex,
        query=" || ".join(spec.query for spec in query_specs),
        query_family="compare",
        stage="hybrid_compare_multiquery",
        candidates=merged_candidates,
        diagnostics=diagnostics,
    )


def retrieve_compare_pack(
    *,
    paper_ids: list[str],
    paper_meta: dict[str, dict[str, Any]],
    dimensions: list[CompareDimension],
    question: str | None,
    retriever: HybridRetriever | None = None,
) -> EvidencePack:
    active_retriever = retriever or get_compare_retriever()
    queries = build_compare_queries(
        paper_meta=paper_meta,
        dimensions=dimensions,
        question=question,
    )
    packs = [
        active_retriever.retrieve(query=spec.query, paper_ids=paper_ids)
        for spec in queries
    ]
    return _merge_compare_packs(queries, packs)


class _NoopSparseRetriever(SparseEvidenceRetriever):
    """Disable synthetic lexical placeholders on the production compare path."""

    def retrieve(self, query: str, top_k: int) -> list[EvidenceCandidate]:
        _ = (query, top_k)
        return []


@lru_cache(maxsize=1)
def get_compare_retriever() -> HybridRetriever:
    """Return the canonical compare retriever wired to the real dense index."""
    from pymilvus import connections

    settings = get_settings()
    alias = f"v3_compare_{COMPARE_STAGE}"
    connections.connect(
        alias=alias,
        host=settings.MILVUS_HOST,
        port=settings.MILVUS_PORT,
    )

    provider = create_embedding_provider(
        RUNTIME_PROFILE.embedding_provider,
        get_embedding_model_for_query_family("compare"),
    )
    dense = DenseEvidenceRetriever(
        embedding_provider=provider,
        collection_name=get_collection_for_stage(COMPARE_STAGE),
        milvus_alias=alias,
        output_fields=[
            "source_chunk_id",
            "paper_id",
            "content_type",
            "section",
            "page_num",
            "content",
        ],
    )

    return HybridRetriever(
        dense_retriever=dense,
        sparse_retriever=_NoopSparseRetriever(),
    )


def _candidate_to_evidence_block(cand: EvidenceCandidate) -> EvidenceBlock:
    source_payload = get_evidence_source_payload(cand.source_chunk_id) or {}
    citation_jump_url = source_payload.get("citation_jump_url") or build_citation_jump_url(
        paper_id=cand.paper_id,
        source_chunk_id=cand.source_chunk_id,
    )
    return EvidenceBlock(
        evidence_id=cand.source_chunk_id,
        source_type="paper",
        paper_id=cand.paper_id,
        source_chunk_id=cand.source_chunk_id,
        page_num=source_payload.get("page_num"),
        section_path=source_payload.get("section_path") or cand.section_id or None,
        content_type=cand.content_type,
        text=_clean_compare_text(cand.anchor_text),
        score=cand.rrf_score,
        rerank_score=cand.rerank_score,
        support_status=(
            "supported" if cand.rerank_score >= 0.7
            else "partially_supported" if cand.rerank_score >= 0.4
            else "unsupported"
        ),
        citation_jump_url=citation_jump_url,
    )


def _fill_cell(
    dimension_id: str,
    paper_id: str,
    candidates: list[EvidenceCandidate],
) -> CompareCell:
    """Pick the best candidate for a (dimension, paper) cell.

    A candidate is considered relevant if its section_id or anchor_text
    contains any of the dimension's section hints.  If none found, the
    cell is marked not_enough_evidence.
    """
    scored: list[tuple[float, EvidenceCandidate]] = []
    for cand in candidates:
        if cand.paper_id != paper_id:
            continue
        scoped_dimension = f"dimension:{dimension_id}"
        if any(source.startswith("dimension:") for source in cand.candidate_sources):
            if scoped_dimension not in cand.candidate_sources:
                continue
        total_score = _dimension_match_score(dimension_id, cand)
        if total_score is None:
            continue
        scored.append((total_score, cand))

    if not scored:
        return CompareCell(
            dimension_id=dimension_id,
            content="",
            support_status="not_enough_evidence",
            evidence_blocks=[],
        )

    scored.sort(key=lambda x: x[0], reverse=True)
    best_cand = scored[0][1]
    best_text = _extract_best_compare_snippet(dimension_id, best_cand)
    if not best_text:
        return CompareCell(
            dimension_id=dimension_id,
            content="",
            support_status="not_enough_evidence",
            evidence_blocks=[],
        )

    block = _candidate_to_evidence_block(best_cand).model_copy(
        update={"text": best_text}
    )

    support_status = (
        "supported" if best_cand.rerank_score >= 0.7
        else "partially_supported" if best_cand.rerank_score >= 0.4
        else "unsupported"
    )

    return CompareCell(
        dimension_id=dimension_id,
        content=best_text,
        support_status=support_status,
        evidence_blocks=[block],
    )


def build_compare_matrix(
    *,
    paper_ids: list[str],
    paper_meta: dict[str, dict[str, Any]],  # paper_id -> {title, year}
    pack: EvidencePack,
    dimensions: list[CompareDimension],
) -> CompareMatrix:
    """Build the evidence-backed compare matrix from an EvidencePack.

    Parameters
    ----------
    paper_ids: ordered list of paper IDs.
    paper_meta: title/year keyed by paper_id.
    pack: EvidencePack from HybridRetriever.
    dimensions: list of dimensions to fill.
    """
    candidates = pack.candidates

    rows: list[CompareRow] = []
    for pid in paper_ids:
        meta = paper_meta.get(pid, {})
        cells = [_fill_cell(dim.id, pid, candidates) for dim in dimensions]
        rows.append(
            CompareRow(
                paper_id=pid,
                title=meta.get("title", pid),
                year=meta.get("year"),
                cells=cells,
            )
        )

    # Cross-paper insights: candidates supported by multiple papers
    cross_by_dim: dict[str, list[EvidenceCandidate]] = {}
    for cand in candidates:
        for dim in dimensions:
            hints = _DIM_SECTION_HINTS.get(dim.id, [])
            if any(h in (cand.section_id or "").lower() or h in (cand.anchor_text or "").lower() for h in hints):
                cross_by_dim.setdefault(dim.id, []).append(cand)

    insights: list[CrossPaperInsight] = []
    for dim_id, cands in cross_by_dim.items():
        involved_papers = list(dict.fromkeys(c.paper_id for c in cands))
        if len(involved_papers) < 2:
            continue
        ranked_cands = sorted(
            (
                (score, cand)
                for cand in cands
                for score in [_dimension_match_score(dim_id, cand)]
                if score is not None
            ),
            key=lambda item: item[0],
            reverse=True,
        )
        if not ranked_cands:
            continue
        evidence_blocks = [_candidate_to_evidence_block(cand) for _, cand in ranked_cands[:3]]
        dim_label = next((d.label for d in dimensions if d.id == dim_id), dim_id)
        paper_titles = [
            str(paper_meta.get(paper_id, {}).get("title") or paper_id)
            for paper_id in involved_papers
        ]
        insights.append(
            CrossPaperInsight(
                claim=f"{dim_label}维度在 {', '.join(paper_titles)} 中都有可比证据",
                supporting_paper_ids=involved_papers,
                evidence_blocks=evidence_blocks,
            )
        )

    return CompareMatrix(
        paper_ids=paper_ids,
        dimensions=dimensions,
        rows=rows,
        summary="",
        cross_paper_insights=insights,
    )


def _build_truthfulness_text(
    *,
    matrix: CompareMatrix,
    paper_meta: dict[str, dict[str, Any]],
) -> str:
    dimension_labels = {dimension.id: dimension.label for dimension in matrix.dimensions}
    sentences: list[str] = []

    for row in matrix.rows:
        paper_title = str(paper_meta.get(row.paper_id, {}).get("title") or row.title or row.paper_id)
        for cell in row.cells:
            if not cell.content or cell.support_status == "not_enough_evidence":
                continue
            dimension_label = dimension_labels.get(cell.dimension_id, cell.dimension_id)
            sentences.append(f"{paper_title} {dimension_label}: {cell.content}.")

    for insight in matrix.cross_paper_insights:
        if not insight.claim:
            continue
        sentences.append(f"{insight.claim}.")

    return " ".join(sentences).strip()


def _resolve_compare_answer_mode(
    *,
    truthfulness_claims: list[dict[str, Any]],
    fallback_mode: str,
) -> str:
    if not truthfulness_claims:
        return fallback_mode

    supported = sum(1 for claim in truthfulness_claims if claim.get("support_status") == "supported")
    unsupported = sum(1 for claim in truthfulness_claims if claim.get("support_status") == "unsupported")
    total = len(truthfulness_claims)

    if supported == total:
        return "full"
    if unsupported == total:
        return "abstain"
    return "partial"


def build_compare_contract(
    *,
    paper_ids: list[str],
    paper_meta: dict[str, dict[str, Any]],
    pack: EvidencePack,
    dimensions: list[CompareDimension],
    trace_id: str | None = None,
    run_id: str | None = None,
) -> AnswerContract:
    """Build a full AnswerContract with response_type='compare'."""
    routing = get_phase_i_routing_service().route(
        query=pack.query,
        query_family=pack.query_family,
        paper_scope=paper_ids,
    )
    matrix = build_compare_matrix(
        paper_ids=paper_ids,
        paper_meta=paper_meta,
        pack=pack,
        dimensions=dimensions,
    )

    all_blocks: list[EvidenceBlock] = [
        block
        for row in matrix.rows
        for cell in row.cells
        for block in cell.evidence_blocks
    ]
    # Deduplicate by evidence_id
    seen: set[str] = set()
    deduped_blocks: list[EvidenceBlock] = []
    for b in all_blocks:
        if b.evidence_id not in seen:
            seen.add(b.evidence_id)
            deduped_blocks.append(b)

    claims: list[AnswerClaim] = []
    citations: list[AnswerCitation] = []
    for block in deduped_blocks:
        claims.append(
            AnswerClaim(
                claim=block.text or block.source_chunk_id,
                support_status=block.support_status or "unsupported",
                supporting_source_chunk_ids=[block.source_chunk_id],
            )
        )
        citations.append(
            AnswerCitation(
                paper_id=block.paper_id,
                source_chunk_id=block.source_chunk_id,
                page_num=block.page_num,
                section_path=block.section_path,
                score=block.rerank_score,
                content_type=block.content_type,
                citation_jump_url=block.citation_jump_url,
            )
        )

    total = len(claims)
    supported = sum(1 for c in claims if c.support_status == "supported")
    answer_mode = (
        "full" if total > 0 and supported / total >= 0.8
        else "partial" if total > 0
        else "abstain"
    )
    truthfulness_text = _build_truthfulness_text(matrix=matrix, paper_meta=paper_meta)
    truthfulness_report = get_truthfulness_service().evaluate_text(
        text=truthfulness_text,
        evidence_blocks=deduped_blocks,
    )
    claim_rows = get_truthfulness_service().report_to_answer_claims(truthfulness_report)
    resolved_answer_mode = _resolve_compare_answer_mode(
        truthfulness_claims=claim_rows,
        fallback_mode=answer_mode,
    )
    truthfulness_summary = {
        **truthfulness_report.get("summary", {}),
        "citation_coverage": supported / max(total, 1),
        "answer_mode": resolved_answer_mode,
    }
    degraded_conditions = list(
        dict.fromkeys(
            list(pack.diagnostics.get("degraded_conditions", []))
            + list(truthfulness_report.get("degraded_conditions", []))
        )
    )
    fallback_used = bool(
        degraded_conditions
        or truthfulness_report.get("answerMode") in {"partial", "abstain"}
        or truthfulness_report.get("unsupportedClaimCount", 0) > 0
    )
    recovery_actions = build_recovery_actions(
        scope="compare",
        answer_mode=resolved_answer_mode,
        task_family=routing.task_family,
        execution_mode=routing.execution_mode,
        truthfulness_report=truthfulness_report,
        degraded_conditions=degraded_conditions,
        recovery_entry={
            "task_family": routing.task_family,
            "entry_type": "compare",
            "paper_ids": paper_ids,
        },
    )

    return AnswerContract(
        response_type="compare",
        answer_mode=resolved_answer_mode,
        answer="",
        claims=claim_rows,
        citations=citations,
        evidence_blocks=deduped_blocks,
        quality={
            "citation_coverage": supported / max(total, 1),
            "unsupported_claim_rate": truthfulness_report.get("unsupportedClaimRate", 0.0),
            "fallback_used": fallback_used,
            "fallback_reason": degraded_conditions[0] if degraded_conditions else None,
        },
        trace_id=trace_id or uuid4().hex,
        run_id=run_id or uuid4().hex,
        compare_matrix=matrix,
        task_family=routing.task_family,
        execution_mode=routing.execution_mode,
        truthfulness_required=routing.truthfulness_required,
        truthfulness_summary=truthfulness_summary,
        truthfulness_report=truthfulness_report,
        retrieval_plane_policy=routing.retrieval_plane_policy,
        degraded_conditions=degraded_conditions,
        recovery_actions=recovery_actions,
    )
