"""
ScholarAI Python AI Service

基于FastAPI的AI服务，提供：
- PDF解析 (Docling)
- RAG问答 (PaperQA2)
- 实体抽取
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import health, parse, rag, entities, papers, internal, search, notes, compare, graph
from app.core.config import settings
from app.core.logging import setup_logging
from app.core.database import init_databases, close_databases
from app.utils.logger import logger
from app.core.milvus_service import get_milvus_service
from app.core.reranker_service import get_reranker_service


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
        logger.info("ReRanker model loaded", model=reranker_service.MODEL_NAME)
    except Exception as e:
        logger.error("Failed to initialize ReRanker", error=str(e))
        # Don't fail startup - ReRanker is optional for basic functionality
        app.state.reranker_service = None

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


@app.get("/")
async def root():
    """根路径"""
    return {
        "service": "ScholarAI AI Service",
        "version": "1.0.0",
        "docs": "/docs",
        "status": "running"
    }
