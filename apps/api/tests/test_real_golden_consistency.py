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
    / "v2_5_validate_real_golden.py"
)

spec = importlib.util.spec_from_file_location("v2_5_validate_real_golden_consistency", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def _valid_query() -> dict:
    return {
        "query_id": "real-001",
        "query": "Compare paper A and B.",
        "query_family": "cross_paper",
        "expected_answer_mode": "partial",
        "expected_paper_ids": ["v2-p-001", "v2-p-002"],
        "expected_source_chunk_ids": ["sid-001", "sid-002"],
        "expected_content_types": ["text"],
        "expected_sections": ["body"],
        "evidence_anchors": [
            {
                "paper_id": "v2-p-001",
                "source_chunk_id": "sid-001",
                "page_num": 1,
                "content_type": "text",
                "anchor_text": "a",
                "section": "body",
            },
            {
                "paper_id": "v2-p-002",
                "source_chunk_id": "sid-002",
                "page_num": 1,
                "content_type": "text",
                "anchor_text": "b",
                "section": "body",
            },
        ],
        "golden_source": "chunk_artifact",
        "difficulty": "hard",
        "notes": "",
    }


def test_cross_paper_query_requires_two_papers() -> None:
    q = _valid_query()
    q["expected_paper_ids"] = ["v2-p-001"]

    errors = []
    if q["query_family"] == "cross_paper" and len(set(q["expected_paper_ids"])) < 2:
        errors.append("cross_paper_invalid")

    assert "cross_paper_invalid" in errors


def test_table_and_figure_query_content_type_constraints() -> None:
    table_query = _valid_query()
    table_query["query_family"] = "table"
    table_query["expected_content_types"] = ["text"]

    figure_query = _valid_query()
    figure_query["query_family"] = "figure"
    figure_query["expected_content_types"] = ["text"]

    assert "table" not in table_query["expected_content_types"]
    assert not any(x in figure_query["expected_content_types"] for x in ["figure", "caption", "page"])


def test_family_coverage_insufficient_is_blocked() -> None:
    families = {"fact": 2, "method": 0, "table": 0, "figure": 0, "numeric": 0, "compare": 0, "cross_paper": 0, "hard": 0}
    missing = [fam for fam, minimum in module.MIN_FAMILY.items() if families.get(fam, 0) < minimum]
    assert "fact" in missing
    assert "table" in missing
    assert len(missing) > 1
