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
        get_user_by_id,
        get_user_by_email,
        get_user_roles,
    )

Migration Notes:
    - Migrated from postgres_db (asyncpg) to SQLAlchemy ORM
    - Functions accept optional db: AsyncSession parameter
    - When db is None, creates a new session using AsyncSessionLocal
"""

from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from uuid import uuid4

from sqlalchemy import select, delete, insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.core.database import redis_db
from app.models import User as UserModel, Role, UserRole, RefreshToken
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


# =============================================================================
# Helper Classes and Functions
# =============================================================================


class User:
    """User DTO (Data Transfer Object) for authentication.

    This is a simple class used to transfer user data between
    the auth service and API routes. It provides a clean interface
    independent of the SQLAlchemy ORM model.

    Note: This is intentionally kept separate from the ORM model
    to avoid exposing database-specific details in the API layer.
    """

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


def _orm_to_user(orm_user: UserModel, role_names: List[str] = None) -> User:
    """Convert SQLAlchemy ORM User to DTO User.

    Args:
        orm_user: SQLAlchemy User model instance
        role_names: List of role names for the user

    Returns:
        User DTO instance
    """
    return User(
        id=str(orm_user.id),
        email=orm_user.email,
        name=orm_user.name,
        password_hash=orm_user.password_hash,
        email_verified=orm_user.email_verified,
        avatar=orm_user.avatar,
        created_at=orm_user.created_at,
        updated_at=orm_user.updated_at,
        roles=role_names or [],
    )


async def _get_session(db: Optional[AsyncSession]) -> AsyncSession:
    """Get or create a database session.

    If db is provided, returns it directly.
    Otherwise, creates a new session using AsyncSessionLocal.

    Args:
        db: Optional existing session

    Returns:
        AsyncSession to use for database operations
    """
    if db is not None:
        return db
    return AsyncSessionLocal()


# =============================================================================
# Role Management
# =============================================================================


async def get_user_roles(
    user_id: str,
    db: Optional[AsyncSession] = None,
) -> List[str]:
    """Get roles for a user.

    Args:
        user_id: User ID
        db: Optional database session

    Returns:
        List of role names
    """
    session = await _get_session(db)
    should_commit = db is None

    try:
        # Query roles through UserRole join
        stmt = (
            select(Role.name)
            .join(UserRole, Role.id == UserRole.role_id)
            .where(UserRole.user_id == user_id)
        )
        result = await session.execute(stmt)
        role_names = [row[0] for row in result.all()]

        if should_commit:
            await session.commit()

        return role_names

    except Exception as e:
        if should_commit:
            await session.rollback()
        logger.error("Failed to get user roles", user_id=user_id, error=str(e))
        raise
    finally:
        if should_commit:
            await session.close()


# =============================================================================
# User Registration
# =============================================================================


async def register_user(
    email: str,
    password: str,
    name: str,
    db: Optional[AsyncSession] = None,
) -> User:
    """Register a new user.

    Args:
        email: User email
        password: Plain text password
        name: User display name
        db: Optional database session for transaction control

    Returns:
        Created User DTO object

    Raises:
        ValueError: If email already exists or validation fails
    """
    session = await _get_session(db)
    should_commit = db is None

    try:
        # Check if email already exists
        stmt = select(UserModel.id).where(UserModel.email == email)
        result = await session.execute(stmt)
        existing = result.scalar_one_or_none()

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
        # Database uses TIMESTAMP WITHOUT TIME ZONE, so use naive datetime
        now = datetime.now()

        new_user = UserModel(
            id=user_id,
            email=email,
            name=name,
            password_hash=password_hash,
            email_verified=True,  # email_verified default True for MVP
            created_at=now,
            updated_at=now,
        )
        session.add(new_user)

        # Find 'user' role
        role_stmt = select(Role).where(Role.name == "user")
        role_result = await session.execute(role_stmt)
        role = role_result.scalar_one_or_none()

        if role:
            # Assign default 'user' role
            user_role = UserRole(
                id=str(uuid4()),
                user_id=user_id,
                role_id=role.id,
            )
            session.add(user_role)

        if should_commit:
            await session.commit()

        logger.info("User registered", user_id=user_id, email=email)

        # Return user with roles
        roles = await get_user_roles(user_id, session if not should_commit else None)
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

    except ValueError:
        if should_commit:
            await session.rollback()
        raise
    except Exception as e:
        if should_commit:
            await session.rollback()
        logger.error("User registration failed", email=email, error=str(e))
        raise ValueError("Registration failed") from e
    finally:
        if should_commit:
            await session.close()


# =============================================================================
# User Authentication
# =============================================================================


async def authenticate_user(
    email: str,
    password: str,
    db: Optional[AsyncSession] = None,
) -> Optional[User]:
    """Authenticate a user by email and password.

    Args:
        email: User email
        password: Plain text password
        db: Optional database session

    Returns:
        User DTO if authenticated, None otherwise
    """
    session = await _get_session(db)
    should_commit = db is None

    try:
        # Find user by email
        stmt = select(UserModel).where(UserModel.email == email)
        result = await session.execute(stmt)
        orm_user = result.scalar_one_or_none()

        if not orm_user:
            logger.warning("User not found", email=email)
            return None

        # Verify password
        if not verify_password(password, orm_user.password_hash):
            logger.warning("Invalid password", email=email)
            return None

        if should_commit:
            await session.commit()

        # Get user roles
        roles = await get_user_roles(
            orm_user.id, session if not should_commit else None
        )

        return _orm_to_user(orm_user, roles)

    except Exception as e:
        if should_commit:
            await session.rollback()
        logger.error("Authentication failed", email=email, error=str(e))
        return None
    finally:
        if should_commit:
            await session.close()


# =============================================================================
# Token Management
# =============================================================================


async def create_user_tokens(
    user: User,
    db: Optional[AsyncSession] = None,
) -> Dict[str, Any]:
    """Create access and refresh tokens for a user.

    Args:
        user: User DTO object
        db: Optional database session

    Returns:
        Dictionary with access_token, refresh_token, and refresh_jti
    """
    # Create access token with user info
    access_token = create_access_token(
        {
            "sub": user.id,
            "email": user.email,
            "roles": user.roles,
            "jti": str(uuid4()),
        }
    )

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
    session = await _get_session(db)
    should_commit = db is None

    try:
        expires_at = datetime.now(timezone.utc) + timedelta(days=7)
        refresh_token_record = RefreshToken(
            id=refresh_jti,
            token_hash=refresh_token,  # Note: In production, should hash the token
            user_id=user.id,
            expires_at=expires_at,
            created_at=datetime.now(timezone.utc),
        )
        session.add(refresh_token_record)

        if should_commit:
            await session.commit()

    except Exception as e:
        if should_commit:
            await session.rollback()
        logger.error("Failed to store refresh token", user_id=user.id, error=str(e))
        # Continue anyway - Redis storage is the primary mechanism
    finally:
        if should_commit:
            await session.close()

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "refresh_jti": refresh_jti,
    }


async def refresh_access_token(
    refresh_token: str,
    db: Optional[AsyncSession] = None,
) -> Optional[Dict[str, Any]]:
    """Refresh access token using refresh token.

    Args:
        refresh_token: Refresh token string
        db: Optional database session

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

        redis_client = redis_db.client
        if not redis_client:
            logger.error("Redis unavailable during token refresh (fail-closed)")
            raise ValueError("Authentication service temporarily unavailable")

        # Check if token is blacklisted in Redis
        blacklisted = await redis_client.exists(f"blacklist:{jti}")
        if blacklisted:
            logger.warning("Blacklisted refresh token used", jti=jti)
            raise ValueError("Token has been revoked")

        # Check if token exists in Redis (valid session)
        exists = await redis_client.exists(f"refresh:{user_id}:{jti}")
        if not exists:
            logger.warning("Refresh token not found in Redis", jti=jti)
            raise ValueError("Token has been revoked or expired")

        # Get user from database
        session = await _get_session(db)
        should_commit = db is None

        try:
            stmt = select(UserModel).where(UserModel.id == user_id)
            result = await session.execute(stmt)
            orm_user = result.scalar_one_or_none()

            if not orm_user:
                raise ValueError("User not found")

            # Get user roles
            roles = await get_user_roles(
                user_id, session if not should_commit else None
            )
            user = _orm_to_user(orm_user, roles)

            # Create new tokens
            new_tokens = await create_user_tokens(
                user, session if not should_commit else None
            )

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
            delete_stmt = delete(RefreshToken).where(RefreshToken.id == jti)
            await session.execute(delete_stmt)

            if should_commit:
                await session.commit()

            logger.info("Token refreshed", user_id=user_id)

            return new_tokens

        except ValueError:
            if should_commit:
                await session.rollback()
            raise
        except Exception as e:
            if should_commit:
                await session.rollback()
            logger.error("Token refresh database error", error=str(e))
            raise ValueError("Token refresh failed") from e
        finally:
            if should_commit:
                await session.close()

    except ValueError:
        raise
    except Exception as e:
        logger.error("Token refresh failed", error=str(e))
        raise ValueError("Token refresh failed") from e


