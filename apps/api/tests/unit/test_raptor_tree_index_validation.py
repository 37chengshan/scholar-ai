"""Tests for RaptorTreeIndex input validation - prevents Milvus filter injection."""

import pytest

from app.rag_v3.indexes.raptor_tree_index import RaptorTreeIndex


class TestRaptorTreeIndexSearchValidation:
    """Tests that RaptorTreeIndex.search() validates inputs before building filter expressions."""

    def test_search_rejects_empty_user_id(self):
        index = RaptorTreeIndex(milvus_alias="test", collection_name="test_col")
        with pytest.raises(ValueError, match="user_id cannot be empty"):
            index.search(
                query_embedding=[0.1, 0.2, 0.3],
                user_id="",
            )

    def test_search_rejects_user_id_with_double_quote(self):
        index = RaptorTreeIndex(milvus_alias="test", collection_name="test_col")
        with pytest.raises(ValueError, match="invalid characters"):
            index.search(
                query_embedding=[0.1, 0.2, 0.3],
                user_id='user" OR 1==1 --',
            )

    def test_search_rejects_user_id_with_single_quote(self):
        index = RaptorTreeIndex(milvus_alias="test", collection_name="test_col")
        with pytest.raises(ValueError, match="invalid characters"):
            index.search(
                query_embedding=[0.1, 0.2, 0.3],
                user_id="user' OR '1'='1",
            )

    def test_search_rejects_paper_id_with_injection_chars(self):
        index = RaptorTreeIndex(milvus_alias="test", collection_name="test_col")
        with pytest.raises(ValueError, match="invalid characters"):
            index.search(
                query_embedding=[0.1, 0.2, 0.3],
                user_id="valid-user",
                paper_ids=['paper" OR 1==1 --'],
            )

    def test_search_rejects_user_id_with_semicolon(self):
        index = RaptorTreeIndex(milvus_alias="test", collection_name="test_col")
        with pytest.raises(ValueError, match="invalid characters"):
            index.search(
                query_embedding=[0.1, 0.2, 0.3],
                user_id="user; DROP TABLE users;",
            )


class TestRaptorTreeIndexDeleteValidation:
    """Tests that RaptorTreeIndex.delete_by_paper() validates inputs before building filter expressions."""

    def test_delete_rejects_empty_paper_id(self):
        index = RaptorTreeIndex(milvus_alias="test", collection_name="test_col")
        with pytest.raises(ValueError, match="paper_id cannot be empty"):
            index.delete_by_paper(paper_id="", user_id="valid-user")

    def test_delete_rejects_empty_user_id(self):
        index = RaptorTreeIndex(milvus_alias="test", collection_name="test_col")
        with pytest.raises(ValueError, match="user_id cannot be empty"):
            index.delete_by_paper(paper_id="valid-paper", user_id="")

    def test_delete_rejects_paper_id_with_double_quote(self):
        index = RaptorTreeIndex(milvus_alias="test", collection_name="test_col")
        with pytest.raises(ValueError, match="invalid characters"):
            index.delete_by_paper(
                paper_id='paper" OR 1==1 --',
                user_id="valid-user",
            )

    def test_delete_rejects_user_id_with_double_quote(self):
        index = RaptorTreeIndex(milvus_alias="test", collection_name="test_col")
        with pytest.raises(ValueError, match="invalid characters"):
            index.delete_by_paper(
                paper_id="valid-paper",
                user_id='user" OR 1==1 --',
            )

    def test_delete_rejects_paper_id_with_single_quote(self):
        index = RaptorTreeIndex(milvus_alias="test", collection_name="test_col")
        with pytest.raises(ValueError, match="invalid characters"):
            index.delete_by_paper(
                paper_id="paper' OR '1'='1",
                user_id="valid-user",
            )


