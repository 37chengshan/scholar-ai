"""Tests for benchmark runtime/profile guard behavior."""

from __future__ import annotations

from pathlib import Path
import importlib.util
import sys

import pytest


MODULE_PATH = (
    Path(__file__).resolve().parents[3]
    / "scripts"
    / "evals"
    / "v2_3_benchmark.py"
)

spec = importlib.util.spec_from_file_location("v2_3_benchmark", MODULE_PATH)
v2_3_benchmark = importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules[spec.name] = v2_3_benchmark
spec.loader.exec_module(v2_3_benchmark)


class _Row:
    def __init__(self, paper_ids):
        self.paper_ids = paper_ids


def test_official_runtime_profile_only():
    with pytest.raises(v2_3_benchmark.BenchmarkGuardError):
        v2_3_benchmark.validate_benchmark_runtime("qwen_dual")


def test_official_benchmark_blocks_synthetic_golden():
    with pytest.raises(v2_3_benchmark.BenchmarkGuardError, match="synthetic"):
        v2_3_benchmark.validate_official_gate_inputs(
            golden_mode="synthetic",
            rows=[_Row(["v2-p-001"])],
        )


def test_eval_blocked_when_golden_id_not_in_current_corpus():
    with pytest.raises(v2_3_benchmark.BenchmarkGuardError, match="EVAL_BLOCKED"):
        v2_3_benchmark.validate_official_gate_inputs(
            golden_mode="real",
            rows=[_Row(["legacy-001"])],
        )


def test_runtime_metadata_contains_required_fields():
    metadata = v2_3_benchmark.build_runtime_metadata(
        runtime_profile="api_flash_qwen_rerank_glm",
        deprecated_branch_used=False,
        synthetic_for_official=False,
    )
    assert metadata["runtime_profile"] == "api_flash_qwen_rerank_glm"
    assert metadata["embedding_model"] == "tongyi-embedding-vision-flash-2026-03-06"
    assert metadata["reranker_model"] == "qwen3-vl-rerank"
    assert metadata["llm_model"] == "glm-4.5-air"
    assert metadata["deprecated_branch_used"] is False
    assert metadata["synthetic_golden_used_for_official_gate"] is False
