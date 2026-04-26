from __future__ import annotations

from pathlib import Path
import importlib.util
import sys

MODULE_PATH = (
    Path(__file__).resolve().parents[3]
    / "scripts"
    / "evals"
    / "v2_5_validate_real_golden.py"
)

spec = importlib.util.spec_from_file_location("v2_5_validate_real_golden_schema", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def test_real_golden_schema_valid() -> None:
    query = {
        "query_id": "real-001",
        "query": "What method is used in v2-p-001?",
        "query_family": "method",
        "expected_answer_mode": "full",
        "expected_paper_ids": ["v2-p-001"],
        "expected_source_chunk_ids": ["sid-001"],
        "expected_content_types": ["text"],
        "expected_sections": ["Methods"],
        "evidence_anchors": [
            {
                "paper_id": "v2-p-001",
                "source_chunk_id": "sid-001",
                "page_num": 1,
                "content_type": "text",
                "anchor_text": "method details",
                "section": "Methods",
            }
        ],
        "golden_source": "chunk_artifact",
        "difficulty": "easy",
        "notes": "",
    }
    assert module.validate_query_schema(query) is True


def test_real_golden_schema_invalid() -> None:
    query = {
        "query_id": "",
        "query": "",
        "query_family": "fact",
    }
    assert module.validate_query_schema(query) is False
