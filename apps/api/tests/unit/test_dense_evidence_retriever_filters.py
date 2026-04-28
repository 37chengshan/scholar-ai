from app.rag_v3.retrieval.dense_evidence_retriever import DenseEvidenceRetriever



def test_build_filter_expression_supports_phase3_filters():
    expr = DenseEvidenceRetriever._build_filter_expression(
        paper_id_filter=["paper-1"],
        section_paths=["methods/model", "results"],
        page_from=3,
        page_to=8,
        content_types=["text", "table"],
    )

    assert 'paper_id in ["paper-1"]' in expr
    assert 'normalized_section_path like "methods/model%"' in expr
    assert 'normalized_section_path like "results%"' in expr
    assert "page_num >= 3" in expr
    assert "page_num <= 8" in expr
    assert 'content_type in ["text", "table"]' in expr



def test_build_filter_expression_falls_back_to_indexable_only():
    expr = DenseEvidenceRetriever._build_filter_expression()

    assert expr == "indexable == true"


def test_dense_fallback_preserves_phase3_filters():
    retriever = DenseEvidenceRetriever(
        embedding_provider=object(),
        collection_name="paper_contents",
    )
    calls: list[dict[str, object]] = []

    def fake_milvus_search(**kwargs):
        calls.append(kwargs)
        if len(calls) == 1:
            raise RuntimeError("Unsupported field type")
        return []

    retriever._milvus_search = fake_milvus_search  # type: ignore[method-assign]

    retriever.retrieve(
        query="methods question",
        top_k=5,
        paper_id_filter=["paper-1"],
        section_paths=["methods/model"],
        page_from=2,
        page_to=6,
        content_types=["text", "table"],
    )

    assert len(calls) == 2
    assert calls[1]["paper_id_filter"] == ["paper-1"]
    assert calls[1]["section_paths"] == ["methods/model"]
    assert calls[1]["page_from"] == 2
    assert calls[1]["page_to"] == 6
    assert calls[1]["content_types"] == ["text", "table"]
