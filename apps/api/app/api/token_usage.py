"""Token usage API endpoints.

Provides endpoints for:
- GET /api/token-usage/monthly: Get monthly token usage for user
"""

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from typing import List, Optional

from app.deps import CurrentUserId
from app.utils.token_tracker import TokenTracker
from app.utils.logger import logger

router = APIRouter()
tracker = TokenTracker()


# =============================================================================
# Response Models
# =============================================================================

class DailyUsageBreakdown(BaseModel):
    """Daily token usage breakdown."""
    date: str
    tokens: int
    cost: float
    requests: int


class TokenUsageData(BaseModel):
    """Token usage data payload."""
    total_tokens: int
    input_tokens: int
    output_tokens: int
    total_cost_cny: float
    request_count: int
    daily_breakdown: List[DailyUsageBreakdown]


class TokenUsageResponse(BaseModel):
    """Response for token usage endpoints."""
    success: bool = True
    data: TokenUsageData


# =============================================================================
# Endpoints
# =============================================================================

@router.get("/token-usage/monthly", response_model=TokenUsageResponse)
async def get_monthly_token_usage(
    user_id: str = CurrentUserId,
    year: Optional[int] = Query(None, description="Year (default: current year)"),
    month: Optional[int] = Query(None, description="Month (default: current month)"),
):
    """Get user monthly token usage.

    Returns aggregated token usage for specified month including:
    - Total tokens, input/output breakdown
    - Total cost in CNY
    - Request count
    - Daily breakdown

    Args:
        user_id: User ID (from JWT)
        year: Year (optional, defaults to current year)
        month: Month (optional, defaults to current month)

    Returns:
        Monthly usage statistics
    """
    try:
        logger.info(
            "Monthly token usage requested",
            user_id=user_id,
            year=year,
            month=month,
        )

        usage = await tracker.get_monthly_usage(user_id, year, month)

        return TokenUsageResponse(
            success=True,
            data=TokenUsageData(**usage),
        )

    except Exception as e:
        logger.error("Failed to get monthly token usage", error=str(e), user_id=user_id)

        return TokenUsageResponse(
            success=False,
            data=TokenUsageData(
                total_tokens=0,
                input_tokens=0,
                output_tokens=0,
                total_cost_cny=0.0,
                request_count=0,
                daily_breakdown=[],
            ),
        )
