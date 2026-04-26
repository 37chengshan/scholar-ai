from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


MODULE_PATH = (
    Path(__file__).resolve().parents[3]
    / "scripts"
    / "evals"
    / "v2_6_official_rag_evaluation.py"
)

spec = importlib.util.spec_from_file_location("v2_6_metrics", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def test_result_record_contains_required_fields() -> None:
    record = module.build_result_record(
        row=module.GoldenRow(
            query_id="q1",
            query="what is the method",
            query_family="method",
            expected_paper_ids=["v2-p-001"],
            expected_source_chunk_ids=["sid-001"],
            expected_content_types=["text"],
            expected_sections=["methods"],
            expected_answer_mode="full",
            evidence_anchors=[],
        ),
        stage="raw",
        collection="paper_contents_v2_api_tongyi_flash_raw_v2_4",
        runtime_profile="api_flash_qwen_rerank_glm",
        retrieved_source_chunk_ids_top5=["sid-001"],
        retrieved_paper_ids_top5=["v2-p-001"],
        metrics={
            "recall_at_5": 1.0,
            "recall_at_10": 1.0,
            "mrr": 1.0,
            "ndcg_at_10": 1.0,
            "paper_hit_rate": 1.0,
            "section_hit_rate": 1.0,
            "chunk_hit_rate": 1.0,
            "table_hit_rate": 0.0,
            "figure_hit_rate": 0.0,
            "numeric_exact_match": 0.0,
            "citation_coverage": 1.0,
            "unsupported_claim_rate": 0.0,
            "answer_evidence_consistency": 1.0,
            "citation_jump_validity": 1.0,
        },
        answer_mode="full",
        fallback_used=False,
        deprecated_branch_used=False,
        dimension_mismatch=False,
        provider_error=None,
        timeout=False,
        latency_ms=123,
    )

    required_keys = {
        "query_id",
        "query_family",
        "stage",
        "runtime_profile",
        "embedding_model",
        "reranker_model",
        "llm_model",
        "collection",
        "expected_paper_ids",
        "expected_source_chunk_ids",
        "retrieved_source_chunk_ids_top5",
        "retrieved_paper_ids_top5",
        "recall_at_5",
        "recall_at_10",
        "mrr",
        "ndcg_at_10",
        "paper_hit_rate",
        "section_hit_rate",
        "chunk_hit_rate",
        "table_hit_rate",
        "figure_hit_rate",
        "numeric_exact_match",
        "citation_coverage",
        "unsupported_claim_rate",
        "answer_evidence_consistency",
        "citation_jump_validity",
        "answer_mode",
        "fallback_used",
        "deprecated_branch_used",
        "dimension_mismatch",
        "provider_error",
        "timeout",
        "latency_ms",
    }
    assert required_keys.issubset(record.keys())


def test_summary_emits_overall_and_family_metrics() -> None:
    results = [
        {
            "query_id": "q1",
            "query_family": "fact",
            "stage": "raw",
            "recall_at_10": 1.0,
            "citation_coverage": 0.9,
            "unsupported_claim_rate": 0.0,
            "answer_evidence_consistency": 0.8,
            "citation_jump_validity": 1.0,
            "answer_mode": "full",
            "fallback_used": False,
            "deprecated_branch_used": False,
            "dimension_mismatch": False,
            "provider_error": None,
            "timeout": False,
            "latency_ms": 1000,
            "table_hit_rate": 0.0,
            "figure_hit_rate": 0.0,
            "paper_hit_rate": 1.0,
            "section_hit_rate": 1.0,
            "chunk_hit_rate": 1.0,
            "recall_at_5": 1.0,
            "mrr": 1.0,
            "ndcg_at_10": 1.0,
            "numeric_exact_match": 0.0,
        },
        {
            "query_id": "q2",
            "query_family": "table",
            "stage": "raw",
            "recall_at_10": 0.8,
            "citation_coverage": 0.8,
            "unsupported_claim_rate": 0.1,
            "answer_evidence_consistency": 0.7,
            "citation_jump_validity": 1.0,
            "answer_mode": "partial",
            "fallback_used": False,
            "deprecated_branch_used": False,
            "dimension_mismatch": False,
            "provider_error": None,
            "timeout": False,
            "latency_ms": 2000,
            "table_hit_rate": 1.0,
            "figure_hit_rate": 0.0,
            "paper_hit_rate": 1.0,
            "section_hit_rate": 1.0,
            "chunk_hit_rate": 1.0,
            "recall_at_5": 1.0,
            "mrr": 0.5,
            "ndcg_at_10": 0.9,
            "numeric_exact_match": 0.0,
        },
    ]

    summary = module.summarize_results(results)

    assert "overall" in summary
    assert "by_query_family" in summary
    assert summary["by_query_family"]["table"]["table_hit_rate"] == 1.0
