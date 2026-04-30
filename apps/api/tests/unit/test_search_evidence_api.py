from app.api.search import V3SearchRequest, search_evidence_v3


def _boom(**_: object) -> dict:
    raise RuntimeError("artifact loader unavailable")


def test_search_evidence_v3_returns_degraded_payload_when_backend_fails(monkeypatch):
    monkeypatch.setattr("app.api.search.build_answer_contract_payload", _boom)

    payload = __import__("asyncio").run(
        search_evidence_v3(V3SearchRequest(query="test", top_k=5))
    )

    assert payload["paper_results"] == []
    assert payload["evidence_matches"] == []
    assert payload["answer_mode"] == "abstain"
    assert payload["quality"]["error"] == "search_evidence_unavailable"
