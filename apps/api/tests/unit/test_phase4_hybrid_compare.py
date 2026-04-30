"""Tests for Phase 4 – HybridRetriever, CompareService, CompareMatrix contract."""
from __future__ import annotations

import pytest

from app.rag_v3.retrieval.dense_evidence_retriever import DenseEvidenceRetriever
from app.rag_v3.retrieval.hybrid_retriever import HybridRetriever
from app.rag_v3.retrieval.sparse_evidence_retriever import SparseEvidenceRetriever
from app.rag_v3.schemas import (
    EvidenceCandidate,
    CompareDimension,
    CompareMatrix,
    CompareRow,
    CompareCell,
    AnswerContract,
)
from app.services.compare_service import (
    ALLOWED_DIMENSION_IDS,
    DEFAULT_DIMENSIONS,
    build_compare_contract,
    build_compare_matrix,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_candidate(
    source_chunk_id: str,
    paper_id: str,
    section_id: str = "method",
    rerank_score: float = 0.8,
    rrf_score: float = 0.6,
    pre_rerank_rank: int = 0,
    post_rerank_rank: int = 0,
) -> EvidenceCandidate:
    return EvidenceCandidate(
        source_chunk_id=source_chunk_id,
        paper_id=paper_id,
        section_id=section_id,
        content_type="text",
        anchor_text=f"Content from {paper_id} in {section_id}",
        candidate_sources=["dense"],
        rerank_score=rerank_score,
        rrf_score=rrf_score,
        pre_rerank_rank=pre_rerank_rank,
        post_rerank_rank=post_rerank_rank,
    )


class _StubDense(DenseEvidenceRetriever):
    """Dense retriever stub that returns parameterised fixtures."""

    def __init__(self, per_paper_responses: dict[str, list[EvidenceCandidate]]) -> None:
        super().__init__()
        self._responses = per_paper_responses

    def retrieve(  # type: ignore[override]
        self,
        query: str,
        top_k: int,
        paper_id_filter: list[str] | None = None,
        **kwargs,
    ) -> list[EvidenceCandidate]:
        if paper_id_filter and len(paper_id_filter) == 1:
            return self._responses.get(paper_id_filter[0], [])[:top_k]
        # Fallback: all candidates
        all_cands: list[EvidenceCandidate] = []
        for cands in self._responses.values():
            all_cands.extend(cands)
        return all_cands[:top_k]


# ---------------------------------------------------------------------------
# HybridRetriever tests
# ---------------------------------------------------------------------------


class TestHybridRetriever:
    """Validate Phase 4 hybrid retrieval contracts."""

    def _make_retriever(
        self,
        per_paper: dict[str, list[EvidenceCandidate]],
        per_paper_budget: int = 4,
    ) -> HybridRetriever:
        dense = _StubDense(per_paper)
        sparse = SparseEvidenceRetriever()  # stub, returns generic lexical results
        return HybridRetriever(
            dense_retriever=dense,
            sparse_retriever=sparse,
            per_paper_budget=per_paper_budget,
            rerank_top_k=10,
        )

    def test_uses_both_dense_and_sparse(self):
        """Pack candidates should include both dense and sparse sources after fusion."""
        paper_a = [_make_candidate(f"c-a-{i}", "p-001", rrf_score=0.9 - i * 0.1) for i in range(5)]
        paper_b = [_make_candidate(f"c-b-{i}", "p-002", rrf_score=0.85 - i * 0.1) for i in range(5)]
        retriever = self._make_retriever({"p-001": paper_a, "p-002": paper_b})

        pack = retriever.retrieve(query="test", paper_ids=["p-001", "p-002"])

        # Some candidates from dense pool exist
        dense_ids = {f"c-a-{i}" for i in range(5)} | {f"c-b-{i}" for i in range(5)}
        found_dense = any(c.source_chunk_id in dense_ids for c in pack.candidates)
        assert found_dense, "Pack must contain at least one dense candidate"
        # Sparse candidates have lexical- prefix
        found_sparse = any("lexical" in c.source_chunk_id for c in pack.candidates)
        assert found_sparse, "Pack must contain at least one sparse/lexical candidate"

    def test_per_paper_budget_enforced(self):
        """No single paper should supply more than per_paper_budget candidates."""
        budget = 3
        # Paper A has many strong candidates
        paper_a = [_make_candidate(f"c-a-{i}", "p-001", rrf_score=1.0 - i * 0.01) for i in range(20)]
        paper_b = [_make_candidate(f"c-b-{i}", "p-002", rrf_score=0.5 - i * 0.01) for i in range(5)]
        retriever = self._make_retriever(
            {"p-001": paper_a, "p-002": paper_b},
            per_paper_budget=budget,
        )

        pack = retriever.retrieve(query="test", paper_ids=["p-001", "p-002"])

        # After per-paper budget slice, paper_a contributes at most `budget` dense candidates
        p_a_dense = [
            c for c in pack.candidates
            if c.paper_id == "p-001" and c.source_chunk_id.startswith("c-a-")
        ]
        assert len(p_a_dense) <= budget, (
            f"paper_a contributed {len(p_a_dense)} dense candidates, budget={budget}"
        )

    def test_rerank_trace_fields_populated(self):
        """pre_rerank_rank and post_rerank_rank must be set on all returned candidates."""
        paper_a = [_make_candidate(f"c-a-{i}", "p-001") for i in range(5)]
        retriever = self._make_retriever({"p-001": paper_a})

        pack = retriever.retrieve(query="test", paper_ids=["p-001"])

        for cand in pack.candidates:
            assert cand.pre_rerank_rank > 0, f"{cand.source_chunk_id}: pre_rerank_rank not set"
            assert cand.post_rerank_rank > 0, f"{cand.source_chunk_id}: post_rerank_rank not set"

    def test_rerank_score_present(self):
        """rerank_score must be non-negative for all candidates."""
        paper_a = [_make_candidate(f"c-a-{i}", "p-001") for i in range(5)]
        retriever = self._make_retriever({"p-001": paper_a})

        pack = retriever.retrieve(query="test", paper_ids=["p-001"])

        for cand in pack.candidates:
            assert cand.rerank_score >= 0.0, f"{cand.source_chunk_id}: negative rerank_score"

    def test_diagnostics_include_paper_coverage(self):
        """diagnostics must include paper_coverage_count."""
        paper_a = [_make_candidate("c-a-0", "p-001")]
        paper_b = [_make_candidate("c-b-0", "p-002")]
        retriever = self._make_retriever({"p-001": paper_a, "p-002": paper_b})

        pack = retriever.retrieve(query="test", paper_ids=["p-001", "p-002"])

        assert "paper_coverage_count" in pack.diagnostics


# ---------------------------------------------------------------------------
# CompareService tests
# ---------------------------------------------------------------------------


class TestCompareService:
    def _make_pack_for_papers(self, paper_ids: list[str]):
        """Build a fake EvidencePack with candidates for each paper × dimension."""
        from app.rag_v3.schemas import EvidencePack

        candidates: list[EvidenceCandidate] = []
        sections = ["method", "result", "introduction", "limitation", "dataset"]
        for i, pid in enumerate(paper_ids):
            for j, sec in enumerate(sections):
                cand = _make_candidate(
                    source_chunk_id=f"c-{i}-{j}",
                    paper_id=pid,
                    section_id=sec,
                    rerank_score=0.85 - j * 0.05,
                    rrf_score=0.7 - j * 0.05,
                    pre_rerank_rank=j + 1,
                    post_rerank_rank=j + 1,
                )
                candidates.append(cand)

        return EvidencePack(
            query_id="test-q",
            query="compare",
            query_family="compare",
            stage="hybrid",
            candidates=candidates,
        )

    def test_compare_matrix_shape(self):
        """CompareMatrix must have correct number of rows and cells."""
        paper_ids = ["p-001", "p-002", "p-003"]
        dims = [CompareDimension(id=d["id"], label=d["label"]) for d in DEFAULT_DIMENSIONS]
        pack = self._make_pack_for_papers(paper_ids)
        paper_meta = {pid: {"title": f"Title {pid}", "year": 2022 + i} for i, pid in enumerate(paper_ids)}

        matrix = build_compare_matrix(
            paper_ids=paper_ids,
            paper_meta=paper_meta,
            pack=pack,
            dimensions=dims,
        )

        assert isinstance(matrix, CompareMatrix)
        assert len(matrix.rows) == 3
        for row in matrix.rows:
            assert len(row.cells) == len(dims)

    def test_cells_never_fabricated(self):
        """Cells with no evidence must be marked not_enough_evidence, not empty content."""
        paper_ids = ["p-001"]
        dims = [CompareDimension(id="innovation", label="Key Innovation")]
        from app.rag_v3.schemas import EvidencePack
        # Pack with zero candidates → no evidence for any cell
        empty_pack = EvidencePack(
            query_id="q",
            query="test",
            query_family="compare",
            stage="hybrid",
            candidates=[],
        )
        matrix = build_compare_matrix(
            paper_ids=paper_ids,
            paper_meta={"p-001": {"title": "T"}},
            pack=empty_pack,
            dimensions=dims,
        )

        cell = matrix.rows[0].cells[0]
        assert cell.support_status == "not_enough_evidence"
        assert cell.evidence_blocks == []

    def test_compare_contract_response_type(self):
        """build_compare_contract must return response_type='compare'."""
        paper_ids = ["p-001", "p-002"]
        dims = [CompareDimension(id=d["id"], label=d["label"]) for d in DEFAULT_DIMENSIONS[:3]]
        pack = self._make_pack_for_papers(paper_ids)
        paper_meta = {pid: {"title": f"Paper {pid}", "year": 2020} for pid in paper_ids}

        contract = build_compare_contract(
            paper_ids=paper_ids,
            paper_meta=paper_meta,
            pack=pack,
            dimensions=dims,
        )

        assert isinstance(contract, AnswerContract)
        assert contract.response_type == "compare"
        assert contract.compare_matrix is not None

    def test_compare_contract_truthfulness_tracks_compare_output_not_raw_evidence_concat(self):
        paper_ids = ["p-001", "p-002"]
        dims = [CompareDimension(id="method", label="Method"), CompareDimension(id="dataset", label="Dataset")]
        pack = self._make_pack_for_papers(paper_ids)
        paper_meta = {
            "p-001": {"title": "Paper 1", "year": 2020},
            "p-002": {"title": "Paper 2", "year": 2021},
        }

        contract = build_compare_contract(
            paper_ids=paper_ids,
            paper_meta=paper_meta,
            pack=pack,
            dimensions=dims,
        )

        assert contract.answer_mode in {"full", "partial"}
        assert len(contract.claims) >= 2
        assert contract.truthfulness_summary["total_claims"] >= 2
        assert contract.execution_mode == "local_compare"
        assert contract.truthfulness_required is True
        assert "answer_mode" in contract.truthfulness_summary

    def test_compare_matrix_all_required_fields(self):
        """CompareMatrix must expose paper_ids, dimensions, rows, summary, cross_paper_insights."""
        paper_ids = ["p-001", "p-002"]
        dims = [CompareDimension(id="method", label="Method")]
        pack = self._make_pack_for_papers(paper_ids)

        matrix = build_compare_matrix(
            paper_ids=paper_ids,
            paper_meta={pid: {"title": pid, "year": 2021} for pid in paper_ids},
            pack=pack,
            dimensions=dims,
        )

        assert hasattr(matrix, "paper_ids")
        assert hasattr(matrix, "dimensions")
        assert hasattr(matrix, "rows")
        assert hasattr(matrix, "summary")
        assert hasattr(matrix, "cross_paper_insights")

    def test_evidence_blocks_use_citation_jump_url(self):
        """Each evidence block in a supported cell must have a citation_jump_url."""
        paper_ids = ["p-001"]
        dims = [CompareDimension(id="method", label="Method")]
        pack = self._make_pack_for_papers(paper_ids)

        matrix = build_compare_matrix(
            paper_ids=paper_ids,
            paper_meta={"p-001": {"title": "Paper", "year": 2022}},
            pack=pack,
            dimensions=dims,
        )

        for row in matrix.rows:
            for cell in row.cells:
                for block in cell.evidence_blocks:
                    assert isinstance(block.citation_jump_url, str), (
                        f"Block {block.evidence_id} missing citation_jump_url"
                    )

    def test_kb_scope_with_paper_ids_filters(self):
        """Hybrid retriever must restrict dense phase to provided paper_ids only."""
        # Use _StubDense to verify per-paper calls
        all_ids = ["p-001", "p-002", "p-003"]
        per_paper = {
            pid: [_make_candidate(f"c-{pid}-0", pid)] for pid in all_ids
        }
        dense = _StubDense(per_paper)
        retriever = HybridRetriever(dense_retriever=dense, rerank_top_k=20)

        # Only request p-001 and p-002
        requested = ["p-001", "p-002"]
        pack = retriever.retrieve(query="q", paper_ids=requested)

        # p-003 dense candidates must NOT appear (per-paper phase only fetched p-001, p-002)
        p3_dense = [c for c in pack.candidates if c.source_chunk_id == "c-p-003-0"]
        assert len(p3_dense) == 0, "Candidates from non-requested paper should not appear"
