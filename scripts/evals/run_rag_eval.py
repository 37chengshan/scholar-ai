#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
from statistics import mean


def load_answers(path: Path):
    payload = json.loads(path.read_text(encoding="utf-8"))
    items = payload.get("results", payload)
    return {item["case_id"]: item for item in items}


def mock_answer(case):
    must_cite = case.get("must_have_citation", False)
    allow_low = case.get("allow_low_confidence", False)
    case_id = case.get("case_id", "")

    low_flag = allow_low and case_id.startswith(("E-", "F-", "D-"))
    consistency = 0.42 if low_flag else 0.84
    citations = [
        {
            "paper_id": case.get("paper_ids", ["unknown"])[0] if case.get("paper_ids") else "unknown",
            "source_id": f"src-{case_id.lower()}",
            "page_num": 1,
            "section_path": "method",
            "anchor_text": "mock anchor",
            "text_preview": "mock evidence"
        }
    ] if must_cite else []

    return {
        "case_id": case_id,
        "answer": "mock answer",
        "citations": citations,
        "low_confidence_flag": low_flag,
        "answer_evidence_consistency": consistency,
    }


def evaluate_case(case, result):
    must_cite = case.get("must_have_citation", False)
    allow_low = case.get("allow_low_confidence", False)

    citations = result.get("citations", [])
    low_flag = bool(result.get("low_confidence_flag", False))
    consistency = float(result.get("answer_evidence_consistency", 0.0))

    reasons = []
    if must_cite and not citations:
        reasons.append("missing_citation")

    if (not allow_low) and low_flag:
        reasons.append("unexpected_low_confidence")

    if (not allow_low) and consistency < 0.5:
        reasons.append("consistency_too_low")

    return {
        "case_id": case.get("case_id"),
        "pass": len(reasons) == 0,
        "citation_present": bool(citations),
        "low_confidence_flag": low_flag,
        "answer_evidence_consistency": consistency,
        "reasons": reasons,
    }


def summarize(evals):
    total = len(evals)
    passed = sum(1 for e in evals if e["pass"])
    citation_present = sum(1 for e in evals if e["citation_present"])
    low_conf = sum(1 for e in evals if e["low_confidence_flag"])
    consistency_values = [e["answer_evidence_consistency"] for e in evals]
    failed_case_ids = [e["case_id"] for e in evals if not e["pass"]]

    return {
        "total_cases": total,
        "passed_cases": passed,
        "citation_present_rate": round(citation_present / total, 4) if total else 0.0,
        "low_confidence_rate": round(low_conf / total, 4) if total else 0.0,
        "average_consistency": round(mean(consistency_values), 4) if consistency_values else 0.0,
        "failed_case_ids": failed_case_ids,
        "case_results": evals,
    }


def main():
    parser = argparse.ArgumentParser(description="Run vNext+1 rag eval baseline")
    parser.add_argument("--dataset", required=True, help="Path to rag_eval_dataset.json")
    parser.add_argument("--answers-file", help="Optional path to real answers JSON")
    parser.add_argument("--output", required=True, help="Output summary JSON path")
    args = parser.parse_args()

    dataset_path = Path(args.dataset)
    output_path = Path(args.output)

    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    cases = dataset.get("cases", [])

    answers = None
    if args.answers_file:
        answers = load_answers(Path(args.answers_file))

    missing_answer_case_ids = []
    if answers is not None:
        for case in cases:
            case_id = case.get("case_id")
            if case_id not in answers:
                missing_answer_case_ids.append(case_id)
        if missing_answer_case_ids:
            raise ValueError(
                "answers-file is missing case_id entries: "
                + ", ".join(missing_answer_case_ids)
            )

    evals = []
    for case in cases:
        if answers is not None:
            result = answers[case["case_id"]]
        else:
            result = mock_answer(case)
        evals.append(evaluate_case(case, result))

    summary = summarize(evals)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
