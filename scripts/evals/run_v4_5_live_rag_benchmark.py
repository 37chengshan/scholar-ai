#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
import os
import signal
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import error as urllib_error
from urllib import request as urllib_request


REPO_ROOT = Path(__file__).resolve().parents[2]
API_ROOT = REPO_ROOT / "apps" / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from sqlalchemy import func, select  # noqa: E402

from app.database import AsyncSessionLocal  # noqa: E402
from app.models.knowledge_base import KnowledgeBase  # noqa: E402
from app.models.knowledge_base_paper import KnowledgeBasePaper  # noqa: E402
from app.models.paper import Paper, PaperChunk  # noqa: E402
from app.models.user import User as UserModel  # noqa: E402
from app.services.auth_service import get_user_roles  # noqa: E402
from app.utils.security import create_access_token  # noqa: E402


@dataclass
class PaperSample:
    id: str
    title: str
    status: str | None
    is_search_ready: bool | None
    is_multimodal_ready: bool | None
    chunk_count: int


@dataclass
class BenchmarkUser:
    id: str
    email: str
    name: str
    paper_count: int
    papers: list[PaperSample]


@dataclass
class KnowledgeBaseSample:
    id: str
    name: str
    paper_count: int
    paper_ids: list[str]
    chunk_count: int


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the v4.5 live backend RAG benchmark against local ScholarAI routes."
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8010)
    parser.add_argument("--base-url", default=None, help="Override base URL. Defaults to host+port.")
    parser.add_argument("--launch-backend", action="store_true", help="Launch backend locally before probing.")
    parser.add_argument("--user-email", default=None, help="Optional benchmark user email override.")
    parser.add_argument("--timeout-sec", type=float, default=60.0)
    parser.add_argument("--health-timeout-sec", type=float, default=45.0)
    parser.add_argument("--output-dir", default=None)
    return parser.parse_args()


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def benchmark_output_dir(custom: str | None) -> Path:
    if custom:
        return Path(custom).resolve()
    stamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%SZ")
    return REPO_ROOT / "artifacts" / "validation-results" / "v4_5" / "live_rag_benchmark" / stamp


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_markdown(path: Path, report: dict[str, Any]) -> None:
    summary = report["summary"]
    lines = [
        "# v4.5 Live RAG Benchmark",
        "",
        f"Generated at: {report['generated_at']}",
        f"Base URL: {report['base_url']}",
        f"Backend launched by script: {report['backend_launch']['launched']}",
        "",
        "## Dataset Truth",
        f"- Benchmark user: `{report['benchmark_user']['email']}` ({report['benchmark_user']['paper_count']} papers)",
        f"- Papers total: {report['dataset_truth']['papers_total']}",
        f"- Knowledge bases total: {report['dataset_truth']['knowledge_bases_total']}",
        f"- Knowledge base papers total: {report['dataset_truth']['knowledge_base_papers_total']}",
        f"- Papers with primary KB membership: {report['dataset_truth']['papers_with_knowledge_base_id_total']}",
        "",
        "## Summary",
        f"- Passed: {summary['passed']}",
        f"- Failed: {summary['failed']}",
        f"- Blocked: {summary['blocked']}",
        f"- Success rate: {summary['success_rate']:.2%}",
        f"- P95 latency: {summary['p95_latency_ms']:.2f} ms",
        "",
        "## Cases",
    ]
    for case in report["cases"]:
        lines.append(
            f"- `{case['case_id']}`: {case['status']} ({case['latency_ms']:.2f} ms) - {case['summary']}"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return float(ordered[0])
    rank = (len(ordered) - 1) * p
    low = int(rank)
    high = min(low + 1, len(ordered) - 1)
    weight = rank - low
    return ordered[low] * (1 - weight) + ordered[high] * weight


async def gather_dataset_truth(
    user_email: str | None,
) -> tuple[BenchmarkUser, dict[str, int], KnowledgeBaseSample | None]:
    async with AsyncSessionLocal() as session:
        paper_total = int((await session.execute(select(func.count()).select_from(Paper))).scalar_one())
        kb_total = int((await session.execute(select(func.count()).select_from(KnowledgeBase))).scalar_one())
        kbp_total = int((await session.execute(select(func.count()).select_from(KnowledgeBasePaper))).scalar_one())
        kb_primary_total = int(
            (
                await session.execute(
                    select(func.count()).select_from(Paper).where(Paper.knowledge_base_id.is_not(None))
                )
            ).scalar_one()
        )

        if user_email:
            stmt = (
                select(UserModel, func.count(Paper.id).label("paper_count"))
                .join(Paper, Paper.user_id == UserModel.id)
                .where(UserModel.email == user_email)
                .group_by(UserModel.id)
            )
        else:
            stmt = (
                select(UserModel, func.count(Paper.id).label("paper_count"))
                .join(Paper, Paper.user_id == UserModel.id)
                .group_by(UserModel.id)
                .order_by(func.count(Paper.id).desc(), UserModel.email.asc())
                .limit(1)
            )

        user_row = (await session.execute(stmt)).first()
        if user_row is None:
            raise RuntimeError("No benchmark user with papers found in local database.")

        orm_user, paper_count = user_row
        paper_rows = await session.execute(
            select(Paper, func.count(PaperChunk.id).label("chunk_count"))
            .outerjoin(Paper.paper_chunks)
            .where(Paper.user_id == orm_user.id)
            .group_by(Paper.id)
            .order_by(
                func.count(PaperChunk.id).desc(),
                Paper.updated_at.desc().nullslast(),
                Paper.created_at.desc().nullslast(),
                Paper.id.asc(),
            )
            .limit(4)
        )
        papers = [
            PaperSample(
                id=str(paper.id),
                title=str(paper.title or paper.id),
                status=getattr(paper, "status", None),
                is_search_ready=getattr(paper, "is_search_ready", None),
                is_multimodal_ready=getattr(paper, "is_multimodal_ready", None),
                chunk_count=int(chunk_count or 0),
            )
            for paper, chunk_count in paper_rows.all()
        ]

        if len(papers) < 2:
            raise RuntimeError("Benchmark user must have at least two papers for compare coverage.")

        benchmark_user = BenchmarkUser(
            id=str(orm_user.id),
            email=str(orm_user.email),
            name=str(orm_user.name),
            paper_count=int(paper_count),
            papers=papers,
        )
        kb_stmt = (
            select(
                KnowledgeBase,
                func.count(func.distinct(Paper.id)).label("paper_count"),
                func.count(PaperChunk.id).label("chunk_count"),
            )
            .join(Paper, Paper.knowledge_base_id == KnowledgeBase.id)
            .outerjoin(Paper.paper_chunks)
            .where(KnowledgeBase.user_id == orm_user.id, Paper.user_id == orm_user.id)
            .group_by(KnowledgeBase.id)
            .order_by(
                func.count(PaperChunk.id).desc(),
                func.count(func.distinct(Paper.id)).desc(),
                KnowledgeBase.created_at.asc(),
            )
            .limit(1)
        )
        kb_row = (await session.execute(kb_stmt)).first()
        benchmark_kb: KnowledgeBaseSample | None = None
        if kb_row is not None:
            kb_obj, kb_paper_count, kb_chunk_count = kb_row
            kb_paper_rows = await session.execute(
                select(Paper.id, func.count(PaperChunk.id).label("chunk_count"))
                .outerjoin(Paper.paper_chunks)
                .where(Paper.user_id == orm_user.id, Paper.knowledge_base_id == kb_obj.id)
                .group_by(Paper.id)
                .order_by(
                    func.count(PaperChunk.id).desc(),
                    Paper.updated_at.desc().nullslast(),
                    Paper.created_at.desc().nullslast(),
                    Paper.id.asc(),
                )
                .limit(8)
            )
            benchmark_kb = KnowledgeBaseSample(
                id=str(kb_obj.id),
                name=str(kb_obj.name),
                paper_count=int(kb_paper_count),
                paper_ids=[str(row[0]) for row in kb_paper_rows.fetchall()],
                chunk_count=int(kb_chunk_count or 0),
            )
        dataset_truth = {
            "papers_total": paper_total,
            "knowledge_bases_total": kb_total,
            "knowledge_base_papers_total": kbp_total,
            "papers_with_knowledge_base_id_total": kb_primary_total,
        }
        return benchmark_user, dataset_truth, benchmark_kb


async def mint_access_token(user: BenchmarkUser) -> str:
    roles = await get_user_roles(user.id)
    return create_access_token(
        {
            "sub": user.id,
            "email": user.email,
            "roles": roles,
        }
    )


async def prepare_benchmark_context(
    user_email: str | None,
) -> tuple[BenchmarkUser, dict[str, int], KnowledgeBaseSample | None, str]:
    benchmark_user, dataset_truth, benchmark_kb = await gather_dataset_truth(user_email)
    access_token = await mint_access_token(benchmark_user)
    return benchmark_user, dataset_truth, benchmark_kb, access_token


def http_request_json(
    *,
    method: str,
    url: str,
    timeout_sec: float,
    payload: dict[str, Any] | None = None,
    bearer_token: str | None = None,
) -> tuple[int, dict[str, Any]]:
    headers = {"Accept": "application/json"}
    data = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload).encode("utf-8")
    if bearer_token:
        headers["Authorization"] = f"Bearer {bearer_token}"

    request = urllib_request.Request(url=url, data=data, headers=headers, method=method.upper())
    try:
        with urllib_request.urlopen(request, timeout=timeout_sec) as response:
            status = response.getcode()
            body = response.read().decode("utf-8")
            return status, json.loads(body) if body else {}
    except urllib_error.HTTPError as exc:
        body = exc.read().decode("utf-8")
        try:
            payload = json.loads(body) if body else {}
        except json.JSONDecodeError:
            payload = {"raw": body}
        return exc.code, payload


