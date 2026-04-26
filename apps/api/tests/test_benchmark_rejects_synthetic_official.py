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

spec = importlib.util.spec_from_file_location("v2_3_benchmark_reject_synthetic", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def test_synthetic_paper_id_blocked_in_official_mode() -> None:
    rows = [
        module.QueryRow(
            query_id="q1",
            query="test",
            family="fact",
            paper_ids=["test-paper-001"],
            source_chunk_ids=["sid-001"],
        )
    ]
    with pytest.raises(module.BenchmarkGuardError, match="EVAL_BLOCKED"):
        module.validate_official_gate_inputs(golden_mode="real", rows=rows, mode="official")


def test_synthetic_golden_mode_only_allowed_for_smoke() -> None:
    rows = [
        module.QueryRow(
            query_id="q1",
            query="test",
            family="fact",
            paper_ids=["v2-p-001"],
            source_chunk_ids=["sid-001"],
        )
    ]
    with pytest.raises(module.BenchmarkGuardError, match="EVAL_BLOCKED"):
        module.validate_official_gate_inputs(golden_mode="synthetic", rows=rows, mode="official")
