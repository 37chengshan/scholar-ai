"""Unit tests for Iteration 2 modules:
- contextual_chunk_builder
- citation_hints
- multi_index_router
"""

import pytest

# ─────────────────── contextual_chunk_builder ────────────────────


def _make_chunk(**kwargs):
    base = {
        "text": "BERT achieves 92.1 F1 on SQuAD 2.0.",
        "page_start": 3,
        "section": "Results",
        "raw_section_path": "4. Results",
        "table_ref": None,
        "figure_ref": None,
    }
    base.update(kwargs)
    return base


def test_build_contextual_text_basic():
    from app.core.contextual_chunk_builder import build_contextual_text

    result = build_contextual_text(
        chunk_text="BERT achieves 92.1 F1.",
        paper_title="Attention Is All You Need",
        section_path="Results",
        page_num=3,
    )
    assert "Attention Is All You Need" in result
    assert "Results" in result
    assert "BERT achieves 92.1 F1." in result


def test_build_contextual_text_with_table_ref():
    from app.core.contextual_chunk_builder import build_contextual_text

    result = build_contextual_text(
        chunk_text="See Table 3.",
        paper_title="BERT Paper",
        section_path="Experiments",
        page_num=5,
        table_ref="Table 3",
    )
    assert "Table 3" in result


def test_enrich_chunk_adds_fields():
    from app.core.contextual_chunk_builder import enrich_chunk

    chunk = _make_chunk()
    all_items = [{"page": 3, "text": "Context line.", "type": "text"}]
    result = enrich_chunk(
        chunk=chunk,
        paper_title="Test Paper",
        all_page_items=all_items,
        chunk_index=0,
        window_size=1,
    )
    assert "content_data" in result
    assert isinstance(result["content_data"], str)
    assert len(result["content_data"]) > 10
    assert "context_window" in result


def test_build_section_summary_text_basic():
    from app.core.contextual_chunk_builder import build_section_summary_text

    chunks = [
        {"text": "Result A: 90.1", "section": "Results"},
        {"text": "Result B: 91.2", "section": "Results"},
    ]
    result = build_section_summary_text("Results", chunks, "Test Paper")
    assert "Results" in result
    assert "Test Paper" in result
    assert "Result A" in result


def test_build_contextual_text_respects_max_len():
    from app.core.contextual_chunk_builder import build_contextual_text

    long_text = "word " * 2000
    result = build_contextual_text(
        chunk_text=long_text,
        paper_title="Long Paper",
        section_path="Results",
        page_num=1,
        max_total_len=500,
    )
    assert len(result) <= 500


# ──────────────────────── citation_hints ─────────────────────────


def _make_retrieved_chunk(paper_id="p1", method=None):
    return {
        "paper_id": paper_id,
        "content_data": "Uses BERT fine-tuning on NER task.",
        "section": "Methods",
        "method": method or "BERT",  # citation_hints reads 'method' (singular)
    }


def test_build_same_method_hints_basic():
    from app.core.citation_hints import build_same_method_hints

    # citation_hints uses chunk["method"] (singular string) and Jaccard on per-chunk methods
    retrieved = [_make_retrieved_chunk("p1", method="BERT")]
    candidates = [
        _make_retrieved_chunk("p2", method="BERT"),  # same method -> overlap=1.0
        _make_retrieved_chunk("p3", method="SVM"),   # different method
    ]
    hints = build_same_method_hints(retrieved, candidates, min_overlap=0.25, max_hints=5)
    assert any(h.paper_id == "p2" for h in hints)
    assert not any(h.paper_id == "p3" for h in hints)


def test_build_all_hints_returns_dict_keys():
    from app.core.citation_hints import build_all_hints

    retrieved = [_make_retrieved_chunk("p1")]
    result = build_all_hints(
        retrieved_chunks=retrieved,
        query_family="fact",
        citing_papers_meta=None,
        reference_entries=None,
        candidate_chunks=[],
        all_paper_meta=None,
    )
    assert set(result.keys()) == {"forward", "backward", "same_method", "evolution"}


def test_citation_hint_to_dict():
    from app.core.citation_hints import CitationHint

    hint = CitationHint(
        paper_id="p99",
        relation_type="same_method",
        cited_by_count=5,
        method_overlap=0.5,
        year=2021,
        title="Some Paper",
        hint_text="Shares BERT method",
    )
    d = hint.to_dict()
    assert d["paper_id"] == "p99"
    assert d["relation_type"] == "same_method"
    assert d["method_overlap"] == 0.5


# ──────────────────────── multi_index_router ─────────────────────


def test_route_fact_returns_local_evidence():
    from app.core.multi_index_router import route_query, primary_index

    plan = route_query("fact")
    assert primary_index("fact") == "local_evidence"
    assert any(r.index_type == "local_evidence" for r in plan.routes)


def test_route_survey_uses_summary_index():
    from app.core.multi_index_router import route_query, uses_summary_index

    plan = route_query("survey")
    assert uses_summary_index("survey") is True
    assert any(r.index_type == "summary" for r in plan.routes)


def test_route_evolution_uses_summary_index():
    from app.core.multi_index_router import uses_summary_index

    assert uses_summary_index("evolution") is True


def test_route_table_sets_content_type_filter():
    from app.core.multi_index_router import content_type_filters

    filters = content_type_filters("table")
    assert "table" in filters


def test_route_figure_sets_content_type_filter():
    from app.core.multi_index_router import content_type_filters

    filters = content_type_filters("figure")
    assert "image" in filters


def test_fact_query_includes_citation_hints():
    # 'fact' is in the hints set so include_citation_hints=True
    from app.core.multi_index_router import route_query

    plan = route_query("fact")
    assert plan.include_citation_hints is True


def test_compare_query_includes_citation_hints():
    from app.core.multi_index_router import route_query

    plan = route_query("compare")
    assert plan.include_citation_hints is True


def test_force_index_type_override():
    from app.core.multi_index_router import route_query

    plan = route_query("fact", force_index_type="summary")
    assert all(r.index_type == "summary" for r in plan.routes)
