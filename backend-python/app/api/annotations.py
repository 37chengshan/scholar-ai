"""Annotations API endpoints.

Provides CRUD endpoints for PDF annotations:
- GET /api/v1/annotations/:paperId - List annotations for a paper
- POST /api/v1/annotations - Create annotation
- PATCH /api/v1/annotations/:id - Update annotation
- DELETE /api/v1/annotations/:id - Delete annotation
"""

import re
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, HTTPException, Depends, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.annotation import Annotation
from app.models.paper import Paper
from app.utils.logger import logger
from app.core.auth import CurrentUserId
from app.utils.problem_detail import Errors

router = APIRouter()


# =============================================================================
# Request/Response Models
# =============================================================================

class AnnotationCreate(BaseModel):
    """Request to create an annotation."""
    paperId: str
    type: str = Field(..., pattern=r"^(highlight|note|bookmark)$")
    pageNumber: int = Field(..., ge=1)
    position: Dict[str, Any]
    content: Optional[str] = None
    color: Optional[str] = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")


class AnnotationUpdate(BaseModel):
    """Request to update an annotation."""
    content: Optional[str] = None
    color: Optional[str] = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")


class AnnotationResponse(BaseModel):
    """Response for a single annotation."""
    id: str
    paper_id: str
    user_id: str
    type: str
    page_number: int
    position: Dict[str, Any]
    content: Optional[str]
    color: str
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class AnnotationListResponse(BaseModel):
    """Response for annotations list."""
    success: bool = True
    data: List[AnnotationResponse]


# =============================================================================
# CRUD Endpoints
# =============================================================================

@router.get("/{paper_id}", response_model=AnnotationListResponse)
async def list_annotations(
    paper_id: str,
    user_id: str = CurrentUserId,
    db: AsyncSession = Depends(get_db)
):
    """List annotations for a paper."""
    try:
        # Verify paper exists and belongs to user
        paper_result = await db.execute(
            select(Paper).where(Paper.id == paper_id, Paper.user_id == user_id)
        )
        paper = paper_result.scalar_one_or_none()

        if not paper:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=Errors.not_found("Paper not found")
            )

        # Get all annotations for this paper by the user
        result = await db.execute(
            select(Annotation)
            .where(Annotation.paper_id == paper_id, Annotation.user_id == user_id)
            .order_by(Annotation.page_number.asc(), Annotation.created_at.asc())
        )
        annotations = result.scalars().all()

        return AnnotationListResponse(
            success=True,
            data=[
                AnnotationResponse(
                    id=a.id,
                    paper_id=a.paper_id,
                    user_id=a.user_id,
                    type=a.type,
                    page_number=a.page_number,
                    position=a.position,
                    content=a.content,
                    color=a.color,
                    created_at=a.created_at.isoformat(),
                    updated_at=a.updated_at.isoformat()
                )
                for a in annotations
            ]
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to list annotations", error=str(e), paper_id=paper_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=Errors.internal(f"Failed to list annotations: {str(e)}")
        )


@router.post("", response_model=AnnotationResponse, status_code=status.HTTP_201_CREATED)
async def create_annotation(
    request: AnnotationCreate,
    user_id: str = CurrentUserId,
    db: AsyncSession = Depends(get_db)
):
    """Create an annotation."""
    try:
        # Validate annotation type
        valid_types = ["highlight", "note", "bookmark"]
        if request.type not in valid_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=Errors.validation(f"Invalid annotation type. Must be one of: {', '.join(valid_types)}")
            )

        # Verify paper exists and belongs to user
        paper_result = await db.execute(
            select(Paper).where(Paper.id == request.paperId, Paper.user_id == user_id)
        )
        paper = paper_result.scalar_one_or_none()

        if not paper:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=Errors.not_found("Paper not found")
            )

        # Validate color format
        color = request.color or "#FFEB3B"
        if not re.match(r"^#[0-9A-Fa-f]{6}$", color):
            color = "#FFEB3B"

        # Create annotation
        annotation = Annotation(
            paper_id=request.paperId,
            user_id=user_id,
            type=request.type,
            page_number=request.pageNumber,
            position=request.position,
            content=request.content,
            color=color
        )

        db.add(annotation)
        await db.flush()
        await db.refresh(annotation)

        logger.info(
            "Annotation created",
            annotation_id=annotation.id,
            paper_id=request.paperId,
            type=request.type,
            user_id=user_id
        )

        return AnnotationResponse(
            id=annotation.id,
            paper_id=annotation.paper_id,
            user_id=annotation.user_id,
            type=annotation.type,
            page_number=annotation.page_number,
            position=annotation.position,
            content=annotation.content,
            color=annotation.color,
            created_at=annotation.created_at.isoformat(),
            updated_at=annotation.updated_at.isoformat()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to create annotation", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=Errors.internal(f"Failed to create annotation: {str(e)}")
        )


@router.patch("/{annotation_id}", response_model=AnnotationResponse)
async def update_annotation(
    annotation_id: str,
    request: AnnotationUpdate,
    user_id: str = CurrentUserId,
    db: AsyncSession = Depends(get_db)
):
    """Update an annotation."""
    try:
        # Find annotation
        result = await db.execute(
            select(Annotation).where(Annotation.id == annotation_id, Annotation.user_id == user_id)
        )
        annotation = result.scalar_one_or_none()

        if not annotation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=Errors.not_found("Annotation not found")
            )

        # Validate at least one field provided
        if request.content is None and request.color is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=Errors.validation("At least one field (content or color) is required")
            )

        # Update fields
        if request.content is not None:
            annotation.content = request.content or None
        if request.color is not None:
            if re.match(r"^#[0-9A-Fa-f]{6}$", request.color):
                annotation.color = request.color

        await db.flush()
        await db.refresh(annotation)

        logger.info("Annotation updated", annotation_id=annotation_id, user_id=user_id)

        return AnnotationResponse(
            id=annotation.id,
            paper_id=annotation.paper_id,
            user_id=annotation.user_id,
            type=annotation.type,
            page_number=annotation.page_number,
            position=annotation.position,
            content=annotation.content,
            color=annotation.color,
            created_at=annotation.created_at.isoformat(),
            updated_at=annotation.updated_at.isoformat()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to update annotation", error=str(e), annotation_id=annotation_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=Errors.internal(f"Failed to update annotation: {str(e)}")
        )


@router.delete("/{annotation_id}")
async def delete_annotation(
    annotation_id: str,
    user_id: str = CurrentUserId,
    db: AsyncSession = Depends(get_db)
):
    """Delete an annotation."""
    try:
        # Find annotation
        result = await db.execute(
            select(Annotation).where(Annotation.id == annotation_id, Annotation.user_id == user_id)
        )
        annotation = result.scalar_one_or_none()

        if not annotation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=Errors.not_found("Annotation not found")
            )

        await db.delete(annotation)

        logger.info("Annotation deleted", annotation_id=annotation_id, user_id=user_id)

        return {"success": True, "data": {"id": annotation_id, "deleted": True}}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete annotation", error=str(e), annotation_id=annotation_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=Errors.internal(f"Failed to delete annotation: {str(e)}")
        )