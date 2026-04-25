#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Set

ROOT = Path(__file__).resolve().parents[2]
API_ROOT = ROOT / "apps" / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from pymilvus import Collection, connections, utility


def load_golden(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def extract_paper_ids(golden: Dict[str, Any]) -> Set[str]:
    paper_ids: Set[str] = set()
    for paper in golden.get("papers", []):
        pid = str(paper.get("paper_id") or "")
        if pid:
            paper_ids.add(pid)
    for q in golden.get("cross_paper_queries", []):
        for pid in q.get("paper_ids") or []:
            paper_ids.add(str(pid))
    return paper_ids


def extract_query_families(golden: Dict[str, Any]) -> Set[str]:
    families: Set[str] = set()
    for paper in golden.get("papers", []):
        for q in paper.get("queries", []):
            families.add(str(q.get("query_type") or "fact"))
    for q in golden.get("cross_paper_queries", []):
        families.add(str(q.get("query_type") or "compare"))
    return families


def get_collection_paper_ids(collection: Collection) -> Set[str]:
    collection.load()
    paper_ids: Set[str] = set()
    offset = 0
    limit = 16384
    while True:
        results = collection.query(
            expr="",
            output_fields=["paper_id"],
            limit=limit,
            offset=offset,
        )
        if not results:
            break
        for r in results:
            pid = r.get("paper_id")
            if pid:
                paper_ids.add(str(pid))
        if len(results) < limit:
            break
        offset += limit
    return paper_ids


def check_golden_consistency(
    golden: Dict[str, Any],
    collection_names: Dict[str, str],
    milvus_alias: str = "v23_golden_check",
) -> Dict[str, Any]:
    golden_paper_ids = extract_paper_ids(golden)
    query_families = extract_query_families(golden)
    is_synthetic = "test-paper" in str(golden_paper_ids)
    
    required_families = {"fact", "method", "compare"}
    
    errors: List[Dict[str, Any]] = []
    warnings: List[Dict[str, Any]] = []
    checks: List[Dict[str, Any]] = []
    
    checks.append({
        "check": "golden_mode",
        "status": "PASS" if not is_synthetic else "WARN",
        "message": f"golden_mode={'synthetic' if is_synthetic else 'real'}",
    })
    
    if is_synthetic:
        warnings.append({
            "check": "synthetic_golden",
            "message": "synthetic golden detected - NOT allowed for official gate",
        })
    
    connections.connect(alias=milvus_alias, host="localhost", port=19530)
    
    for stage, col_name in collection_names.items():
        if not utility.has_collection(col_name, using=milvus_alias):
            errors.append({
                "check": f"collection_{stage}",
                "status": "FAIL",
                "message": f"collection {col_name} does not exist",
            })
            continue
        
        col = Collection(col_name, using=milvus_alias)
        collection_paper_ids = get_collection_paper_ids(col)
        
        missing_papers = golden_paper_ids - collection_paper_ids
        if missing_papers:
            errors.append({
                "check": f"paper_ids_{stage}",
                "status": "FAIL",
                "message": f"golden papers {sorted(missing_papers)} not in {col_name}",
                "details": {
                    "golden_count": len(golden_paper_ids),
                    "collection_count": len(collection_paper_ids),
                },
            })
        else:
            checks.append({
                "check": f"paper_ids_{stage}",
                "status": "PASS",
                "message": f"all {len(golden_paper_ids)} golden papers found in {col_name}",
            })
    
    missing_families = required_families - query_families
    if missing_families:
        warnings.append({
            "check": "query_family_coverage",
            "message": f"missing query families: {sorted(missing_families)}",
        })
    else:
        checks.append({
            "check": "query_family_coverage",
            "status": "PASS",
            "message": f"all required families covered: {required_families}",
        })
    
    total_queries = (
        sum(len(p.get("queries", [])) for p in golden.get("papers", []))
        + len(golden.get("cross_paper_queries", []))
    )
    if total_queries < 16:
        warnings.append({
            "check": "query_count",
            "message": f"only {total_queries} queries - recommend at least 16",
        })
    
    overall_status = "PASS" if not errors else "FAIL"
    
    return {
        "overall_status": overall_status,
        "golden_mode": "synthetic" if is_synthetic else "real",
        "is_synthetic": is_synthetic,
        "golden_paper_count": len(golden_paper_ids),
        "golden_papers": sorted(golden_paper_ids),
        "query_family_count": len(query_families),
        "query_families": sorted(query_families),
        "total_queries": total_queries,
        "errors": errors,
        "warnings": warnings,
        "checks": checks,
    }


def write_report(report: Dict[str, Any], out_dir: Path) -> None:
    json_path = out_dir / "golden_consistency_report.json"
    json_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    
    lines = [
        "# Golden Consistency Report",
        "",
        f"## Status: {report['overall_status']}",
        "",
        f"- golden_mode: {report['golden_mode']}",
        f"- golden_papers: {report['golden_paper_count']}",
        f"- query_families: {report['query_family_count']}",
        f"- total_queries: {report['total_queries']}",
        "",
        "## Golden Papers",
        "",
        ", ".join(report["golden_papers"]),
        "",
        "## Query Families",
        "",
        ", ".join(report["query_families"]),
        "",
        "## Checks",
        "",
    ]
    for check in report.get("checks", []):
        status_icon = "✅" if check["status"] == "PASS" else "❌"
        lines.append(f"- {status_icon} {check['check']}: {check['message']}")
    
    if report.get("warnings"):
        lines.append("")
        lines.append("## Warnings")
        lines.append("")
        for w in report["warnings"]:
            lines.append(f"- ⚠️ {w['check']}: {w['message']}")
    
    if report.get("errors"):
        lines.append("")
        lines.append("## Errors")
        lines.append("")
        for e in report["errors"]:
            lines.append(f"- ❌ {e['check']}: {e['message']}")
    
    md_path = out_dir / "golden_consistency_report.md"
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


FLASH_COLLECTIONS = {
    "raw": "paper_contents_v2_api_tongyi_flash_raw_v2_3",
    "rule": "paper_contents_v2_api_tongyi_flash_rule_v2_3",
    "llm": "paper_contents_v2_api_tongyi_flash_llm_v2_3",
}


def main() -> int:
    p = argparse.ArgumentParser(description="v2.3 golden consistency validator")
    p.add_argument("--golden-path", required=True)
    p.add_argument("--output-dir", default=str(ROOT / "artifacts" / "benchmarks" / "v2_3_1"))
    p.add_argument("--milvus-host", default="localhost")
    p.add_argument("--milvus-port", type=int, default=19530)
    args = p.parse_args()
    
    golden = load_golden(Path(args.golden_path))
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    
    report = check_golden_consistency(
        golden,
        FLASH_COLLECTIONS,
        milvus_alias="v23_golden_check",
    )
    
    write_report(report, out_dir)
    
    print(json.dumps({"status": report["overall_status"], "report": report}, ensure_ascii=False, indent=2))
    
    return 0 if report["overall_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())