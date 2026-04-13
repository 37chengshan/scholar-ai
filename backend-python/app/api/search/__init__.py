"""Search module - Router aggregation for split search sub-modules.

Split from search.py per D-11: 按 CRUD/业务域/外部集成划分.
Per D-04: router.include_router aggregation.
"""

from fastapi import APIRouter

from .external import router as external_router
from .library import router as library_router
from .multimodal import router as multimodal_router


router = APIRouter()
router.include_router(external_router)
router.include_router(library_router)
router.include_router(multimodal_router)


__all__ = ["router"]