class TestRaptorTreeIndexSearchWithMockedMilvus:
    """Tests that RaptorTreeIndex.search() passes validated inputs to Milvus."""

    def test_search_passes_validated_user_id_to_milvus(self, monkeypatch):
        """Verify that validated user_id is used in the filter expression."""
        captured_expr = {}

        class _FakeCollection:
            def load(self):
                return None

            def search(self, **kwargs):
                captured_expr["expr"] = kwargs.get("expr", "")
                return []

        import pymilvus

        monkeypatch.setattr(pymilvus, "Collection", lambda *args, **kwargs: _FakeCollection())

        index = RaptorTreeIndex(milvus_alias="test", collection_name="test_col")
        index.search(
            query_embedding=[0.1, 0.2],
            user_id="valid-user-123",
        )

        assert 'user_id == "valid-user-123"' in captured_expr["expr"]

    def test_search_passes_validated_paper_ids_to_milvus(self, monkeypatch):
        """Verify that validated paper_ids are used in the filter expression."""
        captured_expr = {}

        class _FakeCollection:
            def load(self):
                return None

            def search(self, **kwargs):
                captured_expr["expr"] = kwargs.get("expr", "")
                return []

        import pymilvus

        monkeypatch.setattr(pymilvus, "Collection", lambda *args, **kwargs: _FakeCollection())

        index = RaptorTreeIndex(milvus_alias="test", collection_name="test_col")
        index.search(
            query_embedding=[0.1, 0.2],
            user_id="valid-user",
            paper_ids=["paper-1", "paper-2"],
        )

        assert 'paper_id in ["paper-1", "paper-2"]' in captured_expr["expr"]

    def test_search_rejects_injection_attempt_in_paper_ids(self, monkeypatch):
        """Verify that injection attempt in paper_ids raises ValueError."""
        index = RaptorTreeIndex(milvus_alias="test", collection_name="test_col")
        with pytest.raises(ValueError, match="invalid characters"):
            index.search(
                query_embedding=[0.1, 0.2],
                user_id="valid-user",
                paper_ids=['paper" OR 1==1 --'],
            )


class TestHierarchicalRetrieverTreeCandidatesUserId:
    """Tests that _retrieve_tree_candidates() requires user_id."""

    def test_tree_candidates_returns_empty_when_user_id_empty(self, monkeypatch):
        from app.rag_v3.retrieval.hierarchical_retriever import HierarchicalRetriever

        retriever = HierarchicalRetriever()
        monkeypatch.setattr(
            "app.rag_v3.retrieval.hierarchical_retriever.RAPTOR_ENABLED",
            True,
        )

        class _FakeTreeIndex:
            def search(self, **kwargs):
                return [{"node_id": "n1", "paper_id": "p1", "user_id": "u1", "level": 0, "text": "t", "cluster_label": 0, "score": 0.9}]

        class _FakeEmbeddingProvider:
            def embed_texts(self, texts):
                return [[0.1, 0.2]]

        retriever._raptor_tree_index = _FakeTreeIndex()
        retriever._embedding_provider = _FakeEmbeddingProvider()

        result = retriever._retrieve_tree_candidates(
            query="test query",
            paper_ids=["paper-1"],
            user_id="",
        )

        assert result == []

    def test_tree_candidates_passes_user_id_to_search(self, monkeypatch):
        from app.rag_v3.retrieval.hierarchical_retriever import HierarchicalRetriever

        retriever = HierarchicalRetriever()
        monkeypatch.setattr(
            "app.rag_v3.retrieval.hierarchical_retriever.RAPTOR_ENABLED",
            True,
        )

        captured_user_id = {}

        class _FakeTreeIndex:
            def search(self, **kwargs):
                captured_user_id["user_id"] = kwargs.get("user_id")
                return []

        class _FakeEmbeddingProvider:
            def embed_texts(self, texts):
                return [[0.1, 0.2]]

        retriever._raptor_tree_index = _FakeTreeIndex()
        retriever._embedding_provider = _FakeEmbeddingProvider()

        retriever._retrieve_tree_candidates(
            query="test query",
            paper_ids=["paper-1"],
            user_id="real-user-456",
        )

        assert captured_user_id["user_id"] == "real-user-456"
