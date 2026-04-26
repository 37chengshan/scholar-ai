from __future__ import annotations

import json
import importlib.util
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
MODULE_PATH = ROOT / "scripts" / "evals" / "v2_4_validate_artifacts.py"

spec = importlib.util.spec_from_file_location("v2_4_validate_artifacts", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def _write(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_artifact_consistency_blocked_when_root_missing(tmp_path):
    out = tmp_path / "out"
    # direct CLI-style run
    import sys

    argv = sys.argv
    try:
        sys.argv = [
            "v2_4_validate_artifacts.py",
            "--artifact-root",
            str(tmp_path / "missing"),
            "--output-dir",
            str(out),
        ]
        rc = module.main()
    finally:
        sys.argv = argv

    assert rc == 1
    report = json.loads((out / "artifact_consistency_report.json").read_text(encoding="utf-8"))
    assert report["status"] == "BLOCKED"
    assert any("artifact_root_missing_or_empty" in e for e in report["errors"])


def test_artifact_consistency_pass_minimal_valid(tmp_path):
    artifact_root = tmp_path / "papers"
    paper = artifact_root / "paper-a"

    parse = {
        "parse_mode": "native",
        "quality_level": "high",
    }
    chunk_base = {
        "source_chunk_id": "paper-a::p1::sec-a",
        "chunk_id": "paper-a::chunk::raw::0",
        "paper_id": "paper-a",
        "parse_id": "parse-a",
        "page_num": 1,
        "section_path": "Intro",
        "normalized_section_path": "intro",
        "content_type": "text",
        "content_data": "hello",
        "anchor_text": "hello",
        "char_start": 0,
        "char_end": 5,
        "stage": "raw",
        "indexable": True,
    }
    raw = [dict(chunk_base)]
    rule = [dict(chunk_base, stage="rule", chunk_id="paper-a::chunk::rule::0")]
    llm = [dict(chunk_base, stage="llm", chunk_id="paper-a::chunk::llm::0")]

    _write(paper / "parse_artifact.json", parse)
    _write(paper / "chunks_raw.json", raw)
    _write(paper / "chunks_rule.json", rule)
    _write(paper / "chunks_llm.json", llm)

    out = tmp_path / "out"
    import sys

    argv = sys.argv
    try:
        sys.argv = [
            "v2_4_validate_artifacts.py",
            "--artifact-root",
            str(artifact_root),
            "--output-dir",
            str(out),
        ]
        rc = module.main()
    finally:
        sys.argv = argv

    assert rc == 0
    report = json.loads((out / "artifact_consistency_report.json").read_text(encoding="utf-8"))
    assert report["status"] == "PASS"
    assert report["papers_scanned"] == 1
