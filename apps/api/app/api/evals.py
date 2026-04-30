"""Phase 6 Evaluation API — read-only eval endpoints under /api/v1/evals."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.services.eval_service import (
    get_overview,
    list_run_summaries,
    get_run_detail,
    compute_diff,
)


router = APIRouter()


def _matches_mode_filter(run_mode: str | None, requested_mode: str) -> bool:
    if requested_mode == "offline":
        return run_mode in {"offline", "public_offline", "blind_offline"}
    if requested_mode == "online":
        return run_mode in {"online", "public_online", "blind_online"}
    return run_mode == requested_mode


@router.get("/overview")
async def eval_overview(
    benchmark: str = Query("phase6", description="Benchmark namespace: phase6 | v3_0_academic"),
):
    """Latest offline gate verdict + recent run summaries."""
    overview = get_overview(benchmark)
    return {"success": True, "data": overview}


@router.get("/runs")
async def eval_runs(
    benchmark: str = Query("phase6", description="Benchmark namespace: phase6 | v3_0_academic"),
    mode: str | None = Query(None, description="Filter by mode: offline | online"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """List all eval runs from manifest, optionally filtered by mode."""
    runs = list_run_summaries(benchmark)
    if mode:
        runs = [r for r in runs if _matches_mode_filter(r.get("mode"), mode)]
    total = len(runs)
    page = runs[offset: offset + limit]
    return {
        "success": True,
        "data": {"items": page, "total": total},
        "meta": {"total": total, "limit": limit, "offset": offset},
    }


@router.get("/runs/{run_id}")
async def eval_run_detail(
    run_id: str,
    benchmark: str = Query("phase6", description="Benchmark namespace: phase6 | v3_0_academic"),
):
    """Full run detail: meta + normalized metrics + per-family breakdowns."""
    detail = get_run_detail(run_id, benchmark)
    if detail is None:
        raise HTTPException(
            status_code=404, detail=f"Eval run '{run_id}' not found or missing artifacts."
        )
    return {"success": True, "data": detail}


@router.get("/diff")
async def eval_diff(
    benchmark: str = Query("phase6", description="Benchmark namespace: phase6 | v3_0_academic"),
    base_run_id: str = Query(..., description="Baseline run ID"),
    candidate_run_id: str = Query(..., description="Candidate run ID to compare"),
):
    """Compute metric deltas between base and candidate runs."""
    diff = compute_diff(base_run_id, candidate_run_id, benchmark)
    if diff is None:
        raise HTTPException(
            status_code=404,
            detail=f"One or both runs not found: base='{base_run_id}', candidate='{candidate_run_id}'",
        )
    return {"success": True, "data": diff}
