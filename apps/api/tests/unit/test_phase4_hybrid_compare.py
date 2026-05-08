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
    build_compare_queries,
    build_compare_contract,
    build_compare_matrix,
    _fill_cell,
    _extract_best_compare_snippet,
    retrieve_compare_pack,
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

    def test_tracks_both_dense_and_sparse_candidate_pools(self):
        """Hybrid retriever diagnostics should record both dense and sparse pools."""
        paper_a = [_make_candidate(f"c-a-{i}", "p-001", rrf_score=0.9 - i * 0.1) for i in range(5)]
        paper_b = [_make_candidate(f"c-b-{i}", "p-002", rrf_score=0.85 - i * 0.1) for i in range(5)]
        retriever = self._make_retriever({"p-001": paper_a, "p-002": paper_b})

        pack = retriever.retrieve(query="test", paper_ids=["p-001", "p-002"])

        assert pack.diagnostics["dense_candidates_total"] > 0
        assert pack.diagnostics["sparse_candidates_total"] >= 0

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
        assert contract.quality["unsupported_claim_rate"] == contract.truthfulness_report["unsupportedClaimRate"]
        assert contract.quality["citation_coverage"] == contract.truthfulness_summary["citation_coverage"]

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

    def test_compare_matrix_strips_retrieval_prefix_markup_and_localizes_cross_paper_claims(self):
        from app.rag_v3.schemas import EvidencePack

        dirty_text = "[Paper: LIMA]\n[Section: method]\n[Page:1]\nGLYPH<22> Core method summary"
        candidate = EvidenceCandidate(
            source_chunk_id="c-1",
            paper_id="p-001",
            section_id="method",
            content_type="text",
            anchor_text=dirty_text,
            candidate_sources=["dense"],
            rerank_score=0.91,
            rrf_score=0.77,
            pre_rerank_rank=1,
            post_rerank_rank=1,
        )
        pack = EvidencePack(
            query_id="q",
            query="compare",
            query_family="compare",
            stage="hybrid",
            candidates=[candidate, candidate.model_copy(update={"paper_id": "p-002", "source_chunk_id": "c-2"})],
        )

        matrix = build_compare_matrix(
            paper_ids=["p-001", "p-002"],
            paper_meta={
                "p-001": {"title": "Paper 1", "year": 2020},
                "p-002": {"title": "Paper 2", "year": 2021},
            },
            pack=pack,
            dimensions=[CompareDimension(id="method", label="方法")],
        )

        assert matrix.rows[0].cells[0].content == "Core method summary"
        assert matrix.rows[0].cells[0].evidence_blocks[0].text == "Core method summary"
        assert matrix.cross_paper_insights

    def test_extract_best_compare_snippet_normalizes_method_heading_fragments(self):
        candidate = EvidenceCandidate(
            source_chunk_id="c-method",
            paper_id="p-001",
            section_id="introduction",
            content_type="text",
            anchor_text=(
                "[Paper: LIMA] [Section: introduction] [Page:4] "
                "this small sample adds diversity to the overall mix of training examples. "
                "3 Training LIMA We train LIMA, a pretrained 65B-parameter LLaMa model fine-tuned on this set of 1,000 demonstrations."
            ),
            candidate_sources=["dense", "dimension:method"],
            rerank_score=0.8,
            rrf_score=0.7,
            pre_rerank_rank=1,
            post_rerank_rank=1,
        )

        assert _extract_best_compare_snippet("method", candidate) == (
            "We train LIMA, a pretrained 65B-parameter LLaMa model fine-tuned on this set of 1,000 demonstrations."
        )

    def test_extract_best_compare_snippet_rejects_weak_result_commentary(self):
        candidate = EvidenceCandidate(
            source_chunk_id="c-result",
            paper_id="p-001",
            section_id="results",
            content_type="text",
            anchor_text=(
                "[Paper: LIMA] [Section: result] [Page:6] "
                "what is striking about this result is the fact that DaVinci003 was trained with RLHF. "
                "Bard shows the opposite trend, with GPT-4 preferring the Bard response 42% of the time, "
                "58% of the time the LIMA response was at least as good as Bard, and GPT-4 prefers LIMA outputs over its own 19% of the time."
            ),
            candidate_sources=["dense", "dimension:results"],
            rerank_score=0.82,
            rrf_score=0.74,
            pre_rerank_rank=1,
            post_rerank_rank=1,
        )

        snippet = _extract_best_compare_snippet("results", candidate)
        assert "42%" in snippet
        assert "58%" in snippet or "19%" in snippet

    def test_fill_cell_requires_dimension_signal_instead_of_using_any_high_score_candidate(self):
        unrelated = EvidenceCandidate(
            source_chunk_id="c-1",
            paper_id="p-001",
            section_id="frontmatter",
            content_type="text",
            anchor_text="LIMA: Less Is More for Alignment Chunting Zhou Pengfei Liu",
            candidate_sources=["dense"],
            rerank_score=0.98,
            rrf_score=0.8,
            pre_rerank_rank=1,
            post_rerank_rank=1,
        )

        cell = _fill_cell("method", "p-001", [unrelated])

        assert cell.support_status == "not_enough_evidence"
        assert cell.content == ""

    def test_fill_cell_summarizes_long_anchor_text_for_compare_display(self):
        candidate = EvidenceCandidate(
            source_chunk_id="c-2",
            paper_id="p-001",
            section_id="method",
            content_type="text",
            anchor_text="[Paper: Demo] [Section: method] [Page: 4] The method introduces supervised fine-tuning on a curated instruction set. Additional implementation details follow in later paragraphs.",
            candidate_sources=["dense"],
            rerank_score=0.92,
            rrf_score=0.81,
            pre_rerank_rank=1,
            post_rerank_rank=1,
        )

        cell = _fill_cell("method", "p-001", [candidate])

        assert cell.support_status in {"supported", "partially_supported"}
        assert cell.content.startswith("The method introduces supervised fine-tuning")
        assert "[Paper:" not in cell.content

    def test_fill_cell_rejects_prompt_template_and_frontmatter_noise(self):
        noisy_candidates = [
            EvidenceCandidate(
                source_chunk_id="c-frontmatter",
                paper_id="p-001",
                section_id="frontmatter",
                content_type="text",
                anchor_text="LIMA Less Is More for Alignment Chunting Zhou Pengfei Liu Puxin Xu Srini Iyer",
                candidate_sources=["dense"],
                rerank_score=0.99,
                rrf_score=0.83,
                pre_rerank_rank=1,
                post_rerank_rank=1,
            ),
            EvidenceCandidate(
                source_chunk_id="c-prompt",
                paper_id="p-001",
                section_id="result",
                content_type="text",
                anchor_text="in a step by step manner your reasoning about the criterion to be sure that your conclusion is correct.",
                candidate_sources=["dense"],
                rerank_score=0.97,
                rrf_score=0.81,
                pre_rerank_rank=2,
                post_rerank_rank=2,
            ),
        ]

        cell = _fill_cell("results", "p-001", noisy_candidates)

        assert cell.support_status == "not_enough_evidence"
        assert cell.content == ""

    def test_build_compare_queries_expands_dimension_specific_retrieval_prompts(self):
        queries = build_compare_queries(
            paper_meta={
                "p-001": {"title": "Paper A"},
                "p-002": {"title": "Paper B"},
            },
            dimensions=[
                CompareDimension(id="method", label="方法"),
                CompareDimension(id="results", label="结果"),
            ],
            question="Compare these papers for RLHF efficiency",
        )

        assert queries[0].query == "Compare these papers for RLHF efficiency"
        assert queries[0].dimension_id is None
        assert any("method, approach, model design" in query.query for query in queries)
        assert any("results, findings, and measured outcomes" in query.query for query in queries)

    def test_retrieve_compare_pack_merges_multi_query_candidates(self):
        class _StubRetriever:
            def __init__(self) -> None:
                self.queries: list[str] = []

            def retrieve(self, query: str, paper_ids: list[str]):
                from app.rag_v3.schemas import EvidencePack

                self.queries.append(query)
                candidate = EvidenceCandidate(
                    source_chunk_id="c-1" if "method" in query else "c-2",
                    paper_id=paper_ids[0],
                    section_id="method" if "method" in query else "result",
                    content_type="text",
                    anchor_text="Method evidence" if "method" in query else "Results evidence",
                    candidate_sources=["dense"],
                    rerank_score=0.8,
                    rrf_score=0.7,
                    pre_rerank_rank=1,
                    post_rerank_rank=1,
                )
                return EvidencePack(
                    query_id=f"q-{len(self.queries)}",
                    query=query,
                    query_family="compare",
                    stage="hybrid",
                    candidates=[candidate],
                    diagnostics={"query_index": len(self.queries)},
                )

        stub = _StubRetriever()
        pack = retrieve_compare_pack(
            paper_ids=["p-001"],
            paper_meta={"p-001": {"title": "Paper A"}},
            dimensions=[
                CompareDimension(id="method", label="方法"),
                CompareDimension(id="results", label="结果"),
            ],
            question=None,
            retriever=stub,  # type: ignore[arg-type]
        )

        assert len(stub.queries) == 2
        assert len(pack.candidates) == 2
        assert pack.stage == "hybrid_compare_multiquery"
        assert pack.diagnostics["sub_query_count"] == 2
        assert "dimension:method" in pack.candidates[0].candidate_sources or "dimension:method" in pack.candidates[1].candidate_sources

    def test_fill_cell_uses_dimension_scoped_candidates_only(self):
        wrong_dimension = EvidenceCandidate(
            source_chunk_id="c-results",
            paper_id="p-001",
            section_id="result",
            content_type="text",
            anchor_text="This paper improves benchmark scores by 4 points.",
            candidate_sources=["dense", "dimension:results"],
            rerank_score=0.95,
            rrf_score=0.84,
            pre_rerank_rank=1,
            post_rerank_rank=1,
        )
        correct_dimension = EvidenceCandidate(
            source_chunk_id="c-method",
            paper_id="p-001",
            section_id="method",
            content_type="text",
            anchor_text="We fine-tune the model on 1,000 curated demonstrations.",
            candidate_sources=["dense", "dimension:method"],
            rerank_score=0.88,
            rrf_score=0.79,
            pre_rerank_rank=2,
            post_rerank_rank=2,
        )

        cell = _fill_cell("method", "p-001", [wrong_dimension, correct_dimension])

        assert cell.content.startswith("We fine-tune the model")
        assert cell.evidence_blocks[0].source_chunk_id == "c-method"

    def test_fill_cell_rejects_reference_sentence_noise(self):
        reference_like = EvidenceCandidate(
            source_chunk_id="c-ref",
            paper_id="p-001",
            section_id="results",
            content_type="text",
            anchor_text="In International Conference on Learning Representations, 2022a.",
            candidate_sources=["dense", "dimension:results"],
            rerank_score=0.94,
            rrf_score=0.82,
            pre_rerank_rank=1,
            post_rerank_rank=1,
        )

        cell = _fill_cell("results", "p-001", [reference_like])

        assert cell.support_status == "not_enough_evidence"
        assert cell.content == ""

    def test_fill_cell_extracts_dimension_specific_sentence_instead_of_first_sentence(self):
        mixed_candidate = EvidenceCandidate(
            source_chunk_id="c-mixed",
            paper_id="p-001",
            section_id="results",
            content_type="text",
            anchor_text=(
                "This small sample adds diversity to the overall mix of tasks. "
                "Results show the model improves accuracy by 7.4 points over the strongest baseline."
            ),
            candidate_sources=["dense", "dimension:results"],
            rerank_score=0.93,
            rrf_score=0.84,
            pre_rerank_rank=1,
            post_rerank_rank=1,
        )

        cell = _fill_cell("results", "p-001", [mixed_candidate])

        assert cell.content.startswith("Results show the model improves accuracy")
        assert cell.evidence_blocks[0].text == cell.content

    def test_fill_cell_prefers_true_method_sentence_inside_mixed_training_chunk(self):
        candidate = EvidenceCandidate(
            source_chunk_id="c-method-mixed",
            paper_id="p-001",
            section_id="introduction",
            content_type="text",
            anchor_text=(
                "this small sample adds diversity to the overall mix of training examples, and can potentially increase model robustness. "
                "We train LIMA using the following protocol. Starting from LLaMa 65B, we fine-tune on our 1,000-example alignment training set."
            ),
            candidate_sources=["dense", "dimension:method"],
            rerank_score=0.88,
            rrf_score=0.79,
            pre_rerank_rank=1,
            post_rerank_rank=1,
        )

        cell = _fill_cell("method", "p-001", [candidate])

        assert cell.content.startswith("We train LIMA using the following protocol")

    def test_fill_cell_prefers_quantified_results_sentence_over_commentary(self):
        candidate = EvidenceCandidate(
            source_chunk_id="c-results-mixed",
            paper_id="p-001",
            section_id="introduction",
            content_type="text",
            anchor_text=(
                "what is striking about this result is the fact that DaVinci003 was trained with RLHF, a supposedly superior alignment method. "
                "Bard shows the opposite trend to DaVinci003, producing better responses than LIMA 42% of the time; however, this also means that 58% of the time the LIMA response was at least as good as Bard."
            ),
            candidate_sources=["dense", "dimension:results"],
            rerank_score=0.9,
            rrf_score=0.82,
            pre_rerank_rank=1,
            post_rerank_rank=1,
        )

        cell = _fill_cell("results", "p-001", [candidate])

        assert "58%" in cell.content or "42%" in cell.content
        assert "DaVinci003 was trained with RLHF" not in cell.content

    def test_fill_cell_rejects_training_sentence_as_dataset_evidence(self):
        training_like = EvidenceCandidate(
            source_chunk_id="c-train",
            paper_id="p-001",
            section_id="dataset",
            content_type="text",
            anchor_text="Finally, we train LIMA through supervised fine-tuning on this set of 1,000 demonstrations.",
            candidate_sources=["dense", "dimension:dataset"],
            rerank_score=0.95,
            rrf_score=0.85,
            pre_rerank_rank=1,
            post_rerank_rank=1,
        )

        cell = _fill_cell("dataset", "p-001", [training_like])

        assert cell.support_status == "not_enough_evidence"
        assert cell.content == ""

    def test_fill_cell_rejects_problem_cell_when_only_section_hint_exists(self):
        weak_intro = EvidenceCandidate(
            source_chunk_id="c-problem-weak",
            paper_id="p-001",
            section_id="introduction",
            content_type="text",
            anchor_text="6 out of 10 prompts with malicious intent).",
            candidate_sources=["dense", "dimension:problem"],
            rerank_score=0.93,
            rrf_score=0.84,
            pre_rerank_rank=1,
            post_rerank_rank=1,
        )

        cell = _fill_cell("problem", "p-001", [weak_intro])

        assert cell.support_status == "not_enough_evidence"
        assert cell.content == ""

    def test_fill_cell_rejects_metric_cell_without_metric_language(self):
        weak_metric = EvidenceCandidate(
            source_chunk_id="c-metric-weak",
            paper_id="p-001",
            section_id="introduction",
            content_type="text",
            anchor_text="what is striking about this result is the fact that DaVinci003 was trained with RLHF, a supposedly superior alignment method.",
            candidate_sources=["dense", "dimension:metrics"],
            rerank_score=0.91,
            rrf_score=0.83,
            pre_rerank_rank=1,
            post_rerank_rank=1,
        )

        cell = _fill_cell("metrics", "p-001", [weak_metric])

        assert cell.support_status == "not_enough_evidence"
        assert cell.content == ""

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
