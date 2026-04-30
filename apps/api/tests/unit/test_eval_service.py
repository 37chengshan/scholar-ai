"""Unit tests for Phase 6 eval_service — filesystem-backed eval metrics."""
from __future__ import annotations

import json
import pathlib
import pytest

from app.services.eval_service import (
    PHASE6_THRESHOLDS,
    PHASE6_REQUIRED_QUERY_FAMILIES,
    NormalizedMetrics,
    _evaluate_gate,
    compute_diff,
    get_overview,
    get_run_detail,
    list_run_summaries,
    load_corpus,
    load_manifest,
    run_offline_gate,
)
from app.api.evals import eval_runs


# ─── Fixtures ─────────────────────────────────────────────────────────────────


def _make_summary(
    *,
    retrieval_hit_rate: float = 0.90,
    recall_at_5: float = 0.88,
    recall_at_10: float = 0.93,
    rerank_gain: float = 0.05,
    citation_jump_valid_rate: float = 0.92,
    answer_supported_rate: float = 0.87,
    groundedness: float = 0.80,
    abstain_precision: float = 0.91,
    fallback_used_count: int = 3,
    latency_p50: float = 1.2,
    latency_p95: float = 4.5,
    cost_per_answer: float = 0.0012,
    overall_verdict: str = "PASS",
) -> dict:
    return {
        "retrieval_hit_rate": retrieval_hit_rate,
        "top_k_recall": {"recall_at_5": recall_at_5, "recall_at_10": recall_at_10},
        "rerank_gain": rerank_gain,
        "citation_jump_valid_rate": citation_jump_valid_rate,
        "answer_supported_rate": answer_supported_rate,
        "groundedness": groundedness,
        "abstain_precision": abstain_precision,
        "fallback_used_count": fallback_used_count,
        "latency_p50": latency_p50,
        "latency_p95": latency_p95,
        "cost_per_answer": cost_per_answer,
        "overall_verdict": overall_verdict,
        "gate_failures": [],
    }


def _make_meta(
    run_id: str = "run_test_001",
    mode: str = "offline",
    reranker: str = "on",
    verdict: str = "PASS",
) -> dict:
    return {
        "run_id": run_id,
        "dataset_version": "phase6-v1",
        "total_queries": 128,
        "mode": mode,
        "reranker": reranker,
        "overall_verdict": verdict,
        "created_at": "2026-04-28T00:00:00Z",
        "family_counts": {},
    }


