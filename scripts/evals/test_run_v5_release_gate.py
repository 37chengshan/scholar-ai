"""Unit tests for run_v5_release_gate.py.

Covers the CRITICAL regex fix (_phases_closed), immutable helpers (_blocked/_ok),
verdict aggregation, and face evaluation parsing.
"""
from __future__ import annotations

import json
import textwrap
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

# Import the module under test.
import run_v5_release_gate as gate


# ---------------------------------------------------------------------------
# _blocked / _ok immutability (HIGH)
# ---------------------------------------------------------------------------

class TestBlockedOkImmutable:
    """_blocked and _ok must return NEW dicts, not mutate the input."""

    def test_blocked_does_not_mutate_input(self):
        original: dict[str, Any] = {"p1_count_open": 1}
        passed, result = gate._blocked("reason", original)
        assert passed is False
        assert result["pass"] is False
        assert result["block_reason"] == "reason"
        # Original must be unchanged
        assert "pass" not in original
        assert "block_reason" not in original

    def test_ok_does_not_mutate_input(self):
        original: dict[str, Any] = {"p1_count_open": 0}
        passed, result = gate._ok(original)
        assert passed is True
        assert result["pass"] is True
        # Original must be unchanged
        assert "pass" not in original

    def test_blocked_preserves_existing_keys(self):
        stub = {"p1_count_open": None, "p2_count_open": 0}
        _, result = gate._blocked("missing", stub)
        assert result["p1_count_open"] is None
        assert result["p2_count_open"] == 0
        assert result["block_reason"] == "missing"

    def test_ok_preserves_existing_keys(self):
        stub = {"p1_count_open": 0, "dims": ["a"]}
        _, result = gate._ok(stub)
        assert result["p1_count_open"] == 0
        assert result["dims"] == ["a"]


# ---------------------------------------------------------------------------
# _phases_closed regex (CRITICAL)
# ---------------------------------------------------------------------------

_PLAN_STATUS_TEMPLATE = textwrap.dedent("""\
    # 计划状态总览

    ## v5.0 方向面板

    | phase | owner | closeout_status | last_verified_at | truth_doc | notes |
    |---|---|---|---|---|---|
    | 0 | product-engineering | closeout-complete / all-deliverables-verified | 2026-05-31 | docs/plans/v5_0/active/phase_0/26.md | Foundation |
    | 1 | web-platform | not-started | - | - | 设计系统 v2 |
    | 2 | web-platform | not-started | - | - | WorkspaceShell v2 |
    | 3 | web-platform | not-started | - | - | 主链精修: Search |
    | 4 | web-platform | not-started | - | - | 主链精修: Read |
    | 5 | web-platform | not-started | - | - | 主链精修: Chat |
    | 6 | web-platform | not-started | - | - | 主链精修: Review |
    | 7 | ai-runtime | not-started | - | - | 后端 Pipeline |
    | 8 | ai-runtime | not-started | - | - | RAG SOTA |
    | 9 | product-engineering | not-started | - | - | Release Gate |

    ## 活跃计划面板
    """)

_ALL_CLOSED_TEMPLATE = textwrap.dedent("""\
    # 计划状态总览

    ## v5.0 方向面板

    | phase | owner | closeout_status | last_verified_at | truth_doc | notes |
    |---|---|---|---|---|---|
    | 0 | product-engineering | closeout-complete / all-deliverables-verified | 2026-05-31 | doc.md | Foundation |
    | 1 | web-platform | closeout-complete | 2026-06-01 | doc.md | 设计系统 |
    | 2 | web-platform | closeout-complete | 2026-06-02 | doc.md | WorkspaceShell |
    | 3 | web-platform | done | 2026-06-03 | doc.md | Search |
    | 4 | web-platform | done | 2026-06-04 | doc.md | Read |
    | 5 | web-platform | done | 2026-06-05 | doc.md | Chat |
    | 6 | web-platform | done | 2026-06-06 | doc.md | Review |
    | 7 | ai-runtime | done | 2026-06-07 | doc.md | Pipeline |
    | 8 | ai-runtime | closeout-complete | 2026-06-08 | doc.md | RAG SOTA |
    | 9 | product-engineering | closeout-complete / verification-passed | 2026-06-09 | doc.md | Gate |

    ## 活跃计划面板
    """)


