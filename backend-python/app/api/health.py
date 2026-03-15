"""健康检查路由"""

from fastapi import APIRouter, status

router = APIRouter()


@router.get("", status_code=status.HTTP_200_OK)
async def health_check():
    """健康检查"""
    return {
        "status": "ok",
        "service": "scholarai-ai"
    }
