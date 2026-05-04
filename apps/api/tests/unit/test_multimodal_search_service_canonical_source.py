from app.core.multimodal_search_service import MultimodalSearchService


def test_canonical_source_chunk_id_ignores_summary_source_id():
    assert (
        MultimodalSearchService._canonical_source_chunk_id(
            {
                "id": "466045819771396907",
                "index_type": "summary",
                "source_id": "466045819771396907",
            }
        )
        is None
    )


def test_canonical_source_chunk_id_prefers_explicit_chunk_fields():
    assert (
        MultimodalSearchService._canonical_source_chunk_id(
            {
                "id": "466045819771396907",
                "index_type": "summary",
                "raw_data": {
                    "source_chunk_id": "chunk-stable-123",
                },
            }
        )
        == "chunk-stable-123"
    )