class TestPhasesClosed:
    """CRITICAL: _phases_closed regex must match the actual v5.0 panel format."""

    def test_returns_false_when_only_phase_0_closed(self, tmp_path: Path):
        """With only phase 0 closed and phases 1-9 not-started, returns False."""
        p = tmp_path / "PLAN_STATUS.md"
        p.write_text(_PLAN_STATUS_TEMPLATE)
        with patch.object(gate, "_PLAN_STATUS", p):
            assert gate._phases_closed() is False

    def test_returns_true_when_all_phases_closed(self, tmp_path: Path):
        """When all phases have closeout-complete or done status, returns True."""
        p = tmp_path / "PLAN_STATUS.md"
        p.write_text(_ALL_CLOSED_TEMPLATE)
        with patch.object(gate, "_PLAN_STATUS", p):
            assert gate._phases_closed() is True

    def test_returns_false_when_plan_status_missing(self, tmp_path: Path):
        p = tmp_path / "PLAN_STATUS.md"
        with patch.object(gate, "_PLAN_STATUS", p):
            assert gate._phases_closed() is False

    def test_returns_false_when_v5_section_missing(self, tmp_path: Path):
        text = "# 计划状态总览\n\n## v3.0 面板\n| phase |\n|---|\n| A |\n"
        p = tmp_path / "PLAN_STATUS.md"
        p.write_text(text)
        with patch.object(gate, "_PLAN_STATUS", p):
            assert gate._phases_closed() is False

    def test_does_not_match_not_started(self, tmp_path: Path):
        """Phases with 'not-started' must NOT be considered closed."""
        p = tmp_path / "PLAN_STATUS.md"
        p.write_text(_PLAN_STATUS_TEMPLATE)
        with patch.object(gate, "_PLAN_STATUS", p):
            assert gate._phases_closed() is False

    def test_does_not_match_v4_panel_phases(self, tmp_path: Path):
        """v4.0 panel uses bare numbers too -- must not be confused with v5.0."""
        text = textwrap.dedent("""\
            # 计划状态总览

            ## v4.0 方向面板

            | phase | owner | closeout_status |
            |---|---|---|
            | 0 | product-engineering | closeout-complete |
            | 1 | product-engineering | closeout-complete |
            | 2 | product-engineering | closeout-complete |
            | 3 | product-engineering | closeout-complete |
            | 4 | web-platform | closeout-complete |
            | 5 | web-platform | closeout-complete |
            | 6 | ai-runtime | done |
            | 7 | ai-platform | done |

            ## v5.0 方向面板

            | phase | owner | closeout_status |
            |---|---|---|
            | 0 | product-engineering | closeout-complete |
            | 1 | web-platform | not-started |
            | 2 | web-platform | not-started |
            | 3 | web-platform | not-started |
            | 4 | web-platform | not-started |
            | 5 | web-platform | not-started |
            | 6 | web-platform | not-started |
            | 7 | ai-runtime | not-started |
            | 8 | ai-runtime | not-started |
            | 9 | product-engineering | not-started |

            ## 活跃计划面板
        """)
        p = tmp_path / "PLAN_STATUS.md"
        p.write_text(text)
        with patch.object(gate, "_PLAN_STATUS", p):
            assert gate._phases_closed() is False

    def test_matches_closeout_status_with_slash(self, tmp_path: Path):
        """closeout-complete / verification-passed style entries must match."""
        text = textwrap.dedent("""\
            ## v5.0 方向面板

            | phase | owner | closeout_status |
            |---|---|---|
            | 0 | x | closeout-complete / verification-passed |
            | 1 | x | closeout-complete / all-deliverables-verified |
            | 2 | x | closeout-complete |
            | 3 | x | done |
            | 4 | x | done |
            | 5 | x | done |
            | 6 | x | done |
            | 7 | x | done |
            | 8 | x | done |
            | 9 | x | done |

            ## 活跃计划面板
        """)
        p = tmp_path / "PLAN_STATUS.md"
        p.write_text(text)
        with patch.object(gate, "_PLAN_STATUS", p):
            assert gate._phases_closed() is True


# ---------------------------------------------------------------------------
# _verdict aggregation
# ---------------------------------------------------------------------------

