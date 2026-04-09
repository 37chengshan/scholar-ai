"""Token usage tracker for cost monitoring.

Tracks LLM token usage and costs per user/session.
Supports budget limits and cost calculations.
Persists usage logs to PostgreSQL for monthly aggregation.

Usage:
    tracker = TokenTracker()
    cost = await tracker.track_usage(
        user_id="user-123",
        model="glm-4.5-air",
        input_tokens=100,
        output_tokens=50,
        session_id="session-456"
    )
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, Dict, List
import uuid

import redis.asyncio as redis
from sqlalchemy import func, select

from app.config import settings
from app.database import AsyncSessionLocal
from app.models.token_usage_log import TokenUsageLog
from app.utils.logger import logger


class TokenTracker:
    """Track LLM token usage and costs.

    Attributes:
        PRICING: Cost per 1M tokens for each model
        redis: Redis client for storage
    """

    PRICING = {"glm-4.5-air": {"input": 0.5, "output": 0.5}}

    def __init__(self):
        """Initialize TokenTracker with Redis client."""
        self.redis: Optional[redis.Redis] = None

    async def _get_redis(self) -> redis.Redis:
        """Get or create Redis client.

        Returns:
            Redis client instance
        """
        if not self.redis:
            self.redis = redis.from_url(settings.REDIS_URL, decode_responses=True)
        return self.redis

    async def track_usage(
        self,
        user_id: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        session_id: Optional[str] = None,
    ) -> float:
        """Track token usage and return cost in CNY.

        Writes to both Redis (temporary cache) and PostgreSQL (persistent log).

        Args:
            user_id: User ID
            model: Model name (e.g., 'glm-4.5-air')
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            session_id: Optional session ID for session-level tracking

        Returns:
            Cost in CNY
        """
        pricing = self.PRICING.get(model)
        if not pricing:
            logger.warning(f"No pricing found for model {model}")
            return 0.0

        cost = (
            input_tokens / 1_000_000 * pricing["input"]
            + output_tokens / 1_000_000 * pricing["output"]
        )

        total_tokens = input_tokens + output_tokens

        r = await self._get_redis()

        date_str = datetime.now().strftime("%Y-%m-%d")
        user_key = f"token_usage:{user_id}:{date_str}"

        await r.hincrbyfloat(user_key, "total_cost", cost)
        await r.hincrby(user_key, "input_tokens", input_tokens)
        await r.hincrby(user_key, "output_tokens", output_tokens)
        await r.expire(user_key, 86400 * 30)

        if session_id:
            session_key = f"token_usage:session:{session_id}"
            await r.hincrbyfloat(session_key, "total_cost", cost)
            await r.expire(session_key, 86400 * 7)

        try:
            async with AsyncSessionLocal() as session:
                log_entry = TokenUsageLog(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    session_id=session_id,
                    model=model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    total_tokens=total_tokens,
                    cost_cny=Decimal(str(cost)),
                    created_at=datetime.now(timezone.utc),
                )
                session.add(log_entry)
                await session.commit()
        except Exception as e:
            logger.error("Failed to persist token usage to PostgreSQL", error=str(e))

        logger.debug(
            "Token usage tracked",
            user_id=user_id,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            cost_cny=cost,
        )

        return cost

    async def get_session_cost(self, session_id: str) -> float:
        """Get total cost for a session.

        Args:
            session_id: Session UUID

        Returns:
            Total cost in CNY
        """
        r = await self._get_redis()
        key = f"token_usage:session:{session_id}"
        cost = await r.hget(key, "total_cost")
        return float(cost or 0.0)

    async def check_budget(self, user_id: str, max_cost: float = 10.0) -> bool:
        """Check if user is within daily budget.

        Args:
            user_id: User ID
            max_cost: Maximum daily cost in CNY (default: ¥10)

        Returns:
            True if within budget, False if exceeded
        """
        r = await self._get_redis()
        date_str = datetime.now().strftime("%Y-%m-%d")
        key = f"token_usage:{user_id}:{date_str}"

        total_cost = await r.hget(key, "total_cost")
        current_cost = float(total_cost or 0.0)

        is_within_budget = current_cost < max_cost

        if not is_within_budget:
            logger.warning(
                "User budget exceeded",
                user_id=user_id,
                current_cost=current_cost,
                max_cost=max_cost,
            )

        return is_within_budget

    async def get_monthly_usage(
        self, user_id: str, year: Optional[int] = None, month: Optional[int] = None
    ) -> Dict:
        """Get user monthly token usage from PostgreSQL.

        Args:
            user_id: User ID
            year: Year (default: current year)
            month: Month (default: current month)

        Returns:
            Dict with monthly stats:
            {
                "total_tokens": int,
                "input_tokens": int,
                "output_tokens": int,
                "total_cost_cny": float,
                "request_count": int,
                "daily_breakdown": List[Dict]
            }
        """
        now = datetime.now()
        year = year or now.year
        month = month or now.month

        month_start = datetime(year, month, 1)
        if month == 12:
            month_end = datetime(year + 1, 1, 1)
        else:
            month_end = datetime(year, month + 1, 1)

        try:
            async with AsyncSessionLocal() as session:
                # Query daily aggregation using SQLAlchemy
                stmt = (
                    select(
                        func.date(TokenUsageLog.created_at).label("date"),
                        func.sum(TokenUsageLog.total_tokens).label("total_tokens"),
                        func.sum(TokenUsageLog.input_tokens).label("input_tokens"),
                        func.sum(TokenUsageLog.output_tokens).label("output_tokens"),
                        func.sum(TokenUsageLog.cost_cny).label("total_cost"),
                        func.count().label("request_count"),
                    )
                    .where(TokenUsageLog.user_id == user_id)
                    .where(TokenUsageLog.created_at >= month_start)
                    .where(TokenUsageLog.created_at < month_end)
                    .group_by(func.date(TokenUsageLog.created_at))
                    .order_by(func.date(TokenUsageLog.created_at))
                )
                result = await session.execute(stmt)
                rows = result.all()

                total_tokens = 0
                input_tokens = 0
                output_tokens = 0
                total_cost = 0.0
                request_count = 0
                daily_breakdown: List[Dict] = []

                for row in rows:
                    row_tokens = row.total_tokens or 0
                    row_input = row.input_tokens or 0
                    row_output = row.output_tokens or 0
                    row_cost = float(row.total_cost or 0)
                    row_count = row.request_count or 0

                    total_tokens += row_tokens
                    input_tokens += row_input
                    output_tokens += row_output
                    total_cost += row_cost
                    request_count += row_count

                    daily_breakdown.append(
                        {
                            "date": row.date.isoformat(),
                            "tokens": row_tokens,
                            "cost": row_cost,
                            "requests": row_count,
                        }
                    )

                return {
                    "total_tokens": total_tokens,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "total_cost_cny": total_cost,
                    "request_count": request_count,
                    "daily_breakdown": daily_breakdown,
                }

        except Exception as e:
            logger.error("Failed to get monthly token usage", error=str(e))
            return {
                "total_tokens": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "total_cost_cny": 0.0,
                "request_count": 0,
                "daily_breakdown": [],
            }


__all__ = ["TokenTracker"]
