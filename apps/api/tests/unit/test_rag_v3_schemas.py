from app.rag_v3.evaluation.answer_policy import build_answer_contract
from app.rag_v3.evaluation.retrieval_evaluator import evaluate_evidence_pack
from app.rag_v3.retrieval.hierarchical_retriever import retrieve_evidence
from app.rag_v3.schemas import EvidenceCandidate, EvidencePack, RelationArtifact, RelationNode


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


def test_retrieve_evidence_contract() -> None:
    pack = retrieve_evidence(
        query="Compare retrieval performance across papers",
        query_family="compare",
        stage="raw",
        top_k=10,
    )
    assert isinstance(pack, EvidencePack)
    assert pack.query_family == "compare"
    assert len(pack.candidates) == 10
    assert "candidate_pool_oracle_recall_at_100" in pack.diagnostics


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
    assert answer.answer_mode == quality.answerability
    assert len(answer.claims) == 2
