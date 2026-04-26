from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest


MODULE_PATH = (
    Path(__file__).resolve().parents[3]
    / "scripts"
    / "evals"
    / "v2_6_official_rag_evaluation.py"
)

spec = importlib.util.spec_from_file_location("v2_6_official_rag_evaluation", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def _write_golden(path: Path, queries: list[dict]) -> Path:
    payload = {
        "version": "v2_5_real_golden",
        "query_count": len(queries),
        "queries": queries,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def test_official_runner_rejects_synthetic_golden(tmp_path: Path) -> None:
    golden_path = tmp_path / "synthetic.json"
    payload = {
        "version": "synthetic_golden",
        "queries": [
            {
                "query_id": "q1",
                "query": "test",
                "query_family": "fact",
                "expected_paper_ids": ["test-paper-001"],
                "expected_source_chunk_ids": ["sid-001"],
            }
        ],
    }
    golden_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(module.BenchmarkGuardError, match="EVAL_BLOCKED"):
        module.load_golden_rows(golden_path, mode="official")


def test_official_runner_requires_real_golden_file() -> None:
    with pytest.raises(module.BenchmarkGuardError, match="EVAL_BLOCKED"):
        module.load_golden_rows(Path("/tmp/does-not-exist-real-golden.json"), mode="official")


def test_runner_supports_resume(tmp_path: Path) -> None:
    rows = [
        module.GoldenRow(
            query_id="q1",
            query="one",
            query_family="fact",
            expected_paper_ids=["v2-p-001"],
            expected_source_chunk_ids=["sid-001"],
            expected_content_types=["text"],
            expected_sections=["body"],
            expected_answer_mode="full",
            evidence_anchors=[],
        ),
        module.GoldenRow(
            query_id="q2",
            query="two",
            query_family="method",
            expected_paper_ids=["v2-p-002"],
            expected_source_chunk_ids=["sid-002"],
            expected_content_types=["text"],
            expected_sections=["methods"],
            expected_answer_mode="full",
            evidence_anchors=[],
        ),
    ]
    partial_path = tmp_path / "partial_results.jsonl"
    partial_path.write_text(
        json.dumps({"query_id": "q1", "stage": "raw", "status": "ok"}) + "\n",
        encoding="utf-8",
    )

    completed = module.load_completed_result_keys(partial_path)
    pending = module.filter_pending_rows(rows, stage="raw", completed_keys=completed)

    assert completed == {"q1::raw"}
    assert [row.query_id for row in pending] == ["q2"]


def test_timeout_query_does_not_block_global(tmp_path: Path) -> None:
    rows = [
        module.GoldenRow(
            query_id="q1",
            query="one",
            query_family="fact",
            expected_paper_ids=["v2-p-001"],
            expected_source_chunk_ids=["sid-001"],
            expected_content_types=["text"],
            expected_sections=["body"],
            expected_answer_mode="full",
            evidence_anchors=[],
        ),
        module.GoldenRow(
            query_id="q2",
            query="two",
            query_family="fact",
            expected_paper_ids=["v2-p-002"],
            expected_source_chunk_ids=["sid-002"],
            expected_content_types=["text"],
            expected_sections=["body"],
            expected_answer_mode="full",
            evidence_anchors=[],
        ),
    ]
    partial_path = tmp_path / "partial_results.jsonl"
    failed_path = tmp_path / "failed_queries.json"
    timeout_path = tmp_path / "timeout_queries.json"

    def evaluator(row: module.GoldenRow, stage: str) -> dict:
        if row.query_id == "q1":
            raise TimeoutError("simulated timeout")
        return {"query_id": row.query_id, "stage": stage, "status": "ok", "latency_ms": 10}

    results = module.process_rows(
        rows=rows,
        stage="raw",
        runtime_profile="api_flash_qwen_rerank_glm",
        evaluator=evaluator,
        partial_results_path=partial_path,
        failed_queries_path=failed_path,
        timeout_queries_path=timeout_path,
        timeout_seconds=1,
        save_every=1,
        fail_fast=False,
    )

    assert len(results) == 2
    assert results[0]["timeout"] is True
    assert results[1]["status"] == "ok"

    timeout_payload = json.loads(timeout_path.read_text(encoding="utf-8"))
    assert timeout_payload[0]["query_id"] == "q1"
