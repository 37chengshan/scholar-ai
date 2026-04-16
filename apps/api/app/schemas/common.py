"""Common response schemas."""

from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class SuccessResponse(BaseModel, Generic[T]):
    """Standard success envelope."""

    success: bool = True
    data: T


class ErrorDetail(BaseModel):
    """Standard API error detail."""

    code: str
    message: str
    details: object | None = None


class FailureResponse(BaseModel):
    """Standard failure envelope."""

    success: bool = False
    error: ErrorDetail


class ListMeta(BaseModel):
    """Pagination metadata."""

    limit: int = Field(..., ge=1)
    offset: int = Field(..., ge=0)
    total: int = Field(..., ge=0)


class ListResponse(BaseModel, Generic[T]):
    """Standard list envelope with metadata."""

    success: bool = True
    data: dict
    meta: ListMeta
