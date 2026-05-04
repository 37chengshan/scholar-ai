from app.core.vector_store_repository import MilvusVectorStoreRepository


def test_normalize_hit_ignores_summary_source_id_as_canonical_chunk_id():
    chunk = MilvusVectorStoreRepository._normalize_hit(
        {
            "id": "466045819771396907",
            "paper_id": "paper-123",
            "index_type": "summary",
            "source_id": "466045819771396907",
            "text": "Summary branch content.",
            "page_num": 1,
        }
    )

    assert chunk.source_id is None


def test_normalize_hit_keeps_non_summary_source_id_as_fallback_chunk_id():
    chunk = MilvusVectorStoreRepository._normalize_hit(
        {
            "id": "466045819771396907",
            "paper_id": "paper-123",
            "source_id": "chunk-stable-123",
            "text": "Evidence chunk content.",
            "page_num": 2,
        }
    )

    assert chunk.source_id == "chunk-stable-123"
