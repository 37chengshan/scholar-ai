#!/usr/bin/env python3
"""Ensure a dedicated PR19 E2E test user exists and can log in.

Usage:
    cd apps/api
    .venv/bin/python scripts/ensure_e2e_test_user.py
"""

import argparse
import json
from datetime import datetime
from pathlib import Path
import sys

API_ROOT = Path(__file__).resolve().parents[1]
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.user import Role, User as UserModel, UserRole
from app.services.auth_service import register_user
from app.utils.security import get_password_hash

DEFAULT_EMAIL = "pr19-e2e@example.com"
DEFAULT_PASSWORD = "Pr19E2EPass123"
DEFAULT_NAME = "PR19 E2E Dedicated User"


async def _ensure_user_role(session, user_id: str) -> bool:
    """Ensure the user has the default 'user' role."""
    role_stmt = select(Role).where(Role.name == "user")
    role_result = await session.execute(role_stmt)
    role = role_result.scalar_one_or_none()

    if role is None:
        return False

    user_role_stmt = select(UserRole.id).where(
        UserRole.user_id == user_id,
        UserRole.role_id == role.id,
    )
    user_role_result = await session.execute(user_role_stmt)
    if user_role_result.scalar_one_or_none() is None:
        session.add(UserRole(user_id=user_id, role_id=role.id))

    return True


async def ensure_test_user(email: str, password: str, name: str) -> dict:
    """Create or update dedicated E2E user and return result summary."""
    normalized_email = email.lower().strip()

    async with AsyncSessionLocal() as session:
        stmt = select(UserModel).where(UserModel.email == normalized_email)
        result = await session.execute(stmt)
        existing_user = result.scalar_one_or_none()

        if existing_user is None:
            created_user = await register_user(
                email=normalized_email,
                password=password,
                name=name,
                db=session,
            )
            await session.commit()
            return {
                "action": "created",
                "user_id": created_user.id,
                "email": created_user.email,
                "name": created_user.name,
            }

        existing_user.name = name
        existing_user.password_hash = get_password_hash(password)
        existing_user.email_verified = True
        existing_user.updated_at = datetime.now()
        role_attached = await _ensure_user_role(session, existing_user.id)

        await session.commit()
        return {
            "action": "updated",
            "user_id": existing_user.id,
            "email": existing_user.email,
            "name": existing_user.name,
            "role_attached": role_attached,
        }


async def _main() -> None:
    parser = argparse.ArgumentParser(
        description="Create or update the dedicated PR19 E2E test user"
    )
    parser.add_argument("--email", default=DEFAULT_EMAIL)
    parser.add_argument("--password", default=DEFAULT_PASSWORD)
    parser.add_argument("--name", default=DEFAULT_NAME)
    args = parser.parse_args()

    result = await ensure_test_user(args.email, args.password, args.name)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    import asyncio

    asyncio.run(_main())
