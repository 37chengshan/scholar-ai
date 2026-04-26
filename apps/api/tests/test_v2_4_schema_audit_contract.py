from __future__ import annotations

import importlib.util
from pathlib import Path
import pytest
import sys

ROOT = Path(__file__).resolve().parents[3]
COMMON_MODULE_PATH = ROOT / "scripts" / "evals" / "v2_4_common.py"

spec = importlib.util.spec_from_file_location("v2_4_common", COMMON_MODULE_PATH)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def test_query_dim_matches_collection_dim_pass():
    module.ensure_query_dim_matches_collection_dim(1024, 1024)


def test_query_dim_matches_collection_dim_fail():
    with pytest.raises(RuntimeError):
        module.ensure_query_dim_matches_collection_dim(1024, 768)
