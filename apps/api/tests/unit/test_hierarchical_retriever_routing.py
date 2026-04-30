from __future__ import annotations

from app.rag_v3.indexes.paper_index import PaperSummaryArtifact
from app.rag_v3.indexes.section_index import SectionSummaryArtifact
from app.rag_v3.retrieval.hierarchical_retriever import HierarchicalRetriever
from app.rag_v3.schemas import EvidenceCandidate


class _StubPaperIndex:
    def __len__(self) -> int:
        return 3

    def search(self, query: str, top_k: int) -> list[PaperSummaryArtifact]:
        return [
            PaperSummaryArtifact(
                paper_id=f"paper-{idx}",
                parse_id=f"parse-{idx}",
                title=f"Paper {idx}",
                created_at="2026-04-30T00:00:00Z",
            )
            for idx in range(top_k)
        ]


class _StubSectionIndex:
    def __len__(self) -> int:
        return 9

    def search_for_paper(self, paper_id: str, query: str, top_k: int) -> list[SectionSummaryArtifact]:
        return [
            SectionSummaryArtifact(
                section_id=f"{paper_id}-sec-{idx}",
                paper_id=paper_id,
                parse_id=f"{paper_id}-parse",
                section_path=f"section.{idx}",
                normalized_section_path=f"section.{idx}",
                section_title=f"Section {idx}",
                section_summary=f"Summary {idx} for {paper_id}",
                source_chunk_ids=[f"{paper_id}-chunk-{idx}"],
                created_at="2026-04-30T00:00:00Z",
            )
            for idx in range(top_k)
        ]


class _StubDenseRetriever:
    def __init__(self) -> None:
        self.last_top_k: int | None = None
        self.last_trace: dict[str, object] = {"fallback_used": False}
        self.unsupported_field_type_count = 0
        self.fallback_used_count = 0

    def retrieve(
        self,
        query: str,
        top_k: int,
        paper_id_filter: list[str] | None = None,
        section_paths: list[str] | None = None,
        page_from: int | None = None,
        page_to: int | None = None,
        content_types: list[str] | None = None,
    ) -> list[EvidenceCandidate]:
        _ = (query, paper_id_filter, section_paths, page_from, page_to, content_types)
        self.last_top_k = top_k
        return [
            EvidenceCandidate(
                source_chunk_id=f"chunk-{idx}",
                paper_id=f"paper-{idx % 3}",
                section_id=f"section-{idx % 4}",
                content_type="text",
                anchor_text=f"Candidate {idx}",
                candidate_sources=["dense"],
                rrf_score=1.0 - (idx * 0.01),
                rerank_score=1.0 - (idx * 0.01),
                pre_rerank_rank=idx + 1,
                post_rerank_rank=idx + 1,
            )
            for idx in range(top_k)
        ]


def test_retrieval_depth_override_changes_candidate_pool(monkeypatch) -> None:
    dense = _StubDenseRetriever()
    retriever = HierarchicalRetriever(
        paper_index=_StubPaperIndex(),
        section_index=_StubSectionIndex(),
        dense_retriever=dense,
    )
    monkeypatch.setattr(
        "app.rag_v3.retrieval.hierarchical_retriever.rerank_candidates",
        lambda query, candidates: candidates,
    )

    shallow_pack = retriever.retrieve_evidence(
        query="simple fact query",
        query_family="fact",
        stage="rule",
        top_k=10,
        retrieval_depth="shallow",
    )
    shallow_dense_top_k = dense.last_top_k

    deep_pack = retriever.retrieve_evidence(
        query="write a survey across papers",
        query_family="survey",
        stage="rule",
        top_k=10,
        retrieval_depth="deep",
    )
    deep_dense_top_k = dense.last_top_k

    assert shallow_dense_top_k == 24
    assert deep_dense_top_k == 72
    assert shallow_pack.diagnostics["candidate_pool_max"] == 24.0
    assert deep_pack.diagnostics["candidate_pool_max"] == 72.0
    assert deep_pack.diagnostics["section_top_k_per_paper"] == 6.0
