"""Authentication service layer.

Provides business logic for user authentication:
- User registration
- User authentication
- Token management
- Token refresh
- Logout

Usage:
    from app.services.auth_service import (
        register_user,
        authenticate_user,
        create_user_tokens,
        refresh_access_token,
        logout_user,
    )
"""

from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from uuid import uuid4

from app.core.database import postgres_db, redis_db
from app.utils.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    create_refresh_token,
    verify_token,
    get_token_expiry_seconds,
)
from app.utils.logger import logger
from app.utils.problem_detail import ProblemDetail, ErrorTypes


class User:
    """User model for type hints."""

    def __init__(
        self,
        id: str,
        email: str,
        name: str,
        password_hash: str,
        email_verified: bool = False,
        avatar: Optional[str] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        roles: Optional[List[str]] = None,
    ):
        self.id = id
        self.email = email
        self.name = name
        self.password_hash = password_hash
        self.email_verified = email_verified
        self.avatar = avatar
        self.created_at = created_at
        self.updated_at = updated_at
        self.roles = roles or []


def _row_to_user(row: dict, roles: List[str] = None) -> User:
    """Convert database row to User object."""
    return User(
        id=row["id"],
        email=row["email"],
        name=row["name"],
        password_hash=row["password_hash"],
        email_verified=row.get("email_verified", False),
        avatar=row.get("avatar"),
        created_at=row.get("created_at"),
        updated_at=row.get("updated_at"),
        roles=roles or [],
    )


async def get_user_roles(user_id: str) -> List[str]:
    """Get roles for a user.

    Args:
        user_id: User ID

    Returns:
        List of role names
    """
    query = """
        SELECT r.name
        FROM roles r
        JOIN user_roles ur ON r.id = ur.role_id
        WHERE ur.user_id = $1
    """
    rows = await postgres_db.fetch(query, user_id)
    return [row["name"] for row in rows]


async def register_user(
    email: str,
    password: str,
    name: str,
) -> User:
    """Register a new user.

    Args:
        email: User email
        password: Plain text password
        name: User display name

    Returns:
        Created User object

    Raises:
        ValueError: If email already exists or validation fails
    """
    # Check if email already exists
    existing = await postgres_db.fetchrow(
        "SELECT id FROM users WHERE email = $1",
        email
    )
    if existing:
        raise ValueError("Email already registered")

    # Validate inputs
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters")
    if len(name) < 2:
        raise ValueError("Name must be at least 2 characters")

    # Create user
    user_id = str(uuid4())
    password_hash = get_password_hash(password)
    now = datetime.now(timezone.utc)

    await postgres_db.execute(
        """
        INSERT INTO users (id, email, name, password_hash, email_verified, created_at, updated_at)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        """,
        user_id,
        email,
        name,
        password_hash,
        True,  # email_verified default True for MVP
        now,
        now,
    )

    # Assign default 'user' role
    role_row = await postgres_db.fetchrow(
        "SELECT id FROM roles WHERE name = $1",
        "user"
    )
    if role_row:
        await postgres_db.execute(
            """
            INSERT INTO user_roles (id, user_id, role_id)
            VALUES ($1, $2, $3)
            """,
            str(uuid4()),
            user_id,
            role_row["id"],
        )

    logger.info("User registered", user_id=user_id, email=email)

    # Return user with roles
    roles = await get_user_roles(user_id)
    return User(
        id=user_id,
        email=email,
        name=name,
        password_hash=password_hash,
        email_verified=True,
        created_at=now,
        updated_at=now,
        roles=roles,
    )


async def authenticate_user(
    email: str,
    password: str,
) -> Optional[User]:
    """Authenticate a user by email and password.

    Args:
        email: User email
        password: Plain text password

    Returns:
        User object if authenticated, None otherwise
    """
    # Find user by email
    row = await postgres_db.fetchrow(
        """
        SELECT id, email, name, password_hash, email_verified, avatar, created_at, updated_at
        FROM users
        WHERE email = $1
        """,
        email
    )

    if not row:
        logger.warning("User not found", email=email)
        return None

    # Verify password
    if not verify_password(password, row["password_hash"]):
        logger.warning("Invalid password", email=email)
        return None

    # Get user roles
    roles = await get_user_roles(row["id"])

    return _row_to_user(dict(row), roles)


async def create_user_tokens(user: User) -> Dict[str, Any]:
    """Create access and refresh tokens for a user.

    Args:
        user: User object

    Returns:
        Dictionary with access_token, refresh_token, and refresh_jti
    """
    # Create access token with user info
    access_token = create_access_token({
        "sub": user.id,
        "email": user.email,
        "roles": user.roles,
        "jti": str(uuid4()),
    })

    # Create refresh token
    refresh_token, refresh_jti = create_refresh_token(user.id)

    # Store refresh token in Redis
    redis_client = redis_db.client
    if redis_client:
        await redis_client.set(
            f"refresh:{user.id}:{refresh_jti}",
            user.id,
            ex=7 * 24 * 60 * 60,  # 7 days
        )

    # Store refresh token in database
    await postgres_db.execute(
        """
        INSERT INTO refresh_tokens (id, token, user_id, expires_at, created_at)
        VALUES ($1, $2, $3, $4, $5)
        """,
        refresh_jti,
        refresh_token,
        user.id,
        datetime.now(timezone.utc).replace(
            day=datetime.now(timezone.utc).day + 7
        ),
        datetime.now(timezone.utc),
    )

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "refresh_jti": refresh_jti,
    }


