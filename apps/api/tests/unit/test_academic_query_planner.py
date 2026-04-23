from app.core.query_planner import build_academic_query_plan, classify_query_family


def test_classify_query_family_extended_types():
    assert classify_query_family("Compare method A and method B on CIFAR-10", "") == "compare"
    assert classify_query_family("Show the figure caption for ablation", "") == "figure"
    assert classify_query_family("What is the accuracy score on CIFAR-10?", "") == "numeric"
    assert classify_query_family("What limitations are reported?", "") == "limitation"


def test_build_academic_plan_compare_has_required_structure():
    plan = build_academic_query_plan(
        "How does method A compare with method B on CIFAR-10 accuracy?",
        "compare",
        paper_ids=["paper-a", "paper-b"],
    )

    assert plan["query_family"] == "compare"
    assert plan["decontextualized_query"]
    assert plan["planner_query_count"] >= 1
    assert len(plan["sub_questions"]) >= 4
    roles = {item["role"] for item in plan["sub_questions"]}
    assert {"method_a_result", "method_b_result", "metric_difference", "applicability_condition"}.issubset(roles)
    assert "table" in plan["expected_evidence_types"]
    assert plan["iterative_actions"]["enable_citation_expansion"] is True
    assert plan["evidence_plan"]["must_cover_cross_paper"] is True


def test_build_academic_plan_limitation_has_failure_mode_subquestions():
    plan = build_academic_query_plan(
        "What are the limitations and failure modes of this method?",
        "question",
        paper_ids=["paper-x"],
    )

    assert plan["query_family"] in {"limitation", "critique"}
    roles = {item["role"] for item in plan["sub_questions"]}
    assert "author_stated_limitations" in roles
    assert "failure_modes" in roles
    assert plan["fallback_rewrites"]
    assert isinstance(plan["iterative_actions"]["rewrite_queries"], list)
