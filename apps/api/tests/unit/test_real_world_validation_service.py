from __future__ import annotations

from app.services.real_world_validation_service import (
    render_markdown_report,
    summarize_real_world_validation,
    validate_real_world_payload,
)


def _sample(sample_id: str, sample_type: str, risk: str = "high") -> dict:
    return {
        "sample_id": sample_id,
        "title": f"Sample {sample_id}",
        "sample_type": sample_type,
        "source_type": "arxiv",
        "discipline": "cs.AI",
        "document_complexity": "standard",
        "language_mix": "en",
        "expected_risk": risk,
    }


def _run(run_id: str, sample_ids: list[str], bucket: str = "degrading") -> dict:
    return {
        "run_id": run_id,
        "sample_ids": sample_ids,
        "workflow_steps": [
            {"step_name": "search", "status": "passed", "consumed_by_next": True},
            {"step_name": "import", "status": "passed", "consumed_by_next": True},
            {"step_name": "read", "status": "passed", "consumed_by_next": True},
            {"step_name": "chat", "status": "passed", "consumed_by_next": True},
            {"step_name": "review", "status": "passed", "consumed_by_next": True},
        ],
        "success_state": "pass",
        "failure_points": [
            {
                "failure_id": f"F-{run_id}-01",
                "sample_id": sample_ids[0],
                "workflow_step": "review",
                "bucket": bucket,
                "description": "unsupported claim visible in review",
                "is_recoverable": True,
                "recovery_path": "repair_claim",
                "affects_honesty": bucket != "paper_cut",
            }
        ],
        "recovery_actions": [{"action": "repair_claim", "status": "available"}],
        "evidence_reviews": [
            {
                "surface": "review",
                "citation_jump_passed": True,
                "unsupported_claim_count": 1,
                "weakly_supported_claim_count": 1,
                "notes": ["one unsupported claim surfaced"],
            }
        ],
        "honesty_checks": {
            "metadata_only_honest": True,
            "fulltext_ready_honest": True,
            "unsupported_claim_visible": True,
            "citation_jump_honest": True,
        },
        "user_visible_confusions": [],
    }


def test_validate_real_world_payload_accepts_valid_payload() -> None:
    payload = {
        "sample_registry": [
            _sample("D-001", "external_import"),
            _sample("D-010", "scan_pdf"),
        ],
        "runs": [_run("RW-001", ["D-001"]), _run("RW-002", ["D-010"], bucket="blocking")],
    }

    errors = validate_real_world_payload(payload)

    assert errors == []


def test_validate_real_world_payload_rejects_unknown_sample_reference() -> None:
    payload = {
        "sample_registry": [_sample("D-001", "external_import")],
        "runs": [_run("RW-001", ["D-999"])],
    }

    errors = validate_real_world_payload(payload)

    assert any("D-999" in error for error in errors)


def test_summarize_real_world_validation_aggregates_buckets_and_honesty() -> None:
    payload = {
        "sample_registry": [
            _sample("D-001", "external_import", risk="medium"),
            _sample("D-010", "scan_pdf"),
        ],
        "runs": [
            _run("RW-001", ["D-001"], bucket="degrading"),
            {
                **_run("RW-002", ["D-010"], bucket="blocking"),
                "success_state": "blocked",
                "honesty_checks": {
                    "metadata_only_honest": False,
                    "fulltext_ready_honest": True,
                    "unsupported_claim_visible": True,
                    "citation_jump_honest": False,
                },
            },
        ],
    }

    summary = summarize_real_world_validation(payload)

    assert summary["sample_summary"]["total_samples"] == 2
    assert summary["run_summary"]["total_runs"] == 2
    assert summary["run_summary"]["success_state_counts"]["blocked"] == 1
    assert summary["failure_summary"]["bucket_counts"]["blocking"] == 1
    assert summary["failure_summary"]["bucket_counts"]["degrading"] == 1
    assert summary["honesty_summary"]["failed_checks"]["metadata_only_honest"] == 1
    assert summary["recommendation"]["beta_readiness"] == "not_ready"


