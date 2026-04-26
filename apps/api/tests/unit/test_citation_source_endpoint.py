from __future__ import annotations

from pathlib import Path


def test_citation_source_endpoint() -> None:
    file_path = Path(__file__).resolve().parents[2] / "app" / "api" / "evidence.py"
    content = file_path.read_text(encoding="utf-8")

    assert "@router.get(\"/source/{source_chunk_id}\")" in content
    assert "def get_evidence_source" in content
    assert "read_url" in content
    assert "source_chunk_id" in content