async def refresh_access_token(
    refresh_token: str,
) -> Optional[Dict[str, Any]]:
    """Refresh access token using refresh token.

    Args:
        refresh_token: Refresh token string

    Returns:
        New tokens dictionary or None if invalid

    Raises:
        ValueError: If token is invalid or revoked
    """
    try:
        # Verify refresh token
        payload = verify_token(refresh_token, "refresh")
        user_id = payload.get("sub")
        jti = payload.get("jti")

        if not user_id or not jti:
            raise ValueError("Invalid token payload")

        # Check if token is blacklisted in Redis
        redis_client = redis_db.client
        if redis_client:
            blacklisted = await redis_client.exists(f"blacklist:{jti}")
            if blacklisted:
                logger.warning("Blacklisted refresh token used", jti=jti)
                raise ValueError("Token has been revoked")

        # Check if token exists in Redis (valid session)
        if redis_client:
            exists = await redis_client.exists(f"refresh:{user_id}:{jti}")
            if not exists:
                logger.warning("Refresh token not found in Redis", jti=jti)
                raise ValueError("Token has been revoked or expired")

        # Get user from database
        row = await postgres_db.fetchrow(
            """
            SELECT id, email, name, password_hash, email_verified, avatar, created_at, updated_at
            FROM users
            WHERE id = $1
            """,
            user_id
        )

        if not row:
            raise ValueError("User not found")

        # Get user roles
        roles = await get_user_roles(user_id)
        user = _row_to_user(dict(row), roles)

        # Create new tokens
        new_tokens = await create_user_tokens(user)

        # Blacklist old refresh token
        if redis_client:
            ttl = get_token_expiry_seconds(refresh_token)
            await redis_client.set(
                f"blacklist:{jti}",
                "revoked",
                ex=max(ttl, 1),
            )
            # Remove old refresh token from Redis
            await redis_client.delete(f"refresh:{user_id}:{jti}")

        # Delete old refresh token from database
        await postgres_db.execute(
            "DELETE FROM refresh_tokens WHERE id = $1",
            jti,
        )

        logger.info("Token refreshed", user_id=user_id)

        return new_tokens

    except ValueError:
        raise
    except Exception as e:
        logger.error("Token refresh failed", error=str(e))
        raise ValueError("Token refresh failed") from e


async def logout_user(
    access_token: Optional[str],
    refresh_token: Optional[str],
) -> None:
    """Logout user by blacklisting tokens.

    Args:
        access_token: Access token to blacklist
        refresh_token: Refresh token to blacklist
    """
    redis_client = redis_db.client

    # Blacklist access token
    if access_token:
        try:
            from app.utils.security import decode_token_unsafe
            payload = decode_token_unsafe(access_token)
            if payload and "jti" in payload:
                jti = payload["jti"]
                ttl = get_token_expiry_seconds(access_token)
                if redis_client:
                    await redis_client.set(
                        f"blacklist:{jti}",
                        "revoked",
                        ex=max(ttl, 1),
                    )
                logger.info("Access token blacklisted", jti=jti)
        except Exception as e:
            logger.warning("Failed to blacklist access token", error=str(e))

    # Blacklist refresh token
    if refresh_token:
        try:
            payload = verify_token(refresh_token, "refresh")
            jti = payload.get("jti")
            user_id = payload.get("sub")

            if jti:
                if redis_client:
                    ttl = get_token_expiry_seconds(refresh_token)
                    await redis_client.set(
                        f"blacklist:{jti}",
                        "revoked",
                        ex=max(ttl, 1),
                    )
                    # Remove from valid refresh tokens
                    if user_id:
                        await redis_client.delete(f"refresh:{user_id}:{jti}")

                # Delete from database
                await postgres_db.execute(
                    "DELETE FROM refresh_tokens WHERE id = $1",
                    jti,
                )
                logger.info("Refresh token blacklisted", jti=jti)

        except Exception as e:
            logger.warning("Failed to blacklist refresh token", error=str(e))


async def get_user_by_id(user_id: str) -> Optional[User]:
    """Get user by ID.

    Args:
        user_id: User ID

    Returns:
        User object or None if not found
    """
    row = await postgres_db.fetchrow(
        """
        SELECT id, email, name, password_hash, email_verified, avatar, created_at, updated_at
        FROM users
        WHERE id = $1
        """,
        user_id
    )

    if not row:
        return None

    roles = await get_user_roles(user_id)
    return _row_to_user(dict(row), roles)


async def get_user_by_email(email: str) -> Optional[User]:
    """Get user by email.

    Args:
        email: User email

    Returns:
        User object or None if not found
    """
    row = await postgres_db.fetchrow(
        """
        SELECT id, email, name, password_hash, email_verified, avatar, created_at, updated_at
        FROM users
        WHERE email = $1
        """,
        email
    )

    if not row:
        return None

    roles = await get_user_roles(row["id"])
    return _row_to_user(dict(row), roles)


__all__ = [
    "User",
    "register_user",
    "authenticate_user",
    "create_user_tokens",
    "refresh_access_token",
    "logout_user",
    "get_user_by_id",
    "get_user_by_email",
    "get_user_roles",
]