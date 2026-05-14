from app.api.search import V3SearchRequest, search_evidence_v3


def _boom(**_: object) -> dict:
    raise RuntimeError("artifact loader unavailable")


def test_search_evidence_v3_returns_degraded_payload_when_backend_fails(monkeypatch):
    monkeypatch.setattr("app.api.search.build_answer_contract_payload", _boom)

    payload = __import__("asyncio").run(
        search_evidence_v3(V3SearchRequest(query="test", top_k=5), user_id="user-1")
    )

    assert payload["paper_results"] == []
    assert payload["evidence_matches"] == []
    assert payload["answer_mode"] == "abstain"
    assert payload["quality"]["error"] == "search_evidence_unavailable"


def test_search_evidence_v3_forwards_kb_id(monkeypatch):
    captured = {}

    async def _fake_build_answer_contract_payload(**kwargs):
        captured.update(kwargs)
        return {
            "citations": [],
            "evidence_blocks": [],
            "answer_mode": "partial",
            "quality": {},
            "trace_id": "trace-kb",
        }

    monkeypatch.setattr("app.api.search.build_answer_contract_payload", _fake_build_answer_contract_payload)

    __import__("asyncio").run(
        search_evidence_v3(V3SearchRequest(query="test", top_k=5, kb_id="kb-1"), user_id="user-1")
    )

    assert captured["kb_id"] == "kb-1"
    assert captured["user_id"] == "user-1"
