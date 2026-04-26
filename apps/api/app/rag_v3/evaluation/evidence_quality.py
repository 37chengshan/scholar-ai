from __future__ import annotations

from app.rag_v3.evaluation.retrieval_evaluator import evaluate_evidence_pack
from app.rag_v3.schemas import EvidencePack, EvidenceQualityScore


def score_evidence(pack: EvidencePack) -> EvidenceQualityScore:
    return evaluate_evidence_pack(pack)