def test_render_markdown_report_includes_required_sections() -> None:
    payload = {
        "sample_registry": [_sample("D-001", "external_import")],
        "runs": [_run("RW-001", ["D-001"], bucket="paper_cut")],
    }

    summary = summarize_real_world_validation(payload)
    markdown = render_markdown_report(summary)

    assert "# v3.0 Real-world Validation Report" in markdown
    assert "## 样本组成" in markdown
    assert "## Workflow 覆盖" in markdown
    assert "## 本次真实执行链路" in markdown
    assert "## 失败分桶" in markdown
    assert "## Release 建议" in markdown


def test_summarize_real_world_validation_includes_run_level_closeout_details() -> None:
    payload = {
        "sample_registry": [_sample("D-001", "external_import")],
        "runs": [
            {
                **_run("RW-001", ["D-001"], bucket="degrading"),
                "workflow_steps": [
                    {
                        "step_name": "search",
                        "status": "passed",
                        "consumed_by_next": True,
                        "notes": ["real search returned the target paper"],
                    },
                    {
                        "step_name": "review",
                        "status": "passed",
                        "consumed_by_next": False,
                        "notes": ["review run completed with draft_finalizer"],
                    },
                ],
                "user_visible_confusions": ["review surfaced partial content honestly"],
            }
        ],
    }

    summary = summarize_real_world_validation(payload)

    assert summary["run_details"][0]["run_id"] == "RW-001"
    assert summary["run_details"][0]["step_details"][0]["notes"] == ["real search returned the target paper"]
    assert summary["run_details"][0]["degraded_conditions"] == ["unsupported claim visible in review"]


def test_validate_real_world_payload_requires_minimum_run_fields() -> None:
    payload = {
        "sample_registry": [_sample("D-001", "external_import")],
        "runs": [
            {
                "run_id": "RW-001",
                "sample_ids": ["D-001"],
                "workflow_steps": [{"step_name": "search", "status": "passed", "consumed_by_next": True}],
                "success_state": "pass",
                "failure_points": [],
            }
        ],
    }

    errors = validate_real_world_payload(payload)

    assert any("recovery_actions" in error for error in errors)
    assert any("evidence_reviews" in error for error in errors)
    assert any("honesty_checks" in error for error in errors)
    assert any("user_visible_confusions" in error for error in errors)


def test_blocked_run_without_explicit_failure_is_not_ready() -> None:
    payload = {
        "sample_registry": [_sample("D-001", "external_import")],
        "runs": [
            {
                **_run("RW-001", ["D-001"], bucket="paper_cut"),
                "success_state": "blocked",
                "failure_points": [],
            }
        ],
    }

    summary = summarize_real_world_validation(payload)

    assert summary["run_summary"]["success_state_counts"]["blocked"] == 1
    assert summary["recommendation"]["beta_readiness"] == "not_ready"


def test_full_chain_runs_require_all_standard_steps_to_pass() -> None:
    payload = {
        "sample_registry": [_sample("D-001", "external_import")],
        "runs": [
            {
                **_run("RW-001", ["D-001"], bucket="blocking"),
                "workflow_steps": [
                    {"step_name": "search", "status": "passed", "consumed_by_next": True},
                    {"step_name": "import", "status": "failed", "consumed_by_next": False},
                    {"step_name": "read", "status": "skipped", "consumed_by_next": False},
                    {"step_name": "chat", "status": "skipped", "consumed_by_next": False},
                    {"step_name": "notes", "status": "skipped", "consumed_by_next": False},
                    {"step_name": "compare", "status": "skipped", "consumed_by_next": False},
                    {"step_name": "review", "status": "skipped", "consumed_by_next": False}
                ],
                "success_state": "blocked",
            }
        ],
    }

    summary = summarize_real_world_validation(payload)

    assert summary["run_summary"]["full_chain_runs"] == 0
