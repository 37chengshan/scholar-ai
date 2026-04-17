"""Unit tests for citation verifier."""

from app.core.citation_verifier import CitationVerifier


def test_citation_verifier_accepts_valid_citations():
    verifier = CitationVerifier()
    sources = [
        {
            "paper_id": "paper-1",
            "paper_title": "Paper A",
            "section": "Methods",
            "page_num": 3,
            "citation": "[Paper A, Methods]",
        }
    ]
    answer = "The method is robust [Paper A, Methods]."

    report = verifier.verify(answer, sources)

    assert report["invalid_citations"] == []
    assert report["matched_citation_count"] == 1


def test_citation_verifier_flags_invalid_citations():
    verifier = CitationVerifier()
    sources = [
        {
            "paper_id": "paper-1",
            "paper_title": "Paper A",
            "section": "Results",
            "page_num": 4,
        }
    ]
    answer = "Claim text [Unknown Paper, Intro]."

    report = verifier.verify(answer, sources)

    assert report["invalid_citations"]


def test_prune_unsupported_claims_appends_notice_when_support_low():
    verifier = CitationVerifier()
    sources = [
        {
            "paper_id": "paper-1",
            "paper_title": "Paper A",
            "section": "Results",
            "page_num": 4,
            "citation": "[Paper A, Results]",
        }
    ]
    answer = "This sentence has no citation and is long enough to count as unsupported claim in verification."

    pruned, report = verifier.prune_unsupported_claims(answer, sources)

    assert report["support_score"] < 0.45
    assert "Evidence Notice" in pruned
