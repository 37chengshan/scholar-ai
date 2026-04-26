from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

INGEST_MODULE_PATH = ROOT / "scripts" / "evals" / "v2_4_build_api_flash_collections.py"
ingest_spec = importlib.util.spec_from_file_location("v2_4_build_api_flash_collections", INGEST_MODULE_PATH)
ingest_module = importlib.util.module_from_spec(ingest_spec)
assert ingest_spec and ingest_spec.loader
sys.modules[ingest_spec.name] = ingest_module
ingest_spec.loader.exec_module(ingest_module)

COMMON_MODULE_PATH = ROOT / "scripts" / "evals" / "v2_4_common.py"
common_spec = importlib.util.spec_from_file_location("v2_4_common", COMMON_MODULE_PATH)
common_module = importlib.util.module_from_spec(common_spec)
assert common_spec and common_spec.loader
sys.modules[common_spec.name] = common_module
common_spec.loader.exec_module(common_module)


def test_stage_mapping_all():
    assert ingest_module.stages_from_arg("all") == ["raw", "rule", "llm"]


def test_stage_collection_name_suffix():
    assert common_module.stage_collection_name("raw", "v2_4") == "paper_contents_v2_api_tongyi_flash_raw_v2_4"


def test_deprecated_collection_detection():
    assert common_module.is_deprecated_output_collection("paper_contents")
    assert common_module.is_deprecated_output_collection("paper_contents_v2_qwen_v2_raw")
    assert not common_module.is_deprecated_output_collection("paper_contents_v2_api_tongyi_flash_raw_v2_4")
