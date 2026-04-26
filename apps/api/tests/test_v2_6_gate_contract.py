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

spec = importlib.util.spec_from_file_location("v2_6_gate", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def _overall(**overrides):
    baseline = {
        "citation_coverage": 0.86,
        "unsupported_claim_rate": 0.08,
        "answer_evidence_consistency": 0.66,
        "citation_jump_validity": 0.95,
        "recall_at_10": 0.9,
        "table_hit_rate": 0.2,
        "figure_hit_rate": 0.2,
        "cross_paper_coverage": 0.2,
        "fallback_used_count": 0,
        "deprecated_branch_used_count": 0,
        "dimension_mismatch_count": 0,
        "provider_hard_error_count": 0,
    }
    baseline.update(overrides)
    return baseline


def test_gate_blocked_when_fallback_used() -> None:
    verdict = module.decide_gate(_overall(fallback_used_count=1))
    assert verdict["status"] == "BLOCKED"


def test_gate_blocked_when_deprecated_branch_used() -> None:
    verdict = module.decide_gate(_overall(deprecated_branch_used_count=1))
    assert verdict["status"] == "BLOCKED"


def test_gate_blocked_when_dimension_mismatch_used() -> None:
    verdict = module.decide_gate(_overall(dimension_mismatch_count=1))
    assert verdict["status"] == "BLOCKED"


def test_comparison_selects_recommended_default_stage() -> None:
    comparison = module.build_stage_comparison(
        {
            "raw": {"overall": {"citation_coverage": 0.88, "answer_evidence_consistency": 0.67, "latency_p95_ms": 4000}},
            "rule": {"overall": {"citation_coverage": 0.84, "answer_evidence_consistency": 0.7, "latency_p95_ms": 4200}},
            "llm": {"overall": {"citation_coverage": 0.8, "answer_evidence_consistency": 0.6, "latency_p95_ms": 8000}},
        }
    )

    assert comparison["recommended_default_stage"] in {"raw", "rule", "llm"}
    assert comparison["recommended_default_stage"] == "raw"