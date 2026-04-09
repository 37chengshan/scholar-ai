"""Service layer for business logic.

Services encapsulate business logic and coordinate between
API routes, database, and external services.

Per D-04: Service layer for business logic separation.
"""

from app.services.auth_service import (
    User,
    register_user,
    authenticate_user,
    create_user_tokens,
    refresh_access_token,
    logout_user,
    get_user_by_id,
    get_user_by_email,
    get_user_roles,
)
from app.services.paper_service import PaperService
from app.services.storage_service import StorageService, get_storage_service
from app.services.task_service import TaskService, PROGRESS_STAGES


__all__ = [
    # Auth service
    "User",
    "register_user",
    "authenticate_user",
    "create_user_tokens",
    "refresh_access_token",
    "logout_user",
    "get_user_by_id",
    "get_user_by_email",
    "get_user_roles",
    # Paper service
    "PaperService",
    # Storage service
    "StorageService",
    "get_storage_service",
    # Task service
    "TaskService",
    "PROGRESS_STAGES",
]