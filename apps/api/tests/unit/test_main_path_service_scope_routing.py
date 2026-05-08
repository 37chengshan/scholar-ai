from __future__ import annotations

from app.rag_v3.main_path_service import retrieve_evidence
from app.rag_v3.schemas import EvidenceCandidate, EvidencePack


class _CapturingRetriever:
    def __init__(self) -> None:
        self.kwargs: dict[str, object] | None = None

    def retrieve_evidence(self, **kwargs) -> EvidencePack:
        self.kwargs = kwargs
        return EvidencePack(
            query_id="q-scope",
            query=str(kwargs["query"]),
            query_family="fact",
            stage=str(kwargs["stage"]),
            candidates=[
                EvidenceCandidate(
                    source_chunk_id="chunk-1",
                    paper_id="paper-1",
                    section_id="intro",
                    content_type="text",
                    anchor_text="scoped evidence",
                    rerank_score=0.91,
                )
            ],
            diagnostics={},
        )


def test_main_path_retrieve_evidence_forwards_explicit_paper_scope(monkeypatch) -> None:
    retriever = _CapturingRetriever()
    monkeypatch.setattr(
        "app.rag_v3.main_path_service._get_retriever",
        lambda stage, embedding_model: retriever,
    )
    monkeypatch.setattr(
        "app.rag_v3.main_path_service.create_embedding_provider",
        lambda provider, model: type(
            "Provider",
            (),
            {
                "dim": 1024,
                "embed_texts": lambda self, texts: [[0.1] * 1024 for _ in texts],
                "get_runtime_binding": lambda self: type(
                    "Binding",
                    (),
                    {"to_dict": lambda _self: {"resolved_mode": "online", "degraded_conditions": []}},
                )(),
            },
        )(),
    )
    monkeypatch.setattr(
        "app.rag_v3.main_path_service.get_rerank_runtime_binding",
        lambda: type("Binding", (), {"to_dict": lambda self: {"resolved_mode": "online", "degraded_conditions": []}})(),
    )

    pack = retrieve_evidence(
        query="请总结这篇论文的核心贡献",
        user_id="u-1",
        paper_scope=["paper-1"],
        query_family="fact",
        stage="rule",
    )

    assert retriever.kwargs is not None
    assert retriever.kwargs["paper_scope"] == ["paper-1"]
    assert len(pack.candidates) == 1
    assert pack.candidates[0].paper_id == "paper-1"
