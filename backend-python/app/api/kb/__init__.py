"""KB module - Router aggregation for split KB sub-modules.

Split from knowledge_base.py per D-11: 按 CRUD/业务域/外部集成划分
Per D-04: router.include_router 聚合
"""

from fastapi import APIRouter

from .kb_crud import router as crud_router
from .kb_import import router as import_router
from .kb_search import router as search_router
from .kb_query import router as query_router


router = APIRouter()
router.include_router(crud_router, prefix="")
router.include_router(import_router, prefix="")
router.include_router(search_router, prefix="")
router.include_router(query_router, prefix="")


__all__ = ["router"]