class TestVerdict:
    def test_release_pass_when_all_pass(self):
        faces = {
            "face_a": (True, {"pass": True}),
            "face_b": (True, {"pass": True}),
            "face_c": (True, {"pass": True}),
            "face_d": (True, {"pass": True}),
            "face_e": (True, {"pass": True}),
        }
        verdict, blocks, downgrades = gate._verdict(faces)
        assert verdict == gate.RELEASE_PASS
        assert blocks == []
        assert downgrades == []

    def test_blocked_when_any_face_blocked(self):
        faces = {
            "face_a": (True, {"pass": True}),
            "face_b": (False, {"pass": False, "block_reason": "regression"}),
            "face_c": (True, {"pass": True}),
            "face_d": (True, {"pass": True}),
            "face_e": (True, {"pass": True}),
        }
        verdict, blocks, _ = gate._verdict(faces)
        assert verdict == gate.BLOCKED
        assert len(blocks) == 1
        assert "face_b" in blocks[0]

    def test_experiment_only_when_downgrade_no_blocks(self):
        faces = {
            "face_a": (True, {"pass": True}),
            "face_b": (True, {"pass": True, "experiment_only": True, "downgrade_reason": "rag_skipped"}),
            "face_c": (True, {"pass": True}),
            "face_d": (True, {"pass": True}),
            "face_e": (True, {"pass": True}),
        }
        verdict, blocks, downgrades = gate._verdict(faces)
        assert verdict == gate.EXPERIMENT_ONLY
        assert blocks == []
        assert len(downgrades) == 1

    def test_blocked_takes_precedence_over_downgrade(self):
        faces = {
            "face_a": (False, {"pass": False, "block_reason": "p1_open"}),
            "face_b": (True, {"pass": True, "experiment_only": True, "downgrade_reason": "rag_skipped"}),
            "face_c": (True, {"pass": True}),
            "face_d": (True, {"pass": True}),
            "face_e": (True, {"pass": True}),
        }
        verdict, _, _ = gate._verdict(faces)
        assert verdict == gate.BLOCKED


# ---------------------------------------------------------------------------
# Face A: Audit parsing
# ---------------------------------------------------------------------------

class TestFaceA:
    def test_blocked_when_no_files(self, tmp_path: Path):
        passed, d = gate._evaluate_face_a(str(tmp_path / "*.md"))
        assert passed is False
        assert d["block_reason"] == "input_missing"

    def test_pass_when_p1_zero(self, tmp_path: Path):
        report = tmp_path / "2026-05-31_multidimensional_audit.md"
        report.write_text(textwrap.dedent("""\
            p1_count_open: `0`
            p2_count_open: `2`
            last_audit_date: `2026-05-31`
            audit_dimensions_covered: `["frontend", "backend", "rag", "governance", "perf"]`
        """))
        with patch.object(gate, "ROOT", tmp_path):
            passed, d = gate._evaluate_face_a(str(tmp_path / "*_multidimensional_audit.md"))
        assert passed is True
        assert d["p1_count_open"] == 0
        assert d["pass"] is True

    def test_blocked_when_p1_positive(self, tmp_path: Path):
        report = tmp_path / "2026-05-31_multidimensional_audit.md"
        report.write_text(textwrap.dedent("""\
            p1_count_open: `3`
            p2_count_open: `0`
            last_audit_date: `2026-05-31`
            audit_dimensions_covered: `["frontend", "backend", "rag", "governance", "perf"]`
        """))
        with patch.object(gate, "ROOT", tmp_path):
            passed, d = gate._evaluate_face_a(str(tmp_path / "*_multidimensional_audit.md"))
        assert passed is False
        assert "p1_open=3" in d["block_reason"]

    def test_experiment_only_when_dims_incomplete(self, tmp_path: Path):
        report = tmp_path / "2026-05-31_multidimensional_audit.md"
        report.write_text(textwrap.dedent("""\
            p1_count_open: `0`
            p2_count_open: `0`
            last_audit_date: `2026-05-31`
            audit_dimensions_covered: `["frontend", "backend"]`
        """))
        with patch.object(gate, "ROOT", tmp_path):
            passed, d = gate._evaluate_face_a(str(tmp_path / "*_multidimensional_audit.md"))
        assert passed is True
        assert d.get("experiment_only") is True


# ---------------------------------------------------------------------------
# Face D: Governance (_phases_closed integration)
# ---------------------------------------------------------------------------