def wait_for_live(base_url: str, timeout_sec: float) -> dict[str, Any]:
    deadline = time.time() + timeout_sec
    last_payload: dict[str, Any] = {}
    while time.time() < deadline:
        try:
            status, payload = http_request_json(
                method="GET",
                url=f"{base_url}/health/live",
                timeout_sec=5.0,
            )
            last_payload = payload
            if status == 200:
                return payload
        except Exception as exc:  # pragma: no cover - runtime probe
            last_payload = {"error": str(exc)}
        time.sleep(1.0)
    raise RuntimeError(f"Timed out waiting for /health/live. Last payload: {last_payload}")


def launch_backend(host: str, port: int, output_dir: Path) -> tuple[subprocess.Popen[str], Path]:
    log_path = output_dir / "backend.log"
    env = os.environ.copy()
    env.update(
        {
            "ENVIRONMENT": "test",
            "NEO4J_DISABLED": "true",
            "AI_STARTUP_MODE": "off",
            "PREFLIGHT_ON_STARTUP": "false",
            "PORT": str(port),
        }
    )
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_handle = open(log_path, "w", encoding="utf-8")
    process = subprocess.Popen(
        [
            str(API_ROOT / ".venv" / "bin" / "python"),
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            host,
            "--port",
            str(port),
        ],
        cwd=str(API_ROOT),
        env=env,
        stdout=log_handle,
        stderr=subprocess.STDOUT,
        text=True,
    )
    return process, log_path


