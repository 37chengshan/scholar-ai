"""Import API router exports.

Wave 1 endpoints per D-01/D-03/D-08:
- POST /knowledge-bases/{kb_id}/imports - Create ImportJob
- PUT /import-jobs/{job_id}/file - Upload PDF to ImportJob
- GET /import-jobs/{job_id} - Get ImportJob status
- GET /import-jobs - List ImportJobs

Wave 2 endpoints per D-02:
- POST /import-sources/resolve - Resolve single source
- POST /import-sources/resolve-batch - Resolve multiple sources

Wave 3 endpoints per D-06:
- POST /import-jobs/{job_id}/dedupe-decision - Submit dedupe decision
- POST /knowledge-bases/{kb_id}/imports/batch - Batch import
- GET /import-batches/{batch_id} - Get batch status
- POST /import-batches/{batch_id}/files - Upload local files for batch jobs

Wave 5 endpoints per D-09:
- POST /import-jobs/{job_id}/retry - Retry failed job
- POST /import-jobs/{job_id}/cancel - Cancel running job
- GET /import-jobs/{job_id}/stream - SSE progress streaming
"""

from app.api.imports.jobs import router as jobs_router
from app.api.imports.sources import router as sources_router
from app.api.imports.dedupe import router as dedupe_router
from app.api.imports.batches import router as batches_router
from app.api.imports.events import router as events_router

from fastapi import APIRouter

# Combine routers under /api/v1 prefix
router = APIRouter()
router.include_router(jobs_router)
router.include_router(sources_router)
router.include_router(dedupe_router)
router.include_router(batches_router)
router.include_router(events_router)

__all__ = ["router"]