class TestFaceD:
    def test_blocked_when_phases_not_closed(self, tmp_path: Path):
        """Face D should block when _phases_closed returns False."""
        p = tmp_path / "PLAN_STATUS.md"
        p.write_text(_PLAN_STATUS_TEMPLATE)
        with (
            patch.object(gate, "_PLAN_STATUS", p),
            patch.object(gate, "_run_script", return_value=True),
        ):
            passed, d = gate._evaluate_face_d()
        assert passed is False
        assert d["all_phases_closeout"] is False
        assert "all_phases_closeout" in d.get("block_reason", "")


# ---------------------------------------------------------------------------
# V5_PHASE_COUNT constant
# ---------------------------------------------------------------------------

class TestConstants:
    def test_v5_phase_count_is_10(self):
        assert gate._V5_PHASE_COUNT == 10


# ---------------------------------------------------------------------------
# _safe_path helper
# ---------------------------------------------------------------------------

class TestSafePath:
    def test_accepts_path_under_root(self, tmp_path: Path):
        """Paths under ROOT are accepted without error."""
        child = tmp_path / "sub" / "file.txt"
        child.parent.mkdir(parents=True, exist_ok=True)
        child.touch()
        with patch.object(gate, "ROOT", tmp_path):
            result = gate._safe_path(child)
        assert result == child.resolve()

    def test_rejects_path_outside_root(self, tmp_path: Path):
        """Paths that escape ROOT raise ValueError."""
        outside = Path("/etc/passwd")
        with patch.object(gate, "ROOT", tmp_path):
            with pytest.raises(ValueError, match="outside ROOT"):
                gate._safe_path(outside)

    def test_rejects_dot_dot_escape(self, tmp_path: Path):
        """Paths with ../ that escape ROOT raise ValueError."""
        tricky = tmp_path / ".." / ".." / "etc" / "passwd"
        with patch.object(gate, "ROOT", tmp_path):
            with pytest.raises(ValueError, match="outside ROOT"):
                gate._safe_path(tricky)


# ---------------------------------------------------------------------------
# Face C: walkthrough_path parameter wiring
# ---------------------------------------------------------------------------

class TestFaceCParam:
    def test_playwright_report_param_wired(self, tmp_path: Path):
        """_evaluate_face_c accepts walkthrough_path and reads from it."""
        summary = tmp_path / "latest_summary.json"
        summary.write_text(json.dumps({
            "journey_passed_count": 7,
            "journey_failed_count": 0,
            "journey_skipped_count": 0,
            "journey_details": [],
            "last_run_at": "2026-05-31T10:00:00Z",
            "playwright_report_path": "apps/web/playwright-report",
        }))
        passed, d = gate._evaluate_face_c(str(summary))
        assert passed is True
        assert d["journey_passed_count"] == 7

    def test_default_path_used_when_none(self, tmp_path: Path):
        """When walkthrough_path is None, the default _WALKTHROUGH is used."""
        summary = tmp_path / "latest_summary.json"
        summary.write_text(json.dumps({
            "journey_passed_count": 7,
            "journey_failed_count": 0,
            "journey_skipped_count": 0,
            "journey_details": [],
        }))
        with patch.object(gate, "_WALKTHROUGH", summary):
            passed, d = gate._evaluate_face_c()
        assert passed is True


# ---------------------------------------------------------------------------
# Face B: last_benchmark_date population
# ---------------------------------------------------------------------------

