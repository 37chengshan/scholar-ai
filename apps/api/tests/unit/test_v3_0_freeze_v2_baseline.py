from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load_module():
    current = Path(__file__).resolve()
    root = next(path for path in current.parents if (path / "scripts" / "evals").exists())
    module_path = root / "scripts" / "evals" / "v3_0_freeze_v2_baseline.py"
    spec = importlib.util.spec_from_file_location("v3_0_freeze_v2_baseline", module_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_build_baseline_payload_contains_required_metrics() -> None:
    module = _load_module()
    payload = module.build_baseline_payload()

    assert payload["status"] == "FROZEN"
    metrics = payload["metrics"]
    assert metrics["recall_at_10"] == 0.0
    assert metrics["recall_at_50"] == 0.0
    assert metrics["recall_at_100"] == 0.0
    assert metrics["same_paper_hit_rate"] == 0.2812
    assert metrics["citation_coverage"] == 0.6042
    assert metrics["unsupported_claim_rate"] == 0.4896
    assert metrics["answer_evidence_consistency"] == 0.3295


def test_expected_constraints_locked() -> None:
    module = _load_module()
    payload = module.build_baseline_payload()
    constraints = payload["constraints"]

    assert constraints["modify_step5_real_golden"] is False
    assert constraints["reparse_pdf"] is False
    assert constraints["rechunk"] is False
    assert constraints["rebuild_v2_4_collection"] is False
    assert constraints["replace_primary_embedding_model"] is False
    assert constraints["allow_official_64_80x3"] is False
