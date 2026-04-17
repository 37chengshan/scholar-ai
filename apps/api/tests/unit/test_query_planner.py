"""Unit tests for PR8 query planner."""

from app.core.query_planner import plan_queries


def test_plan_queries_includes_raw_query_first():
    query = "Compare YOLOv3 and YOLOv4 performance"
    planned = plan_queries(query, "compare")

    assert planned
    assert planned[0] == query


def test_plan_queries_adds_intent_variant_for_compare():
    planned = plan_queries("比较模型A和模型B", "compare")

    assert any("对比" in item or "差异" in item for item in planned)


def test_plan_queries_deduplicates_and_limits():
    planned = plan_queries("table figure table figure", "summary")

    assert len(planned) <= 4
    assert len(planned) == len(set(planned))