async def logout_user(
    access_token: Optional[str],
    refresh_token: Optional[str],
    db: Optional[AsyncSession] = None,
) -> None:
    """Logout user by blacklisting tokens.

    Args:
        access_token: Access token to blacklist
        refresh_token: Refresh token to blacklist
        db: Optional database session
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
                session = await _get_session(db)
                should_commit = db is None

                try:
                    delete_stmt = delete(RefreshToken).where(RefreshToken.id == jti)
                    await session.execute(delete_stmt)

                    if should_commit:
                        await session.commit()

                    logger.info("Refresh token blacklisted", jti=jti)

                except Exception as e:
                    if should_commit:
                        await session.rollback()
                    logger.warning(
                        "Failed to delete refresh token from db", error=str(e)
                    )
                finally:
                    if should_commit:
                        await session.close()

        except Exception as e:
            logger.warning("Failed to blacklist refresh token", error=str(e))


# =============================================================================
# User Retrieval
# =============================================================================


async def get_user_by_id(
    user_id: str,
    db: Optional[AsyncSession] = None,
) -> Optional[User]:
    """Get user by ID.

    Args:
        user_id: User ID
        db: Optional database session

    Returns:
        User DTO or None if not found
    """
    session = await _get_session(db)
    should_commit = db is None

    try:
        stmt = select(UserModel).where(UserModel.id == user_id)
        result = await session.execute(stmt)
        orm_user = result.scalar_one_or_none()

        if not orm_user:
            return None

        if should_commit:
            await session.commit()

        roles = await get_user_roles(
            orm_user.id, session if not should_commit else None
        )
        return _orm_to_user(orm_user, roles)

    except Exception as e:
        if should_commit:
            await session.rollback()
        logger.error("Failed to get user by id", user_id=user_id, error=str(e))
        return None
    finally:
        if should_commit:
            await session.close()


async def get_user_by_email(
    email: str,
    db: Optional[AsyncSession] = None,
) -> Optional[User]:
    """Get user by email.

    Args:
        email: User email
        db: Optional database session

    Returns:
        User DTO or None if not found
    """
    session = await _get_session(db)
    should_commit = db is None

    try:
        stmt = select(UserModel).where(UserModel.email == email)
        result = await session.execute(stmt)
        orm_user = result.scalar_one_or_none()

        if not orm_user:
            return None

        if should_commit:
            await session.commit()

        roles = await get_user_roles(
            orm_user.id, session if not should_commit else None
        )
        return _orm_to_user(orm_user, roles)

    except Exception as e:
        if should_commit:
            await session.rollback()
        logger.error("Failed to get user by email", email=email, error=str(e))
        return None
    finally:
        if should_commit:
            await session.close()


# =============================================================================
# Exports
# =============================================================================

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
