"""ScholarAI Unified FastAPI Application Package.

This package contains the complete FastAPI backend for ScholarAI:
- API routes (20+ routers)
- SQLAlchemy models
- Business services
- Middleware (auth, CORS, logging, errors)
- Core AI services
- Background workers

Usage:
    # Start the server
    uvicorn app.main:app --reload

    # Import in tests
    from app.main import app
    from app.config import settings
    from app.deps import get_db, get_current_user
"""

from app.main import app
from app.config import settings, get_settings

__all__ = [
    "app",
    "settings",
    "get_settings",
]