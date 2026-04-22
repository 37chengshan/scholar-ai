from __future__ import annotations

import importlib.util
import json
import sys
from types import ModuleType
from pathlib import Path

import pytest


def _load_eval_module():
    repo_root = Path(__file__).resolve().parents[4]
    module_path = repo_root / "scripts" / "eval_retrieval.py"
    spec = importlib.util.spec_from_file_location("eval_retrieval", module_path)
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.asyncio
async def test_mock_eval_uses_paper_ids_for_single_paper_queries(tmp_path: Path):
    eval_module = _load_eval_module()
    golden_path = tmp_path / "golden_single.json"
    golden_path.write_text(
        json.dumps(
            {
                "papers": [
                    {
                        "paper_id": "dataset-s-001",
                        "queries": [
                            {
                                "id": "single-paper-q1",
                                "query": "What does the paper say about multimodal capability?",
                                "expected_paper_ids": ["dataset-s-001"],
                                "expected_sections": ["Abstract"],
                                "query_type": "single",
                            }
                        ],
                    }
                ]
            }
        )
    )

    report = await eval_module.evaluate_retrieval(
        str(golden_path),
        mock_mode=True,
    )

    assert report["total_queries"] == 1
    assert report["paper_hit_rate_avg"] == pytest.approx(1.0)
    assert report["recall_at_5_avg"] == pytest.approx(1.0)
    assert report["mrr_avg"] == pytest.approx(1.0)


@pytest.mark.asyncio
async def test_mock_eval_uses_paper_ids_for_cross_paper_queries(tmp_path: Path):
    eval_module = _load_eval_module()
    golden_path = tmp_path / "golden_cross.json"
    golden_path.write_text(
        json.dumps(
            {
                "cross_paper_queries": [
                    {
                        "id": "cross-paper-q1",
                        "query": "Which paper is about instruction following or model alignment?",
                        "paper_ids": ["dataset-s-002", "dataset-s-003"],
                        "expected_paper_ids": ["dataset-s-002", "dataset-s-003"],
                        "expected_sections": ["Introduction", "Conclusion"],
                    }
                ]
            }
        )
    )

    report = await eval_module.evaluate_retrieval(
        str(golden_path),
        mock_mode=True,
    )

    assert report["total_queries"] == 1
    assert report["paper_hit_rate_avg"] == pytest.approx(0.5)
    assert report["recall_at_5_avg"] == pytest.approx(0.5)
    assert report["mrr_avg"] == pytest.approx(1.0)


@pytest.mark.asyncio
async def test_real_eval_forwards_use_reranker_flag(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    eval_module = _load_eval_module()
    golden_path = tmp_path / "golden_real.json"
    golden_path.write_text(
        json.dumps(
            {
                "papers": [
                    {
                        "paper_id": "dataset-s-001",
                        "queries": [
                            {
                                "id": "real-paper-q1",
                                "query": "What does the paper say about multimodal capability?",
                                "expected_paper_ids": ["dataset-s-001"],
                                "expected_sections": ["Abstract"],
                            }
                        ],
                    }
                ]
            }
        )
    )

    calls: list[dict[str, object]] = []

    class FakeService:
        async def search(self, **kwargs):
            calls.append(kwargs)
            return {
                "results": [
                    {
                        "id": "dataset-s-001",
                        "paper_id": "dataset-s-001",
                        "section": "Abstract",
                    }
                ]
            }

    fake_module = ModuleType("app.core.multimodal_search_service")
    fake_module.get_multimodal_search_service = lambda: FakeService()
    monkeypatch.setitem(sys.modules, "app.core.multimodal_search_service", fake_module)

    report = await eval_module.evaluate_retrieval(
        str(golden_path),
        mock_mode=False,
        use_reranker=True,
    )

    assert report["total_queries"] == 1
    assert report["use_reranker"] is True
    assert calls
    assert calls[0]["use_reranker"] is True