def stop_backend(process: subprocess.Popen[str] | None) -> None:
    if process is None or process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.send_signal(signal.SIGKILL)
        process.wait(timeout=5)


def extract_citation_paper_ids(payload: dict[str, Any]) -> list[str]:
    ids: list[str] = []
    for item in payload.get("citations", []) or []:
        paper_id = str(item.get("paper_id") or "").strip()
        if paper_id:
            ids.append(paper_id)
    for item in payload.get("sources", []) or []:
        paper_id = str(item.get("paper_id") or "").strip()
        if paper_id:
            ids.append(paper_id)
    for item in payload.get("paper_results", []) or []:
        paper_id = str(item or "").strip()
        if paper_id:
            ids.append(paper_id)
    for block in payload.get("evidence_blocks", []) or []:
        paper_id = str(block.get("paper_id") or "").strip()
        if paper_id:
            ids.append(paper_id)
    compare_matrix = payload.get("compare_matrix") or {}
    for row in compare_matrix.get("rows", []) or []:
        paper_id = str(row.get("paper_id") or "").strip()
        if paper_id:
            ids.append(paper_id)
        for cell in row.get("cells", []) or []:
            for block in cell.get("evidence_blocks", []) or []:
                nested_paper_id = str(block.get("paper_id") or "").strip()
                if nested_paper_id:
                    ids.append(nested_paper_id)
    for insight in compare_matrix.get("cross_paper_insights", []) or []:
        for paper_id in insight.get("supporting_paper_ids", []) or []:
            normalized = str(paper_id or "").strip()
            if normalized:
                ids.append(normalized)
    return sorted(dict.fromkeys(ids))


