"""
ScholarAI Unified FastAPI Backend

Provides complete API services for ScholarAI:
- OAuth 2.0 + Cookie-based Authentication
- User management
- Paper CRUD operations
- PDF upload and processing
- Task management
- Notes, Projects, Annotations
- Reading progress tracking
- Dashboard statistics
- External search integration
- Semantic Scholar integration
- Session management
- Chat with SSE streaming
- Entity extraction
- Knowledge graph
- Paper comparison
- RAG Q&A
- System diagnostics

Wave 4 Integration - Unified backend replacing Node.js + Python split architecture.
"""

# Set default HuggingFace mode before importing any ML libraries
import os

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

from contextlib import asynccontextmanager
from typing import Optional, Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# API Routes - Wave 1-3 routers
from app.api import (
    # Wave 1 (27-02): Auth
    auth,
    # Wave 2 (27-03a): Users
    users,
    # Wave 2 (27-03b): Papers, Uploads, Tasks
    uploads,
    tasks,
    # Wave 3 (27-04): Extended APIs
    notes,
    projects,
    annotations,
    reading_progress,
    dashboard,
    search,
    semantic_scholar,
    session,
    chat,
    entities,
    graph,
    compare,
    system,
    # Legacy/Python-specific routes
    health,
    parse,
    rag,
    token_usage,
)

# Wave 2: Papers (split per 38-05)
from app.api.papers import router as papers_router

from app.config import settings
from app.core.logging import setup_logging
from app.core.database import init_databases, close_databases
from app.database import (
    init_sqlalchemy_engine,
    ensure_non_production_tables,
    close_sqlalchemy_engine,
)
from app.utils.logger import logger
from app.core.milvus_service import get_milvus_service
from app.core.reranker.factory import get_reranker_service
from app.core.embedding.factory import get_embedding_service
from app.utils.preflight import run_preflight

# Middleware
from app.middleware.cors import get_cors_config
from app.middleware.observability import ObservabilityMiddleware
from app.middleware.logging import RequestLoggingMiddleware
from app.middleware.error_handler import setup_error_handlers


# ============================================================================
# Lazy Initialization Helpers
# ============================================================================


async def get_app_milvus_service(app) -> Optional[Any]:
    """Get or lazily initialize Milvus service."""
    if app.state.milvus_service is None:
        try:
            logger.info("Initializing Milvus (lazy)...")
            milvus_service = get_milvus_service()
            milvus_service.connect()
            milvus_service.create_collections()
            app.state.milvus_service = milvus_service
            logger.info("Milvus initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Milvus: {e}")
            return None
    return app.state.milvus_service


async def get_app_reranker_service(app) -> Optional[Any]:
    """Get or lazily initialize ReRanker service."""
    if app.state.reranker_service is None:
        try:
            logger.info("Initializing ReRanker (lazy)...")
            reranker_service = get_reranker_service()
            reranker_service.load_model()
            app.state.reranker_service = reranker_service
            logger.info("ReRanker initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize ReRanker: {e}")
            return None
    return app.state.reranker_service


async def get_app_embedding_service(app) -> Optional[Any]:
    """Get or lazily initialize Embedding service."""
    if app.state.embedding_service is None:
        try:
            logger.info("Initializing Embedding (lazy)...")
            embedding_service = get_embedding_service()
            embedding_service.load_model()
            app.state.embedding_service = embedding_service
            logger.info("Embedding initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Embedding: {e}")
            return None
    return app.state.embedding_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动
    setup_logging()

    # Validate production settings
    try:
        settings.validate_production_settings()
        logger.info("✅ Security settings validated")
    except ValueError as e:
        logger.error(f"❌ Security validation failed: {e}")
        raise

    logger.info("🤖 ScholarAI AI Service starting...")
    logger.info(f"🧭 Runtime profile: {settings.RUNTIME_PROFILE}")
    logger.info(f"⚙️ AI startup mode: {settings.AI_STARTUP_MODE}")
    logger.info(f"📚 Log level: {settings.LOG_LEVEL}")
    logger.info(f"🔗 Database: {settings.DB_HOST}")
    logger.info(f"🕸️  Neo4j: {settings.NEO4J_HOST}")
    logger.info(f"⚡ Redis: {settings.REDIS_HOST}")

    # 1. SQLAlchemy PostgreSQL (首先初始化)
    try:
        await init_sqlalchemy_engine()
        logger.info("✅ SQLAlchemy PostgreSQL initialized")
    except Exception as e:
        logger.error(f"❌ SQLAlchemy initialization failed: {e}")
        raise

    try:
        await ensure_non_production_tables(
            ("knowledge_base_papers", "import_batches", "import_jobs")
        )
    except Exception as e:
        logger.error(f"❌ Non-production schema bootstrap failed: {e}")
        raise

    # 2. Neo4j + Redis
    await init_databases()

    if settings.PREFLIGHT_ON_STARTUP:
        preflight_report = run_preflight(strict=True)
        logger.info(
            "✅ Startup preflight passed",
            profile=preflight_report.get("profile"),
            ai_startup_mode=preflight_report.get("ai_startup_mode"),
        )

    app.state.runtime_profile = settings.RUNTIME_PROFILE
    app.state.ai_startup_mode = settings.AI_STARTUP_MODE
    app.state.milvus_service = None
    app.state.embedding_service = None
    app.state.reranker_service = None

    if settings.AI_STARTUP_MODE == "off":
        logger.warning("AI startup mode is off; AI services will not initialize automatically")
    elif settings.AI_STARTUP_MODE == "lazy":
        logger.info("AI startup mode is lazy; AI services will initialize on-demand")
    else:
        logger.info("AI startup mode is eager; initializing AI services at startup")

    if settings.AI_STARTUP_MODE == "eager":
        # 1. Embedding Service (Qwen3-VL-Embedding-2B)
        try:
            logger.info("Loading Embedding model...")
            embedding_service = get_embedding_service()
            embedding_service.load_model()
            app.state.embedding_service = embedding_service
            logger.info("✅ Embedding model loaded successfully")
        except Exception as e:
            logger.error(f"❌ Failed to load Embedding model: {e}")

        # 2. Reranker Service (Qwen3-VL-Reranker-2B)
        try:
            logger.info("Loading ReRanker model...")
            reranker_service = get_reranker_service()
            reranker_service.load_model()
            app.state.reranker_service = reranker_service
            logger.info("✅ ReRanker model loaded successfully")
        except Exception as e:
            logger.error(f"❌ Failed to load ReRanker model: {e}")

    app.state.ai_services_initialized = True

    yield

    # 关闭
    logger.info("🛑 ScholarAI AI Service shutting down...")

    # Disconnect Milvus
    if hasattr(app.state, "milvus_service") and app.state.milvus_service:
        try:
            app.state.milvus_service.disconnect()
            logger.info("Milvus disconnected")
        except Exception as e:
            logger.warning("Error disconnecting Milvus", error=str(e))

    # Neo4j + Redis
    await close_databases()

    # SQLAlchemy PostgreSQL (最后关闭)
    await close_sqlalchemy_engine()
    logger.info("Database connections closed")


