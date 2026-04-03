"""Token usage tracker for cost monitoring.

Tracks LLM token usage and costs per user/session.
Supports budget limits and cost calculations.

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

from datetime import datetime
from typing import Optional

import redis.asyncio as redis

from app.core.config import settings
from app.utils.logger import logger


class TokenTracker:
    """Track LLM token usage and costs.
    
    Attributes:
        PRICING: Cost per 1M tokens for each model
        redis: Redis client for storage
    """
    
    # GLM-4.5-Air pricing (per 1M tokens)
    PRICING = {
        "glm-4.5-air": {
            "input": 0.5,   # ¥0.5 per 1M input tokens
            "output": 0.5   # ¥0.5 per 1M output tokens
        }
    }
    
    def __init__(self):
        """Initialize TokenTracker with Redis client."""
        self.redis: Optional[redis.Redis] = None
    
    async def _get_redis(self) -> redis.Redis:
        """Get or create Redis client.
        
        Returns:
            Redis client instance
        """
        if not self.redis:
            self.redis = redis.from_url(
                settings.REDIS_URL,
                decode_responses=True
            )
        return self.redis
    
    async def track_usage(
        self,
        user_id: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        session_id: Optional[str] = None
    ) -> float:
        """Track token usage and return cost in CNY.
        
        Args:
            user_id: User ID
            model: Model name (e.g., 'glm-4.5-air')
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            session_id: Optional session ID for session-level tracking
            
        Returns:
            Cost in CNY
            
        Example:
            >>> tracker = TokenTracker()
            >>> cost = await tracker.track_usage(
            ...     user_id="user-123",
            ...     model="glm-4.5-air",
            ...     input_tokens=1000,
            ...     output_tokens=500
            ... )
            >>> print(f"Cost: ¥{cost}")
        """
        # Get pricing for model
        pricing = self.PRICING.get(model)
        if not pricing:
            logger.warning(f"No pricing found for model {model}")
            return 0.0
        
        # Calculate cost
        cost = (
            input_tokens / 1_000_000 * pricing["input"] +
            output_tokens / 1_000_000 * pricing["output"]
        )
        
        # Get Redis client
        r = await self._get_redis()
        
        # Store daily user usage
        date_str = datetime.now().strftime('%Y-%m-%d')
        user_key = f"token_usage:{user_id}:{date_str}"
        
        await r.hincrbyfloat(user_key, "total_cost", cost)
        await r.hincrby(user_key, "input_tokens", input_tokens)
        await r.hincrby(user_key, "output_tokens", output_tokens)
        await r.expire(user_key, 86400 * 30)  # 30 days TTL
        
        # Store session usage if session_id provided
        if session_id:
            session_key = f"token_usage:session:{session_id}"
            await r.hincrbyfloat(session_key, "total_cost", cost)
            await r.expire(session_key, 86400 * 7)  # 7 days TTL
        
        logger.debug(
            "Token usage tracked",
            user_id=user_id,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_cny=cost
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
    
    async def check_budget(
        self,
        user_id: str,
        max_cost: float = 10.0
    ) -> bool:
        """Check if user is within daily budget.
        
        Args:
            user_id: User ID
            max_cost: Maximum daily cost in CNY (default: ¥10)
            
        Returns:
            True if within budget, False if exceeded
        """
        r = await self._get_redis()
        date_str = datetime.now().strftime('%Y-%m-%d')
        key = f"token_usage:{user_id}:{date_str}"
        
        total_cost = await r.hget(key, "total_cost")
        current_cost = float(total_cost or 0.0)
        
        is_within_budget = current_cost < max_cost
        
        if not is_within_budget:
            logger.warning(
                "User budget exceeded",
                user_id=user_id,
                current_cost=current_cost,
                max_cost=max_cost
            )
        
        return is_within_budget


__all__ = ["TokenTracker"]