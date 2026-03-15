"""内部服务JWT认证

用于验证来自Node.js API Gateway的RS256 JWT令牌
"""

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.config import settings

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