def case_result(
    *,
    case_id: str,
    status: str,
    latency_ms: float,
    summary: str,
    details: dict[str, Any],
) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "status": status,
        "latency_ms": round(latency_ms, 2),
        "summary": summary,
        "details": details,
    }


def run_route_case(
    *,
    case_id: str,
    method: str,
    url: str,
    timeout_sec: float,
    payload: dict[str, Any],
    bearer_token: str | None,
    evaluator,
) -> dict[str, Any]:
    started = time.perf_counter()
    status_code, response_payload = http_request_json(
        method=method,
        url=url,
        timeout_sec=timeout_sec,
        payload=payload,
        bearer_token=bearer_token,
    )
    latency_ms = (time.perf_counter() - started) * 1000
    return evaluator(status_code, response_payload, latency_ms)


def main() -> None:
    args = parse_args()
    output_dir = benchmark_output_dir(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    base_url = args.base_url or f"http://{args.host}:{args.port}"

    backend_process: subprocess.Popen[str] | None = None
    backend_log = output_dir / "backend.log"
    try:
        benchmark_user, dataset_truth, benchmark_kb, access_token = asyncio.run(
            prepare_benchmark_context(args.user_email)
        )

        if args.launch_backend:
            backend_process, backend_log = launch_backend(args.host, args.port, output_dir)

        live_payload = wait_for_live(base_url, args.health_timeout_sec)
        ready_status, ready_payload = http_request_json(
            method="GET",
            url=f"{base_url}/health/ready",
            timeout_sec=10.0,
        )

        first_paper = benchmark_user.papers[0]
        second_paper = benchmark_user.papers[1]
        cases: list[dict[str, Any]] = []

        def eval_chat(status_code: int, response: dict[str, Any], latency_ms: float) -> dict[str, Any]:
            data = response.get("data", {}) if isinstance(response, dict) else {}
            hit_ids = extract_citation_paper_ids(data)
            passed = (
                status_code == 200
                and bool(data.get("answer"))
                and first_paper.id in hit_ids
            )
            return case_result(
                case_id="single-paper-chat",
                status="passed" if passed else "failed",
                latency_ms=latency_ms,
                summary=(
                    "chat route returned scoped answer with target paper evidence"
                    if passed
                    else "chat route missing scoped evidence or answer"
                ),
                details={
                    "http_status": status_code,
                    "answer_mode": data.get("answer_mode"),
                    "quality": data.get("quality"),
                    "hit_paper_ids": hit_ids,
                    "target_paper_id": first_paper.id,
                },
            )

        def eval_search(status_code: int, response: dict[str, Any], latency_ms: float) -> dict[str, Any]:
            hit_ids = extract_citation_paper_ids(response)
            evidence_matches = response.get("evidence_matches", []) or []
            passed = (
                status_code == 200
                and bool(evidence_matches)
                and first_paper.id in hit_ids
            )
            return case_result(
                case_id="single-paper-evidence",
                status="passed" if passed else "failed",
                latency_ms=latency_ms,
                summary=(
                    "search evidence returned scoped evidence rows"
                    if passed
                    else "search evidence returned no usable scoped evidence"
                ),
                details={
                    "http_status": status_code,
                    "answer_mode": response.get("answer_mode"),
                    "quality": response.get("quality"),
                    "hit_paper_ids": hit_ids,
                    "evidence_match_count": len(evidence_matches),
                    "target_paper_id": first_paper.id,
                },
            )

        def eval_rag(status_code: int, response: dict[str, Any], latency_ms: float) -> dict[str, Any]:
            hit_ids = extract_citation_paper_ids(response)
            distinct_hits = len(set(hit_ids) & {first_paper.id, second_paper.id})
            passed = (
                status_code == 200
                and bool(response.get("answer"))
                and distinct_hits >= 1
            )
            return case_result(
                case_id="multi-paper-compare",
                status="passed" if passed else "failed",
                latency_ms=latency_ms,
                summary=(
                    "rag compare returned answer with compare-scope evidence"
                    if passed
                    else "rag compare failed to return usable compare evidence"
                ),
                details={
                    "http_status": status_code,
                    "answer_mode": response.get("answerMode"),
                    "confidence": response.get("confidence"),
                    "low_confidence_reasons": response.get("lowConfidenceReasons"),
                    "hit_paper_ids": hit_ids,
                    "target_paper_ids": [first_paper.id, second_paper.id],
                },
            )

        def eval_compare_v4(status_code: int, response: dict[str, Any], latency_ms: float) -> dict[str, Any]:
            data = response.get("data", response) if isinstance(response, dict) else {}
            hit_ids = extract_citation_paper_ids(data)
            passed = (
                status_code == 200
                and data.get("response_type") == "compare"
                and bool(data.get("compare_matrix"))
                and len(set(hit_ids) & {first_paper.id, second_paper.id}) >= 1
            )
            return case_result(
                case_id="compare-v4-contract",
                status="passed" if passed else "failed",
                latency_ms=latency_ms,
                summary=(
                    "compare/v4 returned compare contract with evidence-backed matrix"
                    if passed
                    else "compare/v4 contract missing compare matrix or target evidence"
                ),
                details={
                    "http_status": status_code,
                    "response_type": data.get("response_type"),
                    "answer_mode": data.get("answer_mode"),
                    "degraded_conditions": data.get("degraded_conditions"),
                    "fallback_used": (data.get("quality") or {}).get("fallback_used"),
                    "hit_paper_ids": hit_ids,
                },
            )

        def eval_kb_query(status_code: int, response: dict[str, Any], latency_ms: float) -> dict[str, Any]:
            data = response.get("data", {}) if isinstance(response, dict) else {}
            hit_ids = extract_citation_paper_ids(data)
            expected_ids = set((benchmark_kb.paper_ids if benchmark_kb else [])[:5])
            matched_scope_ids = sorted(expected_ids & set(hit_ids))
            passed = (
                status_code == 200
                and bool(data.get("answer"))
                and bool(data.get("citations"))
                and bool(matched_scope_ids)
            )
            return case_result(
                case_id="kb-query",
                status="passed" if passed else "failed",
                latency_ms=latency_ms,
                summary=(
                    "knowledge-base query returned answer and citations within KB scope"
                    if passed
                    else "knowledge-base query failed to return KB-scoped evidence"
                ),
                details={
                    "http_status": status_code,
                    "confidence": data.get("confidence"),
                    "hit_paper_ids": hit_ids,
                    "matched_scope_ids": matched_scope_ids,
                    "kb_id": benchmark_kb.id if benchmark_kb else None,
                },
            )

        def eval_kb_chat(status_code: int, response: dict[str, Any], latency_ms: float) -> dict[str, Any]:
            data = response.get("data", {}) if isinstance(response, dict) else {}
            hit_ids = extract_citation_paper_ids(data)
            expected_ids = set((benchmark_kb.paper_ids if benchmark_kb else [])[:5])
            matched_scope_ids = sorted(expected_ids & set(hit_ids))
            passed = (
                status_code == 200
                and bool(data.get("answer"))
                and bool(matched_scope_ids)
            )
            return case_result(
                case_id="kb-scoped-chat",
                status="passed" if passed else "failed",
                latency_ms=latency_ms,
                summary=(
                    "chat route respected KB scope and returned in-scope evidence"
                    if passed
                    else "chat route failed to return KB-scoped evidence"
                ),
                details={
                    "http_status": status_code,
                    "answer_mode": data.get("answer_mode"),
                    "hit_paper_ids": hit_ids,
                    "matched_scope_ids": matched_scope_ids,
                    "kb_id": benchmark_kb.id if benchmark_kb else None,
                },
            )

        def eval_kb_evidence(status_code: int, response: dict[str, Any], latency_ms: float) -> dict[str, Any]:
            hit_ids = extract_citation_paper_ids(response)
            expected_ids = set((benchmark_kb.paper_ids if benchmark_kb else [])[:5])
            matched_scope_ids = sorted(expected_ids & set(hit_ids))
            passed = (
                status_code == 200
                and bool(response.get("evidence_matches"))
                and bool(matched_scope_ids)
            )
            return case_result(
                case_id="kb-scoped-evidence",
                status="passed" if passed else "failed",
                latency_ms=latency_ms,
                summary=(
                    "search evidence respected KB scope and returned in-scope rows"
                    if passed
                    else "search evidence failed to return KB-scoped rows"
                ),
                details={
                    "http_status": status_code,
                    "answer_mode": response.get("answer_mode"),
                    "hit_paper_ids": hit_ids,
                    "matched_scope_ids": matched_scope_ids,
                    "kb_id": benchmark_kb.id if benchmark_kb else None,
                },
            )

        cases.append(
            run_route_case(
                case_id="single-paper-chat",
                method="POST",
                url=f"{base_url}/api/v1/chat",
                timeout_sec=args.timeout_sec,
                bearer_token=access_token,
                payload={
                    "message": "Summarize the main method and cite the paper evidence.",
                    "mode": "rag",
                    "scope": {
                        "type": "paper",
                        "paper_id": first_paper.id,
                    },
                    "context": {
                        "paper_ids": [first_paper.id],
                    },
                },
                evaluator=eval_chat,
            )
        )
        cases.append(
            run_route_case(
                case_id="single-paper-evidence",
                method="POST",
                url=f"{base_url}/api/v1/search/evidence",
                timeout_sec=args.timeout_sec,
                bearer_token=access_token,
                payload={
                    "query": "What method is proposed in this paper?",
                    "query_family": "fact",
                    "top_k": 5,
                    "paper_id": first_paper.id,
                },
                evaluator=eval_search,
            )
        )
        cases.append(
            run_route_case(
                case_id="multi-paper-compare",
                method="POST",
                url=f"{base_url}/api/v1/queries/query",
                timeout_sec=args.timeout_sec,
                bearer_token=access_token,
                payload={
                    "question": "Compare the main approach of these two papers and name at least one concrete difference.",
                    "paper_ids": [first_paper.id, second_paper.id],
                    "query_type": "compare",
                    "top_k": 8,
                },
                evaluator=eval_rag,
            )
        )
        cases.append(
            run_route_case(
                case_id="compare-v4-contract",
                method="POST",
                url=f"{base_url}/api/v1/compare/v4",
                timeout_sec=args.timeout_sec,
                bearer_token=access_token,
                payload={
                    "paper_ids": [first_paper.id, second_paper.id],
                    "question": "Compare the core method and main evidence-backed difference.",
                },
                evaluator=eval_compare_v4,
            )
        )

        if benchmark_kb and benchmark_kb.paper_count > 0:
            cases.append(
                run_route_case(
                    case_id="kb-scoped-chat",
                    method="POST",
                    url=f"{base_url}/api/v1/chat",
                    timeout_sec=args.timeout_sec,
                    bearer_token=access_token,
                    payload={
                        "message": "Summarize the main method from this knowledge base and cite the evidence.",
                        "mode": "rag",
                        "scope": {
                            "type": "knowledge_base",
                            "knowledge_base_id": benchmark_kb.id,
                        },
                    },
                    evaluator=eval_kb_chat,
                )
            )
            cases.append(
                run_route_case(
                    case_id="kb-scoped-evidence",
                    method="POST",
                    url=f"{base_url}/api/v1/search/evidence",
                    timeout_sec=args.timeout_sec,
                    bearer_token=access_token,
                    payload={
                        "query": "What method is proposed in this knowledge base?",
                        "query_family": "fact",
                        "top_k": 5,
                        "kb_id": benchmark_kb.id,
                    },
                    evaluator=eval_kb_evidence,
                )
            )
            cases.append(
                run_route_case(
                    case_id="kb-query",
                    method="POST",
                    url=f"{base_url}/api/v1/knowledge-bases/{benchmark_kb.id}/query",
                    timeout_sec=args.timeout_sec,
                    bearer_token=access_token,
                    payload={
                        "query": "Summarize the main method from this knowledge base and cite the evidence.",
                        "topK": 5,
                    },
                    evaluator=eval_kb_query,
                )
            )
        else:
            cases.append(
                case_result(
                    case_id="kb-scope-benchmark",
                    status="blocked",
                    latency_ms=0.0,
                    summary="blocked-by-data-truth: no knowledge-base membership sample found for benchmark user",
                    details={
                        "reason": "blocked-by-data-truth",
                        "knowledge_base_papers_total": dataset_truth["knowledge_base_papers_total"],
                        "papers_with_knowledge_base_id_total": dataset_truth["papers_with_knowledge_base_id_total"],
                    },
                )
            )

        passed = sum(1 for case in cases if case["status"] == "passed")
        failed = sum(1 for case in cases if case["status"] == "failed")
        blocked = sum(1 for case in cases if case["status"] == "blocked")
        latencies = [float(case["latency_ms"]) for case in cases if case["status"] != "blocked"]
        report = {
            "generated_at": now_utc(),
            "base_url": base_url,
            "backend_launch": {
                "launched": bool(args.launch_backend),
                "log_path": str(backend_log),
            },
            "health": {
                "live": live_payload,
                "ready_status": ready_status,
                "ready": ready_payload,
            },
            "dataset_truth": dataset_truth,
            "benchmark_user": {
                **asdict(benchmark_user),
            },
            "benchmark_kb": asdict(benchmark_kb) if benchmark_kb else None,
            "cases": cases,
            "summary": {
                "passed": passed,
                "failed": failed,
                "blocked": blocked,
                "success_rate": passed / max(passed + failed, 1),
                "p95_latency_ms": round(percentile(latencies, 0.95), 2),
            },
        }

        write_json(output_dir / "summary.json", report)
        write_markdown(output_dir / "summary.md", report)
        print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
        print(f"Artifacts written to: {output_dir}")
    finally:
        stop_backend(backend_process)


if __name__ == "__main__":
    main()