class TestFaceBBenchmarkDate:
    def test_date_from_generated_at(self, tmp_path: Path):
        """last_benchmark_date is extracted from generated_at in artifact JSON."""
        run = tmp_path / "run_001"
        run.mkdir()
        acad = run / "academic_bench_001.json"
        acad.write_text(json.dumps({
            "run_id": "r1", "verdict": "pass",
            "generated_at": "2026-05-30T10:00:00Z", "regression_flag": False,
        }))
        wf = run / "workflow_bench_001.json"
        wf.write_text(json.dumps({
            "run_id": "r2", "verdict": "pass",
            "generated_at": "2026-05-30T12:00:00Z", "regression_flag": False,
        }))
        _, d = gate._evaluate_face_b(str(tmp_path))
        assert d["last_benchmark_date"] == "2026-05-30"

    def test_date_from_timestamp_key(self, tmp_path: Path):
        """Falls back to 'timestamp' key when 'generated_at' is absent."""
        run = tmp_path / "run_001"
        run.mkdir()
        acad = run / "academic_bench_001.json"
        acad.write_text(json.dumps({
            "run_id": "r1", "verdict": "pass",
            "timestamp": "2026-04-15T08:00:00Z", "regression_flag": False,
        }))
        wf = run / "workflow_bench_001.json"
        wf.write_text(json.dumps({
            "run_id": "r2", "verdict": "pass",
            "timestamp": "2026-04-15T09:00:00Z", "regression_flag": False,
        }))
        _, d = gate._evaluate_face_b(str(tmp_path))
        assert d["last_benchmark_date"] == "2026-04-15"

    def test_date_fallback_to_mtime(self, tmp_path: Path):
        """Falls back to file mtime when no date key is present."""
        run = tmp_path / "run_001"
        run.mkdir()
        acad = run / "academic_bench_001.json"
        acad.write_text(json.dumps({
            "run_id": "r1", "verdict": "pass", "regression_flag": False,
        }))
        wf = run / "workflow_bench_001.json"
        wf.write_text(json.dumps({
            "run_id": "r2", "verdict": "pass", "regression_flag": False,
        }))
        _, d = gate._evaluate_face_b(str(tmp_path))
        # mtime-based date should be today
        assert d["last_benchmark_date"] is not None
        assert len(d["last_benchmark_date"]) == 10  # YYYY-MM-DD

    def test_none_when_no_artifacts(self, tmp_path: Path):
        """Returns None when no artifact files exist."""
        run = tmp_path / "run_001"
        run.mkdir()
        _, d = gate._evaluate_face_b(str(tmp_path))
        assert d["last_benchmark_date"] is None


# ---------------------------------------------------------------------------
# Face E: a11y score gate
# ---------------------------------------------------------------------------

def _make_lighthouse_json(perf_score: float = 0.95, a11y_score: float = 0.95,
                          lcp: float = 1800, inp: float = 100, cls: float = 0.02,
                          fcp: float = 1200, tbt: float = 150) -> str:
    """Return a minimal Lighthouse JSON string."""
    return json.dumps({
        "categories": {
            "performance": {"score": perf_score},
            "accessibility": {"score": a11y_score},
        },
        "audits": {
            "largest-contentful-paint": {"numericValue": lcp},
            "interactive": {"numericValue": inp},
            "cumulative-layout-shift": {"numericValue": cls},
            "first-contentful-paint": {"numericValue": fcp},
            "total-blocking-time": {"numericValue": tbt},
        },
        "fetchTime": "2026-05-31T10:00:00Z",
    })


class TestFaceEA11y:
    def _setup_perf_dir(self, tmp_path: Path, perf: float = 0.95,
                        a11y: float = 0.95) -> Path:
        pdir = tmp_path / "perf"
        pdir.mkdir()
        for rid in gate._ROUTES:
            f = pdir / f"lighthouse-{rid}.json"
            f.write_text(_make_lighthouse_json(perf_score=perf, a11y_score=a11y))
        return pdir

    def test_a11y_scores_in_output(self, tmp_path: Path):
        """Face E output includes a11y_scores and a11y_min_score."""
        pdir = self._setup_perf_dir(tmp_path, a11y=0.92)
        _, d = gate._evaluate_face_e(str(pdir))
        assert "a11y_scores" in d
        assert "a11y_min_score" in d
        assert d["a11y_min_score"] == 92

    def test_blocked_when_a11y_below_90(self, tmp_path: Path):
        """Face E blocks when a11y_min_score < 90."""
        pdir = self._setup_perf_dir(tmp_path, perf=0.95, a11y=0.85)
        passed, d = gate._evaluate_face_e(str(pdir))
        assert passed is False
        assert "a11y_min=85<90" in d["block_reason"]

    def test_pass_when_a11y_at_90(self, tmp_path: Path):
        """Face E passes when a11y_min_score is exactly 90."""
        pdir = self._setup_perf_dir(tmp_path, a11y=0.90)
        passed, d = gate._evaluate_face_e(str(pdir))
        assert passed is True
        assert d["a11y_min_score"] == 90

    def test_perf_blocked_before_a11y(self, tmp_path: Path):
        """Performance block takes priority over a11y block (checked first)."""
        pdir = self._setup_perf_dir(tmp_path, perf=0.80, a11y=0.85)
        passed, d = gate._evaluate_face_e(str(pdir))
        assert passed is False
        assert "lighthouse_min=80<90" in d["block_reason"]
