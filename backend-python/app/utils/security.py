"""Security utilities for authentication.

Provides password hashing with Argon2id and JWT token handling.
Matches Node.js implementation for password hash compatibility.

Usage:
    from app.utils.security import (
        get_password_hash,
        verify_password,
        create_access_token,
        create_refresh_token,
        verify_token,
    )
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
from uuid import uuid4

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHashError

from app.core.config import settings
from app.utils.logger import logger


# Argon2id password hasher with secure defaults
# Parameters match Node.js crypto.ts OWASP 2023 recommended settings
ph = PasswordHasher(
    time_cost=3,       # 3 iterations
    memory_cost=65536, # 64 MB
    parallelism=4,     # 4 parallel threads
    hash_len=32,       # 32 bytes hash length
    salt_len=16,       # 16 bytes salt length
)


def get_password_hash(password: str) -> str:
    """Hash a password using Argon2id.

    Args:
        password: Plain text password

    Returns:
        Argon2id hash string

    Example:
        >>> hash = get_password_hash("my_password")
        >>> # Returns something like: $argon2id$v=19$m=65536,t=3,p=4$...
    """
    try:
        return ph.hash(password)
    except Exception as e:
        logger.error("Failed to hash password", error=str(e))
        raise ValueError("Failed to hash password") from e


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against an Argon2id hash.

    Uses constant-time comparison internally to prevent timing attacks.

    Args:
        plain_password: Plain text password to verify
        hashed_password: Stored Argon2id hash

    Returns:
        True if password matches, False otherwise

    Example:
        >>> hash = get_password_hash("my_password")
        >>> verify_password("my_password", hash)
        True
        >>> verify_password("wrong_password", hash)
        False
    """
    try:
        ph.verify(hashed_password, plain_password)
        return True
    except VerifyMismatchError:
        # Password does not match
        return False
    except (VerificationError, InvalidHashError) as e:
        # Invalid hash format or other verification error
        logger.warning("Password verification error", error=str(e))
        return False
    except Exception as e:
        logger.error("Unexpected error during password verification", error=str(e))
        return False


def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None
) -> str:
    """Create a JWT access token.

    Args:
        data: Payload data to encode in the token
        expires_delta: Optional custom expiration time

    Returns:
        JWT access token string

    The token includes:
        - 'exp': Expiration timestamp
        - 'iat': Issued at timestamp
        - 'type': 'access' token type
        - 'jti': Unique token identifier for blacklisting

    Example:
        >>> token = create_access_token({"sub": "user-123", "email": "test@example.com"})
        >>> # Returns JWT string
    """
    to_encode = data.copy()

    # Set expiration
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    # Add standard claims
    now = datetime.now(timezone.utc)
    to_encode.update({
        "exp": expire,
        "iat": now,
        "type": "access",
    })

    # Add jti if not present (for blacklisting)
    if "jti" not in to_encode:
        to_encode["jti"] = str(uuid4())

    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM
    )

    return encoded_jwt


def create_refresh_token(user_id: str) -> Tuple[str, str]:
    """Create a JWT refresh token with jti for rotation.

    Args:
        user_id: User ID to associate with the token

    Returns:
        Tuple of (token_string, jti) where jti is the unique identifier
        for token blacklisting during rotation.

    Example:
        >>> token, jti = create_refresh_token("user-123")
        >>> # token is the JWT string
        >>> # jti is the unique identifier for blacklisting
    """
    jti = str(uuid4())
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )

    to_encode = {
        "sub": user_id,
        "jti": jti,
        "type": "refresh",
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }

    token = jwt.encode(
        to_encode,
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM
    )

    return token, jti


def verify_token(token: str, token_type: str = "access") -> dict:
    """Verify and decode a JWT token.

    Args:
        token: JWT token string
        token_type: Expected token type ('access' or 'refresh')

    Returns:
        Decoded token payload as dictionary

    Raises:
        HTTPException: If token is invalid, expired, or type mismatch

    Example:
        >>> payload = verify_token(token, "access")
        >>> user_id = payload["sub"]
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM]
        )

        # Verify token type
        if payload.get("type") != token_type:
            logger.warning(
                "Token type mismatch",
                expected=token_type,
                actual=payload.get("type")
            )
            raise ValueError(f"Expected {token_type} token, got {payload.get('type')}")

        return payload

    except jwt.ExpiredSignatureError as e:
        logger.warning("Token expired", error=str(e))
        raise ValueError("Token has expired") from e
    except jwt.InvalidTokenError as e:
        logger.warning("Invalid token", error=str(e))
        raise ValueError("Invalid token") from e


def decode_token_unsafe(token: str) -> Optional[dict]:
    """Decode a token without verification (for debugging/inspection).

    WARNING: This does NOT verify the signature. Do not use for authentication.

    Args:
        token: JWT token string

    Returns:
        Decoded payload or None if invalid format
    """
    try:
        # Decode without verification
        return jwt.decode(
            token,
            options={"verify_signature": False}
        )
    except Exception as e:
        logger.warning("Failed to decode token", error=str(e))
        return None


def get_token_expiry_seconds(token: str) -> int:
    """Get remaining seconds until token expires.

    Args:
        token: JWT token string

    Returns:
        Remaining seconds until expiry, or 0 if expired/invalid
    """
    try:
        payload = decode_token_unsafe(token)
        if not payload or "exp" not in payload:
            return 0

        exp_timestamp = payload["exp"]
        now_timestamp = datetime.now(timezone.utc).timestamp()

        remaining = int(exp_timestamp - now_timestamp)
        return max(0, remaining)

    except Exception:
        return 0


__all__ = [
    "get_password_hash",
    "verify_password",
    "create_access_token",
    "create_refresh_token",
    "verify_token",
    "decode_token_unsafe",
    "get_token_expiry_seconds",
]