@pytest.fixture()
def fake_run_tree(tmp_path: pathlib.Path) -> tuple[pathlib.Path, str]:
    """Create a fake phase6 artifact tree under tmp_path and return (root, run_id)."""
    run_id = "run_fake_001"
    run_dir = tmp_path / "runs" / run_id
    run_dir.mkdir(parents=True)

    (run_dir / "meta.json").write_text(json.dumps(_make_meta(run_id=run_id)), encoding="utf-8")
    (run_dir / "dashboard_summary.json").write_text(json.dumps(_make_summary()), encoding="utf-8")
    (run_dir / "retrieval.json").write_text(
        json.dumps({
            "retrieval_hit_rate": 0.90,
            "recall_at_5": 0.88,
            "recall_at_10": 0.93,
            "by_family": {"rag_basics": {"recall_at_5": 0.90, "recall_at_10": 0.94}},
        }),
        encoding="utf-8",
    )
    (run_dir / "answer_quality.json").write_text(
        json.dumps({
            "answer_supported_rate": 0.87,
            "groundedness": 0.80,
            "abstain_precision": 0.91,
            "by_family": {"rag_basics": {"answer_supported_rate": 0.88}},
        }),
        encoding="utf-8",
    )
    (run_dir / "citation_jump.json").write_text(
        json.dumps({
            "citation_jump_valid_rate": 0.92,
            "total_citations_checked": 100,
            "valid_citations": 92,
            "invalid_citations": 8,
            "invalid_reasons": {},
        }),
        encoding="utf-8",
    )
    (run_dir / "diff_from_baseline.json").write_text(
        json.dumps({"base_run_id": None, "note": "initial baseline"}),
        encoding="utf-8",
    )

    manifest = {"runs": [_make_meta(run_id=run_id)]}
    (tmp_path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    return tmp_path, run_id


# ─── _evaluate_gate ──────────────────────────────────────────────────────────


def test_evaluate_gate_pass():
    """All metrics above threshold → PASS with no failures."""
    m = NormalizedMetrics(
        retrieval_hit_rate=0.85,
        recall_at_5=0.80,
        recall_at_10=0.90,
        rerank_gain=0.05,
        citation_jump_valid_rate=0.90,
        answer_supported_rate=0.85,
        groundedness=0.75,
        abstain_precision=0.85,
        fallback_used_count=0,
        latency_p50=1.0,
        latency_p95=5.0,
        cost_per_answer=0.001,
    )
    verdict, failures = _evaluate_gate(m)
    assert verdict == "PASS"
    assert failures == []


def test_evaluate_gate_fail_retrieval():
    """retrieval_hit_rate below threshold → FAIL with relevant message."""
    m = NormalizedMetrics(
        retrieval_hit_rate=0.70,  # below 0.80
        recall_at_5=0.80,
        recall_at_10=0.90,
        rerank_gain=0.0,
        citation_jump_valid_rate=0.90,
        answer_supported_rate=0.85,
        groundedness=0.75,
        abstain_precision=0.85,
        fallback_used_count=0,
        latency_p50=1.0,
        latency_p95=5.0,
        cost_per_answer=0.001,
    )
    verdict, failures = _evaluate_gate(m)
    assert verdict == "FAIL"
    assert any("retrieval_hit_rate" in f for f in failures)


def test_evaluate_gate_fail_latency():
    """latency_p95 above max threshold → FAIL."""
    m = NormalizedMetrics(
        retrieval_hit_rate=0.85,
        recall_at_5=0.80,
        recall_at_10=0.90,
        rerank_gain=0.0,
        citation_jump_valid_rate=0.90,
        answer_supported_rate=0.85,
        groundedness=0.75,
        abstain_precision=0.85,
        fallback_used_count=0,
        latency_p50=2.0,
        latency_p95=12.0,  # above max 8.0
        cost_per_answer=0.001,
    )
    verdict, failures = _evaluate_gate(m)
    assert verdict == "FAIL"
    assert any("latency_p95" in f for f in failures)


def test_evaluate_gate_multiple_failures():
    """Multiple metrics below threshold → FAIL with multiple messages."""
    m = NormalizedMetrics(
        retrieval_hit_rate=0.50,
        recall_at_5=0.50,
        recall_at_10=0.60,
        rerank_gain=0.0,
        citation_jump_valid_rate=0.70,
        answer_supported_rate=0.60,
        groundedness=0.50,
        abstain_precision=0.60,
        fallback_used_count=0,
        latency_p50=3.0,
        latency_p95=15.0,
        cost_per_answer=0.001,
    )
    verdict, failures = _evaluate_gate(m)
    assert verdict == "FAIL"
    assert len(failures) >= 3


def test_evaluate_gate_fails_when_fallback_count_exceeds_limit():
    m = NormalizedMetrics(
        retrieval_hit_rate=0.85,
        recall_at_5=0.80,
        recall_at_10=0.90,
        rerank_gain=0.0,
        citation_jump_valid_rate=0.90,
        answer_supported_rate=0.85,
        groundedness=0.75,
        abstain_precision=0.85,
        fallback_used_count=9,
        latency_p50=2.0,
        latency_p95=5.0,
        cost_per_answer=0.001,
    )
    verdict, failures = _evaluate_gate(m)
    assert verdict == "FAIL"
    assert any("fallback_used_count" in failure for failure in failures)


def test_evaluate_gate_fails_when_cost_is_missing():
    m = NormalizedMetrics(
        retrieval_hit_rate=0.85,
        recall_at_5=0.80,
        recall_at_10=0.90,
        rerank_gain=0.0,
        citation_jump_valid_rate=0.90,
        answer_supported_rate=0.85,
        groundedness=0.75,
        abstain_precision=0.85,
        fallback_used_count=0,
        latency_p50=2.0,
        latency_p95=5.0,
        cost_per_answer=0.0,
        cost_per_answer_present=False,
    )
    verdict, failures = _evaluate_gate(m)
    assert verdict == "FAIL"
    assert any("cost_per_answer" in failure for failure in failures)


# ─── load_manifest / list_run_summaries ──────────────────────────────────────


def test_load_manifest_returns_real_manifest():
    """load_manifest() reads from the actual phase6 artifacts (baseline seed run present)."""
    manifest = load_manifest()
    assert "runs" in manifest
    # At minimum the seed baseline run should exist
    assert len(manifest["runs"]) >= 1


def test_list_run_summaries_newest_first():
    """list_run_summaries returns newest-first (reversed manifest order)."""
    runs = list_run_summaries()
    assert isinstance(runs, list)
    assert len(runs) >= 1
    assert "run_id" in runs[0]


# ─── get_run_detail ───────────────────────────────────────────────────────────


def test_get_run_detail_baseline_seed():
    """get_run_detail works on the real seed baseline run."""
    detail = get_run_detail("run_phase6_baseline_001")
    assert detail is not None
    assert detail["run_id"] == "run_phase6_baseline_001"
    assert "metrics" in detail
    assert "retrieval_hit_rate" in detail["metrics"]
    assert "top_k_recall" in detail["metrics"]
    assert "by_family" in detail


def test_get_run_detail_missing_returns_none():
    """Non-existent run_id returns None (no exception)."""
    result = get_run_detail("run_does_not_exist_xyz_999")
    assert result is None


def test_get_run_detail_metrics_gate_reevaluated():
    """Metrics gate is re-evaluated regardless of stored verdict."""
    detail = get_run_detail("run_phase6_baseline_001")
    assert detail is not None
    verdict = detail["metrics"]["overall_verdict"]
    assert verdict in ("PASS", "FAIL", "UNKNOWN")
    # gate_failures list must be present
    assert isinstance(detail["metrics"]["gate_failures"], list)


def test_get_run_detail_v3_reads_evidence_artifact(tmp_path, monkeypatch):
    import app.services.eval_service as svc

    run_id = "run_v3_001"
    run_dir = tmp_path / "runs" / run_id
    run_dir.mkdir(parents=True)

    meta = _make_meta(run_id=run_id, mode="public_offline")
    meta["dataset_version"] = "v3_0_academic"
    (run_dir / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    (run_dir / "dashboard_summary.json").write_text(json.dumps(_make_summary()), encoding="utf-8")
    (run_dir / "retrieval.json").write_text(json.dumps({"by_family": {}}), encoding="utf-8")
    (run_dir / "answer_quality.json").write_text(json.dumps({"by_family": {}}), encoding="utf-8")
    (run_dir / "evidence.json").write_text(
        json.dumps(
            {
                "total_citations_checked": 12,
                "valid_citations": 10,
                "invalid_citations": 2,
                "invalid_reasons": {"missing_anchor": 2},
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(svc, "_benchmark_root", lambda benchmark="phase6": tmp_path)

    detail = get_run_detail(run_id, "v3_0_academic")
    assert detail is not None
    assert detail["citation_jump_detail"]["total_checked"] == 12
    assert detail["citation_jump_detail"]["valid"] == 10
    assert detail["citation_jump_detail"]["invalid"] == 2


@pytest.mark.asyncio
async def test_eval_runs_offline_filter_includes_v3_offline_modes(mocker):
    mocker.patch(
        "app.api.evals.list_run_summaries",
        return_value=[
            {"run_id": "run-1", "mode": "public_offline"},
            {"run_id": "run-2", "mode": "blind_offline"},
            {"run_id": "run-3", "mode": "online"},
        ],
    )

    response = await eval_runs(benchmark="v3_0_academic", mode="offline", limit=20, offset=0)

    assert response["meta"]["total"] == 2
    assert [item["run_id"] for item in response["data"]["items"]] == ["run-1", "run-2"]


# ─── get_overview ─────────────────────────────────────────────────────────────


def test_get_overview_structure():
    """get_overview() returns required keys."""
    ov = get_overview()
    assert "run_count" in ov
    assert "offline_count" in ov
    assert "online_count" in ov
    assert "recent_runs" in ov
    assert isinstance(ov["recent_runs"], list)


def test_get_overview_latest_offline_gate():
    """latest_offline_gate is populated (seed baseline is offline)."""
    ov = get_overview()
    gate = ov.get("latest_offline_gate")
    assert gate is not None
    assert "run_id" in gate
    assert "verdict" in gate
    assert "metrics" in gate
    assert "gate_failures" in gate


# ─── compute_diff ─────────────────────────────────────────────────────────────


def test_compute_diff_same_run_all_unchanged():
    """Diffing a run against itself → all deltas 0, status unchanged."""
    diff = compute_diff("run_phase6_baseline_001", "run_phase6_baseline_001")
    assert diff is not None
    for key, d in diff["deltas"].items():
        assert d["delta"] == pytest.approx(0.0, abs=1e-6), f"Expected 0 delta for {key}"
        assert d["status"] == "unchanged"
    assert diff["summary"]["improved"] == 0
    assert diff["summary"]["regressed"] == 0


def test_compute_diff_missing_run_returns_none():
    """Missing candidate run → None."""
    result = compute_diff("run_phase6_baseline_001", "run_missing_xyz_999")
    assert result is None


def test_compute_diff_delta_classification(tmp_path, monkeypatch):
    """Delta classification: positive for higher-is-better = improved; negative = regressed."""
    import app.services.eval_service as svc

    # Create two stub runs under tmp_path
    runs_dir = tmp_path / "runs"
    base_dir = runs_dir / "run_base"
    cand_dir = runs_dir / "run_cand"
    base_dir.mkdir(parents=True)
    cand_dir.mkdir(parents=True)

    base_summary = _make_summary(retrieval_hit_rate=0.80, latency_p95=6.0)
    cand_summary = _make_summary(retrieval_hit_rate=0.90, latency_p95=4.0)  # both improved

    (base_dir / "meta.json").write_text(json.dumps(_make_meta("run_base")), encoding="utf-8")
    (cand_dir / "meta.json").write_text(json.dumps(_make_meta("run_cand")), encoding="utf-8")
    (base_dir / "dashboard_summary.json").write_text(json.dumps(base_summary), encoding="utf-8")
    (cand_dir / "dashboard_summary.json").write_text(json.dumps(cand_summary), encoding="utf-8")

    # Monkeypatch the _runs_dir helper
    monkeypatch.setattr(svc, "_runs_dir", lambda: runs_dir)

    diff = compute_diff("run_base", "run_cand")
    assert diff is not None
    assert diff["deltas"]["retrieval_hit_rate"]["status"] == "improved"
    assert diff["deltas"]["latency_p95"]["status"] == "improved"
    assert diff["summary"]["improved"] >= 2


# ─── Threshold sanity ─────────────────────────────────────────────────────────


def test_phase6_thresholds_present():
    """All required threshold keys are present."""
    required = {
        "retrieval_hit_rate",
        "recall_at_5",
        "citation_jump_valid_rate",
        "answer_supported_rate",
        "groundedness",
        "abstain_precision",
        "latency_p95",
    }
    assert required.issubset(PHASE6_THRESHOLDS.keys())


def test_load_corpus_real_metadata_shape():
    corpus = load_corpus()
    assert corpus.get("paper_count", 0) >= 50
    assert corpus.get("query_count", 0) >= 128
    assert PHASE6_REQUIRED_QUERY_FAMILIES.issubset(set(corpus.get("query_families", [])))


def test_run_offline_gate_real_artifacts_pass():
    passed, detail = run_offline_gate()
    assert passed is True
    assert detail["verdict"] == "PASS"
    assert detail["baseline_run_id"] == "run_phase6_baseline_001"
    assert detail["candidate_run_id"] == "run_phase6_candidate_001"
    assert isinstance(detail["gate_failures"], list)
    assert detail["gate_failures"] == []


def test_run_offline_gate_passes_with_full_candidate_bundle(tmp_path, monkeypatch):
    import app.services.eval_service as svc

    corpus = {
        "version": "phase6-v1",
        "paper_count": 50,
        "query_count": 128,
        "query_families": sorted(PHASE6_REQUIRED_QUERY_FAMILIES),
        "queries": [
            {
                "query_id": f"q{i:03d}",
                "family": sorted(PHASE6_REQUIRED_QUERY_FAMILIES)[i % len(PHASE6_REQUIRED_QUERY_FAMILIES)],
                "question": f"Question {i}",
                "expected_paper_ids": ["paper-1"],
                "expected_sections": ["method"],
                "must_abstain": False,
                "expected_citation_targets": [],
            }
            for i in range(128)
        ],
    }
    (tmp_path / "corpus.json").write_text(json.dumps(corpus), encoding="utf-8")

    runs_dir = tmp_path / "runs"
    base_dir = runs_dir / "run_base"
    cand_dir = runs_dir / "run_cand"
    base_dir.mkdir(parents=True)
    cand_dir.mkdir(parents=True)

    (base_dir / "meta.json").write_text(json.dumps(_make_meta("run_base")), encoding="utf-8")
    (cand_dir / "meta.json").write_text(json.dumps(_make_meta("run_cand")), encoding="utf-8")
    (base_dir / "dashboard_summary.json").write_text(json.dumps(_make_summary()), encoding="utf-8")
    (cand_dir / "dashboard_summary.json").write_text(json.dumps(_make_summary()), encoding="utf-8")
    (base_dir / "retrieval.json").write_text(json.dumps({"by_family": {}}), encoding="utf-8")
    (cand_dir / "retrieval.json").write_text(json.dumps({"by_family": {}}), encoding="utf-8")
    (base_dir / "answer_quality.json").write_text(json.dumps({"by_family": {}}), encoding="utf-8")
    (cand_dir / "answer_quality.json").write_text(json.dumps({"by_family": {}}), encoding="utf-8")
    (base_dir / "citation_jump.json").write_text(json.dumps({"invalid_reasons": {}}), encoding="utf-8")
    (cand_dir / "citation_jump.json").write_text(json.dumps({"invalid_reasons": {}}), encoding="utf-8")
    (cand_dir / "diff_from_baseline.json").write_text(
        json.dumps({"base_run_id": "run_base", "candidate_run_id": "run_cand"}),
        encoding="utf-8",
    )
    (tmp_path / "manifest.json").write_text(
        json.dumps(
            {
                "runs": [
                    _make_meta("run_base"),
                    _make_meta("run_cand"),
                ]
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(svc, "_phase6_root", lambda: tmp_path)

    passed, detail = run_offline_gate()
    assert passed is True
    assert detail["verdict"] == "PASS"
    assert detail["baseline_run_id"] == "run_base"
    assert detail["candidate_run_id"] == "run_cand"
