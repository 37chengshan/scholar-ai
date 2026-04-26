from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
COMMON_MODULE_PATH = ROOT / "scripts" / "evals" / "v2_4_common.py"

spec = importlib.util.spec_from_file_location("v2_4_common", COMMON_MODULE_PATH)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def test_official_output_fields_no_raw_data_dependency():
    assert "raw_data" not in module.OFFICIAL_OUTPUT_FIELDS
    for must in ["source_chunk_id", "paper_id", "content_data"]:
        assert must in module.OFFICIAL_OUTPUT_FIELDS
