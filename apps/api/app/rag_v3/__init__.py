"""ScholarAI v3 retrieval package."""

from .retrieval.hierarchical_retriever import HierarchicalRetriever, retrieve_evidence
from .schemas import EvidencePack

__all__ = ["HierarchicalRetriever", "EvidencePack", "retrieve_evidence"]
