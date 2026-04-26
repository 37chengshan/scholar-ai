from __future__ import annotations

from pathlib import Path


def test_search_uses_v3_retriever() -> None:
    file_path = Path(__file__).resolve().parents[2] / "app" / "api" / "search" / "__init__.py"
    content = file_path.read_text(encoding="utf-8")

    assert "@router.post(\"/evidence\")" in content
    assert "def search_evidence_v3" in content
    assert "build_answer_contract_payload(" in content
    assert "paper_results" in content
    assert "section_matches" in content
    assert "evidence_matches" in content
