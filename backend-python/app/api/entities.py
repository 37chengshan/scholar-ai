"""实体抽取路由"""

from typing import List

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.utils.logger import logger

router = APIRouter()


class EntityExtractionRequest(BaseModel):
    """实体抽取请求"""
    text: str
    entity_types: List[str] = ["method", "dataset", "metric", "author"]


class EntityExtractionResponse(BaseModel):
    """实体抽取响应"""
    entities: List[dict]
    relationships: List[dict]


@router.post("/extract", response_model=EntityExtractionResponse)
async def extract_entities(request: EntityExtractionRequest):
    """
    从文本中抽取实体和关系

    - 抽取方法、数据集、作者等实体
    - 识别实体间关系
    """
    try:
        logger.info(f"Extracting entities from text ({len(request.text)} chars)")

        # TODO: 使用LLM进行实体抽取
        # - 命名实体识别
        # - 关系抽取

        return {
            "entities": [
                {
                    "id": "ent-1",
                    "type": "method",
                    "name": "Transformer",
                    "confidence": 0.95
                }
            ],
            "relationships": [
                {
                    "source": "ent-1",
                    "target": "ent-2",
                    "type": "improves",
                    "confidence": 0.85
                }
            ]
        }

    except Exception as e:
        logger.error(f"Entity extraction error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"实体抽取失败: {str(e)}"
        )
