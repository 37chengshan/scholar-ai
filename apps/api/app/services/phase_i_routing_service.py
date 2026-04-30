from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from app.rag_v3.planner.query_family_router import infer_query_family, normalize_query_family


@dataclass(frozen=True)
class PhaseIRoutingDecision:
    query_family: str
    task_family: str
    execution_mode: str
    kernel_scope: str
    retrieval_depth: str
    retrieval_model_policy: str
    truthfulness_required: bool
    global_synthesis_required: bool
    review_strategy: str
    verification_backend: str
    retrieval_plane_policy: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


_TASK_FAMILY_MAP: dict[str, str] = {
    "fact": "single_paper_fact",
    "numeric": "single_paper_fact",
    "method": "single_paper_method",
    "table": "single_paper_table_figure",
    "figure": "single_paper_table_figure",
    "compare": "compare",
    "cross_paper": "cross_paper",
    "survey": "survey",
    "related_work": "related_work",
    "method_evolution": "cross_paper",
    "conflicting_evidence": "conflicting_evidence",
    "hard": "hard",
}

_EXECUTION_MODE_MAP: dict[str, str] = {
    "fact": "local_evidence",
    "numeric": "local_evidence",
    "method": "local_evidence",
    "table": "local_evidence",
    "figure": "local_evidence",
    "compare": "local_compare",
    "cross_paper": "global_review",
    "survey": "global_review",
    "related_work": "global_review",
    "method_evolution": "global_review",
    "conflicting_evidence": "global_review",
    "hard": "global_review",
}

_DEPTH_MAP: dict[str, str] = {
    "fact": "shallow",
    "numeric": "shallow",
    "method": "medium",
    "table": "medium",
    "figure": "medium",
    "compare": "medium",
    "cross_paper": "deep",
    "survey": "deep",
    "related_work": "deep",
    "method_evolution": "deep",
    "conflicting_evidence": "deep",
    "hard": "deep",
}

_MODEL_POLICY_MAP: dict[str, str] = {
    "fact": "flash",
    "numeric": "flash",
    "method": "flash",
    "table": "flash",
    "figure": "flash",
    "compare": "pro",
    "cross_paper": "pro",
    "survey": "pro",
    "related_work": "pro",
    "method_evolution": "pro",
    "conflicting_evidence": "pro",
    "hard": "pro",
}

_KERNEL_SCOPE_MAP: dict[str, str] = {
    "fact": "local_kernel",
    "numeric": "local_kernel",
    "method": "local_kernel",
    "table": "local_kernel",
    "figure": "local_kernel",
    "compare": "dual_kernel",
    "cross_paper": "global_kernel",
    "survey": "global_kernel",
    "related_work": "global_kernel",
    "method_evolution": "global_kernel",
    "conflicting_evidence": "global_kernel",
    "hard": "global_kernel",
}

_REVIEW_STRATEGY_MAP: dict[str, str] = {
    "fact": "citation_first",
    "numeric": "citation_first",
    "method": "citation_first",
    "table": "citation_first",
    "figure": "citation_first",
    "compare": "matrix_first",
    "cross_paper": "storm_lite",
    "survey": "storm_lite",
    "related_work": "storm_lite",
    "method_evolution": "storm_lite",
    "conflicting_evidence": "storm_lite",
    "hard": "storm_lite",
}

_VERIFICATION_BACKEND_MAP: dict[str, str] = {
    "fact": "rarr_cove_scifact_lite",
    "numeric": "rarr_cove_scifact_lite",
    "method": "rarr_cove_scifact_lite",
    "table": "rarr_cove_scifact_lite",
    "figure": "rarr_cove_scifact_lite",
    "compare": "rarr_cove_scifact_lite",
    "cross_paper": "rarr_cove_scifact_lite",
    "survey": "rarr_cove_scifact_lite",
    "related_work": "rarr_cove_scifact_lite",
    "method_evolution": "rarr_cove_scifact_lite",
    "conflicting_evidence": "rarr_cove_scifact_lite",
    "hard": "rarr_cove_scifact_lite",
}


class PhaseIRoutingService:
    def route(
        self,
        *,
        query: str,
        query_family: str | None = None,
        paper_scope: list[str] | None = None,
        claim_repair: bool = False,
    ) -> PhaseIRoutingDecision:
        family = normalize_query_family(query_family) if query_family else infer_query_family(query)
        if claim_repair:
            return PhaseIRoutingDecision(
                query_family=family,
                task_family=_TASK_FAMILY_MAP.get(family, "single_paper_fact"),
                execution_mode="truthfulness_repair",
                kernel_scope="truthfulness_kernel",
                retrieval_depth="focused",
                retrieval_model_policy="flash",
                truthfulness_required=True,
                global_synthesis_required=False,
                review_strategy="repair_loop",
                verification_backend="rarr_cove_scifact_lite",
                retrieval_plane_policy={
                    "mode": "truthfulness_repair",
                    "kernel_scope": "truthfulness_kernel",
                    "embedding_tier": "flash",
                    "paper_scope_count": len(paper_scope or []),
                    "routing_policy": "focused_claim_repair",
                    "review_strategy": "repair_loop",
                    "verification_backend": "rarr_cove_scifact_lite",
                    "benchmark_profile": "phase_j_truthfulness_gate",
                },
            )

        execution_mode = _EXECUTION_MODE_MAP.get(family, "local_evidence")
        kernel_scope = _KERNEL_SCOPE_MAP.get(family, "local_kernel")
        truthfulness_required = execution_mode in {"local_compare", "global_review"} or family in {
            "fact",
            "method",
            "numeric",
            "conflicting_evidence",
            "hard",
        }
        retrieval_depth = _DEPTH_MAP.get(family, "shallow")
        retrieval_model_policy = _MODEL_POLICY_MAP.get(family, "flash")
        global_synthesis_required = execution_mode == "global_review"
        review_strategy = _REVIEW_STRATEGY_MAP.get(family, "citation_first")
        verification_backend = _VERIFICATION_BACKEND_MAP.get(family, "rarr_cove_scifact_lite")

        return PhaseIRoutingDecision(
            query_family=family,
            task_family=_TASK_FAMILY_MAP.get(family, "single_paper_fact"),
            execution_mode=execution_mode,
            kernel_scope=kernel_scope,
            retrieval_depth=retrieval_depth,
            retrieval_model_policy=retrieval_model_policy,
            truthfulness_required=truthfulness_required,
            global_synthesis_required=global_synthesis_required,
            review_strategy=review_strategy,
            verification_backend=verification_backend,
            retrieval_plane_policy={
                "mode": execution_mode,
                "kernel_scope": kernel_scope,
                "embedding_tier": retrieval_model_policy,
                "paper_scope_count": len(paper_scope or []),
                "retrieval_depth": retrieval_depth,
                "routing_policy": "adaptive_depth" if retrieval_depth in {"medium", "deep"} else "fixed_depth",
                "review_strategy": review_strategy,
                "verification_backend": verification_backend,
                "benchmark_profile": (
                    "phase_j_global_review_gate"
                    if execution_mode == "global_review"
                    else "phase_j_local_kernel_gate"
                ),
                "hierarchical_retrieval": execution_mode == "global_review",
            },
        )


_phase_i_routing_service: PhaseIRoutingService | None = None


def get_phase_i_routing_service() -> PhaseIRoutingService:
    global _phase_i_routing_service
    if _phase_i_routing_service is None:
        _phase_i_routing_service = PhaseIRoutingService()
    return _phase_i_routing_service
