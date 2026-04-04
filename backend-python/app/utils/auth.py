"""JWT authentication utility.

Provides JWT token validation for API endpoints.

Usage:
    from app.utils.auth import validate_jwt_token
    
    user_id = await validate_jwt_token(token)
"""

from typing import Optional

from jose import JWTError, jwt

from app.core.config import settings
from app.utils.logger import logger


async def validate_jwt_token(token: str) -> Optional[str]:
    """Validate JWT token and return user_id.
    
    Args:
        token: JWT token string
        
    Returns:
        User ID if valid, None if invalid
        
    Example:
        >>> user_id = await validate_jwt_token("eyJhbGciOiJIUzI1NiIs...")
        >>> if user_id:
        ...     # Token is valid
        ...     pass
    """
    try:
        # Debug logging - print FULL token and secret for comparison
        logger.info(
            "Validating JWT token",
            token_full=token,
            jwt_secret_full=settings.JWT_SECRET,
            jwt_algorithm=settings.JWT_ALGORITHM
        )
        
        # Decode JWT
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM]
        )
        
        # Extract user_id from 'sub' claim
        user_id: str = payload.get("sub")
        
        if user_id is None:
            logger.warning("JWT token missing 'sub' claim")
            return None
        
        logger.debug("JWT token validated", user_id=user_id)
        return user_id
        
    except JWTError as e:
        logger.warning(
            "JWT validation failed",
            error=str(e),
            jwt_secret_used=settings.JWT_SECRET,
            token_received=token
        )
        return None
    except Exception as e:
        logger.error("Unexpected error during JWT validation", error=str(e))
        return None


__all__ = ["validate_jwt_token"]