"""Tests for retrieval branch registry closure to api_flash_dense."""

from __future__ import annotations

import pytest

from app.core.retrieval_branch_registry import (
    RetrievalPreflightError,
    get_qwen_collection,
    infer_stage_from_collection,
    ensure_branch_collection_allowed,
)


def test_active_collection_registry_only_api_tongyi_flash():
    raw = get_qwen_collection("raw")
    rule = get_qwen_collection("rule")
    llm = get_qwen_collection("llm")

    assert raw == "paper_contents_v2_api_tongyi_flash_raw_v2_3"
    assert rule == "paper_contents_v2_api_tongyi_flash_rule_v2_3"
    assert llm == "paper_contents_v2_api_tongyi_flash_llm_v2_3"
    assert infer_stage_from_collection(raw) == "raw"
    assert infer_stage_from_collection(rule) == "rule"
    assert infer_stage_from_collection(llm) == "llm"


@pytest.mark.parametrize("branch", ["qwen_dense", "bge_dense", "specter2", "academic_hybrid"])
def test_deprecated_branch_is_rejected(branch):
    with pytest.raises(RetrievalPreflightError, match="Deprecated retrieval branch is not allowed"):
        ensure_branch_collection_allowed(branch, "paper_contents_v2_api_tongyi_flash_llm_v2_3")
