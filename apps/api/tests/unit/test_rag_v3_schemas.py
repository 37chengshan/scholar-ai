from app.rag_v3.evaluation.answer_policy import build_answer_contract
from app.rag_v3.evaluation.retrieval_evaluator import evaluate_evidence_pack
from app.rag_v3.retrieval.hierarchical_retriever import HierarchicalRetriever
from app.rag_v3.schemas import (
    EvidenceCandidate,
    EvidencePack,
    PaperSummaryArtifact,
    RelationArtifact,
    RelationNode,
    SectionSummaryArtifact,
)


class _StubPaperIndex:
    def __len__(self) -> int:
        return 2

    def search(self, query: str, top_k: int) -> list[PaperSummaryArtifact]:
        _ = query
        return [
            PaperSummaryArtifact(
                paper_id=f"paper-{idx}",
                parse_id=f"parse-{idx}",
                title=f"Paper {idx}",
                paper_summary=f"Retrieval summary {idx}",
                created_at="2026-04-30T00:00:00Z",
            )
            for idx in range(top_k)
        ]


class _StubSectionIndex:
    def __len__(self) -> int:
        return 4

    def search_for_paper(self, paper_id: str, query: str, top_k: int) -> list[SectionSummaryArtifact]:
        _ = query
        return [
            SectionSummaryArtifact(
                section_id=f"{paper_id}-sec-{idx}",
                paper_id=paper_id,
                parse_id=f"{paper_id}-parse",
                section_path=f"section.{idx}",
                normalized_section_path=f"section.{idx}",
                section_title=f"Section {idx}",
                section_summary=f"Section summary {idx} for {paper_id}",
                source_chunk_ids=[f"{paper_id}-chunk-{idx}"],
                created_at="2026-04-30T00:00:00Z",
            )
            for idx in range(top_k)
        ]


class _StubDenseRetriever:
    def __init__(self) -> None:
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
        return [
            EvidenceCandidate(
                source_chunk_id=f"chunk-{idx}",
                paper_id=f"paper-{idx % 2}",
                section_id=f"section-{idx % 5}",
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


def test_relation_artifact_schema() -> None:
    relation = RelationArtifact(
        relation_id="r-001",
        subject=RelationNode(type="paper", id="p-001", text="Paper A"),
        predicate="extends",
        object=RelationNode(type="method", id="m-001", text="Method B"),
        paper_id="p-001",
        evidence_source_chunk_ids=["sid-001"],
        confidence=0.85,
        created_at="2026-04-26T00:00:00Z",
    )
    assert relation.predicate == "extends"
    assert relation.subject.type == "paper"


def test_retrieve_evidence_contract(monkeypatch) -> None:
    retriever = HierarchicalRetriever(
        paper_index=_StubPaperIndex(),
        section_index=_StubSectionIndex(),
        dense_retriever=_StubDenseRetriever(),
    )
    monkeypatch.setattr(
        "app.rag_v3.retrieval.hierarchical_retriever.rerank_candidates",
        lambda query, candidates: candidates,
    )

    pack = retriever.retrieve_evidence(
        query="Compare retrieval performance across papers",
        query_family="compare",
        stage="raw",
        top_k=10,
    )

    assert isinstance(pack, EvidencePack)
    assert pack.query_family == "compare"
    assert len(pack.candidates) == 10
    assert pack.diagnostics["candidate_pool_size"] >= 10
    assert pack.diagnostics["dense_retrieved"] >= 10.0
    assert pack.diagnostics["section_candidates"] > 0.0
    assert pack.diagnostics["paper_index_size"] == 2.0
    assert "citation_support_score" in pack.diagnostics


def test_evidence_quality_and_answer_policy() -> None:
    pack = EvidencePack(
        query_id="q-1",
        query="What is the key result?",
        query_family="fact",
        stage="raw",
        candidates=[
            EvidenceCandidate(
                source_chunk_id="sid-1",
                paper_id="p-1",
                section_id="s-1",
                content_type="text",
                rerank_score=0.9,
            ),
            EvidenceCandidate(
                source_chunk_id="sid-2",
                paper_id="p-2",
                section_id="s-2",
                content_type="text",
                rerank_score=0.2,
            ),
        ],
    )

    quality = evaluate_evidence_pack(pack)
    answer = build_answer_contract(pack, quality)

    assert quality.answerability in {"full", "partial", "abstain"}
    assert answer.answer_mode in {"full", "partial", "abstain"}
    assert answer.answer_mode == "abstain"
    assert quality.answerability == "partial"
    assert len(answer.claims) == 2
