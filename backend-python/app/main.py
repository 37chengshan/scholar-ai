"""
ScholarAI Python AI Service

基于FastAPI的AI服务，提供：
- PDF解析 (Docling)
- RAG问答 (PaperQA2)
- 实体抽取
"""

# Set HuggingFace offline mode before importing any ML libraries
import os
os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['TRANSFORMERS_OFFLINE'] = '1'

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import health, parse, rag, entities, papers, internal, search, notes, compare, graph, session, chat, tasks, semantic_scholar
from app.core.config import settings
from app.core.logging import setup_logging
from app.core.database import init_databases, close_databases
from app.utils.logger import logger
from app.core.milvus_service import get_milvus_service
from app.core.reranker.factory import get_reranker_service  # Updated to use factory
from app.core.embedding.factory import get_embedding_service  # Updated to use factory
from fastapi.exceptions import RequestValidationError
from app.middleware.error_handler import (
    validation_exception_handler,
    generic_exception_handler
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动
    setup_logging()
    logger.info("🤖 ScholarAI AI Service starting...")
    logger.info(f"📚 Log level: {settings.LOG_LEVEL}")
    logger.info(f"🔗 Database: {settings.DATABASE_URL}")
    logger.info(f"🕸️  Neo4j: {settings.NEO4J_URI}")
    logger.info(f"⚡ Redis: {settings.REDIS_URL}")

    # 初始化数据库连接
    await init_databases()

    # Initialize Milvus
    try:
        logger.info("Initializing Milvus...")
        milvus_service = get_milvus_service()
        milvus_service.connect()
        milvus_service.create_collections()
        app.state.milvus_service = milvus_service
        logger.info("Milvus initialized successfully")
    except Exception as e:
        logger.error("Failed to initialize Milvus", error=str(e))
        # Don't fail startup - Milvus is optional for basic functionality
        app.state.milvus_service = None

    # Initialize ReRanker
    try:
        logger.info("Initializing ReRanker...")
        reranker_service = get_reranker_service()
        reranker_service.load_model()
        app.state.reranker_service = reranker_service
        model_info = reranker_service.get_model_info()
        logger.info("ReRanker model loaded", model=model_info.get("name", "unknown"))
    except Exception as e:
        logger.error("Failed to initialize ReRanker", error=str(e))
        # Don't fail startup - ReRanker is optional for basic functionality
        app.state.reranker_service = None

    # Initialize Embedding Service (via factory)
    try:
        logger.info("Initializing Embedding Service...")
        embedding_service = get_embedding_service()
        embedding_service.load_model()
        app.state.embedding_service = embedding_service
        model_info = embedding_service.get_model_info()
        logger.info(
            "Embedding model loaded",
            model=model_info.get("name", "unknown"),
            type=model_info.get("type", "unknown"),
            dimension=model_info.get("dimension", "unknown")
        )
    except Exception as e:
        logger.error("Failed to initialize Embedding Service", error=str(e))
        # Don't fail startup - Embedding is optional for basic functionality
        app.state.embedding_service = None

    yield

    # 关闭
    logger.info("🛑 ScholarAI AI Service shutting down...")

    # Disconnect Milvus
    if hasattr(app.state, 'milvus_service') and app.state.milvus_service:
        try:
            app.state.milvus_service.disconnect()
            logger.info("Milvus disconnected")
        except Exception as e:
            logger.warning("Error disconnecting Milvus", error=str(e))

    await close_databases()


app = FastAPI(
    title="ScholarAI AI Service",
    description="AI services for ScholarAI - PDF parsing, RAG Q&A, Entity extraction",
    version="1.0.0",
    lifespan=lifespan
)

# Register exception handlers
app.add_exception_handler(RequestValidationError, validation_exception_handler)
# Don't add generic handler in development - let FastAPI show tracebacks
# In production, uncomment:
# app.add_exception_handler(Exception, generic_exception_handler)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_HOSTS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 路由
app.include_router(health.router, prefix="/health", tags=["Health"])
app.include_router(papers.router, prefix="/papers", tags=["Papers"])
app.include_router(notes.router, prefix="/notes", tags=["Notes"])
app.include_router(parse.router, prefix="/parse", tags=["PDF Parsing"])
app.include_router(rag.router, prefix="/rag", tags=["RAG Q&A"])
app.include_router(entities.router, prefix="/entities", tags=["Entity Extraction"])
app.include_router(internal.router, prefix="/internal", tags=["Internal API"])
app.include_router(search.router, prefix="/search", tags=["External Search"])
app.include_router(compare.router, prefix="/compare", tags=["Comparison"])
app.include_router(graph.router, prefix="/api/graph", tags=["Graph"])
app.include_router(session.router, prefix="/api", tags=["Session"])
app.include_router(chat.router, prefix="/api", tags=["Chat"])
app.include_router(tasks.router, tags=["Tasks"])
app.include_router(semantic_scholar.router, prefix="/semantic-scholar", tags=["Semantic Scholar"])


@app.get("/")
async def root():
    """根路径"""
    return {
        "service": "ScholarAI AI Service",
        "version": "1.0.0",
        "docs": "/docs",
        "status": "running"
    }
