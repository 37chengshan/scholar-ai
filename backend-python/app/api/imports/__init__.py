"""Import API router exports.

Wave 1 endpoints per D-01/D-03/D-08:
- POST /knowledge-bases/{kb_id}/imports - Create ImportJob
- PUT /import-jobs/{job_id}/file - Upload PDF to ImportJob
- GET /import-jobs/{job_id} - Get ImportJob status
- GET /import-jobs - List ImportJobs

Wave 2 endpoints per D-02:
- POST /import-sources/resolve - Resolve single source
- POST /import-sources/resolve-batch - Resolve multiple sources
"""

from app.api.imports.jobs import router as jobs_router
from app.api.imports.sources import router as sources_router

from fastapi import APIRouter

# Combine routers under /api/v1 prefix
router = APIRouter()
router.include_router(jobs_router)
router.include_router(sources_router)

__all__ = ["router"]