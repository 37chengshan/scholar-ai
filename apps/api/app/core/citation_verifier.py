"""Citation verifier for claim-level synthesis outputs."""

import re
from typing import Dict, List, Set, Tuple


class CitationVerifier:
    """Verify citation validity and surface citation coverage."""

    CITATION_PATTERN = re.compile(r"\[[^\[\],]+,\s*[^\[\]]+\]")
    SENTENCE_SPLIT_PATTERN = re.compile(r"(?<=[。！？.!?])\s+")

    @staticmethod
    def _format_source_citation(source: Dict) -> str:
        paper_title = source.get("paper_title") or source.get("paper_id") or "Unknown"
        section = source.get("section")
        page_num = source.get("page_num", source.get("page"))
        location = section or (f"Page {page_num}" if page_num is not None else "N/A")
        return f"[{paper_title}, {location}]"

    def _valid_citation_set(self, sources: List[Dict]) -> Set[str]:
        citations: Set[str] = set()
        for source in sources:
            explicit = source.get("citation")
            if explicit:
                citations.add(explicit)
            citations.add(self._format_source_citation(source))
        return citations

    def verify(self, answer: str, sources: List[Dict]) -> Dict:
        """Verify citation validity and sentence-level citation surface coverage."""
        text = answer or ""
        citations_in_answer = set(self.CITATION_PATTERN.findall(text))
        valid_citations = self._valid_citation_set(sources)

        invalid_citations = sorted(citations_in_answer - valid_citations)
        matched_citations = citations_in_answer & valid_citations

        raw_sentences = self.SENTENCE_SPLIT_PATTERN.split(text)
        sentences = [s.strip() for s in raw_sentences if s and s.strip()]

        unsupported_sentences = []
        for sentence in sentences:
            # Ignore very short sentences and list-only markers.
            if len(sentence) < 20:
                continue
            if not self.CITATION_PATTERN.search(sentence):
                unsupported_sentences.append(sentence)

        total_claim_sentences = max(len([s for s in sentences if len(s) >= 20]), 1)
        sentence_coverage = 1.0 - (len(unsupported_sentences) / total_claim_sentences)
        sentence_coverage = max(0.0, min(sentence_coverage, 1.0))

        citation_coverage = 0.0
        if citations_in_answer:
            citation_coverage = len(matched_citations) / len(citations_in_answer)

        return {
            "citation_count": len(citations_in_answer),
            "matched_citation_count": len(matched_citations),
            "invalid_citations": invalid_citations,
            "unsupported_sentence_count": len(unsupported_sentences),
            "citation_coverage": round(citation_coverage, 4),
            "surface_sentence_coverage": round(sentence_coverage, 4),
        }

    def prune_unsupported_claims(
        self,
        answer: str,
        sources: List[Dict],
        min_surface_sentence_coverage: float = 0.45,
    ) -> Tuple[str, Dict]:
        """Backward-compatible wrapper to append warning for low citation surface coverage."""
        report = self.verify(answer, sources)
        if (
            report["surface_sentence_coverage"] >= min_surface_sentence_coverage
            and not report["invalid_citations"]
        ):
            return answer, report

        warning = (
            "\n\n[Evidence Notice, Verification] "
            "Evidence coverage is limited for parts of this answer. "
            "Treat unsupported claims as tentative."
        )
        return f"{answer}{warning}", report


_citation_verifier: CitationVerifier | None = None


def get_citation_verifier() -> CitationVerifier:
    """Get or create citation verifier singleton."""
    global _citation_verifier
    if _citation_verifier is None:
        _citation_verifier = CitationVerifier()
    return _citation_verifier
