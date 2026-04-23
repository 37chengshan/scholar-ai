from __future__ import annotations

import importlib.util
from pathlib import Path

from app.core.chunk_identity import build_stable_chunk_id
from app.core.section_normalizer import canonicalize_section_name, normalize_section_path, serialize_section_path


def _load_eval_module():
    repo_root = Path(__file__).resolve().parents[4]
    module_path = repo_root / "scripts" / "eval_retrieval.py"
    spec = importlib.util.spec_from_file_location("eval_retrieval", module_path)
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_section_alias_normalize_to_canonical_taxonomy() -> None:
    assert canonicalize_section_name("background") == "introduction"
    assert canonicalize_section_name("preliminaries") == "introduction"
    assert canonicalize_section_name("methodology") == "method"
    assert canonicalize_section_name("approach") == "method"
    assert canonicalize_section_name("experimental setup") == "experiment"
    assert canonicalize_section_name("findings") == "result"
    assert canonicalize_section_name("analysis") == "discussion"
    assert canonicalize_section_name("future work") == "limitation"


def test_raw_section_path_maps_to_canonical_path() -> None:
    normalized = normalize_section_path("2. Methodology > Approach")
    assert normalized == ["method"]
    assert serialize_section_path(normalized) == "method"


def test_stable_chunk_id_is_deterministic() -> None:
    first = build_stable_chunk_id(
        paper_id="paper-1",
        page_num=2,
        normalized_section_path="method",
        char_start=120,
        char_end=240,
    )
    second = build_stable_chunk_id(
        paper_id="paper-1",
        page_num=2,
        normalized_section_path="method",
        char_start=120,
        char_end=240,
    )
    assert first == second


def test_same_chunk_repeated_generation_keeps_same_chunk_id() -> None:
    chunk_identity_args = {
        "paper_id": "paper-2",
        "page_num": 5,
        "normalized_section_path": "experiment",
        "char_start": 0,
        "char_end": 180,
    }
    ids = [build_stable_chunk_id(**chunk_identity_args) for _ in range(3)]
    assert ids[0] == ids[1] == ids[2]


def test_methodology_and_approach_hit_same_canonical_method() -> None:
    eval_module = _load_eval_module()
    results = [{"section": "Approach"}]
    hit = eval_module.calculate_section_hit_rate(results, ["Methodology"])
    assert hit == 1.0


def test_exact_overlap_anchor_chunk_hits() -> None:
    eval_module = _load_eval_module()
    exact_id = build_stable_chunk_id(
        paper_id="paper-3",
        page_num=3,
        normalized_section_path="method",
        char_start=100,
        char_end=200,
    )
    results = [
        {
            "chunk_id": exact_id,
            "paper_id": "paper-3",
            "page_num": 3,
            "normalized_section_path": "method",
            "char_start": 100,
            "char_end": 200,
            "anchor_text": "we propose a method with two stages",
        },
        {
            "chunk_id": "chunk_overlap_candidate",
            "paper_id": "paper-3",
            "page_num": 3,
            "normalized_section_path": "method",
            "char_start": 180,
            "char_end": 280,
            "anchor_text": "secondary chunk",
        },
    ]
    expected_chunks = [
        {
            "chunk_id": exact_id,
            "paper_id": "paper-3",
            "page_num": 3,
            "normalized_section_path": "method",
            "char_start": 100,
            "char_end": 200,
            "anchor_text": "we propose a method",
        },
        {
            "chunk_id": "chunk_missing_but_overlap",
            "paper_id": "paper-3",
            "page_num": 3,
            "normalized_section_path": "method",
            "char_start": 170,
            "char_end": 190,
            "anchor_text": "secondary chunk",
        },
    ]

    metrics = eval_module.calculate_chunk_match_metrics(results, expected_chunks, k=10)
    assert metrics["exact_chunk_hit"] > 0.0
    assert metrics["overlap_chunk_hit"] > 0.0
    assert metrics["anchor_hit"] > 0.0


def test_failure_bucket_classification() -> None:
    eval_module = _load_eval_module()

    retrieval_miss = eval_module.classify_failure_bucket(
        results=[],
        expected_paper_ids=["paper-1"],
        expected_sections=["method"],
        chunk_metrics={"any_chunk_hit": 0.0},
        expected_chunks=[{"chunk_id": "chunk-1"}],
    )
    assert retrieval_miss == "retrieval_miss"

    paper_hit_section_miss = eval_module.classify_failure_bucket(
        results=[{"paper_id": "paper-1", "section": "introduction"}],
        expected_paper_ids=["paper-1"],
        expected_sections=["method"],
        chunk_metrics={"any_chunk_hit": 0.0},
        expected_chunks=[{"chunk_id": "chunk-1"}],
    )
    assert paper_hit_section_miss == "paper_hit_but_section_miss"

    section_hit_chunk_miss = eval_module.classify_failure_bucket(
        results=[{"paper_id": "paper-1", "section": "method"}],
        expected_paper_ids=["paper-1"],
        expected_sections=["method"],
        chunk_metrics={"any_chunk_hit": 0.0},
        expected_chunks=[{"chunk_id": "chunk-1"}],
    )
    assert section_hit_chunk_miss == "section_hit_but_chunk_miss"

    mapping_error = eval_module.classify_failure_bucket(
        results=[{"paper_id": "paper-1", "section": "method"}],
        expected_paper_ids=[],
        expected_sections=[],
        chunk_metrics={"any_chunk_hit": 0.0},
        expected_chunks=[],
    )
    assert mapping_error == "evaluation_mapping_error"
