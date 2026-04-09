"""Authentication dependencies for Python FastAPI endpoints.

Provides two authentication modes:
1. Service-to-service auth: RS256 JWT verification (existing)
2. User authentication: X-User-ID header pass-through from Node.js Gateway (new)

Architecture Decision D-01:
    - Node.js Gateway validates JWT tokens for user authentication
    - Node.js passes verified user_id via X-User-ID header to Python
    - Python service trusts X-User-ID header from Node.js
    - No user JWT validation in Python (avoid duplication, reduce latency)
    - Service-to-service auth still uses RS256 JWT for internal communication

Usage for user endpoints:
    from app.core.auth import CurrentUserId

    @router.get("/protected")
    async def protected_endpoint(user_id: str = CurrentUserId):
        # user_id is guaranteed to be authenticated
        return {"user_id": user_id}

Usage for internal service endpoints:
    from app.core.auth import get_current_service

    @router.get("/internal")
    async def internal_endpoint(service: dict = Depends(get_current_service)):
        return {"service": service["sub"]}
"""

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.config import settings
from app.utils.user_context import get_current_user_id, require_user_id

security = HTTPBearer()


def verify_internal_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """验证来自Node.js Gateway的RS256 JWT

    Args:
        credentials: HTTP Bearer token

    Returns:
        dict: JWT payload包含sub, aud, exp, iat, jti等声明

    Raises:
        HTTPException: 401 当token无效、过期或验证失败
    """
    token = credentials.credentials

    try:
        # 从环境变量加载公钥
        if not settings.JWT_INTERNAL_PUBLIC_KEY:
            raise HTTPException(
                status_code=401,
                detail="JWT public key not configured"
            )

        # 加载PEM格式公钥
        public_key = serialization.load_pem_public_key(
            settings.JWT_INTERNAL_PUBLIC_KEY.encode(),
            backend=default_backend()
        )

        # 验证JWT
        payload = jwt.decode(
            token,
            public_key,
            algorithms=['RS256'],
            audience='python-ai-service',
            options={
                'require': ['exp', 'iat', 'sub', 'aud']
            }
        )

        return payload

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=401,
            detail="Token expired"
        )
    except jwt.InvalidAudienceError:
        raise HTTPException(
            status_code=401,
            detail="Invalid audience"
        )
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=401,
            detail=f"Invalid token: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=401,
            detail=f"Token verification failed: {str(e)}"
        )


async def get_current_service(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """FastAPI依赖: 验证内部服务token

    Usage:
        @router.get("/protected")
        async def protected_endpoint(service: dict = Depends(get_current_service)):
            return {"service": service["sub"]}
    """
    return verify_internal_token(credentials)


# =============================================================================
# User Authentication Dependencies (from X-User-ID header)
# =============================================================================

# Convenience dependency for user endpoints
# Usage: async def endpoint(user_id: str = CurrentUserId):
CurrentUserId = Depends(get_current_user_id)

# Alias for backwards compatibility
RequireUserId = Depends(require_user_id)


__all__ = [
    "verify_internal_token",
    "get_current_service",
    "get_current_user_id",
    "require_user_id",
    "CurrentUserId",
    "RequireUserId",
]
