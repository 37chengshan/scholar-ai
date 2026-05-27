from __future__ import annotations

import asyncio

from app.api.chat import chat_v3_query
from app.models.chat import ChatStreamRequest


def test_chat_v3_query_forwards_knowledge_base_scope(monkeypatch) -> None:
    captured: dict[str, object] = {}

    async def _fake_build_answer_contract_payload(**kwargs):
        captured.update(kwargs)
        return {
            "answer": "ok",
            "answer_mode": "partial",
            "claims": [],
            "citations": [],
            "evidence_blocks": [],
            "quality": {},
        }

    monkeypatch.setattr("app.api.chat.build_answer_contract_payload", _fake_build_answer_contract_payload)

    result = asyncio.run(
        chat_v3_query(
            ChatStreamRequest(
                message="请基于这个知识库回答",
                mode="rag",
                scope={"type": "knowledge_base", "knowledge_base_id": "kb-1"},
            ),
            user_id="user-1",
        )
    )

    assert result["success"] is True
    assert captured["kb_id"] == "kb-1"
    assert captured["paper_scope"] is None
