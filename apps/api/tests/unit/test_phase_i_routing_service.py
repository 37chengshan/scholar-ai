from app.services.phase_i_routing_service import get_phase_i_routing_service


def test_phase_i_router_maps_compare_to_local_compare() -> None:
    decision = get_phase_i_routing_service().route(
        query="Compare method A and method B on CIFAR-10",
        paper_scope=["paper-a", "paper-b"],
    )

    assert decision.query_family == "compare"
    assert decision.task_family == "compare"
    assert decision.execution_mode == "local_compare"
    assert decision.kernel_scope == "dual_kernel"
    assert decision.truthfulness_required is True


def test_phase_i_router_maps_survey_to_global_review() -> None:
    decision = get_phase_i_routing_service().route(
        query="Write a literature review of retrieval augmented generation",
    )

    assert decision.query_family == "survey"
    assert decision.execution_mode == "global_review"
    assert decision.review_strategy == "storm_lite"
    assert decision.global_synthesis_required is True
    assert decision.retrieval_model_policy == "pro"


def test_phase_i_router_detects_chinese_survey_terms() -> None:
    decision = get_phase_i_routing_service().route(
        query="请基于这些论文做一个研究现状综述",
    )

    assert decision.query_family == "survey"
    assert decision.execution_mode == "global_review"


def test_phase_i_router_maps_claim_repair_to_truthfulness_repair() -> None:
    decision = get_phase_i_routing_service().route(
        query="repair this claim",
        claim_repair=True,
        paper_scope=["paper-a"],
    )

    assert decision.execution_mode == "truthfulness_repair"
    assert decision.verification_backend == "rarr_cove_scifact_lite"
    assert decision.truthfulness_required is True
    assert decision.retrieval_plane_policy["mode"] == "truthfulness_repair"