app = FastAPI(
    title="ScholarAI Unified API",
    description="Complete API services for ScholarAI - Authentication, Papers, Chat, RAG, Knowledge Graph",
    version="1.0.0",
    lifespan=lifespan,
)

# ============================================================================
# Middleware Registration
# ============================================================================

# Observability middleware (first - binds request context)
app.add_middleware(ObservabilityMiddleware)

# Request logging middleware
app.add_middleware(RequestLoggingMiddleware)

# CORS middleware (use unified config)
app.add_middleware(CORSMiddleware, **get_cors_config())

# Error handlers (RFC 7807 format)
setup_error_handlers(app, include_generic=settings.ENVIRONMENT == "production")

# ============================================================================
# Router Registration - API v1 Routes
# ============================================================================

# Wave 1: Authentication (27-02)
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])

# Wave 2: Users (27-03a)
app.include_router(users.router, prefix="/api/v1/users", tags=["users"])

# Wave 2: Papers, Uploads, Tasks (27-03b)
app.include_router(papers_router, prefix="/api/v1/papers", tags=["papers"])
app.include_router(uploads.router, prefix="/api/v1/uploads", tags=["uploads"])
app.include_router(tasks.router, prefix="/api/v1/tasks", tags=["tasks"])

# Wave 3: Notes, Projects, Annotations, Reading Progress (27-04)
app.include_router(notes.router, prefix="/api/v1/notes", tags=["notes"])
app.include_router(projects.router, prefix="/api/v1/projects", tags=["projects"])
app.include_router(
    annotations.router, prefix="/api/v1/annotations", tags=["annotations"]
)
app.include_router(
    reading_progress.router,
    prefix="/api/v1/reading-progress",
    tags=["reading-progress"],
)

# Wave 3: Knowledge Base (36-02)
# Split per38-05: KB module (kb_crud + kb_import  kb_search  kb_query)
from app.api.kb import router as kb_router

app.include_router(
    kb_router,
    prefix="/api/v1/knowledge-bases",
    tags=["knowledge-bases"],
)

# Wave 1: ImportJob (41-01) - Unified import system
from app.api.imports import router as imports_router

app.include_router(
    imports_router,
    prefix="/api/v1",
    tags=["imports"],
)

# Wave 3: Dashboard, Search, System (27-04)
app.include_router(dashboard.router, prefix="/api/v1/dashboard", tags=["dashboard"])
app.include_router(search.router, prefix="/api/v1/search", tags=["search"])
app.include_router(system.router, prefix="/api/v1/system", tags=["system"])

# Wave 3: Semantic Scholar, Session, Chat (27-04)
app.include_router(
    semantic_scholar.router,
    prefix="/api/v1/semantic-scholar",
    tags=["semantic-scholar"],
)
app.include_router(session.router, prefix="/api/v1/sessions", tags=["session"])
app.include_router(chat.router, prefix="/api/v1/chat", tags=["chat"])

# Wave 3: Entities, Graph, Compare (27-04)
app.include_router(entities.router, prefix="/api/v1/entities", tags=["entities"])
app.include_router(graph.router, prefix="/api/v1/graph", tags=["graph"])
app.include_router(compare.router, prefix="/api/v1/compare", tags=["compare"])

# ============================================================================
# Legacy/Python-specific Routes (keep for backward compatibility)
# ============================================================================

# RAG Q&A - Python-specific AI service
app.include_router(rag.router, prefix="/api/v1/queries", tags=["queries"])

# PDF Parsing - Python-specific AI service
app.include_router(parse.router, prefix="/parse", tags=["pdf-parsing"])

# Token Usage - Monitoring
app.include_router(
    token_usage.router, prefix="/api/v1/token-usage", tags=["token-usage"]
)

# ============================================================================
# Health Check - No auth required
# ============================================================================

app.include_router(health.router, prefix="/health", tags=["health"])


# ============================================================================
# Root Endpoint
# ============================================================================


@app.get("/")
async def root():
    """Root endpoint - API info."""
    return {
        "service": "ScholarAI Unified API",
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc",
        "health": "/health",
        "status": "running",
    }
