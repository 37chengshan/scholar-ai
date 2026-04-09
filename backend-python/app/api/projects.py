"""Projects API endpoints.

Provides CRUD endpoints for user projects:
- GET /api/v1/projects - List user projects
- POST /api/v1/projects - Create project
- GET /api/v1/projects/:id - Get project with papers
- PATCH /api/v1/projects/:id - Update project
- DELETE /api/v1/projects/:id - Delete project
- PATCH /api/v1/projects/paper/:paperId - Assign paper to project
"""

import re
import uuid
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Depends, Query, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.project import Project
from app.models.paper import Paper
from app.utils.logger import logger
from app.core.auth import CurrentUserId
from app.utils.problem_detail import Errors

router = APIRouter()


# =============================================================================
# Request/Response Models
# =============================================================================

class ProjectCreate(BaseModel):
    """Request to create a project."""
    name: str = Field(..., min_length=1, max_length=200)
    color: Optional[str] = Field("#3B82F6", pattern=r"^#[0-9A-Fa-f]{6}$")


class ProjectUpdate(BaseModel):
    """Request to update a project."""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    color: Optional[str] = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")


class ProjectResponse(BaseModel):
    """Response for a single project."""
    id: str
    user_id: str
    name: str
    color: str
    paper_count: int = 0
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class ProjectListResponse(BaseModel):
    """Response for projects list."""
    success: bool = True
    data: List[ProjectResponse]


class PaperProjectUpdate(BaseModel):
    """Request to assign paper to project."""
    projectId: Optional[str] = None


# =============================================================================
# CRUD Endpoints
# =============================================================================

