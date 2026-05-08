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
    assert 'section like "methods/model%"' in expr
    assert 'section like "results%"' in expr
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
    search_calls: list[dict[str, object]] = []
    fallback_calls: list[dict[str, object]] = []

    def fake_milvus_search(**kwargs):
        search_calls.append(kwargs)
        raise RuntimeError("Unsupported field type")

    def fake_query_fallback(**kwargs):
        fallback_calls.append(kwargs)
        return []

    retriever._milvus_search = fake_milvus_search  # type: ignore[method-assign]
    retriever._query_fallback = fake_query_fallback  # type: ignore[method-assign]

    retriever.retrieve(
        query="methods question",
        top_k=5,
        paper_id_filter=["paper-1"],
        section_paths=["methods/model"],
        page_from=2,
        page_to=6,
        content_types=["text", "table"],
    )

    assert len(search_calls) == 1
    assert len(fallback_calls) == 1
    assert fallback_calls[0]["paper_id_filter"] == ["paper-1"]
    assert fallback_calls[0]["section_paths"] == ["methods/model"]
    assert fallback_calls[0]["page_from"] == 2
    assert fallback_calls[0]["page_to"] == 6
    assert fallback_calls[0]["content_types"] == ["text", "table"]


def test_dense_default_output_fields_include_canonical_source_chunk_id():
    retriever = DenseEvidenceRetriever(
        embedding_provider=object(),
        collection_name="paper_contents",
    )

    assert retriever._output_fields[0] == "source_chunk_id"
    assert "source_chunk_id" in retriever._output_fields


def test_effective_output_fields_adapts_to_legacy_schema_and_keeps_raw_data():
    retriever = DenseEvidenceRetriever(
        embedding_provider=object(),
        collection_name="paper_contents",
    )

    fields = retriever._effective_output_fields(
        schema_fields={"id", "paper_id", "page_num", "content_type", "section", "content_data", "raw_data", "embedding"},
        requested_output_fields=["source_chunk_id", "paper_id", "content_type", "section", "page_num", "content_data"],
        include_embedding=True,
    )

    assert "source_chunk_id" not in fields
    assert "raw_data" in fields
    assert "embedding" in fields


def test_dense_fallback_prefers_canonical_source_chunk_id_over_row_id(monkeypatch):
    retriever = DenseEvidenceRetriever(
        embedding_provider=object(),
        collection_name="paper_contents",
    )
    retriever._embedding_provider = type("Embed", (), {"embed_texts": staticmethod(lambda texts: [[0.1, 0.2]])})()

    class _FakeCollection:
        def load(self):
            return None

        def query(self, **kwargs):
            return [{
                "id": 466045819771397281,
                "source_chunk_id": "chunk_canonical_1",
                "paper_id": "paper-1",
                "page_num": 1,
                "content_type": "text",
                "section": "intro",
                "content_data": "summary chunk",
                "embedding": [0.1, 0.2],
            }]

    import pymilvus

    monkeypatch.setattr(pymilvus, "Collection", lambda *args, **kwargs: _FakeCollection())
    candidates = retriever._query_fallback(query="q", top_k=1)

    assert candidates[0].source_chunk_id == "chunk_canonical_1"
