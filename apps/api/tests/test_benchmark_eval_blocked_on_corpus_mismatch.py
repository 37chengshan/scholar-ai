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

spec = importlib.util.spec_from_file_location("v2_3_benchmark_corpus_mismatch", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def test_eval_blocked_when_expected_paper_id_missing_in_collection() -> None:
    rows = [
        module.QueryRow(
            query_id="q1",
            query="test",
            family="fact",
            paper_ids=["v2-p-999"],
            source_chunk_ids=["sid-001"],
        )
    ]
    with pytest.raises(module.BenchmarkGuardError, match="EVAL_BLOCKED"):
        module.validate_official_collection_membership(
            rows=rows,
            collection_paper_ids={"v2-p-001", "v2-p-002"},
            collection_source_chunk_ids={"sid-001", "sid-002"},
        )


def test_eval_blocked_when_expected_source_chunk_id_missing_in_collection() -> None:
    rows = [
        module.QueryRow(
            query_id="q1",
            query="test",
            family="fact",
            paper_ids=["v2-p-001"],
            source_chunk_ids=["sid-missing"],
        )
    ]
    with pytest.raises(module.BenchmarkGuardError, match="EVAL_BLOCKED"):
        module.validate_official_collection_membership(
            rows=rows,
            collection_paper_ids={"v2-p-001"},
            collection_source_chunk_ids={"sid-001", "sid-002"},
        )