@router.get("", response_model=ProjectListResponse)
async def list_projects(
    user_id: str = CurrentUserId,
    db: AsyncSession = Depends(get_db)
):
    """List user's projects with paper counts."""
    try:
        # Query projects with paper count
        query = (
            select(Project, func.count(Paper.id).label("paper_count"))
            .outerjoin(Paper, Paper.project_id == Project.id)
            .where(Project.user_id == user_id)
            .group_by(Project.id)
            .order_by(desc(Project.created_at))
        )

        result = await db.execute(query)
        rows = result.all()

        projects = [
            ProjectResponse(
                id=row[0].id,
                user_id=row[0].user_id,
                name=row[0].name,
                color=row[0].color,
                paper_count=row[1] or 0,
                created_at=row[0].created_at.isoformat(),
                updated_at=row[0].updated_at.isoformat()
            )
            for row in rows
        ]

        return ProjectListResponse(success=True, data=projects)

    except Exception as e:
        logger.error("Failed to list projects", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=Errors.internal(f"Failed to list projects: {str(e)}")
        )


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    request: ProjectCreate,
    user_id: str = CurrentUserId,
    db: AsyncSession = Depends(get_db)
):
    """Create a new project."""
    try:
        # Validate color format
        color = request.color
        if not re.match(r"^#[0-9A-Fa-f]{6}$", color):
            color = "#3B82F6"

        project = Project(
            id=str(uuid.uuid4()),
            user_id=user_id,
            name=request.name.strip(),
            color=color
        )

        db.add(project)
        await db.flush()
        await db.refresh(project)

        logger.info("Project created", project_id=project.id, user_id=user_id, name=request.name)

        return ProjectResponse(
            id=project.id,
            user_id=project.user_id,
            name=project.name,
            color=project.color,
            paper_count=0,
            created_at=project.created_at.isoformat(),
            updated_at=project.updated_at.isoformat()
        )

    except Exception as e:
        logger.error("Failed to create project", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=Errors.internal(f"Failed to create project: {str(e)}")
        )


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    user_id: str = CurrentUserId,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific project with paper count."""
    try:
        # Query project with paper count
        query = (
            select(Project, func.count(Paper.id).label("paper_count"))
            .outerjoin(Paper, Paper.project_id == Project.id)
            .where(Project.id == project_id, Project.user_id == user_id)
            .group_by(Project.id)
        )

        result = await db.execute(query)
        row = result.first()

        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=Errors.not_found("Project not found")
            )

        project, paper_count = row

        return ProjectResponse(
            id=project.id,
            user_id=project.user_id,
            name=project.name,
            color=project.color,
            paper_count=paper_count or 0,
            created_at=project.created_at.isoformat(),
            updated_at=project.updated_at.isoformat()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get project", error=str(e), project_id=project_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=Errors.internal(f"Failed to get project: {str(e)}")
        )


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    request: ProjectUpdate,
    user_id: str = CurrentUserId,
    db: AsyncSession = Depends(get_db)
):
    """Update a project."""
    try:
        # Validate at least one field provided
        if request.name is None and request.color is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=Errors.validation("At least one field (name or color) is required")
            )

        # Find project
        result = await db.execute(
            select(Project).where(Project.id == project_id, Project.user_id == user_id)
        )
        project = result.scalar_one_or_none()

        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=Errors.not_found("Project not found")
            )

        # Update fields
        if request.name is not None:
            project.name = request.name.strip()
        if request.color is not None:
            if re.match(r"^#[0-9A-Fa-f]{6}$", request.color):
                project.color = request.color

        await db.flush()
        await db.refresh(project)

        # Get paper count
        count_result = await db.execute(
            select(func.count(Paper.id)).where(Paper.project_id == project_id)
        )
        paper_count = count_result.scalar() or 0

        logger.info("Project updated", project_id=project_id, user_id=user_id)

        return ProjectResponse(
            id=project.id,
            user_id=project.user_id,
            name=project.name,
            color=project.color,
            paper_count=paper_count,
            created_at=project.created_at.isoformat(),
            updated_at=project.updated_at.isoformat()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to update project", error=str(e), project_id=project_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=Errors.internal(f"Failed to update project: {str(e)}")
        )


@router.delete("/{project_id}")
async def delete_project(
    project_id: str,
    user_id: str = CurrentUserId,
    db: AsyncSession = Depends(get_db)
):
    """Delete a project.

    Papers in the project will have projectId set to null (SetNull behavior).
    """
    try:
        # Find project
        result = await db.execute(
            select(Project).where(Project.id == project_id, Project.user_id == user_id)
        )
        project = result.scalar_one_or_none()

        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=Errors.not_found("Project not found")
            )

        # Delete project (papers will have projectId set to null via database)
        await db.delete(project)

        logger.info("Project deleted", project_id=project_id, user_id=user_id)

        return {"success": True, "data": {"id": project_id, "deleted": True}}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete project", error=str(e), project_id=project_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=Errors.internal(f"Failed to delete project: {str(e)}")
        )


@router.patch("/paper/{paper_id}")
async def assign_paper_to_project(
    paper_id: str,
    request: PaperProjectUpdate,
    user_id: str = CurrentUserId,
    db: AsyncSession = Depends(get_db)
):
    """Assign paper to a project.

    Set projectId to null to remove paper from project.
    """
    try:
        # Verify paper exists and belongs to user
        result = await db.execute(
            select(Paper).where(Paper.id == paper_id, Paper.user_id == user_id)
        )
        paper = result.scalar_one_or_none()

        if not paper:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=Errors.not_found("Paper not found")
            )

        # If projectId provided, verify project exists and belongs to user
        if request.projectId:
            project_result = await db.execute(
                select(Project).where(
                    Project.id == request.projectId,
                    Project.user_id == user_id
                )
            )
            project = project_result.scalar_one_or_none()

            if not project:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=Errors.not_found("Project not found")
                )

        # Update paper's project
        paper.project_id = request.projectId

        await db.flush()
        await db.refresh(paper)

        logger.info(
            "Paper assigned to project",
            paper_id=paper_id,
            project_id=request.projectId or "none",
            user_id=user_id
        )

        return {
            "success": True,
            "data": {
                "id": paper.id,
                "title": paper.title,
                "project_id": paper.project_id
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to assign paper to project", error=str(e), paper_id=paper_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=Errors.internal(f"Failed to assign paper: {str(e)}")
        )