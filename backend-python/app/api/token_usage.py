"""Token usage API endpoints.

Provides endpoints for:
- GET /api/token-usage/monthly: Get monthly token usage for user
"""

from fastapi import APIRouter, Depends, Query
from typing import Optional

from app.core.auth import CurrentUserId
from app.utils.token_tracker import TokenTracker
from app.utils.logger import logger

router = APIRouter()
tracker = TokenTracker()


@router.get("/token-usage/monthly")
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

        return {
            "success": True,
            "data": usage,
        }

    except Exception as e:
        logger.error("Failed to get monthly token usage", error=str(e), user_id=user_id)

        return {
            "success": False,
            "error": str(e),
            "data": {
                "total_tokens": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "total_cost_cny": 0.0,
                "request_count": 0,
                "daily_breakdown": [],
            },
        }
