from __future__ import annotations

from typing import Any

from app.core.claim_extractor import get_claim_extractor
from app.core.claim_schema import AnswerClaim, ClaimSupportLevel
from app.core.claim_verifier import get_claim_verifier
from app.rag_v3.schemas import EvidenceBlock


class TruthfulnessService:
    def evaluate_text(
        self,
        *,
        text: str,
        evidence_blocks: list[EvidenceBlock] | None = None,
    ) -> dict[str, Any]:
        claims = get_claim_extractor().extract(text)
        return self.evaluate_claims(claims=claims, evidence_blocks=evidence_blocks or [])

    def evaluate_claims(
        self,
        *,
        claims: list[AnswerClaim],
        evidence_blocks: list[EvidenceBlock] | None = None,
    ) -> dict[str, Any]:
        sources = [self._block_to_source(block) for block in (evidence_blocks or [])]
        results = get_claim_verifier().verify(claims, sources)
        report = get_claim_verifier().build_report(results)
        report["answerMode"] = self._answer_mode_from_report(report)
        report["summary"] = {
            "total_claims": report["totalClaims"],
            "supported_claims": report["supportedClaimCount"],
            "weakly_supported_claims": report["weaklySupportedClaimCount"],
            "partially_supported_claims": report["partiallySupportedClaimCount"],
            "unsupported_claims": report["unsupportedClaimCount"],
            "unsupported_claim_rate": report["unsupportedClaimRate"],
            "answer_mode": report["answerMode"],
            "verifier_backend": report.get("verifierBackend", "lexical_overlap"),
        }
        return report

    def repair_claim(
        self,
        *,
        claim_text: str,
        claim_id: str,
        claim_type: str,
        evidence_blocks: list[EvidenceBlock] | None = None,
    ) -> dict[str, Any]:
        claim = AnswerClaim(
            claim_id=claim_id,
            text=claim_text,
            claim_type=claim_type,
            citations=[],
        )
        report = self.evaluate_claims(claims=[claim], evidence_blocks=evidence_blocks or [])
        result = report["results"][0] if report["results"] else {
            "claim_id": claim_id,
            "text": claim_text,
            "claim_type": claim_type,
            "support_level": ClaimSupportLevel.unsupported.value,
            "support_score": 0.0,
            "evidence_ids": [],
            "reason": "no evidence available for repair",
        }
        result["repairable"] = result["support_level"] != ClaimSupportLevel.supported.value
        result["repair_hint"] = (
            result.get("reason")
            if not result["repairable"]
            else self._build_repair_hint(result)
        )
        return result

    @staticmethod
    def report_to_answer_claims(report: dict[str, Any]) -> list[dict[str, Any]]:
        claims: list[dict[str, Any]] = []
        for item in report.get("results", []):
            claims.append(
                {
                    "claim": item.get("text") or "",
                    "claim_id": item.get("claim_id") or "",
                    "claim_type": item.get("claim_type") or "factual",
                    "support_status": item.get("support_level") or ClaimSupportLevel.unsupported.value,
                    "support_score": item.get("support_score") or 0.0,
                    "repairable": item.get("support_level") != ClaimSupportLevel.supported.value,
                    "repair_hint": item.get("reason"),
                    "supporting_source_chunk_ids": item.get("evidence_ids", []),
                    "citation_ids": item.get("evidence_ids", []),
                }
            )
        return claims

    @staticmethod
    def _build_repair_hint(result: dict[str, Any]) -> str:
        evidence_ids = result.get("evidence_ids") or []
        support_level = str(result.get("support_level") or ClaimSupportLevel.unsupported.value)
        if evidence_ids:
            return f"Relink claim to stronger evidence {', '.join(evidence_ids[:2])} and rewrite for {support_level} support."
        return "Retrieve stronger evidence or narrow the claim before rewriting."

    @staticmethod
    def _block_to_source(block: EvidenceBlock) -> dict[str, Any]:
        return {
            "source_id": block.source_chunk_id or block.evidence_id,
            "text": block.text or block.quote_text or "",
            "anchor_text": block.quote_text or block.text or "",
            "text_preview": block.text or "",
        }

    @staticmethod
    def _answer_mode_from_report(report: dict[str, Any]) -> str:
        total = int(report.get("totalClaims") or 0)
        unsupported = int(report.get("unsupportedClaimCount") or 0)
        supported = int(report.get("supportedClaimCount") or 0)
        if total == 0:
            return "abstain"
        if unsupported > 0 or supported == 0:
            return "abstain"
        if supported == total:
            return "full"
        return "partial"


_truthfulness_service: TruthfulnessService | None = None


def get_truthfulness_service() -> TruthfulnessService:
    global _truthfulness_service
    if _truthfulness_service is None:
        _truthfulness_service = TruthfulnessService()
    return _truthfulness_service
