from __future__ import annotations

from pathlib import Path


def test_chat_uses_v3_retriever() -> None:
    file_path = Path(__file__).resolve().parents[2] / "app" / "api" / "chat.py"
    content = file_path.read_text(encoding="utf-8")

    assert "def chat_v3_query" in content
    assert "build_answer_contract_payload(" in content
    assert "@router.post(\"\")" in content
