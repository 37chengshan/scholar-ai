from __future__ import annotations

from typing import Dict


class GraphQueryCompiler:
    """Compile query family and question text into graph retrieval hints."""

    def compile(self, query: str, query_family: str) -> Dict:
        family = (query_family or "fact").lower()
        requires_graph = family in {"compare", "evolution", "numeric"}
        return {
            "query_family": family,
            "requires_graph": requires_graph,
            "intent": "graph_compare" if family in {"compare", "evolution"} else "graph_metric" if family == "numeric" else "graph_none",
            "expected_relations": self._expected_relations(family),
            "query": query,
        }

    @staticmethod
    def _expected_relations(family: str) -> list[str]:
        if family == "compare":
            return ["compares_against_baseline", "improves_metric_on_dataset"]
        if family == "evolution":
            return ["improves_metric_on_dataset", "evaluated_on_dataset"]
        if family == "numeric":
            return ["improves_metric_on_dataset"]
        return []


_graph_query_compiler: GraphQueryCompiler | None = None


def get_graph_query_compiler() -> GraphQueryCompiler:
    global _graph_query_compiler
    if _graph_query_compiler is None:
        _graph_query_compiler = GraphQueryCompiler()
    return _graph_query_compiler
