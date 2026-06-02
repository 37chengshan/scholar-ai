"""Unit tests for generate_walkthrough_summary.py.

Covers: all pass, partial fail, all skip, missing input file.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

import generate_walkthrough_summary as ws


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_pw_result(suites: list[dict]) -> dict:
    """Build a minimal Playwright JSON result structure."""
    return {"suites": suites}


def _make_suite(spec_file: str, status: str = "passed", error_msg: str | None = None) -> dict:
    """Build a single suite with one spec/test/result."""
    result: dict = {"status": status}
    if error_msg:
        result["errors"] = [{"message": error_msg}]
    return {
        "file": spec_file,
        "specs": [{
            "title": f"test for {spec_file}",
            "tests": [{"results": [result]}],
        }],
        "suites": [],
    }


# ---------------------------------------------------------------------------
# All 7 journeys pass
# ---------------------------------------------------------------------------

class TestAllPass:
    def test_all_pass(self, tmp_path: Path):
        suites = [
            _make_suite(f"journey-j{i}-test.spec.ts", "passed")
            for i in range(1, 8)
        ]
        pw_json = tmp_path / "pw.json"
        pw_json.write_text(json.dumps(_make_pw_result(suites)))
        out = tmp_path / "summary.json"

        result = ws.generate_summary(pw_json, out)

        assert result["journey_passed_count"] == 7
        assert result["journey_failed_count"] == 0
        assert result["journey_skipped_count"] == 0
        assert len(result["journey_details"]) == 7
        assert all(d["status"] == "passed" for d in result["journey_details"])
        assert out.exists()


# ---------------------------------------------------------------------------
# Partial failure
# ---------------------------------------------------------------------------

class TestPartialFail:
    def test_some_failed(self, tmp_path: Path):
        suites = [
            _make_suite("journey-j1-test.spec.ts", "passed"),
            _make_suite("journey-j2-test.spec.ts", "failed", "timeout"),
            _make_suite("journey-j3-test.spec.ts", "passed"),
        ]
        pw_json = tmp_path / "pw.json"
        pw_json.write_text(json.dumps(_make_pw_result(suites)))
        out = tmp_path / "summary.json"

        result = ws.generate_summary(pw_json, out)

        assert result["journey_passed_count"] == 2
        assert result["journey_failed_count"] == 1
        assert result["journey_skipped_count"] == 4  # J4-J7 missing -> skipped

        j2 = next(d for d in result["journey_details"] if d["journey_id"] == "J2")
        assert j2["status"] == "failed"
        assert j2["error_summary"] == "timeout"


# ---------------------------------------------------------------------------
# All skipped (no matching journeys)
# ---------------------------------------------------------------------------

class TestAllSkipped:
    def test_no_journey_specs(self, tmp_path: Path):
        """When no journey specs exist, all 7 are skipped."""
        suites = [_make_suite("other-test.spec.ts", "passed")]
        pw_json = tmp_path / "pw.json"
        pw_json.write_text(json.dumps(_make_pw_result(suites)))
        out = tmp_path / "summary.json"

        result = ws.generate_summary(pw_json, out)

        assert result["journey_passed_count"] == 0
        assert result["journey_failed_count"] == 0
        assert result["journey_skipped_count"] == 7
        assert all(d["status"] == "skipped" for d in result["journey_details"])


# ---------------------------------------------------------------------------
# Missing input file
# ---------------------------------------------------------------------------

class TestMissingInput:
    def test_missing_pw_json(self, tmp_path: Path):
        """When Playwright JSON doesn't exist, generates all-skipped summary."""
        pw_json = tmp_path / "nonexistent.json"
        out = tmp_path / "summary.json"

        result = ws.generate_summary(pw_json, out)

        assert result["journey_passed_count"] == 0
        assert result["journey_failed_count"] == 0
        assert result["journey_skipped_count"] == 7
        assert out.exists()


# ---------------------------------------------------------------------------
# Schema contract
# ---------------------------------------------------------------------------

class TestSchemaContract:
    def test_output_matches_gate_runner_face_c_schema(self, tmp_path: Path):
        """Output JSON has all fields that Face C parser expects."""
        pw_json = tmp_path / "pw.json"
        pw_json.write_text(json.dumps(_make_pw_result([])))
        out = tmp_path / "summary.json"

        result = ws.generate_summary(pw_json, out)

        # Required fields per Face C (L224-246 of run_v5_release_gate.py)
        assert "journey_passed_count" in result
        assert "journey_failed_count" in result
        assert "journey_skipped_count" in result
        assert "journey_details" in result
        assert "last_run_at" in result
        assert "playwright_report_path" in result

        # Type checks
        assert isinstance(result["journey_passed_count"], int)
        assert isinstance(result["journey_failed_count"], int)
        assert isinstance(result["journey_skipped_count"], int)
        assert isinstance(result["journey_details"], list)

        for d in result["journey_details"]:
            assert "journey_id" in d
            assert "status" in d
            assert d["status"] in ("passed", "failed", "skipped")
            assert "error_summary" in d


# ---------------------------------------------------------------------------
# Journey ID extraction
# ---------------------------------------------------------------------------

class TestExtractJourneyId:
    def test_extracts_j1(self):
        assert ws._extract_journey_id("journey-j1-landing-login-dashboard.spec.ts") == "J1"

    def test_extracts_j7(self):
        assert ws._extract_journey_id("journey-j7-chat-push-notes.spec.ts") == "J7"

    def test_returns_none_for_non_journey(self):
        assert ws._extract_journey_id("chat-critical.spec.ts") is None

    def test_returns_none_for_malformed(self):
        assert ws._extract_journey_id("journey-jx-test.spec.ts") is None


# ---------------------------------------------------------------------------
# CLI --help
# ---------------------------------------------------------------------------

class TestCLI:
    def test_help_exits_zero(self, monkeypatch):
        monkeypatch.setattr("sys.argv", ["generate_walkthrough_summary.py", "--help"])
        with pytest.raises(SystemExit) as exc_info:
            ws.main()
        assert exc_info.value.code == 0
