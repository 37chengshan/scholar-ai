"""Papers module - Router aggregation for split papers sub-modules.

Split from papers.py per D-11: 按 CRUD/业务域/外部集成划分.
Per D-04: router.include_router aggregation.
"""

from fastapi import APIRouter

from .paper_crud import router as crud_router
from .paper_upload import router as upload_router
from .paper_status import router as status_router


router = APIRouter(tags=["Papers"])
router.include_router(crud_router)
router.include_router(upload_router)
router.include_router(status_router)


__all__ = ["router"]
